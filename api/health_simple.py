from flask import Flask, jsonify, request

app = Flask(__name__)

# Acepta "/" y también "" por si Vercel pasa path vacío
@app.get("/", strict_slashes=False)
def root():
    return jsonify({"ok": True, "who": "health_simple", "path": request.path})
