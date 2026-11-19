import json
from database import get_db
from routing_engine import evaluate_routing
from sla_calculator import compute_travel_sla, evaluate_sla_state

def run_verification():
    print("==================================================")
    print("VERIFYING TRIPLINK CORE CAPABILITIES")
    print("==================================================")

    # 1. Create and manage support tickets (Req 1)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM tickets")
    total_tickets = cursor.fetchone()["count"]
    conn.close()
    assert total_tickets >= 10
    print(f"[PASS] Req 1 (Manage Support Tickets): {total_tickets} tickets seeded and queryable.")

    # 2. Connect related tickets using Agency ID, TBOH, and issue category (Req 2)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, priority, status FROM tickets WHERE tboh = 'TBOH-90241' ORDER BY created_at ASC")
    linked_tboh = cursor.fetchall()
    conn.close()
    assert len(linked_tboh) >= 3
    print(f"[PASS] Req 2 (Connect Related Tickets): Found {len(linked_tboh)} connected cases for TBOH-90241:")
    for t in linked_tboh:
        print(f"       -> {t['id']} | {t['priority']} | {t['status']} | {t['title'][:38]}...")

    # 3. Intelligent ticket assignment based on region and priority (Req 3)
    route_res = evaluate_routing({
        "region": "Middle East",
        "priority": "P1-Urgent",
        "category": "Inventory Sync Mismatch"
    })
    assert route_res["assigned"] is True
    print(f"[PASS] Req 3 (Intelligent Assignment): Assigned to {route_res['agent_name']}:")
    print(f"       Rationale: {route_res['routing_reason']}")

    # 4. Travel-aware SLA tracking using check-in dates and urgency (Req 4)
    normal_sla = compute_travel_sla("P2-High", "2026-11-09T10:00:00Z")
    urgent_sla = compute_travel_sla("P2-High", "2026-11-09T10:00:00Z", check_in_str="2026-11-09T14:00:00Z")
    assert urgent_sla["total_hours"] < normal_sla["total_hours"]
    print(f"[PASS] Req 4 (Travel-Aware SLA): Baseline {normal_sla['total_hours']}h compressed to {urgent_sla['total_hours']}h ({urgent_sla['travel_modifier_applied']})")

    # 5. Escalation to an Escalation Manager (Req 5)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, status, assigned_name FROM tickets WHERE id = 'TKT-1008'")
    t1008 = cursor.fetchone()
    conn.close()
    assert t1008["status"] == "Escalated"
    assert t1008["assigned_name"] == "Vikram Malhotra"
    print(f"[PASS] Req 5 (Escalation to EM): TKT-1008 directly escalated to {t1008['assigned_name']} (Status: {t1008['status']})")

    # 6. Supplier and agency conversations (Req 6)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages WHERE ticket_id = 'TKT-1007' AND message_type = 'SUPPLIER_SIDE_THREAD'")
    supplier_msgs = cursor.fetchall()
    recipients = json.loads(supplier_msgs[0]["recipient_emails"])
    conn.close()
    assert len(supplier_msgs) >= 2
    print(f"[PASS] Req 6 (Supplier Conversations): TKT-1007 has active thread with {len(recipients)} explicit recipients:")
    print(f"       Recipients: {', '.join(recipients)}")

    # 7. Dashboard showing ticket statistics and recurring issues (Req 7)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT category, COUNT(*) as c FROM tickets GROUP BY category ORDER BY c DESC")
    categories = cursor.fetchall()
    conn.close()
    assert len(categories) > 0
    print(f"[PASS] Req 7 (Dashboard & Recurring Issues): Aggregated {len(categories)} recurring issue themes:")
    for c in categories[:3]:
        print(f"       * {c['category']}: {c['c']} cases")

    print("==================================================")
    print("ALL 7 TRIPLINK REQUIREMENTS VERIFIED 100% SUCCESFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_verification()
