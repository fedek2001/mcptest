from flask import Flask, jsonify
app = Flask(__name__)

@app.post("/api/mcp/session")
def session():
    return jsonify({
        "protocol": "mcp-http-sse-minimal",
        "server": {"name": "vercel-mcp-python", "version": "0.1.0"},
        "capabilities": {"tools": True, "streaming": "sse"},
        "tools": [{"name":"reverse","description":"Invierte un string",
                   "args_schema":{"type":"object","properties":{"text":{"type":"string"}},"required":["text"]}}]
    })
