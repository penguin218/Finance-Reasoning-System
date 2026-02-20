from langchain_mcp_adapters.client import MultiServerMCPClient
import os

class MCPToolClient:
    def __init__(self):
        mcp_server_config = {
            "transport": "sse",
            "url": os.getenv("MCP_SERVER_URL", "http://localhost:8000/sse")
        }
        self._client = MultiServerMCPClient({
            "mcp_server": mcp_server_config
        })
        self._tools = None

    def get_client(self):
        return self._client

    async def get_tools(self):
        if self._tools is None:
            self._tools = await self._client.get_tools()
        return self._tools
