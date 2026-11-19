import os
import json
from datetime import datetime, timezone
from starlette.applications import Starlette
from starlette.responses import JSONResponse, FileResponse
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from database import get_db, init_db
from routing_engine import evaluate_routing
from sla_calculator import compute_travel_sla, evaluate_sla_state
from seed_data import seed_database

async def health(request):
    return JSONResponse({"status": "healthy", "service": "TripLink for TBO", "version": "1.0.0"})

async def get_users(request):
    demo_users = [
        {
            "id": "AGY-101",
            "name": "Rajesh Kumar",
            "role": "Agency Requester",
            "label": "Rajesh Kumar (Agency - Apex Travels)",
            "agency_id": "AGY-101",
            "avatar": "👤"
        },
        {
            "id": "AGT-201",
            "name": "Priya Sharma",
            "role": "Support Agent",
            "label": "Priya Sharma (Support Agent - APAC)",
            "region": "APAC",
            "tier": "Tier-2",
            "avatar": "🎧"
        },
        {
            "id": "AGT-901",
            "name": "Vikram Malhotra",
            "role": "Escalation Manager",
            "label": "Vikram Malhotra (Escalation Manager)",
            "region": "Global",
            "tier": "Lead",
            "avatar": "⚡"
        },
        {
            "id": "AGT-902",
            "name": "Neha Gupta",
            "role": "Ops Lead",
            "label": "Neha Gupta (Ops Lead / Governance)",
            "region": "Global",
            "tier": "Lead",
            "avatar": "📊"
        }
    ]
    return JSONResponse({"users": demo_users})

async def list_agencies(request):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agencies")
        rows = [dict(r) for r in cursor.fetchall()]
        return JSONResponse({"agencies": rows})
    finally:
        conn.close()

async def list_agents(request):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agents")
        rows = [dict(r) for r in cursor.fetchall()]
        return JSONResponse({"agents": rows})
    finally:
        conn.close()

async def get_stats(request):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM tickets")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as unassigned FROM tickets WHERE (assigned_agent_id IS NULL OR assigned_agent_id = '') AND status != 'Closed'")
        unassigned = cursor.fetchone()["unassigned"]

        cursor.execute("SELECT COUNT(*) as escalated FROM tickets WHERE status = 'Escalated'")
        escalated = cursor.fetchone()["escalated"]

        cursor.execute("SELECT COUNT(*) as at_risk FROM tickets WHERE sla_status = 'At-Risk' AND status NOT IN ('Resolved', 'Closed')")
        at_risk = cursor.fetchone()["at_risk"]

        cursor.execute("SELECT COUNT(*) as breached FROM tickets WHERE sla_status = 'Breached' AND status NOT IN ('Resolved', 'Closed')")
        breached = cursor.fetchone()["breached"]

        cursor.execute("SELECT COUNT(*) as resolved FROM tickets WHERE status IN ('Resolved', 'Closed')")
        resolved = cursor.fetchone()["resolved"]

        compliance_rate = round(((total - breached) / max(1, total)) * 100, 1)

        return JSONResponse({
            "total": total,
            "unassigned": unassigned,
            "escalated": escalated,
            "at_risk": at_risk,
            "breached": breached,
            "resolved": resolved,
            "compliance_rate": compliance_rate
        })
    finally:
        conn.close()

