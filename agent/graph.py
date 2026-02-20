from langchain_core.runnables import RunnableLambda
from langgraph.graph import StateGraph, START, END
from agent.state import State
from agent.node import create_nodes
from agent.edge import route_after_summary
from agent.agent import get_solver_agent_sync

def build_graph(nodes=None, solver_agent=None):
    active_nodes = nodes or create_nodes()
    active_solver = solver_agent if solver_agent is not None else get_solver_agent_sync()
    solve_chain = None
    if active_solver is not None:
        solve_chain = RunnableLambda(lambda state: {"messages": state.get("messages", [])}) | active_solver

    builder = StateGraph(State)
    builder.add_node("extract_term", active_nodes.extract_term_node)
    builder.add_node("search", active_nodes.search_node)
    builder.add_node("summarize_search", active_nodes.summarize_search_node)
    builder.add_node("build_messages", active_nodes.build_messages_node)
    if solve_chain is not None:
        builder.add_node("solve", solve_chain)
    else:
        builder.add_node("solve", active_nodes.solve_node)
    builder.add_node("answer", active_nodes.answer_node)

    builder.add_edge(START, "extract_term")
    builder.add_edge("extract_term", "search")
    builder.add_edge("search", "summarize_search")

    builder.add_conditional_edges(
        "summarize_search",
        route_after_summary,
        {
            "search": "search",
            "build_messages": "build_messages"
        }
    )
    builder.add_edge("build_messages", "solve")
    builder.add_edge("solve", "answer")
    builder.add_edge("answer", END)
    return builder.compile()

graph = build_graph()
