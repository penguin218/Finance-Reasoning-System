from agent.state import State

def route_after_summary(state: State):
    if state.get("needs_resummary"):
        return "search"
    return "build_messages"
