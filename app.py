import os
import requests
import smtplib
import threading
from email.mime.text import MIMEText
from flask import Flask, jsonify, request
from flask_cors import CORS

# ==============================
# CONFIG (FIXED)
# ==============================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
print("API KEY:", OPENROUTER_API_KEY)
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")


EMERGENCY_CONTACTS = [
    "muralikrishnamortha6@gmail.com",
    "sunithadevimurtha77@gmail.com"
]

# ==============================
# APP INIT
# ==============================

app = Flask(__name__)
CORS(app)

chat_memory = []
accident_alert_sent = False
obd_thread = None

# Store latest OBD data
latest_data = {
    "rpm": 0,
    "speed": 0,
    "temperature": 0,
    "oil_life": 100
}

# ==============================
# HEALTH CHECK
# ==============================

@app.route("/")
def home():
    return jsonify({
        "status": "running",
        "service": "Engine AI Backend"
    })

# ==============================
# EMAIL SERVICE
# ==============================

def send_emergency_email(map_link):
    try:
        msg = MIMEText(f"""
🚨 Accident Alert

Live Location:
{map_link}
""")

        msg["Subject"] = "Vehicle Emergency Alert"
        msg["From"] = EMAIL_USER

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)

        for r in EMERGENCY_CONTACTS:
            server.sendmail(EMAIL_USER, r, msg.as_string())

        server.quit()
        print("✅ Email sent")

    except Exception as e:
        print("❌ Email error:", e)

# ==============================
# OBD CONTROL
# ==============================

def run_obd():
    import obd_bridge
    obd_bridge.start()

@app.route("/start-obd")
def start_obd():
    global obd_thread

    try:
        import obd
        connection = obd.OBD()

        if not connection.is_connected():
            return jsonify({"status": "failed"})

        if obd_thread is None or not obd_thread.is_alive():
            obd_thread = threading.Thread(target=run_obd, daemon=True)
            obd_thread.start()

        return jsonify({"status": "connected"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
# ==============================
# RECEIVE OBD DATA
# ==============================

@app.route("/engine-data", methods=["POST"])
def engine_data():
    global latest_data
    latest_data = request.json
    print("📡 OBD DATA:", latest_data)
    return jsonify({"status": "stored"})

# ==============================
# SEND OBD DATA TO FRONTEND
# ==============================

@app.route("/obd-data", methods=["GET"])
def obd_data():
    return jsonify(latest_data)

# ==============================
# CHAT AI (SAN)
# ==============================

import requests

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "")

    if not OPENROUTER_API_KEY:
        return jsonify({"reply": "AI key missing ❌"})

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are SAN, a friendly AI assistant. Talk in English and Telugu casually."},
                    {"role": "user", "content": user_message}
                ]
            },
            timeout=10
        )

        if response.status_code != 200:
            print("API ERROR:", response.text)
            return jsonify({"reply": "AI service error ⚠️"})

        data = response.json()

        if "choices" in data:
            reply = data["choices"][0]["message"]["content"]
        else:
            print("AI RESPONSE ERROR:", data)
            reply = "AI not responding properly 😢"

    except Exception as e:
        print("AI ERROR:", e)
        reply = "I'm offline now, but still here to help 😊"

    return jsonify({"reply": reply})
# ==============================
# LOCATION
# ==============================

@app.route("/update-location", methods=["POST"])
def update_location():
    return jsonify(request.json)

# ==============================
# ACCIDENT DETECTION
# ==============================

@app.route("/detect-accident", methods=["POST"])
def detect_accident():
    global accident_alert_sent

    data = request.json or {}

    speed = data.get("speed", 0)
    prev_speed = data.get("prev_speed", 0)
    lat = data.get("latitude")
    lon = data.get("longitude")

    accident = prev_speed > 60 and speed < 5

    map_link = f"https://maps.google.com/?q={lat},{lon}"

    if accident and not accident_alert_sent:
        send_emergency_email(map_link)
        accident_alert_sent = True

    if speed > 10:
        accident_alert_sent = False

    return jsonify({
        "accident_detected": accident,
        "map_link": map_link
    })

# ==============================
# OTHER FEATURES
# ==============================

@app.route("/detect-theft", methods=["POST"])
def detect_theft():
    data = request.json or {}
    return jsonify({
        "theft_detected": data.get("speed", 0) > 10 and not data.get("authorized", True)
    })

@app.route("/detect-fatigue", methods=["POST"])
def detect_fatigue():
    data = request.json or {}
    return jsonify({
        "fatigue_detected": data.get("driving_time", 0) > 120
    })

@app.route("/detect-overheat", methods=["POST"])
def detect_overheat():
    data = request.json or {}
    return jsonify({
        "overheat_detected": data.get("temperature", 0) > 100
    })

@app.route("/driving-coach", methods=["POST"])
def driving_coach():
    data = request.json or {}

    rpm = data.get("rpm", 0)
    temp = data.get("temperature", 0)

    if rpm > 4000:
        advice = "Reduce RPM"
    elif temp > 95:
        advice = "Engine heating"
    else:
        advice = "Normal"

    return jsonify({"advice": advice})

@app.route("/service-recommendation", methods=["POST"])
def service():
    oil = request.json.get("oil_life", 100)

    if oil < 30:
        msg = "Change oil soon"
    elif oil < 60:
        msg = "Plan service"
    else:
        msg = "All good"

    return jsonify({"service_recommendation": msg})

@app.route("/speed-monitor", methods=["POST"])
def speed():
    speed = request.json.get("speed", 0)
    return jsonify({
        "warning": speed > 120,
        "speed": speed
    })

# ==============================
# RUN
# ==============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