async def get_recurring_issues(request):
    # Requirement 7: Dashboard showing ticket statistics and recurring issues
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT 
            category,
            COUNT(*) as count,
            SUM(CASE WHEN sla_status = 'Breached' THEN 1 ELSE 0 END) as breached,
            SUM(CASE WHEN sla_status = 'At-Risk' THEN 1 ELSE 0 END) as at_risk
        FROM tickets
        GROUP BY category
        ORDER BY count DESC
        """)
        rows = [dict(r) for r in cursor.fetchall()]

        for r in rows:
            cursor.execute("SELECT id, tboh, title, priority, status FROM tickets WHERE category = ? LIMIT 3", (r["category"],))
            r["sample_tickets"] = [dict(t) for t in cursor.fetchall()]

        return JSONResponse({"recurring_issues": rows})
    finally:
        conn.close()

async def list_tickets(request):
    params = request.query_params
    view = params.get("view", "all")
    agency_id = params.get("agency_id", "")
    agent_id = params.get("agent_id", "")
    region = params.get("region", "")
    priority = params.get("priority", "")
    status_filter = params.get("status", "")
    sla_filter = params.get("sla_status", "")
    search = params.get("search", "").strip()

    conn = get_db()
    try:
        cursor = conn.cursor()

        query = """
        SELECT t.*, a.name as agency_name, a.code as agency_code, a.tier as agency_tier
        FROM tickets t
        LEFT JOIN agencies a ON t.agency_id = a.id
        WHERE 1=1
        """
        args = []

        # Role enforcement
        if agency_id:
            query += " AND t.agency_id = ?"
            args.append(agency_id)

        # View filters
        if view == "triage":
            query += " AND (t.assigned_agent_id IS NULL OR t.assigned_agent_id = '') AND t.status != 'Closed'"
        elif view == "my_queue":
            if agent_id:
                query += " AND t.assigned_agent_id = ? AND t.status NOT IN ('Resolved', 'Closed')"
                args.append(agent_id)
        elif view == "escalation":
            query += " AND (t.status = 'Escalated' OR t.assigned_agent_id = 'AGT-901')"
        elif view == "at_risk":
            query += " AND t.sla_status IN ('At-Risk', 'Breached') AND t.status NOT IN ('Resolved', 'Closed')"
        elif view == "tboh_demo":
            query += " AND t.tboh = 'TBOH-90241'"

        if region and region != "All":
            query += " AND t.region = ?"
            args.append(region)
        if priority and priority != "All":
            query += " AND t.priority = ?"
            args.append(priority)
        if status_filter and status_filter != "All":
            query += " AND t.status = ?"
            args.append(status_filter)
        if sla_filter and sla_filter != "All":
            query += " AND t.sla_status = ?"
            args.append(sla_filter)

        if search:
            search_like = f"%{search}%"
            query += " AND (t.id LIKE ? OR t.tboh LIKE ? OR t.title LIKE ? OR t.description LIKE ? OR a.name LIKE ?)"
            args.extend([search_like, search_like, search_like, search_like, search_like])

        query += """
        ORDER BY 
            CASE 
                WHEN t.status = 'Escalated' THEN 1
                WHEN t.sla_status = 'Breached' THEN 2
                WHEN t.sla_status = 'At-Risk' THEN 3
                ELSE 4
            END,
            t.created_at DESC
        """

        cursor.execute(query, args)
        tickets = [dict(r) for r in cursor.fetchall()]

        # Re-evaluate live dynamic SLA state for accuracy
        for t in tickets:
            sla_calc = compute_travel_sla(t["priority"], t["created_at"], t["check_in_date"], t["lcd_date"])
            state = evaluate_sla_state(sla_calc["sla_deadline"], t["status"], sla_calc["total_hours"])
            t["sla_status"] = state["status"]
            t["sla_remaining_str"] = state["time_remaining_str"]
            t["travel_modifier_applied"] = sla_calc["travel_modifier_applied"]

        return JSONResponse({"tickets": tickets, "count": len(tickets)})
    finally:
        conn.close()

async def get_ticket_detail(request):
    ticket_id = request.path_params["id"]
    conn = get_db()
    try:
        cursor = conn.cursor()

        cursor.execute("""
        SELECT t.*, a.name as agency_name, a.code as agency_code, a.tier as agency_tier, a.email as agency_email, a.country as agency_country
        FROM tickets t
        LEFT JOIN agencies a ON t.agency_id = a.id
        WHERE t.id = ?
        """, (ticket_id,))
        ticket_row = cursor.fetchone()

        if not ticket_row:
            return JSONResponse({"error": "Ticket not found"}, status_code=404)

        ticket = dict(ticket_row)

        # Dynamic SLA update
        sla_calc = compute_travel_sla(ticket["priority"], ticket["created_at"], ticket["check_in_date"], ticket["lcd_date"])
        state = evaluate_sla_state(sla_calc["sla_deadline"], ticket["status"], sla_calc["total_hours"])
        ticket["sla_status"] = state["status"]
        ticket["sla_remaining_str"] = state["time_remaining_str"]
        ticket["travel_modifier_applied"] = sla_calc["travel_modifier_applied"]

        # REQUIREMENT 2: Connect related tickets using Agency ID, TBOH, and issue category
        cursor.execute("""
        SELECT DISTINCT t.id, t.tboh, t.title, t.category, t.priority, t.status, t.created_at, t.assigned_name,
               'Same Booking (TBOH)' as link_reason
        FROM tickets t
        WHERE t.tboh = ? AND t.id != ?
        UNION
        SELECT t.id, t.tboh, t.title, t.category, t.priority, t.status, t.created_at, t.assigned_name,
               'Repeat Agency Issue' as link_reason
        FROM tickets t
        WHERE t.agency_id = ? AND t.category = ? AND t.id != ? AND t.tboh != ?
        UNION
        SELECT t.id, t.tboh, t.title, t.category, t.priority, t.status, t.created_at, t.assigned_name,
               'Manual / System Link' as link_reason
        FROM tickets t
        JOIN ticket_links tl ON (tl.target_ticket_id = t.id AND tl.source_ticket_id = ?) 
                             OR (tl.source_ticket_id = t.id AND tl.target_ticket_id = ?)
        WHERE t.id != ?
        ORDER BY created_at DESC
        LIMIT 10
        """, (ticket["tboh"], ticket["id"], ticket["agency_id"], ticket["category"], ticket["id"], ticket["tboh"], ticket["id"], ticket["id"], ticket["id"]))
        
        linked_tickets = [dict(r) for r in cursor.fetchall()]

        # REQUIREMENT 6: Supplier and agency conversations
        cursor.execute("""
        SELECT * FROM messages WHERE ticket_id = ? ORDER BY created_at ASC
        """, (ticket_id,))
        messages_raw = cursor.fetchall()
        messages = []
        supplier_recipients = []
        for m in messages_raw:
            m_dict = dict(m)
            if m_dict["recipient_emails"]:
                try:
                    m_dict["recipient_emails"] = json.loads(m_dict["recipient_emails"])
                    supplier_recipients = m_dict["recipient_emails"]
                except Exception:
                    pass
            messages.append(m_dict)

        # Activity Timeline
        cursor.execute("""
        SELECT * FROM timeline_events WHERE ticket_id = ? ORDER BY created_at DESC
        """, (ticket_id,))
        timeline = [dict(r) for r in cursor.fetchall()]

        return JSONResponse({
            "ticket": ticket,
            "linked_tickets": linked_tickets,
            "messages": messages,
            "supplier_recipients": supplier_recipients,
            "timeline": timeline
        })
    finally:
        conn.close()

async def create_ticket(request):
    # Requirement 1: Create and manage support tickets
    conn = None
    try:
        data = await request.json()
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
        agency_id = data.get("agency_id", "AGY-101")
        tboh = data.get("tboh", "").strip().upper()
        category = data.get("category", "General Inquiry")
        priority = data.get("priority", "P3-Medium")
        check_in_date = data.get("check_in_date", "") or None
        lcd_date = data.get("lcd_date", "") or None
        creator_name = data.get("creator_name", "Rajesh Kumar")
        creator_role = data.get("creator_role", "Agency")

        if not title:
            return JSONResponse({"error": "Case title is required"}, status_code=400)
        if not tboh:
            return JSONResponse({"error": "Booking reference (TBOH) is required"}, status_code=400)

        if not tboh.startswith("TBOH-"):
            tboh = f"TBOH-{tboh}"

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT region FROM agencies WHERE id = ?", (agency_id,))
        agency_row = cursor.fetchone()
        region = agency_row["region"] if agency_row else "APAC"

        cursor.execute("SELECT MAX(CAST(SUBSTR(id, 5) AS INTEGER)) as max_id FROM tickets")
        max_row = cursor.fetchone()
        max_id = max_row["max_id"] if (max_row and max_row["max_id"] is not None) else 1000
        ticket_id = f"TKT-{max_id + 1}"
        while cursor.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone():
            max_id += 1
            ticket_id = f"TKT-{max_id + 1}"
        now_iso = datetime.now(timezone.utc).isoformat()

        # Requirement 4: Travel-aware SLA calculation
        sla_info = compute_travel_sla(priority, now_iso, check_in_date, lcd_date)
        initial_sla_state = evaluate_sla_state(sla_info["sla_deadline"], "New", sla_info["total_hours"])

        # Requirement 3: Intelligent ticket assignment
        routing_ctx = {
            "region": region,
            "priority": priority,
            "category": category,
            "check_in_date": check_in_date,
            "lcd_date": lcd_date
        }
        route_res = evaluate_routing(routing_ctx, conn=conn)
        assigned_agent_id = route_res["agent_id"]
        assigned_name = route_res["agent_name"]
        routing_reason = route_res["routing_reason"]
        status = "Open" if assigned_agent_id else "New"

        cursor.execute("""
        INSERT INTO tickets (
            id, agency_id, tboh, title, description, category, priority, status,
            region, assigned_agent_id, assigned_name, routing_reason, check_in_date, lcd_date,
            sla_deadline, sla_status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticket_id, agency_id, tboh, title, description, category, priority, status,
            region, assigned_agent_id, assigned_name, routing_reason, check_in_date, lcd_date,
            sla_info["sla_deadline"], initial_sla_state["status"], now_iso, now_iso
        ))

        # Requirement 2: Auto-connect related tickets with matching TBOH
        cursor.execute("SELECT id FROM tickets WHERE tboh = ? AND id != ?", (tboh, ticket_id))
        matching_prior = cursor.fetchall()
        for mt in matching_prior:
            cursor.execute("""
            INSERT INTO ticket_links (source_ticket_id, target_ticket_id, link_type, created_at)
            VALUES (?, ?, 'SAME_TBOH', ?)
            """, (ticket_id, mt["id"], now_iso))

        # Log Timeline
        cursor.execute("""
        INSERT INTO timeline_events (ticket_id, event_type, actor_name, actor_role, summary, created_at)
        VALUES (?, 'CREATED', ?, ?, 'Case opened with TBOH ' || ?, ?)
        """, (ticket_id, creator_name, creator_role, tboh, now_iso))

        cursor.execute("""
        INSERT INTO timeline_events (ticket_id, event_type, actor_name, actor_role, summary, created_at)
        VALUES (?, 'ROUTED', 'TripLink Router', 'System', ?, ?)
        """, (ticket_id, routing_reason, now_iso))

        if matching_prior:
            cursor.execute("""
            INSERT INTO timeline_events (ticket_id, event_type, actor_name, actor_role, summary, created_at)
            VALUES (?, 'LINKED', 'Context Engine', 'System', 'Auto-connected with ' || ? || ' prior cases on ' || ?, ?)
            """, (ticket_id, len(matching_prior), tboh, now_iso))

        conn.commit()

        return JSONResponse({
            "success": True,
            "ticket_id": ticket_id,
            "tboh": tboh,
            "assigned_name": assigned_name,
            "routing_reason": routing_reason,
            "linked_prior_count": len(matching_prior)
        })
    except Exception as e:
        return JSONResponse({"error": f"Failed to create ticket: {str(e)}"}, status_code=500)
    finally:
        if conn:
            conn.close()

