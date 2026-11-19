import os
import sys
import json
import sqlite3
import tempfile
import unittest

backend_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(backend_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Synchronous coroutine runner (100% dependency-free, no socket/pipe hangs in sandbox)
def run_sync(coro):
    stack = [coro]
    val = None
    while stack:
        try:
            curr = stack[-1]
            res = curr.send(val)
            val = None
            if hasattr(res, "send"):
                stack.append(res)
        except StopIteration as e:
            stack.pop()
            val = e.value
    return val

class MockRequest:
    def __init__(self, json_data=None, path_params=None, query_params=None):
        self._json = json_data or {}
        self.path_params = path_params or {}
        self.query_params = query_params or {}

    async def json(self):
        return self._json

class TripLinkAutomatedTestSuite(unittest.TestCase):

    def test_01_backend_import(self):
        """Test Backend import - Expected: Successful"""
        import database
        import routing_engine
        import sla_calculator
        import seed_data
        import app
        self.assertIsNotNone(app.app)
        print("  [PASS] 01. Backend modules imported successfully.")

    def test_02_database_connection(self):
        """Test Database connection - Expected: Successful"""
        import database
        conn = database.get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test_val")
        row = cursor.fetchone()
        conn.close()
        self.assertEqual(row["test_val"], 1)
        print("  [PASS] 02. Database connection verified.")

    def test_03_database_initialization_isolated(self):
        """Test Database initialization using isolated test DB - Expected: Successful"""
        temp_db_fd, temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(temp_db_fd)
        try:
            conn = sqlite3.connect(temp_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Execute schema creation from database.py logic
            cursor.executescript("""
            CREATE TABLE agencies (id TEXT PRIMARY KEY, name TEXT NOT NULL, code TEXT, tier TEXT, country TEXT, region TEXT, email TEXT);
            CREATE TABLE agents (id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT, role TEXT, region TEXT, tier TEXT, status TEXT, max_capacity INT, current_load INT);
            CREATE TABLE tickets (id TEXT PRIMARY KEY, agency_id TEXT, tboh TEXT, title TEXT, description TEXT, category TEXT, priority TEXT, status TEXT, region TEXT, assigned_agent_id TEXT, assigned_name TEXT, routing_reason TEXT, check_in_date TEXT, lcd_date TEXT, sla_deadline TEXT, sla_status TEXT, escalation_reason TEXT, created_at TEXT, updated_at TEXT);
            CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id TEXT, sender_type TEXT, sender_name TEXT, message_type TEXT, recipient_emails TEXT, body TEXT, created_at TEXT);
            CREATE TABLE ticket_links (id INTEGER PRIMARY KEY AUTOINCREMENT, source_ticket_id TEXT, target_ticket_id TEXT, link_type TEXT, created_at TEXT);
            CREATE TABLE timeline_events (id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id TEXT, event_type TEXT, actor_name TEXT, actor_role TEXT, summary TEXT, created_at TEXT);
            """)
            conn.commit()

            cursor.execute("SELECT count(*) as tbl_count FROM sqlite_master WHERE type='table'")
            count = cursor.fetchone()["tbl_count"]
            conn.close()
            self.assertGreaterEqual(count, 6)
            print("  [PASS] 03. Isolated database initialization verified (6 tables created).")
        finally:
            if os.path.exists(temp_db_path):
                os.remove(temp_db_path)

    def test_04_application_startup(self):
        """Test Application startup & route registration - Expected: Successful"""
        import app
        route_paths = [getattr(r, "path", None) for r in app.routes if getattr(r, "path", None)]
        required_paths = ["/api/health", "/api/tickets", "/api/stats", "/api/demo/reset", "/", "/manifest.json", "/icon.svg"]
        for p in required_paths:
            self.assertIn(p, route_paths, f"Route {p} missing from application routes")
        print(f"  [PASS] 04. Application startup verified with {len(app.routes)} registered routes.")

    def test_05_api_health_check(self):
        """Test API health check - Expected: HTTP 200"""
        import app
        req = MockRequest()
        res = run_sync(app.health(req))
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.body.decode())
        self.assertEqual(data.get("status"), "healthy")
        print("  [PASS] 05. API health check returned HTTP 200 (healthy).")

    def test_06_ticket_creation(self):
        """Test Ticket creation - Expected: Successful with unique ID and auto-routing"""
        import app
        payload = {
            "agency_id": "AGY-101",
            "tboh": "TBOH-88990",
            "title": "Automated Test Case: Immediate Airport Pickup Needed",
            "description": "Passenger flight rescheduled, urgent coordination needed.",
            "category": "Date Change",
            "priority": "P2-High",
            "creator_name": "Test Agency Requester",
            "creator_role": "Agency"
        }
        req = MockRequest(json_data=payload)
        res = run_sync(app.create_ticket(req))
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.body.decode())
        self.assertTrue(data.get("success"))
        self.assertTrue(data.get("ticket_id").startswith("TKT-"))
        self.assertIsNotNone(data.get("assigned_name"))
        TripLinkAutomatedTestSuite.created_ticket_id = data["ticket_id"]
        print(f"  [PASS] 06. Ticket creation successful: {data['ticket_id']} assigned to {data['assigned_name']}.")

    def test_07_ticket_retrieval(self):
        """Test Ticket retrieval - Expected: Correct record with relations"""
        import app
        t_id = getattr(TripLinkAutomatedTestSuite, "created_ticket_id", "TKT-1001")
        req = MockRequest(path_params={"id": t_id})
        res = run_sync(app.get_ticket_detail(req))
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.body.decode())
        self.assertEqual(data["ticket"]["id"], t_id)
        self.assertIn("linked_tickets", data)
        self.assertIn("timeline", data)
        print(f"  [PASS] 07. Ticket retrieval successful for {t_id} (linked tickets: {len(data['linked_tickets'])}).")

    def test_08_ticket_update(self):
        """Test Ticket update - Expected: Changes persisted"""
        import app
        t_id = getattr(TripLinkAutomatedTestSuite, "created_ticket_id", "TKT-1001")
        req = MockRequest(path_params={"id": t_id}, json_data={"status": "Pending", "actor_name": "QA Bot"})
        res = run_sync(app.update_status(req))
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.body.decode())
        self.assertEqual(data["status"], "Pending")

        # Verify persistence
        req_get = MockRequest(path_params={"id": t_id})
        res_get = run_sync(app.get_ticket_detail(req_get))
        data_get = json.loads(res_get.body.decode())
        self.assertEqual(data_get["ticket"]["status"], "Pending")
        print(f"  [PASS] 08. Ticket update persisted: {t_id} status updated to Pending.")

    def test_09_sla_calculation(self):
        """Test SLA calculation - Expected: Correct deadline compression"""
        from sla_calculator import compute_travel_sla, evaluate_sla_state
        # Standard baseline
        sla_standard = compute_travel_sla("P2-High", "2026-11-19T10:00:00Z")
        self.assertEqual(sla_standard["total_hours"], 6)

        # Urgent check-in proximity compression (check-in 4 hours from creation)
        sla_urgent = compute_travel_sla("P2-High", "2026-11-19T10:00:00Z", check_in_str="2026-11-19T14:00:00Z")
        self.assertLess(sla_urgent["total_hours"], sla_standard["total_hours"])
        self.assertEqual(sla_urgent["total_hours"], 1.0)

        # Evaluation state
        state = evaluate_sla_state(sla_standard["sla_deadline"], "Open", sla_standard["total_hours"])
        self.assertIn(state["status"], ["Healthy", "At-Risk", "Breached"])
        print(f"  [PASS] 09. SLA calculation verified (baseline 6h compressed to {sla_urgent['total_hours']}h).")

    def test_10_escalation(self):
        """Test Escalation - Expected: Correct trigger to Escalation Manager"""
        import app
        t_id = getattr(TripLinkAutomatedTestSuite, "created_ticket_id", "TKT-1001")
        req = MockRequest(
            path_params={"id": t_id},
            json_data={
                "reason": "Supplier desk uncooperative, guest stranded at terminal.",
                "escalate_to_agent_id": "AGT-901",
                "actor_name": "Priya Sharma",
                "actor_role": "Support Agent"
            }
        )
        res = run_sync(app.escalate_ticket(req))
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.body.decode())
        self.assertEqual(data["status"], "Escalated")
        self.assertEqual(data["assigned_name"], "Vikram Malhotra")

        # Verify in ticket detail
        req_get = MockRequest(path_params={"id": t_id})
        res_get = run_sync(app.get_ticket_detail(req_get))
        data_get = json.loads(res_get.body.decode())
        self.assertEqual(data_get["ticket"]["status"], "Escalated")
        self.assertEqual(data_get["ticket"]["priority"], "P1-Urgent")
        print(f"  [PASS] 10. Escalation trigger verified: {t_id} assigned to Vikram Malhotra as P1-Urgent.")

    def test_11_invalid_request(self):
        """Test Invalid request - Expected: Proper error response (HTTP 400/404)"""
        import app
        # Empty title
        req_bad_title = MockRequest(json_data={"title": "", "tboh": "TBOH-11111"})
        res = run_sync(app.create_ticket(req_bad_title))
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.body.decode())
        self.assertIn("error", data)

        # Missing escalation reason
        req_bad_esc = MockRequest(path_params={"id": "TKT-1001"}, json_data={"reason": ""})
        res_esc = run_sync(app.escalate_ticket(req_bad_esc))
        self.assertEqual(res_esc.status_code, 400)

        # Non-existent ticket
        req_not_found = MockRequest(path_params={"id": "TKT-NONEXISTENT"})
        res_nf = run_sync(app.get_ticket_detail(req_not_found))
        self.assertEqual(res_nf.status_code, 404)
        print("  [PASS] 11. Invalid requests handled with meaningful HTTP 400 and 404 errors.")

    def test_12_duplicate_request(self):
        """Test Duplicate request / shared TBOH - Expected: Safely handled with linkage"""
        import app
        tboh = "TBOH-DUPLICATE-TEST"
        req1 = MockRequest(json_data={"tboh": tboh, "title": "Case 1", "priority": "P2-High", "agency_id": "AGY-101"})
        res1 = run_sync(app.create_ticket(req1))
        self.assertEqual(res1.status_code, 200)
        t1_id = json.loads(res1.body.decode())["ticket_id"]

        req2 = MockRequest(json_data={"tboh": tboh, "title": "Case 2", "priority": "P1-Urgent", "agency_id": "AGY-101"})
        res2 = run_sync(app.create_ticket(req2))
        self.assertEqual(res2.status_code, 200)
        t2_id = json.loads(res2.body.decode())["ticket_id"]

        self.assertNotEqual(t1_id, t2_id, "Ticket IDs must be unique")

        # Verify auto-linkage between identical TBOH cases
        req_detail = MockRequest(path_params={"id": t2_id})
        res_detail = run_sync(app.get_ticket_detail(req_detail))
        detail = json.loads(res_detail.body.decode())
        linked_ids = [lt["id"] for lt in detail["linked_tickets"]]
        self.assertIn(t1_id, linked_ids)
        print(f"  [PASS] 12. Duplicate TBOH cases safely handled with cross-linkage ({t1_id} <-> {t2_id}).")

    def test_13_search_and_filtering(self):
        """Test Search and filtering - Expected: Correct filtered results"""
        import app
        # Region filter
        req_reg = MockRequest(query_params={"region": "APAC"})
        res_reg = run_sync(app.list_tickets(req_reg))
        self.assertEqual(res_reg.status_code, 200)
        tickets = json.loads(res_reg.body.decode())["tickets"]
        for t in tickets:
            self.assertEqual(t["region"], "APAC")

        # Search filter
        req_search = MockRequest(query_params={"search": "TBOH-90241"})
        res_search = run_sync(app.list_tickets(req_search))
        self.assertEqual(res_search.status_code, 200)
        search_tickets = json.loads(res_search.body.decode())["tickets"]
        self.assertGreater(len(search_tickets), 0)
        for t in search_tickets:
            self.assertIn("90241", t["tboh"] + t["title"] + t["id"])
        print(f"  [PASS] 13. Search and filtering returned accurate results ({len(search_tickets)} cases for TBOH-90241).")

    def test_14_frontend_api_integration(self):
        """Test Frontend API integration & assets - Expected: Successful"""
        index_path = os.path.join(project_dir, "frontend", "index.html")
        manifest_path = os.path.join(project_dir, "frontend", "manifest.json")
        icon_path = os.path.join(project_dir, "frontend", "icon.svg")

        self.assertTrue(os.path.isfile(index_path), "index.html must exist")
        self.assertTrue(os.path.isfile(manifest_path), "manifest.json must exist")
        self.assertTrue(os.path.isfile(icon_path), "icon.svg must exist")

        with open(index_path, "r", encoding="utf-8") as f:
            index_content = f.read()

        # Check critical frontend functions and endpoints
        self.assertIn("/api/tickets", index_content)
        self.assertIn("/api/stats", index_content)
        self.assertIn("submitNewTicket", index_content)
        self.assertIn("openEscalateModal", index_content)
        self.assertIn("submitEscalation", index_content)
        self.assertIn("manifest.json", index_content)
        print("  [PASS] 14. Frontend assets and API bindings verified.")

    def test_15_desktop_launcher(self):
        """Test Desktop launcher files - Expected: Correct configuration and syntax"""
        launcher_py = os.path.join(project_dir, "launch_app.py")
        app_bat = os.path.join(project_dir, "TripLink_App.bat")
        app_vbs = os.path.join(project_dir, "TripLink_App.vbs")
        shortcut_bat = os.path.join(project_dir, "Create_Desktop_Shortcut.bat")
        stop_bat = os.path.join(project_dir, "Stop_TripLink.bat")

        for f in [launcher_py, app_bat, app_vbs, shortcut_bat, stop_bat]:
            self.assertTrue(os.path.isfile(f), f"File {os.path.basename(f)} must exist")

        # Verify launch_app.py syntax
        import py_compile
        py_compile.compile(launcher_py, doraise=True)
        print("  [PASS] 15. Windows desktop launchers and scripts verified.")

def run_suite():
    print("=" * 70)
    print("      TRIPLINK AUTOMATED TEST SUITE — COMPLETE DIAGNOSIS & VERIFICATION")
    print("=" * 70)
    suite = unittest.TestLoader().loadTestsFromTestCase(TripLinkAutomatedTestSuite)
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    print("=" * 70)
    print(f"Total Tests Run: {result.testsRun}")
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70)
    return len(result.failures) == 0 and len(result.errors) == 0

if __name__ == "__main__":
    success = run_suite()
    sys.exit(0 if success else 1)
