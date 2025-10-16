from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import json, asyncio
from mcp.server.fastmcp import FastMCP  # o 'from fastmcp import FastMCP' si usás la librería 3rd-party

app = FastAPI()
mcp = FastMCP("vercel-mcp-python")

@mcp.tool()
def reverse(text: str) -> str:
    return text[::-1]

@app.post("/session")
async def session():
    tools = []
    for t in mcp.list_tools():
        tools.append({"name": t.name, "description": t.description or "", "args_schema": t.json_schema})
    return JSONResponse({
        "protocol": "mcp-http-sse",
        "server": {"name": "vercel-mcp-python", "version": "0.1.0"},
        "capabilities": {"tools": True, "streaming": "sse"},
        "tools": tools
    })

def sse(event: str, data: dict) -> bytes:
    return (f"event: {event}\n" + "data: " + json.dumps(data, ensure_ascii=False) + "\n\n").encode("utf-8")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/invoke")
async def invoke(req: Request):
    payload = await req.json()
    tool = payload.get("tool")
    args = payload.get("args") or {}
    req_id = payload.get("request_id")

    tool_impl = next((t for t in mcp.list_tools() if t.name == tool), None)
    if tool_impl is None:
        return JSONResponse({"error": f"unknown tool: {tool}"}, status_code=400)

    async def gen():
        yield sse("start", {"request_id": req_id})
        for p in (0.1, 0.35, 0.7):
            await asyncio.sleep(0.05)
            yield sse("chunk", {"progress": p})
        try:
            out = await tool_impl.fn(**args) if tool_impl.is_async else tool_impl.fn(**args)
            yield sse("result", {"ok": True, "output": out})
        except Exception as e:
            yield sse("result", {"ok": False, "error": str(e)})
        yield sse("end", {"request_id": req_id})

    return StreamingResponse(gen(), media_type="text/event-stream")
