from flask import Flask, jsonify
import asyncio
from ._shared import mcp

app = Flask(__name__)

def list_tools_sync():
    return asyncio.run(mcp.list_tools())

def tool_schema(tool) -> dict | None:
    # Orden de compatibilidad: args_schema → input_model → nada
    if hasattr(tool, "args_schema") and tool.args_schema:
        return tool.args_schema
    if hasattr(tool, "input_model") and tool.input_model is not None:
        # Pydantic v2
        if hasattr(tool.input_model, "model_json_schema"):
            return tool.input_model.model_json_schema()  # dict
        # Pydantic v1 (por si acaso)
        if hasattr(tool.input_model, "schema"):
            return tool.input_model.schema()  # dict
    return None  # como fallback, el cliente puede invocar igual si conoce los args

@app.route("/api/mcp/session", methods=["POST"])
def session():
    tools = []
    for t in list_tools_sync():
        tools.append({
            "name": t.name,
            "description": getattr(t, "description", "") or "",
            "args_schema": tool_schema(t)
        })
    return jsonify({
        "protocol": "mcp-http-sse",
        "server": {"name": "vercel-mcp-python", "version": "0.1.0"},
        "capabilities": {"tools": True, "streaming": "sse"},
        "tools": tools
    })
