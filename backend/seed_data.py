import json
import random
from datetime import datetime, timezone, timedelta
from database import get_db, init_db
from sla_calculator import compute_travel_sla, evaluate_sla_state

AGENCIES = [
    {
        "id": "AGY-101",
        "name": "Apex Travels India",
        "code": "APEX-IN",
        "tier": "Platinum VIP",
        "country": "India",
        "region": "APAC",
        "email": "ops@apextravels.in"
    },
    {
        "id": "AGY-102",
        "name": "Global Voyagers UK",
        "code": "GVOY-UK",
        "tier": "Gold Corporate",
        "country": "United Kingdom",
        "region": "EMEA",
        "email": "support@globalvoyagers.co.uk"
    },
    {
        "id": "AGY-103",
        "name": "Zenith Holidays UAE",
        "code": "ZENITH-AE",
        "tier": "Diamond Premium",
        "country": "United Arab Emirates",
        "region": "Middle East",
        "email": "bookings@zenithholidays.ae"
    },
    {
        "id": "AGY-104",
        "name": "Pacific Journeys SG",
        "code": "PAC-SG",
        "tier": "Silver Standard",
        "country": "Singapore",
        "region": "APAC",
        "email": "desk@pacificjourneys.sg"
    }
]

AGENTS = [
    {
        "id": "AGT-201",
        "name": "Priya Sharma",
        "email": "priya.sharma@tbo.com",
        "role": "Support Agent",
        "region": "APAC",
        "tier": "Tier-2",
        "status": "Online",
        "max_capacity": 5,
        "current_load": 2
    },
    {
        "id": "AGT-202",
        "name": "Oliver Smith",
        "email": "oliver.smith@tbo.com",
        "role": "Support Agent",
        "region": "EMEA",
        "tier": "Tier-1",
        "status": "Online",
        "max_capacity": 5,
        "current_load": 1
    },
    {
        "id": "AGT-203",
        "name": "Tariq Al-Mansoor",
        "email": "tariq.mansoor@tbo.com",
        "role": "Support Agent",
        "region": "Middle East",
        "tier": "Tier-2",
        "status": "Online",
        "max_capacity": 5,
        "current_load": 1
    },
    {
        "id": "AGT-901",
        "name": "Vikram Malhotra",
        "email": "vikram.malhotra@tbo.com",
        "role": "Escalation Manager",
        "region": "Global",
        "tier": "Lead",
        "status": "Online",
        "max_capacity": 10,
        "current_load": 2
    },
    {
        "id": "AGT-902",
        "name": "Neha Gupta",
        "email": "neha.gupta@tbo.com",
        "role": "Ops Lead",
        "region": "Global",
        "tier": "Lead",
        "status": "Online",
        "max_capacity": 15,
        "current_load": 0
    }
]

