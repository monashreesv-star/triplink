from datetime import datetime, timezone, timedelta

PRIORITY_HOURS = {
    "P1-Urgent": 2,
    "P2-High": 6,
    "P3-Medium": 24,
    "P4-Low": 48
}

def parse_iso(iso_str):
    if not iso_str:
        return None
    try:
        if iso_str.endswith("Z"):
            iso_str = iso_str[:-1] + "+00:00"
        return datetime.fromisoformat(iso_str)
    except Exception:
        return None

def compute_travel_sla(priority: str, created_at_str: str, check_in_str: str = None, lcd_str: str = None) -> dict:
    """
    Travel-Aware SLA Tracking (Requirement 4):
    Calculates dynamic SLA target based on Base Priority and Travel Proximity.
    """
    created_at = parse_iso(created_at_str) or datetime.now(timezone.utc)
    base_hours = PRIORITY_HOURS.get(priority, 24)
    target_hours = base_hours
    modifier_note = None

    now = datetime.now(timezone.utc)

    # 1. Check LCD (Last Cancellation Deadline) proximity
    lcd_dt = parse_iso(lcd_str)
    if lcd_dt:
        hours_to_lcd = (lcd_dt - now).total_seconds() / 3600.0
        if hours_to_lcd <= 0 and created_at:
            hours_to_lcd = (lcd_dt - created_at).total_seconds() / 3600.0

        if 0 < hours_to_lcd <= 6:
            target_hours = min(target_hours, 0.75) # 45 minutes!
            modifier_note = f"LCD expires in {round(hours_to_lcd, 1)}h (Urgent penalty deadline)"
        elif 0 < hours_to_lcd <= 18:
            target_hours = min(target_hours, 2.0) # 2 hours
            modifier_note = f"LCD in {round(hours_to_lcd, 1)}h"

    # 2. Check Check-In Date proximity
    check_in_dt = parse_iso(check_in_str)
    if check_in_dt:
        hours_to_checkin = (check_in_dt - now).total_seconds() / 3600.0
        if hours_to_checkin <= 0 and created_at:
            hours_to_checkin = (check_in_dt - created_at).total_seconds() / 3600.0

        if 0 < hours_to_checkin <= 12:
            target_hours = min(target_hours, 1.0) # 1 hour!
            modifier_note = f"Check-in in {round(hours_to_checkin, 1)}h (Imminent guest arrival)"
        elif 0 < hours_to_checkin <= 24:
            target_hours = min(target_hours, 2.0) # 2 hours
            modifier_note = f"Check-in in {round(hours_to_checkin, 1)}h"

    sla_deadline = created_at + timedelta(hours=target_hours)

    return {
        "sla_deadline": sla_deadline.isoformat(),
        "total_hours": target_hours,
        "travel_modifier_applied": modifier_note
    }

def evaluate_sla_state(deadline_str: str, ticket_status: str, total_hours: float = 6.0) -> dict:
    if ticket_status in ["Resolved", "Closed"]:
        return {
            "status": "Resolved",
            "time_remaining_str": "Resolved",
            "badge_color": "green",
            "percent_remaining": 100
        }

    deadline = parse_iso(deadline_str)
    if not deadline:
        return {
            "status": "Healthy",
            "time_remaining_str": "--",
            "badge_color": "gray",
            "percent_remaining": 100
        }

    now = datetime.now(timezone.utc)
    diff = (deadline - now).total_seconds()

    if diff < 0:
        overdue_minutes = int(abs(diff) / 60)
        hours = overdue_minutes // 60
        mins = overdue_minutes % 60
        time_str = f"-{hours}h {mins}m overdue" if hours > 0 else f"-{mins}m overdue"
        return {
            "status": "Breached",
            "time_remaining_str": time_str,
            "badge_color": "red",
            "percent_remaining": 0
        }

    remaining_minutes = int(diff / 60)
    hours = remaining_minutes // 60
    mins = remaining_minutes % 60
    time_str = f"{hours}h {mins}m left" if hours > 0 else f"{mins}m left"

    total_seconds = max(total_hours * 3600, 3600)
    ratio = diff / total_seconds

    if ratio <= 0.4 or remaining_minutes <= 45:
        return {
            "status": "At-Risk",
            "time_remaining_str": time_str,
            "badge_color": "amber",
            "percent_remaining": int(ratio * 100)
        }

    return {
        "status": "Healthy",
        "time_remaining_str": time_str,
        "badge_color": "emerald",
        "percent_remaining": int(ratio * 100)
    }
