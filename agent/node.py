import asyncio
import sys
from pathlib import Path
from langgraph.types import interrupt
from agent.model import llm
from agent.state import TermOutput, SummaryOutput, AnswerOutput, AgentOutput, State
from agent.agent import get_solver_agent

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mcp_config.mcp_server import tavily_search

class AgentNodeFactory:
    def __init__(self, llm_instance, solver_getter, search_func):
        self._llm_instance = llm_instance
        self._solver_getter = solver_getter
        self._search_func = search_func

    async def extract_term(self, state: State) -> State:
        question = state.get("question", "")
        extractor = self._llm_instance.with_structured_output(TermOutput)
        result = await extractor.ainvoke(
            f"从问题中抽取一个最核心的金融数值计算术语，只输出术语。问题：{question}",
            config={"configurable": {"thread_id": "1"}}
        )
        term = result.term.strip()
        return {"term": term}

    async def search(self, state: State) -> State:
        term = state.get("term") or state.get("question", "")
        search_results = await asyncio.to_thread(self._search_func, term)
        return {"search_results": search_results}

    async def summarize_search(self, state: State) -> State:
        question = state.get("question", "")
        term = state.get("term", "")
        search_results = state.get("search_results", "")
        summarizer = self._llm_instance.with_structured_output(SummaryOutput)
        result = await summarizer.ainvoke(
            "将搜索结果总结为标准化内容，结构必须包含三行：\n"
            "术语：<术语名称>\n"
            "概念：<清晰简洁的定义或要点>\n"
            "公式：<可直接用于计算的公式或计算规则，没有则写“无”>\n"
            f"问题：{question}\n术语：{term}\n搜索结果：{search_results}"
        )
        summary = result.summary.strip()
        approved_raw = interrupt({
            "question": question,
            "summary": summary,
            "message": "批准此摘要继续？回复 approve/reject"
        })
        approved = approved_raw
        if isinstance(approved, str):
            approved = approved.strip().lower() in {"approve", "approved", "yes", "y", "true", "1"}
        elif isinstance(approved, (int, float)):
            approved = approved != 0
        else:
            approved = bool(approved)
        if approved:
            return {"search_summary": summary, "needs_resummary": False}
        return {"search_summary": "", "needs_resummary": True}

    async def build_messages(self, state: State) -> State:
        pretty_context = state.get("pretty_context", "")
        question = state.get("question", "")
        term = state.get("term", "")
        search_results = state.get("search_summary") or state.get("search_results", "")
        full_input_message = f"""
【Financial Data Context】
{pretty_context}

【User Question】
{question}

【Extracted Term】
{term}

【Web Search Results】
{search_results}
"""
        return {"messages": [("user", full_input_message)]}

    async def solve(self, state: State) -> State:
        solver = await self._solver_getter()
        result = await solver.ainvoke({"messages": state.get("messages", [])}, config={"configurable": {"thread_id": "1"}})
        return {"structured_response": result}

    def parse_agent_output(self, raw) -> AgentOutput:
        if isinstance(raw, AgentOutput):
            return raw
        if isinstance(raw, dict):
            if "structured_response" in raw:
                return AgentOutput.model_validate(raw.get("structured_response"))
            return AgentOutput.model_validate(raw)
        return AgentOutput()

    async def answer(self, state: State) -> State:
        raw = state.get("structured_response")
        output = self.parse_agent_output(raw)
        question = state.get("question", "")
        term = state.get("term", "")
        search_summary = state.get("search_summary", "")
        prompt = (
            "请根据以下信息给出自然语言回答，强调最终数值结果或无法回答的原因。\n"
            f"问题：{question}\n"
            f"术语：{term}\n"
            f"搜索摘要：{search_summary}\n"
            f"计算结果：{output.final_answer}\n"
            f"is_solved：{output.is_solved}\n"
            f"is_refusal：{output.is_refusal}\n"
            f"refusal_reason：{output.refusal_reason}\n"
        )
        responder = self._llm_instance.with_structured_output(AnswerOutput)
        result = await responder.ainvoke(prompt, config={"configurable": {"thread_id": "1"}})
        return {
            "answer": result.answer.strip(),
            "final_answer": output.final_answer,
            "is_solved": output.is_solved,
            "is_refusal": output.is_refusal,
            "refusal_reason": output.refusal_reason,
            "generated_code": output.generated_code
        }

class NodeSet:
    def __init__(
        self,
        extract_term_node,
        search_node,
        summarize_search_node,
        build_messages_node,
        solve_node,
        answer_node,
    ):
        self.extract_term_node = extract_term_node
        self.search_node = search_node
        self.summarize_search_node = summarize_search_node
        self.build_messages_node = build_messages_node
        self.solve_node = solve_node
        self.answer_node = answer_node

_default_factory = AgentNodeFactory(llm, get_solver_agent, tavily_search)

def create_nodes(factory=None):
    active_factory = factory or _default_factory
    return NodeSet(
        extract_term_node=active_factory.extract_term,
        search_node=active_factory.search,
        summarize_search_node=active_factory.summarize_search,
        build_messages_node=active_factory.build_messages,
        solve_node=active_factory.solve,
        answer_node=active_factory.answer,
    )

async def extract_term_node(state: State) -> State:
    return await _default_factory.extract_term(state)

async def search_node(state: State) -> State:
    return await _default_factory.search(state)

async def summarize_search_node(state: State) -> State:
    return await _default_factory.summarize_search(state)

async def build_messages_node(state: State) -> State:
    return await _default_factory.build_messages(state)

async def solve_node(state: State) -> State:
    return await _default_factory.solve(state)

def parse_agent_output(raw) -> AgentOutput:
    return _default_factory.parse_agent_output(raw)

async def answer_node(state: State) -> State:
    return await _default_factory.answer(state)
