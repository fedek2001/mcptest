from flask import Flask, request, Response
import json, time
app = Flask(__name__)

def sse(event, data):
    return (f"event: {event}\n" + "data: " + json.dumps(data, ensure_ascii=False) + "\n\n").encode("utf-8")

@app.post("/api/mcp/invoke")
def invoke():
    payload = request.get_json(silent=True) or {}
    tool = payload.get("tool"); args = payload.get("args") or {}; req_id = payload.get("request_id")

    def gen():
        yield sse("start", {"request_id": req_id})
        time.sleep(0.03)
        if tool != "reverse":
            yield sse("result", {"ok": False, "error": f"unknown tool: {tool}"})
        else:
            txt = str(args.get("text",""))
            yield sse("result", {"ok": True, "output": txt[::-1]})
        yield sse("end", {"request_id": req_id})

    return Response(gen(), headers={
        "Cache-Control":"no-cache, no-transform",
        "Connection":"keep-alive",
        "X-Accel-Buffering":"no",
        "Content-Type":"text/event-stream; charset=utf-8",
    })
