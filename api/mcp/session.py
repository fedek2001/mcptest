from flask import Flask, jsonify
import asyncio
from ._shared import mcp  # donde registraste los tools

app = Flask(__name__)

def list_tools_sync():
    # FastMCP.list_tools() es async → materializamos la lista
    return asyncio.run(mcp.list_tools())

@app.route("/api/mcp/session", methods=["POST"])
def session():
    tools = []
    for t in list_tools_sync():
        tools.append({
            "name": t.name,
            "description": t.description or "",
            "args_schema": t.json_schema
        })
    return jsonify({
        "protocol": "mcp-http-sse",
        "server": {"name": "vercel-mcp-python", "version": "0.1.0"},
        "capabilities": {"tools": True, "streaming": "sse"},
        "tools": tools
    })
