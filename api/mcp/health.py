from flask import Flask, jsonify, request
app = Flask(__name__)

# La URL pública será EXACTAMENTE /api/mcp/health
@app.get("/api/mcp/health")
def health():
    return jsonify({"ok": True, "path": request.path})