async def assign_ticket(request):
    # Requirement 3 & 6: Assignment / transfer preserving supplier thread
    conn = None
    try:
        ticket_id = request.path_params["id"]
        data = await request.json()
        new_agent_id = data.get("agent_id")
        actor_name = data.get("actor_name", "Support Agent")
        actor_role = data.get("actor_role", "Support Agent")

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        ticket = cursor.fetchone()
        if not ticket:
            return JSONResponse({"error": "Ticket not found"}, status_code=404)

        now_iso = datetime.now(timezone.utc).isoformat()

        if new_agent_id:
            cursor.execute("SELECT * FROM agents WHERE id = ?", (new_agent_id,))
            agent = cursor.fetchone()
            new_agent_name = agent["name"] if agent else None
            new_status = "Open" if ticket["status"] == "New" else ticket["status"]
            summary = f"Transferred from {ticket['assigned_name'] or 'Unassigned'} to {new_agent_name}. Supplier thread preserved intact."
        else:
            new_agent_name = None
            new_status = "New"
            summary = f"Ticket unassigned by {actor_name}."

        cursor.execute("""
        UPDATE tickets SET assigned_agent_id = ?, assigned_name = ?, status = ?, updated_at = ?
        WHERE id = ?
        """, (new_agent_id, new_agent_name, new_status, now_iso, ticket_id))

        cursor.execute("""
        INSERT INTO timeline_events (ticket_id, event_type, actor_name, actor_role, summary, created_at)
        VALUES (?, 'REASSIGNED', ?, ?, ?, ?)
        """, (ticket_id, actor_name, actor_role, summary, now_iso))

        conn.commit()
        return JSONResponse({"success": True, "ticket_id": ticket_id, "assigned_name": new_agent_name})
    except Exception as e:
        return JSONResponse({"error": f"Failed to transfer ticket: {str(e)}"}, status_code=500)
    finally:
        if conn:
            conn.close()

