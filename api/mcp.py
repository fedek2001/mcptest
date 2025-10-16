from flask import Flask, request, Response, jsonify
import json, time
from mcp.server.fastmcp import FastMCP  # o: from fastmcp import FastMCP

app = Flask(__name__)
mcp = FastMCP("vercel-mcp-python")

@app.get("/health")
def health():
    return jsonify({"ok": True})

@mcp.tool()
def reverse(text: str) -> str:
    return text[::-1]

@app.post("/session")
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

def sse(event: str, data: dict) -> bytes:
    return (f"event: {event}\n" + "data: " + json.dumps(data, ensure_ascii=False) + "\n\n").encode("utf-8")

@app.post("/invoke")
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
            out = tool_impl.fn(**args) if not tool_impl.is_async else None  # Flask sync en Vercel
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
