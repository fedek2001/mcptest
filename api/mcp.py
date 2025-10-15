from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Any, Dict, Generator
import json, asyncio, time

# SDK oficial
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("vercel-mcp-python")

@mcp.tool()
def reverse(text: str) -> str:
    """Invierte un string."""
    return text[::-1]

@mcp.tool()
def add(a: float, b: float) -> float:
    """Suma dos números."""
    return a + b

app = FastAPI()

@app.post("/api/mcp/session")
async def session():
    # Exponer capacidades + tools (esquema simple compatible con clientes HTTP)
    tools = []
    for t in mcp.list_tools():
        tools.append({
            "name": t.name,
            "description": t.description or "",
            "args_schema": t.json_schema  # generado por FastMCP
        })
    return JSONResponse({
        "protocol": "mcp-http-sse",
        "server": {"name": "vercel-mcp-python", "version": "0.1.0"},
        "capabilities": {"tools": True, "streaming": "sse"},
        "tools": tools
    })

def sse_event(event: str, data: Dict[str, Any]) -> bytes:
    return (f"event: {event}\n" + "data: " + json.dumps(data, ensure_ascii=False) + "\n\n").encode("utf-8")

@app.post("/api/mcp/invoke")
async def invoke(req: Request):
    payload = await req.json()
    tool = payload.get("tool")
    args = payload.get("args", {}) or {}
    req_id = payload.get("request_id")

    # Look-up del tool registrado en FastMCP
    tool_impl = next((t for t in mcp.list_tools() if t.name == tool), None)
    if tool_impl is None:
        return JSONResponse({"error": f"unknown tool: {tool}"}, status_code=400)

    async def gen() -> Generator[bytes, None, None]:
        yield sse_event("start", {"request_id": req_id})
        for p in (0.1, 0.35, 0.7):
            await asyncio.sleep(0.05)
            yield sse_event("chunk", {"progress": p, "message": f"processing {int(p*100)}%"})
        try:
            # Invocar respetando sync/async
            if tool_impl.is_async:
                output = await tool_impl.fn(**args)
            else:
                output = tool_impl.fn(**args)
            yield sse_event("result", {"ok": True, "output": output})
        except Exception as e:
            yield sse_event("result", {"ok": False, "error": str(e)})
        yield sse_event("end", {"request_id": req_id})

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        "Content-Type": "text/event-stream; charset=utf-8"
    }
    return StreamingResponse(gen(), headers=headers)

@app.get("/api/mcp/health")
async def health():
    return JSONResponse({"status": "ok"})
