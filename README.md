# TripLink for TBO
> **Smart travel support and ticket management platform shaped by TBO's real B2B travel operational complexity.**  
> *Relationships, context, and travel urgency first — isolated tickets second.*

---

## The Problem TripLink Solves
Traditional ticketing software treats customer interactions in silos. At TBO, this model creates operational failure modes:
1. **Isolated Tickets**: A travel agency contacts support 3 times about the same refund. Each becomes a disconnected ticket; agents lose historical context and repeat basic questions.
2. **Blind FIFO Routing**: Standard queues assign tickets based on submission time, ignoring agent shift availability, region expertise, or load.
3. **Rigid SLAs**: Generic countdown timers treat a booking with check-in 2 weeks away the same as a guest stranded at hotel reception today.
4. **Fragile Supplier Threads**: Communication with airlines and hotels drops off when tickets are reassigned or transferred.
5. **No Direct Escalation**: Priority cases get stuck in follower lists or emails rather than reaching Escalation Managers directly.

**TripLink replaces isolated tickets with context-aware travel cases.**

---

## 7 Core Requirements Mapped to Implementation

| # | Requirement | How TripLink Solves It | Code Reference |
|---|-------------|------------------------|----------------|
| **1** | **Create & Manage Support Tickets** | Full ticket lifecycle (`New` $\rightarrow$ `Open` $\rightarrow$ `Pending` $\rightarrow$ `Escalated` $\rightarrow$ `Resolved` $\rightarrow$ `Closed`) with responsive split-screen workbench. | [`app.py`](file:///C:/Users/Monashree%20S%20V/.gemini/antigravity/scratch/triplink/backend/app.py) |
| **2** | **Connect Related Tickets (TBOH, Agency ID, Category)** | Automatic first-class context linker queries related cases by shared `TBOH` or repeat agency issues without third-party bolt-on apps. | [`get_ticket_detail`](file:///C:/Users/Monashree%20S%20V/.gemini/antigravity/scratch/triplink/backend/app.py) |
| **3** | **Intelligent Ticket Assignment** | Multi-factor routing evaluates destination region, active online shifts, workload capacity, and priority tier with transparent explainable audit reasons. | [`evaluate_routing`](file:///C:/Users/Monashree%20S%20V/.gemini/antigravity/scratch/triplink/backend/routing_engine.py) |
| **4** | **Travel-Aware Dynamic SLA Tracking** | Dynamic SLA engine compresses target resolution times when guest check-in is near (<12h $\rightarrow$ 1h) or LCD is near (<6h $\rightarrow$ 45m). | [`compute_travel_sla`](file:///C:/Users/Monashree%20S%20V/.gemini/antigravity/scratch/triplink/backend/sla_calculator.py) |
| **5** | **Escalation to Escalation Manager** | First-class direct escalation action with mandatory rationale that moves the ticket to Lead Escalation Manager Vikram Malhotra's priority queue. | [`escalate_ticket`](file:///C:/Users/Monashree%20S%20V/.gemini/antigravity/scratch/triplink/backend/app.py) |
| **6** | **Supplier & Agency Conversations** | Unified thread supporting public agency replies, private ops notes, and external supplier side-threads with explicit recipient lists that survive reassignment. | [`post_message`](file:///C:/Users/Monashree%20S%20V/.gemini/antigravity/scratch/triplink/backend/app.py) |
| **7** | **Dashboard & Recurring Issues** | Live dashboard tracking total volume, SLA compliance rates, at-risk deadlines, and top recurring friction categories (e.g. Refund Delays, PMS Sync). | [`get_recurring_issues`](file:///C:/Users/Monashree%20S%20V/.gemini/antigravity/scratch/triplink/backend/app.py) |

---

## Quick Start (Desktop App & Web)

### Option 1: Native Windows Desktop App (Recommended)
Double-click:
- **`TripLink_App.vbs`**: Launches TripLink silently in a clean standalone desktop app window (zero terminal clutter).
- Or **`TripLink_App.bat`**: Double-click batch launcher.
- To create a direct Windows Desktop icon, run **`Create_Desktop_Shortcut.bat`**.

### Option 2: Console / Web Browser Mode
```powershell
cd "C:\Users\Monashree S V\.gemini\antigravity\scratch\triplink"
python run.py
```
*(Or double-click `run.bat`)*

Open your browser at:  
👉 **http://localhost:8000** or **http://127.0.0.1:8000**

To stop the background server at any time, run **`Stop_TripLink.bat`**.

---

## Automated Verification Suites

TripLink includes two automated test suites:

1. **Full 15-Point Diagnostic Test Suite:**
```powershell
cd "C:\Users\Monashree S V\.gemini\antigravity\scratch\triplink\backend"
python test_suite.py
```
*(Tests backend import, database connection, isolated schema init, app routes, health check, ticket creation, retrieval, updates, SLA compression, escalation, error handling, duplicate handling, search/filtering, frontend assets, and desktop launchers)*

2. **Core 7 Requirements Verification:**
```powershell
python test_triplink.py
```
*Output: All 7 TripLink requirements verified 100% successfully.*

---

## 3-Minute Hackathon Demo Script for Judges

1. **Introduction & Hook (30s):**
   - Click **`1: Linkage`** in the top navigation bar.
   - *"In standard ticketing, when an agency asks 3 times about a refund, it opens 3 isolated tickets. Notice how TripLink loads TKT-1003 and immediately displays the 2 prior refund tickets for TBOH-90241 on the right panel without any third-party app."*

2. **Intelligent Assignment (40s):**
   - Click **`2: Routing`** in the header.
   - Shows urgent check-in crisis at hotel front desk (`TKT-1004`).
   - Point out the **Routing Rationale Banner**: *"Auto-assigned to Tariq Al-Mansoor: Middle East regional specialist, Tier-2 Urgency response, Load 1/5"*.

3. **Travel-Aware SLA Tracking (40s):**
   - Click **`3: Travel SLA`** in the header.
   - Shows `TKT-1005` where Last Cancellation Date (LCD) expires in 1 hour.
   - The SLA is compressed dynamically with a flashing **At-Risk** badge.

4. **Supplier Side Thread Surviving Transfer (40s):**
   - Click **`4: Supplier Thread`** in the header.
   - Shows `TKT-1007` (Honeymoon suite upgrade).
   - Display the active thread with hotel reservations (`reservations@atlantisthepalm.com`).
   - Transfer the ticket to another agent: the explicit recipient list and thread stay 100% intact!

5. **First-Class Escalation & Dashboard (30s):**
   - Click **`5: Escalate`** to show ticket `TKT-1008` in Escalation Manager Vikram Malhotra's queue.
   - Click **`6: Dashboard`** to showcase the live breakdown of recurring travel issues and SLA compliance.
