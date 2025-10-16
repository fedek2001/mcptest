from flask import Flask, jsonify
from ._shared import mcp

app = Flask(__name__)

@app.post("/api/mcp/session")
def session():
    tools = []
    for t in mcp.list_tools():
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
