import asyncio
import sys
from pathlib import Path
from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware, SummarizationMiddleware
from agent.model import llm
from agent.state import AgentInput, AgentOutput

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mcp_config.client import MCPToolClient

SYSTEM_PROMPT = """You are a financial expert, you are supposed to generate a Python program to answer the given question. The returned value of the program is supposed to be the answer. Here is an example of the Python program:
    ```python
    def solution():
        # Define variables name and value
        ...
        # Do math calculation
        ...
        # return answer
        return answer
    ```
    Generate a Python program to answer the given question. If the question cannot be answered, refuse to answer. Strictly prohibit any fabrication or assumptions. Continue your output:
    ```python
    def solution():
        # Define variables name and value
"""

class SolverAgentFactory:
    def __init__(self, model, mcp_client, system_prompt):
        self._model = model
        self._mcp_client = mcp_client
        self._system_prompt = system_prompt
        self._agent = None
        self._tools = None

    async def get_tools(self):
        if self._tools is None:
            self._tools = await self._mcp_client.get_tools()
        return self._tools

    async def get_agent(self):
        if self._agent is None:
            tools = await self.get_tools()
            self._agent = create_agent(
                model=self._model,
                tools=tools,
                system_prompt=self._system_prompt,
                context_schema=AgentInput,
                response_format=AgentOutput,
                middleware=[
                    ToolCallLimitMiddleware(run_limit=3),
                    SummarizationMiddleware(
                        model="openai:gpt-4o-mini",
                        max_tokens_before_summary=4000,
                        messages_to_keep=20,
                        summary_prompt="Custom prompt for summarization..."
                    )
                ]
            )
        return self._agent

    def get_agent_sync(self):
        try:
            asyncio.get_running_loop()
            return None
        except RuntimeError:
            try:
                return asyncio.run(self.get_agent())
            except Exception:
                return None

_default_factory = SolverAgentFactory(llm, MCPToolClient(), SYSTEM_PROMPT)

async def get_solver_agent():
    return await _default_factory.get_agent()

def get_solver_agent_sync():
    return _default_factory.get_agent_sync()

def init_solver_agent_sync():
    return get_solver_agent_sync()

SOLVER_AGENT = get_solver_agent_sync()
