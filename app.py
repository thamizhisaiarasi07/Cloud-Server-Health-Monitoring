from flask import Flask, jsonify, request, render_template

from database import Database

app = Flask(__name__)
db = Database("server_monitoring.db")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/dashboard")
def dashboard():
    db.simulate_next_cycle()
    summary = db.get_dashboard_summary()
    return jsonify(summary)


@app.route("/api/servers")
def get_servers():
    db.simulate_next_cycle()
    return jsonify({"servers": db.get_servers()})


@app.route("/api/servers/<server_id>")
def get_server(server_id):
    server = db.get_server_by_id(server_id)
    if server is None:
        return jsonify({"error": "Server not found"}), 404
    return jsonify({"server": server})


@app.route("/api/servers", methods=["POST"])
def create_server():
    payload = request.get_json(silent=True) or request.form or {}
    try:
        server = db.create_server(payload)
        return jsonify({"message": "Server added successfully", "server": server}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/servers/<server_id>", methods=["DELETE"])
def delete_server(server_id):
    deleted = db.delete_server(server_id)
    if not deleted:
        return jsonify({"error": "Server not found"}), 404
    return jsonify({"message": "Server removed successfully"})


@app.route("/api/alerts")
def get_alerts():
    alerts = db.get_alerts()
    return jsonify({"alerts": alerts})


@app.route("/api/alerts/<int:alert_id>/resolve", methods=["POST"])
def resolve_alert(alert_id):
    updated = db.resolve_alert(alert_id)
    if updated is None:
        return jsonify({"error": "Alert not found"}), 404
    return jsonify({"message": "Alert resolved successfully", "alerts": updated})


@app.route("/api/thresholds", methods=["GET", "POST"])
def thresholds():
    if request.method == "GET":
        return jsonify({"thresholds": db.get_threshold_map()})
    payload = request.get_json(silent=True) or {}
    if not payload:
        return jsonify({"error": "No threshold payload provided"}), 400
    db.set_thresholds(payload)
    return jsonify({"message": "Thresholds updated"})


@app.route("/api/history/<server_id>")
def history(server_id):
    entries = db.get_history(server_id)
    return jsonify({"history": entries})


@app.route("/api/servers/<server_id>/fail", methods=["POST"])
def fail_server(server_id):
    server = db.fail_server(server_id)
    if server is None:
        return jsonify({"error": "Server not found"}), 404
    return jsonify({"message": "Server marked offline", "server": server})


@app.route("/api/servers/<server_id>/recover", methods=["POST"])
def recover_server(server_id):
    server = db.recover_server(server_id)
    if server is None:
        return jsonify({"error": "Server not found"}), 404
    return jsonify({"message": "Server recovered successfully", "server": server})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=False)
