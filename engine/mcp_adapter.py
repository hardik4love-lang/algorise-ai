"""
Algorise Model Context Protocol (MCP) Adapter
Provides standardized MCP tool discovery and execution endpoints for enterprise AI integration.
"""

from typing import Dict, Any, List

class AlgoriseMCPAdapter:
    def __init__(self, bot_registry):
        self.bot_registry = bot_registry

    def list_tools(self) -> List[Dict[str, Any]]:
        """Returns standard MCP tool declarations for all registered Algorise bots."""
        tools = []
        for bot_id, bot in self.bot_registry.items():
            tools.append({
                "name": f"algorise_{bot_id}",
                "description": bot.description,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Input instruction or query"},
                        "parameters": {"type": "object", "description": "Domain-specific parameters"}
                    },
                    "required": ["query"]
                }
            })
        return tools

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a tool call according to the Model Context Protocol specification."""
        clean_name = tool_name.replace("algorise_", "")
        bot = self.bot_registry.get(clean_name)
        if not bot:
            return {"isError": True, "content": [{"type": "text", "text": f"Tool '{tool_name}' not found."}]}
        
        from .models import BotTask
        task = BotTask(bot_name=clean_name, input_payload=arguments)
        result = bot.execute(task)
        
        return {
            "isError": not result.success,
            "content": [
                {"type": "text", "text": str(result.data)},
                {"type": "metadata", "latency_ms": result.latency_ms, "bot": result.bot_name}
            ]
        }