async def update_status(request):
    conn = None
    try:
        ticket_id = request.path_params["id"]
        data = await request.json()
        new_status = data.get("status")
        actor_name = data.get("actor_name", "Support Agent")
        actor_role = data.get("actor_role", "Support Agent")

        conn = get_db()
        cursor = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()

        cursor.execute("UPDATE tickets SET status = ?, updated_at = ? WHERE id = ?", (new_status, now_iso, ticket_id))

        cursor.execute("""
        INSERT INTO timeline_events (ticket_id, event_type, actor_name, actor_role, summary, created_at)
        VALUES (?, 'STATUS_CHANGED', ?, ?, 'Status changed to ' || ?, ?)
        """, (ticket_id, actor_name, actor_role, new_status, now_iso))

        conn.commit()
        return JSONResponse({"success": True, "ticket_id": ticket_id, "status": new_status})
    except Exception as e:
        return JSONResponse({"error": f"Failed to update status: {str(e)}"}, status_code=500)
    finally:
        if conn:
            conn.close()

async def escalate_ticket(request):
    # Requirement 5: Escalation to an Escalation Manager
    conn = None
    try:
        ticket_id = request.path_params["id"]
        data = await request.json()
        escalation_reason = data.get("reason", "").strip()
        escalate_to = data.get("escalate_to_agent_id", "AGT-901") # Vikram Malhotra
        actor_name = data.get("actor_name", "Support Agent")
        actor_role = data.get("actor_role", "Support Agent")

        if not escalation_reason:
            return JSONResponse({"error": "Escalation reason is required. Please explain why this case requires manager intervention."}, status_code=400)

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        ticket = cursor.fetchone()
        if not ticket:
            return JSONResponse({"error": f"Ticket {ticket_id} was not found."}, status_code=404)

        cursor.execute("SELECT name FROM agents WHERE id = ?", (escalate_to,))
        em = cursor.fetchone()
        em_name = em["name"] if em else "Escalation Manager"

        now_iso = datetime.now(timezone.utc).isoformat()

        cursor.execute("""
        UPDATE tickets 
        SET status = 'Escalated', assigned_agent_id = ?, assigned_name = ?, priority = 'P1-Urgent', escalation_reason = ?, updated_at = ?
        WHERE id = ?
        """, (escalate_to, em_name, escalation_reason, now_iso, ticket_id))

        cursor.execute("""
        INSERT INTO timeline_events (ticket_id, event_type, actor_name, actor_role, summary, created_at)
        VALUES (?, 'ESCALATED', ?, ?, ?, ?)
        """, (ticket_id, actor_name, actor_role, 
              f"First-class escalation to {em_name} (Escalation Queue). Reason: {escalation_reason}",
              now_iso))

        conn.commit()

        return JSONResponse({
            "success": True,
            "ticket_id": ticket_id,
            "status": "Escalated",
            "assigned_name": em_name,
            "escalation_reason": escalation_reason
        })
    except Exception as e:
        return JSONResponse({"error": f"Failed to escalate: {str(e)}"}, status_code=500)
    finally:
        if conn:
            conn.close()

