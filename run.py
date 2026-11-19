import os
import sys

backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import uvicorn
from database import DB_PATH
from seed_data import seed_database

def main():
    print("=" * 65)
    print("      🚀 TripLink for TBO — Smart Travel Support Platform")
    print("=" * 65)
    print(" Relationships, context, and travel urgency first — isolated tickets second.")
    print()

    if not os.path.exists(DB_PATH):
        print("📦 First-time launch: Initializing & seeding TripLink database...")
        seed_database()
        print("✅ Database pre-seeded with realistic TBO travel operations data.")
    else:
        print("✅ Database found at:", DB_PATH)

    # Enable WAL mode for high concurrency
    import sqlite3
    try:
        w_conn = sqlite3.connect(DB_PATH, timeout=5.0)
        w_conn.execute("PRAGMA journal_mode = WAL")
        w_conn.execute("PRAGMA busy_timeout = 5000")
        w_conn.close()
    except Exception:
        pass

    print()
    print("🌐 TripLink Web Application is running at:")
    print("   👉 http://localhost:8000")
    print("   👉 http://127.0.0.1:8000")
    print()
    print("👥 Demo User Roles:")
    print("   1. 👤 Rajesh Kumar      | Agency Requester (Apex Travels India)")
    print("   2. 🎧 Priya Sharma      | Support Agent (APAC Regional Specialist)")
    print("   3. ⚡ Vikram Malhotra   | Escalation Manager (Urgent Overrides)")
    print("   4. 📊 Neha Gupta        | Ops Lead (Governance & Stats)")
    print()
    print("🧭 1-Click Demo Tours (Available in Top Navigation Bar):")
    print("   • 1: Linkage       - Connects 3 contacts for same refund (TBOH-90241)")
    print("   • 2: Routing       - Smart assignment by region, priority & workload")
    print("   • 3: Travel SLA    - Imminent check-in / LCD deadline compression")
    print("   • 4: Supplier      - Hotel thread with explicit recipients surviving transfer")
    print("   • 5: Escalate      - Direct first-class escalation to Escalation Manager")
    print("   • 6: Dashboard     - Recurring issues & SLA compliance stats")
    print("=" * 65)
    print("Press CTRL+C to stop the server.\n")

    os.chdir(backend_dir)
    uvicorn.run("app:app", host="127.0.0.1", port=8000, log_level="info")

if __name__ == "__main__":
    main()
