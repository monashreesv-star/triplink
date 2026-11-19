import sqlite3
import os

ORIG_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "triplink.db")

# Detect Vercel / serverless environment (where repository folder is read-only)
if os.environ.get("VERCEL") or not os.access(os.path.dirname(os.path.abspath(__file__)), os.W_OK):
    import shutil
    import tempfile
    temp_dir = tempfile.gettempdir()
    DB_PATH = os.path.join(temp_dir, "triplink.db")
    if not os.path.exists(DB_PATH) and os.path.exists(ORIG_DB_PATH):
        try:
            shutil.copy2(ORIG_DB_PATH, DB_PATH)
        except Exception:
            pass
else:
    DB_PATH = ORIG_DB_PATH

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA journal_mode = WAL")
    except Exception:
        pass

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS agencies (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        code TEXT NOT NULL,
        tier TEXT NOT NULL,
        country TEXT NOT NULL,
        region TEXT NOT NULL,
        email TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS agents (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        role TEXT NOT NULL,      -- Support Agent, Escalation Manager, Ops Lead
        region TEXT NOT NULL,    -- APAC, EMEA, Middle East, Americas, Global
        tier TEXT NOT NULL,      -- Tier-1, Tier-2, Lead
        status TEXT NOT NULL,    -- Online, Away, Offline
        max_capacity INTEGER NOT NULL DEFAULT 5,
        current_load INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS tickets (
        id TEXT PRIMARY KEY,
        agency_id TEXT NOT NULL,
        tboh TEXT NOT NULL,      -- TBO Booking Reference (e.g. TBOH-90241)
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,  -- Refund Delay, Inventory Sync Mismatch, Date Change, etc.
        priority TEXT NOT NULL,  -- P1-Urgent, P2-High, P3-Medium, P4-Low
        status TEXT NOT NULL,    -- New, Open, Pending, Escalated, Resolved, Closed
        region TEXT NOT NULL,    -- APAC, EMEA, Middle East, Americas
        assigned_agent_id TEXT,
        assigned_name TEXT,
        routing_reason TEXT,
        check_in_date TEXT,      -- ISO format timestamp
        lcd_date TEXT,           -- Last Cancellation Deadline
        sla_deadline TEXT,       -- Calculated SLA deadline timestamp
        sla_status TEXT,         -- Healthy, At-Risk, Breached, Resolved
        escalation_reason TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (agency_id) REFERENCES agencies(id),
        FOREIGN KEY (assigned_agent_id) REFERENCES agents(id)
    );

    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id TEXT NOT NULL,
        sender_type TEXT NOT NULL,   -- Agency, Support Agent, Supplier Desk, Escalation Manager
        sender_name TEXT NOT NULL,
        message_type TEXT NOT NULL,  -- PUBLIC, INTERNAL_NOTE, SUPPLIER_SIDE_THREAD
        recipient_emails TEXT,       -- JSON array for supplier side thread: ["res@hotel.com"]
        body TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (ticket_id) REFERENCES tickets(id)
    );

    CREATE TABLE IF NOT EXISTS ticket_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_ticket_id TEXT NOT NULL,
        target_ticket_id TEXT NOT NULL,
        link_type TEXT NOT NULL,     -- SAME_TBOH, REPEAT_AGENCY_ISSUE, MANUAL_LINK
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS timeline_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id TEXT NOT NULL,
        event_type TEXT NOT NULL,    -- CREATED, ROUTED, REASSIGNED, NOTE_ADDED, SUPPLIER_MSG, ESCALATED, STATUS_CHANGED
        actor_name TEXT NOT NULL,
        actor_role TEXT NOT NULL,
        summary TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (ticket_id) REFERENCES tickets(id)
    );

    CREATE INDEX IF NOT EXISTS idx_tickets_tboh ON tickets(tboh);
    CREATE INDEX IF NOT EXISTS idx_tickets_agency ON tickets(agency_id);
    CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
    CREATE INDEX IF NOT EXISTS idx_tickets_assigned ON tickets(assigned_agent_id);
    CREATE INDEX IF NOT EXISTS idx_tickets_sla ON tickets(sla_status);
    CREATE INDEX IF NOT EXISTS idx_messages_ticket ON messages(ticket_id);
    """);

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("TripLink Database initialized at:", DB_PATH)
