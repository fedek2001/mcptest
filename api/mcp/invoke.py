from flask import Flask, request, Response
from ._shared import mcp
import json, time

app = Flask(__name__)

def sse(event: str, data: dict) -> bytes:
    return (f"event: {event}\n" + "data: " + json.dumps(data, ensure_ascii=False) + "\n\n").encode("utf-8")

@app.post("/api/mcp/invoke")
def invoke():
    payload = request.get_json(silent=True) or {}
    tool_name = payload.get("tool")
    args = payload.get("args") or {}
    req_id = payload.get("request_id")

    tool_impl = next((t for t in mcp.list_tools() if t.name == tool_name), None)
    if tool_impl is None:
        return Response(sse("result", {"ok": False, "error": f"unknown tool: {tool_name}"}),
                        headers={"Content-Type":"text/event-stream; charset=utf-8"})

    def gen():
        yield sse("start", {"request_id": req_id})
        for p in (0.1, 0.35, 0.7):
            time.sleep(0.03)
            yield sse("chunk", {"progress": p})
        try:
            # Evitamos async en Flask serverless
            if tool_impl.is_async:
                raise RuntimeError("async tools not supported here")
            out = tool_impl.fn(**args)
            yield sse("result", {"ok": True, "output": out})
        except Exception as e:
            yield sse("result", {"ok": False, "error": str(e)})
        yield sse("end", {"request_id": req_id})

    return Response(gen(), headers={
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        "Content-Type": "text/event-stream; charset=utf-8",
    })