async def post_message(request):
    # Requirement 6: Supplier and agency conversations
    conn = None
    try:
        ticket_id = request.path_params["id"]
        data = await request.json()
        message_type = data.get("message_type", "PUBLIC") # PUBLIC, INTERNAL_NOTE, SUPPLIER_SIDE_THREAD
        body = data.get("body", "").strip()
        sender_type = data.get("sender_type", "Support Agent")
        sender_name = data.get("sender_name", "Priya Sharma")
        recipient_emails = data.get("recipient_emails") # List of emails for supplier side thread

        if not body:
            return JSONResponse({"error": "Message body cannot be empty"}, status_code=400)

        conn = get_db()
        cursor = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()

        recipients_json = json.dumps(recipient_emails) if recipient_emails else None

        cursor.execute("""
        INSERT INTO messages (ticket_id, sender_type, sender_name, message_type, recipient_emails, body, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ticket_id, sender_type, sender_name, message_type, recipients_json, body, now_iso))

        cursor.execute("UPDATE tickets SET updated_at = ? WHERE id = ?", (now_iso, ticket_id))

        if message_type == "SUPPLIER_SIDE_THREAD":
            summary = f"Supplier side message sent ({sender_name})"
        elif message_type == "INTERNAL_NOTE":
            summary = f"Added private internal note ({sender_name})"
        else:
            summary = f"Sent public reply to agency ({sender_name})"

        cursor.execute("""
        INSERT INTO timeline_events (ticket_id, event_type, actor_name, actor_role, summary, created_at)
        VALUES (?, 'NOTE_ADDED', ?, ?, ?, ?)
        """, (ticket_id, sender_name, sender_type, summary, now_iso))

        conn.commit()
        return JSONResponse({"success": True, "ticket_id": ticket_id, "message_type": message_type})
    except Exception as e:
        return JSONResponse({"error": f"Failed to post message: {str(e)}"}, status_code=500)
    finally:
        if conn:
            conn.close()

async def reset_demo(request):
    seed_database()
    return JSONResponse({"success": True, "message": "TripLink demo data reset to clean initial state."})

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

async def serve_index(request):
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

async def serve_manifest(request):
    return FileResponse(os.path.join(FRONTEND_DIR, "manifest.json"), media_type="application/manifest+json")

async def serve_icon(request):
    return FileResponse(os.path.join(FRONTEND_DIR, "icon.svg"), media_type="image/svg+xml")

routes = [
    Route("/api/health", health),
    Route("/api/users", get_users),
    Route("/api/agencies", list_agencies),
    Route("/api/agents", list_agents),
    Route("/api/stats", get_stats),
    Route("/api/stats/recurring-issues", get_recurring_issues),
    Route("/api/tickets", list_tickets, methods=["GET"]),
    Route("/api/tickets", create_ticket, methods=["POST"]),
    Route("/api/tickets/{id}", get_ticket_detail, methods=["GET"]),
    Route("/api/tickets/{id}/assign", assign_ticket, methods=["POST"]),
    Route("/api/tickets/{id}/status", update_status, methods=["POST"]),
    Route("/api/tickets/{id}/escalate", escalate_ticket, methods=["POST"]),
    Route("/api/tickets/{id}/messages", post_message, methods=["POST"]),
    Route("/api/demo/reset", reset_demo, methods=["POST"]),
    Route("/manifest.json", serve_manifest),
    Route("/icon.svg", serve_icon),
    Route("/favicon.ico", serve_icon),
    Route("/", serve_index),
]

middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
]

app = Starlette(debug=True, routes=routes, middleware=middleware)

if __name__ == "__main__":
    import uvicorn
    print("TripLink Server running on http://127.0.0.1:8000 ...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
