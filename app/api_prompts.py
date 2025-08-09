# app/api_prompts.py
from flask import Blueprint, jsonify
from app.prompts.loader import list_detect_prompts, read_detect_prompt

prompts_bp = Blueprint("prompts_bp", __name__)

@prompts_bp.get("/api/prompts/detect_highlight")
def api_list_detect_prompts():
    items = [{"name": n, "label": n.replace("_", " ")} for n in list_detect_prompts()]
    return jsonify({"items": items})

@prompts_bp.get("/api/prompts/detect_highlight/<name>")
def api_get_detect_prompt(name):
    try:
        content = read_detect_prompt(name)
        return jsonify({"name": name, "content": content})
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
