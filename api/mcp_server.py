# api/mcp.py
from flask import Flask, request, Response, jsonify
import json, time
from mcp.server.fastmcp import FastMCP  # si usás la lib 3rd-party: from fastmcp import FastMCP

app = Flask(__name__)
mcp = FastMCP("vercel-mcp-python")

# --------- TOOLS ---------
@mcp.tool()
def reverse(text: str) -> str:
    return text[::-1]

@mcp.tool()
def add(a: float, b: float) -> float:
    return a + b

# --------- SSE helper ---------
def sse(event: str, data: dict) -> bytes:
    return (f"event: {event}\n" + "data: " + json.dumps(data, ensure_ascii=False) + "\n\n").encode("utf-8")

# --------- ENDPOINTS (con prefijo /api/mcp/ ) ---------
@app.get("/api/mcp_server/health")
def health():
    return jsonify({"ok": True})

@app.post("/api/mcp_server/session")
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

@app.post("/api/mcp_server/invoke")
def invoke():
    payload = request.get_json(silent=True) or {}
    tool = payload.get("tool")
    args = payload.get("args") or {}
    req_id = payload.get("request_id")

    tool_impl = next((t for t in mcp.list_tools() if t.name == tool), None)
    if tool_impl is None:
        return jsonify({"error": f"unknown tool: {tool}"}), 400

    def gen():
        yield sse("start", {"request_id": req_id})
        for p in (0.1, 0.35, 0.7):
            time.sleep(0.05)
            yield sse("chunk", {"progress": p})
        try:
            # Nota: en Flask serverless evitamos async. Si tu tool fuera async, conviértela o maneja un worker externo.
            out = tool_impl.fn(**args) if not tool_impl.is_async else None
            yield sse("result", {"ok": True, "output": out})
        except Exception as e:
            yield sse("result", {"ok": False, "error": str(e)})
        yield sse("end", {"request_id": req_id})

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        "Content-Type": "text/event-stream; charset=utf-8"
    }
    return Response(gen(), headers=headers)
