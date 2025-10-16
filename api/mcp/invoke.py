from flask import Flask, request, Response
import json, time, asyncio
from ._shared import mcp

app = Flask(__name__)

# ---------- helpers ----------
def sse(event: str, data: dict) -> bytes:
    return (f"event: {event}\n" + "data: " + json.dumps(data, ensure_ascii=False) + "\n\n").encode("utf-8")

def list_tools_sync():
    # FastMCP.list_tools() es async → materializamos
    return asyncio.run(mcp.list_tools())

def find_tool_sync(name: str):
    tools = list_tools_sync()
    return next((t for t in tools if getattr(t, "name", None) == name), None)

def run_tool_sync(tool, args: dict):
    """
    Intenta invocar la herramienta sin importar si es:
    - tool.fn (sync/async)
    - tool.call (sync/async)
    - tool itself es callable (sync/async)
    """
    # 1) fn
    fn = getattr(tool, "fn", None)
    if fn:
        if asyncio.iscoroutinefunction(fn):
            return asyncio.run(fn(**args))
        return fn(**args)

    # 2) call
    call = getattr(tool, "call", None)
    if call:
        if asyncio.iscoroutinefunction(call):
            return asyncio.run(call(**args))
        return call(**args)

    # 3) el objeto es invocable
    if callable(tool):
        if asyncio.iscoroutinefunction(tool):
            return asyncio.run(tool(**args))
        return tool(**args)

    raise RuntimeError("No supported call interface for this tool (expected .fn/.call/callable)")

# ---------- endpoint ----------
@app.route("/api/mcp/invoke", methods=["POST"])
def invoke():
    payload   = request.get_json(silent=True) or {}
    tool_name = payload.get("tool")
    args      = payload.get("args") or {}
    req_id    = payload.get("request_id")

    # validaciones rápidas
    if not tool_name:
        return Response(sse("result", {"ok": False, "error": "missing 'tool'"}), mimetype="text/event-stream")
    if not isinstance(args, dict):
        return Response(sse("result", {"ok": False, "error": "'args' must be an object/dict"}), mimetype="text/event-stream")

    tool = find_tool_sync(tool_name)
    if tool is None:
        return Response(sse("result", {"ok": False, "error": f"unknown tool: {tool_name}"}), mimetype="text/event-stream")

    def gen():
        yield sse("start", {"request_id": req_id})
        for p in (0.1, 0.35, 0.7):
            time.sleep(0.02)
            yield sse("chunk", {"progress": p})
        try:
            out = run_tool_sync(tool, args)
            yield sse("result", {"ok": True, "output": out})
        except Exception as e:
            yield sse("result", {"ok": False, "error": str(e)})
        yield sse("end", {"request_id": req_id})

    return Response(gen(), headers={
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }, mimetype="text/event-stream")
