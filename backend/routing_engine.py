from database import get_db

def evaluate_routing(ticket: dict, conn=None) -> dict:
    """
    Intelligent Ticket Assignment (Requirement 3):
    Evaluates:
    1. Region match (APAC, EMEA, Middle East, Americas)
    2. Agent Availability (status == 'Online')
    3. Agent Capacity (current_load < max_capacity)
    4. Priority / Tier matching (P1-Urgent routed to Senior/Tier-2 specialists)
    """
    close_on_exit = False
    if conn is None:
        conn = get_db()
        close_on_exit = True

    cursor = conn.cursor()

    region = ticket.get("region", "APAC")
    priority = ticket.get("priority", "P3-Medium")
    is_urgent = priority in ["P1-Urgent", "P2-High"]

    # Fetch all active online agents
    cursor.execute("SELECT * FROM agents WHERE status = 'Online'")
    online_agents = [dict(r) for r in cursor.fetchall()]

    if not online_agents:
        if close_on_exit:
            conn.close()
        return {
            "agent_id": None,
            "agent_name": None,
            "routing_reason": "Placed in Triage: No support agents currently marked 'Online'.",
            "assigned": False
        }

    scored_agents = []
    for agent in online_agents:
        score = 0
        reasons = []

        # 1. Region match
        if agent["region"].upper() == region.upper():
            score += 40
            reasons.append(f"{region} regional specialist")
        else:
            reasons.append("Cross-region desk fallback")

        # 2. Capacity check
        max_cap = agent.get("max_capacity", 5)
        curr_load = agent.get("current_load", 0)
        remaining_cap = max(0, max_cap - curr_load)

        if remaining_cap > 0:
            score += 30 + (remaining_cap * 3)
            reasons.append(f"Load: {curr_load}/{max_cap}")
        else:
            score -= 50
            reasons.append("At full capacity")

        # 3. Urgency/Tier matching
        agent_tier = agent.get("tier", "Tier-1")
        if is_urgent:
            if agent_tier in ["Tier-2", "Senior", "Lead"]:
                score += 25
                reasons.append("Senior/Tier-2 urgency match")
            else:
                reasons.append("Tier-1 standard agent")
        else:
            score += 15

        scored_agents.append((score, agent, "; ".join(reasons)))

    scored_agents.sort(key=lambda x: x[0], reverse=True)
    best_score, best_agent, detail = scored_agents[0]

    if best_score < 20 or best_agent["current_load"] >= best_agent["max_capacity"]:
        if close_on_exit:
            conn.close()
        return {
            "agent_id": None,
            "agent_name": None,
            "routing_reason": f"Placed in Unassigned Triage: All matching agents in {region} are at capacity.",
            "assigned": False
        }

    # Increment agent's current load
    new_load = best_agent["current_load"] + 1
    cursor.execute("UPDATE agents SET current_load = ? WHERE id = ?", (new_load, best_agent["id"]))
    
    if close_on_exit:
        conn.commit()
        conn.close()

    audit_reason = f"Auto-assigned to {best_agent['name']} ({best_agent['role']}): {region} zone, {best_agent['tier']}, availability score {best_score} ({detail})."
    
    return {
        "agent_id": best_agent["id"],
        "agent_name": best_agent["name"],
        "routing_reason": audit_reason,
        "assigned": True
    }
