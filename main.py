import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, request, jsonify, send_from_directory
from backend.db import (
    init_db, insert_lead, insert_land_data, save_message,
    get_leads, get_messages, approve_message, get_active_signals,
)
from backend.logic  import calculate_usd_m2, score_risk
from backend.agents import generate_all

app = Flask(__name__, static_folder="frontend", static_url_path="")


# ── Static UI ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("frontend", "index.html")

@app.route("/admin")
def admin():
    return send_from_directory("frontend", "admin.html")


# ── Core analysis ──────────────────────────────────────────────────────────

@app.route("/api/analyze", methods=["POST"])
def analyze():
    body = request.get_json(force=True)

    name                = body.get("name", "")
    email               = body.get("email", "")
    phone               = body.get("phone", "")
    language            = body.get("language", "en")
    budget_usd          = float(body.get("budget_usd", 0))
    land_type           = body.get("land_type", "agricultural")
    area_m2             = float(body.get("area_m2", 1000))
    location            = body.get("location", "")
    road_type           = body.get("road_type", "provincial_road")
    highway_proximity_m = float(body.get("highway_proximity_m", 100))
    title_constraints   = body.get("title_constraints", ["no_issue"])
    gov_signal          = body.get("gov_signal", "none")

    analysis = calculate_usd_m2(land_type, area_m2, gov_signal)
    risk     = score_risk(title_constraints, highway_proximity_m, road_type)
    messages = generate_all(analysis, risk)

    lead_id = insert_lead(name, email, phone, language, budget_usd)
    insert_land_data(lead_id, land_type, area_m2, location, road_type,
                     highway_proximity_m, title_constraints, gov_signal)

    for m in messages:
        save_message(lead_id, m["agent"], m["lang"], m["message"], m["status"])

    return jsonify({"lead_id": lead_id, "analysis": analysis, "risk": risk, "messages": messages})


# ── Leads ──────────────────────────────────────────────────────────────────

@app.route("/api/leads", methods=["GET"])
def leads():
    return jsonify(get_leads())

@app.route("/api/leads/<int:lead_id>/messages", methods=["GET"])
def lead_messages(lead_id):
    return jsonify(get_messages(lead_id))


# ── Messages ───────────────────────────────────────────────────────────────

@app.route("/api/messages/<int:msg_id>/approve", methods=["POST"])
def approve(msg_id):
    approve_message(msg_id)
    return jsonify({"ok": True, "message_id": msg_id, "status": "APPROVED"})


# ── Gov Signals ────────────────────────────────────────────────────────────

@app.route("/api/signals", methods=["GET"])
def signals():
    return jsonify(get_active_signals())


# ── Entry ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    from backend.seed import seed
    seed()
    port = int(os.environ.get("PORT", 5000))
    print(f"LandGold Intelligence  →  http://localhost:{port}")
    print(f"Admin Panel            →  http://localhost:{port}/admin")
    app.run(host="0.0.0.0", port=port, debug=False)