def seed_database(scale_records: int = 120):
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    # Clear previous data
    cursor.execute("DELETE FROM agencies")
    cursor.execute("DELETE FROM agents")
    cursor.execute("DELETE FROM tickets")
    cursor.execute("DELETE FROM messages")
    cursor.execute("DELETE FROM ticket_links")
    cursor.execute("DELETE FROM timeline_events")

    now = datetime.now(timezone.utc)

    # Insert agencies
    for a in AGENCIES:
        cursor.execute("""
        INSERT INTO agencies (id, name, code, tier, country, region, email)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (a["id"], a["name"], a["code"], a["tier"], a["country"], a["region"], a["email"]))

    # Insert agents
    for ag in AGENTS:
        cursor.execute("""
        INSERT INTO agents (id, name, email, role, region, tier, status, max_capacity, current_load)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ag["id"], ag["name"], ag["email"], ag["role"], ag["region"], ag["tier"], ag["status"], ag["max_capacity"], ag["current_load"]))

    # Core Demo Tickets
    core_tickets = [
        # --- REQUIREMENT 2: Connected tickets on same TBOH-90241 ("Same refund, 3 contacts") ---
        {
            "id": "TKT-1001",
            "tboh": "TBOH-90241",
            "title": "Initial Refund Inquiry for Cancelled Dubai Flight/Hotel Package",
            "description": "Passenger cancelled booking due to passport renewal delay. Requesting refund timeline and credit note voucher.",
            "agency_id": "AGY-101",
            "category": "Refund Delay",
            "priority": "P3-Medium",
            "status": "Resolved",
            "region": "APAC",
            "assigned_agent_id": "AGT-201",
            "assigned_name": "Priya Sharma",
            "routing_reason": "Auto-assigned to Priya Sharma: APAC regional specialist, Tier-2, Online status.",
            "check_in_date": (now - timedelta(days=5)).isoformat(),
            "lcd_date": (now - timedelta(days=8)).isoformat(),
            "created_at": (now - timedelta(days=6)).isoformat(),
            "updated_at": (now - timedelta(days=4)).isoformat()
        },
        {
            "id": "TKT-1002",
            "tboh": "TBOH-90241",
            "title": "Follow up: Refund status update TBOH-90241 - Agency client escalating",
            "description": "Client visited our agency branch asking why funds are not reversed after 4 days. Please expedite.",
            "agency_id": "AGY-101",
            "category": "Refund Delay",
            "priority": "P2-High",
            "status": "Pending",
            "region": "APAC",
            "assigned_agent_id": "AGT-201",
            "assigned_name": "Priya Sharma",
            "routing_reason": "Continuity Route: Prior ticket on TBOH-90241 assigned to Priya Sharma.",
            "check_in_date": (now - timedelta(days=5)).isoformat(),
            "lcd_date": (now - timedelta(days=8)).isoformat(),
            "created_at": (now - timedelta(days=2)).isoformat(),
            "updated_at": (now - timedelta(days=1)).isoformat()
        },
        {
            "id": "TKT-1003",
            "tboh": "TBOH-90241",
            "title": "URGENT: Wallet refund not received, credit limit blocked on TBOH-90241",
            "description": "Third contact regarding Dubai booking refund! Our agency credit balance is now exhausted preventing new holiday bookings. Need immediate finance reversal credit note.",
            "agency_id": "AGY-101",
            "category": "Refund Delay",
            "priority": "P1-Urgent",
            "status": "Open",
            "region": "APAC",
            "assigned_agent_id": "AGT-201",
            "assigned_name": "Priya Sharma",
            "routing_reason": "Context Linkage Trigger: Flagged 2 prior contacts under TBOH-90241. Retained ownership with Priya Sharma.",
            "check_in_date": (now - timedelta(days=5)).isoformat(),
            "lcd_date": (now - timedelta(days=8)).isoformat(),
            "created_at": (now - timedelta(hours=3)).isoformat(),
            "updated_at": (now - timedelta(hours=1)).isoformat()
        },

        # --- REQUIREMENT 4: Travel-Aware SLA Tracking (Imminent Check-In & LCD Proximity) ---
        {
            "id": "TKT-1004",
            "tboh": "TBOH-84910",
            "title": "Guest at Atlantis Reception - Front Desk claims reservation not found in PMS",
            "description": "Lead guest Dr. Arvind Kapoor is currently standing at the front desk with family. Hotel staff cannot locate confirmation number in Opera PMS. Urgent check-in assistance required!",
            "agency_id": "AGY-101",
            "category": "Inventory Sync Mismatch",
            "priority": "P1-Urgent",
            "status": "Open",
            "region": "Middle East",
            "assigned_agent_id": "AGT-203",
            "assigned_name": "Tariq Al-Mansoor",
            "routing_reason": "Auto-assigned to Tariq Al-Mansoor: Middle East destination desk specialist, Tier-2 Urgency response.",
            "check_in_date": (now + timedelta(hours=3)).isoformat(),
            "lcd_date": (now - timedelta(hours=12)).isoformat(),
            "created_at": (now - timedelta(minutes=45)).isoformat(),
            "updated_at": (now - timedelta(minutes=15)).isoformat()
        },
        {
            "id": "TKT-1005",
            "tboh": "TBOH-77312",
            "title": "LCD Penalty Waiver Request: Medical Hospitalization past deadline",
            "description": "Guest admitted to ICU last night. Last cancellation deadline (LCD) is today at 13:00. Requesting hotel supplier waiver to prevent 100% forfeiture of USD 3,200 booking.",
            "agency_id": "AGY-102",
            "category": "Late Cancellation Waiver",
            "priority": "P2-High",
            "status": "Open",
            "region": "EMEA",
            "assigned_agent_id": "AGT-202",
            "assigned_name": "Oliver Smith",
            "routing_reason": "Auto-assigned to Oliver Smith: EMEA region specialist, Active shift, availability 1/5 load.",
            "check_in_date": (now + timedelta(days=1)).isoformat(),
            "lcd_date": (now + timedelta(hours=1)).isoformat(),
            "created_at": (now - timedelta(hours=1, minutes=30)).isoformat(),
            "updated_at": (now - timedelta(minutes=20)).isoformat()
        },
        {
            "id": "TKT-1006",
            "tboh": "TBOH-66120",
            "title": "Flight Cancelled by Carrier - Check-in Overdue and No-Show notice issued",
            "description": "BA-198 was cancelled. Guest did not arrive in London yesterday. Supplier Hilton marked booking as No-Show. Need retro-active waiver.",
            "agency_id": "AGY-102",
            "category": "Late Cancellation Waiver",
            "priority": "P1-Urgent",
            "status": "Open",
            "region": "EMEA",
            "assigned_agent_id": "AGT-202",
            "assigned_name": "Oliver Smith",
            "routing_reason": "Auto-assigned to Oliver Smith: EMEA region specialist.",
            "check_in_date": (now - timedelta(hours=14)).isoformat(),
            "lcd_date": (now - timedelta(hours=36)).isoformat(),
            "created_at": (now - timedelta(hours=4)).isoformat(),
            "updated_at": (now - timedelta(hours=2)).isoformat()
        },

        # --- REQUIREMENT 6: Supplier Side Conversation Surviving Ticket Transfer ---
        {
            "id": "TKT-1007",
            "tboh": "TBOH-91002",
            "title": "Atlantis The Palm: Honeymoon complimentary upgrade and late check-out",
            "description": "VIP honeymooners requested Ocean View Suite upgrade and late check-out at 4 PM. In touch with hotel reservations manager.",
            "agency_id": "AGY-103",
            "category": "Room Upgrade Request",
            "priority": "P2-High",
            "status": "Open",
            "region": "Middle East",
            "assigned_agent_id": "AGT-201",
            "assigned_name": "Priya Sharma",
            "routing_reason": "Transferred from Tariq Al-Mansoor to Priya Sharma for APAC corporate coordination. Supplier thread recipients preserved.",
            "check_in_date": (now + timedelta(days=2)).isoformat(),
            "lcd_date": (now + timedelta(hours=18)).isoformat(),
            "created_at": (now - timedelta(hours=5)).isoformat(),
            "updated_at": (now - timedelta(minutes=45)).isoformat()
        },

        # --- REQUIREMENT 5: Escalation to Escalation Manager ---
        {
            "id": "TKT-1008",
            "tboh": "TBOH-55219",
            "title": "VIP Escalation: Supplier rate hike dispute at front desk ($1,400 voucher vs $2,200 demanded)",
            "description": "Emergency escalation from Zenith Holidays: Supplier claiming rate season discrepancy and refusing to honor prepaid voucher. Escalated directly to Escalation Manager for commercial override.",
            "agency_id": "AGY-103",
            "category": "Inventory Sync Mismatch",
            "priority": "P1-Urgent",
            "status": "Escalated",
            "region": "Middle East",
            "assigned_agent_id": "AGT-901",
            "assigned_name": "Vikram Malhotra",
            "routing_reason": "Direct Escalation to Escalation Manager: Commercial supplier rate conflict with high-value agency.",
            "check_in_date": (now + timedelta(hours=4)).isoformat(),
            "lcd_date": (now - timedelta(hours=10)).isoformat(),
            "created_at": (now - timedelta(hours=2)).isoformat(),
            "updated_at": (now - timedelta(minutes=15)).isoformat()
        },

        # Triage tickets (Unassigned)
        {
            "id": "TKT-1009",
            "tboh": "TBOH-43891",
            "title": "Passport surname misspelling amendment request on Qatar Airways voucher",
            "description": "Passenger ticketed as 'Rohan Sharm' instead of 'Rohan Sharma'. Need name change reissue before 18:00 cutoff.",
            "agency_id": "AGY-104",
            "category": "Date Change",
            "priority": "P2-High",
            "status": "New",
            "region": "APAC",
            "assigned_agent_id": None,
            "assigned_name": None,
            "routing_reason": "Placed in Triage: Pending support agent assignment. High priority time-sensitive correction.",
            "check_in_date": (now + timedelta(days=1)).isoformat(),
            "lcd_date": (now + timedelta(hours=8)).isoformat(),
            "created_at": (now - timedelta(minutes=15)).isoformat(),
            "updated_at": (now - timedelta(minutes=15)).isoformat()
        }
    ]

    for t in core_tickets:
        sla_calc = compute_travel_sla(t["priority"], t["created_at"], t["check_in_date"], t["lcd_date"])
        state = evaluate_sla_state(sla_calc["sla_deadline"], t["status"], sla_calc["total_hours"])

        cursor.execute("""
        INSERT INTO tickets (
            id, agency_id, tboh, title, description, category, priority, status,
            region, assigned_agent_id, assigned_name, routing_reason, check_in_date, lcd_date,
            sla_deadline, sla_status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            t["id"], t["agency_id"], t["tboh"], t["title"], t["description"], t["category"],
            t["priority"], t["status"], t["region"], t["assigned_agent_id"], t["assigned_name"],
            t["routing_reason"], t["check_in_date"], t["lcd_date"], sla_calc["sla_deadline"],
            state["status"], t["created_at"], t["updated_at"]
        ))

    # Requirement 2: Insert explicit ticket links for TBOH-90241
    cursor.execute("""
    INSERT INTO ticket_links (source_ticket_id, target_ticket_id, link_type, created_at)
    VALUES ('TKT-1003', 'TKT-1001', 'SAME_TBOH', ?)
    """, (now.isoformat(),))
    cursor.execute("""
    INSERT INTO ticket_links (source_ticket_id, target_ticket_id, link_type, created_at)
    VALUES ('TKT-1003', 'TKT-1002', 'SAME_TBOH', ?)
    """, (now.isoformat(),))

    # Requirement 6: Insert Messages (Public Agency Reply, Internal Note, Supplier Thread)
    # 1. Public Agency Message on TKT-1003
    cursor.execute("""
    INSERT INTO messages (ticket_id, sender_type, sender_name, message_type, recipient_emails, body, created_at)
    VALUES ('TKT-1003', 'Agency', 'Rajesh Kumar (Apex Travels)', 'PUBLIC', NULL,
    'Third follow-up on TBOH-90241. Please check prior ticket TKT-1002 and TKT-1001. We urgently need our wallet balance released!', ?)
    """, ((now - timedelta(hours=3)).isoformat(),))

    # 2. Internal Ops Note on TKT-1003
    cursor.execute("""
    INSERT INTO messages (ticket_id, sender_type, sender_name, message_type, recipient_emails, body, created_at)
    VALUES ('TKT-1003', 'Support Agent', 'Priya Sharma', 'INTERNAL_NOTE', NULL,
    'Ops Note: Verified supplier credit note received from Emirates Holidays for USD 1,820. Finance reconciliation pending in Batch 4.', ?)
    """, ((now - timedelta(hours=2)).isoformat(),))

    # 3. Supplier Side Conversation on TKT-1007 (with explicit recipient emails!)
    supplier_recipients = json.dumps(["reservations@atlantisthepalm.com", "duty.manager@atlantis.com", "concierge@atlantis.com"])
    
    cursor.execute("""
    INSERT INTO messages (ticket_id, sender_type, sender_name, message_type, recipient_emails, body, created_at)
    VALUES ('TKT-1007', 'Support Agent', 'Tariq Al-Mansoor (TBO Support)', 'SUPPLIER_SIDE_THREAD', ?,
    'Dear Atlantis Reservations Desk, Guest booking TBOH-91002 has arrived. Please confirm complimentary Honeymoon welcome amenities and Ocean Suite upgrade availability.', ?)
    """, (supplier_recipients, (now - timedelta(hours=4)).isoformat()))

    cursor.execute("""
    INSERT INTO messages (ticket_id, sender_type, sender_name, message_type, recipient_emails, body, created_at)
    VALUES ('TKT-1007', 'Supplier Desk', 'Nadia Rostova (Front Office Duty Manager)', 'SUPPLIER_SIDE_THREAD', ?,
    'Greetings from Atlantis The Palm. We have marked the booking for Honeymoon amenities. Suite upgrade is assigned; late check-out till 2 PM granted.', ?)
    """, (supplier_recipients, (now - timedelta(hours=1, minutes=30)).isoformat()))

    # Insert Timeline events
    cursor.execute("""
    INSERT INTO timeline_events (ticket_id, event_type, actor_name, actor_role, summary, created_at)
    VALUES ('TKT-1003', 'CREATED', 'Rajesh Kumar', 'Agency', 'Ticket submitted via B2B Agency Portal with TBOH-90241', ?)
    """, ((now - timedelta(hours=3)).isoformat(),))

    cursor.execute("""
    INSERT INTO timeline_events (ticket_id, event_type, actor_name, actor_role, summary, created_at)
    VALUES ('TKT-1003', 'ROUTED', 'TripLink Smart Router', 'System', 'Context continuity: Auto-routed to Priya Sharma (2 prior cases on TBOH-90241)', ?)
    """, ((now - timedelta(hours=3)).isoformat(),))

    cursor.execute("""
    INSERT INTO timeline_events (ticket_id, event_type, actor_name, actor_role, summary, created_at)
    VALUES ('TKT-1007', 'REASSIGNED', 'Tariq Al-Mansoor', 'Support Agent', 'Ticket transferred to Priya Sharma. Supplier thread recipients preserved intact.', ?)
    """, ((now - timedelta(hours=1)).isoformat(),))

    cursor.execute("""
    INSERT INTO timeline_events (ticket_id, event_type, actor_name, actor_role, summary, created_at)
    VALUES ('TKT-1008', 'ESCALATED', 'Tariq Al-Mansoor', 'Support Agent', 'First-class escalation to Escalation Manager Vikram Malhotra: Hotel demanding rate surcharge at front desk.', ?)
    """, ((now - timedelta(hours=1)).isoformat(),))

    # Generate additional synthetic records for Requirement 7 (Dashboard & Recurring Issues)
    categories = [
        ("Refund Delay", "P2-High"),
        ("Late Cancellation Waiver", "P1-Urgent"),
        ("Inventory Sync Mismatch", "P1-Urgent"),
        ("Date Change", "P3-Medium"),
        ("Room Upgrade Request", "P3-Medium"),
        ("Payment & Invoicing Discrepancy", "P4-Low")
    ]

    for idx in range(10, scale_records + 1):
        t_id = f"TKT-{1000 + idx}"
        cat, prio = random.choice(categories)
        agency = random.choice(AGENCIES)
        tboh = f"TBOH-{random.randint(10000, 99999)}"
        agent = random.choice([a for a in AGENTS if a["role"] == "Support Agent"] + [None])
        days_ago = random.randint(0, 10)
        hrs_ago = random.randint(1, 23)
        created_dt = now - timedelta(days=days_ago, hours=hrs_ago)
        checkin_dt = now + timedelta(days=random.randint(-1, 8), hours=random.randint(2, 20))
        lcd_dt = checkin_dt - timedelta(days=random.randint(1, 3))
        
        status = random.choice(["Open", "Open", "Pending", "Resolved", "Closed"])
        if not agent:
            status = "New"

        sla_calc = compute_travel_sla(prio, created_dt.isoformat(), checkin_dt.isoformat(), lcd_dt.isoformat())
        state = evaluate_sla_state(sla_calc["sla_deadline"], status, sla_calc["total_hours"])

        cursor.execute("""
        INSERT INTO tickets (
            id, agency_id, tboh, title, description, category, priority, status,
            region, assigned_agent_id, assigned_name, routing_reason, check_in_date, lcd_date,
            sla_deadline, sla_status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            t_id, agency["id"], tboh, f"Operational Inquiry: {cat} ({tboh})",
            f"B2B travel request regarding {cat}. Destination booking reference {tboh}.",
            cat, prio, status, agency["region"],
            agent["id"] if agent else None,
            agent["name"] if agent else None,
            f"Auto-routed: {agency['region']} regional coverage" if agent else "Triage: Unassigned",
            checkin_dt.isoformat(), lcd_dt.isoformat(), sla_calc["sla_deadline"],
            state["status"], created_dt.isoformat(), created_dt.isoformat()
        ))

    conn.commit()
    conn.close()
    print(f"TripLink database seeded with {scale_records} tickets successfully.")

if __name__ == "__main__":
    seed_database()
