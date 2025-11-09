import os
import json
import random
import uuid
import requests
import psycopg2
import fakeredis
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify
from hashlib import sha256
from flask import render_template

app = Flask(__name__)

# === PostgreSQL Config ===
def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        user="postgres",
        password="Naruto@148",
        port="5432",
        database="group_access"
    )

# === In-memory Redis Replacement (for local practice) ===
redis_client = fakeredis.FakeStrictRedis()  #  replaces redis.StrictRedis()

# === Constants ===
SENDGRID_API_KEY = "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"
SENDER_EMAIL = "psharathkumar21@gmail.com"
OTP_TTL_MINUTES = 10
RESET_TOKEN_TTL_MINUTES = 15

# === Helper: Send Email ===
def send_email_via_sendgrid(receiver_email, subject, plain_text_content):
    """Send email using SendGrid REST API."""
    if not SENDGRID_API_KEY:
        print(f"[DEV] Email to {receiver_email}:\n{plain_text_content}")
        return True

    url = "https://api.sendgrid.com/v3/mail/send"
    payload = {
        "personalizations": [{"to": [{"email": receiver_email}]}],
        "from": {"email": SENDER_EMAIL},
        "subject": subject,
        "content": [{"type": "text/plain", "value": plain_text_content}]
    }
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json"
    }

    resp = requests.post(url, headers=headers, json=payload)
    return resp.status_code in (200, 202)

# === Helper: OTP Operations (using fakeredis) ===
def save_otp_to_cache(email, otp_data):
    """Save OTP data with expiry."""
    key = f"otp:{email}"
    redis_client.setex(key, OTP_TTL_MINUTES * 60, json.dumps(otp_data))

def get_otp_from_cache(email):
    key = f"otp:{email}"
    data = redis_client.get(key)
    return json.loads(data) if data else None

def delete_otp_from_cache(email):
    key = f"otp:{email}"
    redis_client.delete(key)

# === Helper: Generate OTP ===
def generate_otp():
    """Generate 6-digit OTP."""
    return f"{random.randint(100000, 999999):06d}"

# === ROUTES ===
#@app.route("/")
#def home():
    #return jsonify({"message": "Flask Forgot-Password API with Fakeredis + PostgreSQL + SendGrid + SHA256."})
    
@app.route("/")
def home():
    return render_template("login.html")

# 1 Send OTP
@app.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "Email is required"}), 400

    # Check if user exists
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM active_directory WHERE lower(user_email) = %s", (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        return jsonify({"error": "Email not found"}), 404

    # Generate OTP
    otp = generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES)
    otp_data = {
        "otp": otp,
        "expires_at": expires_at.isoformat(),
        "verified": False,
        "reset_token": None,
        "reset_token_expires_at": None
    }
    save_otp_to_cache(email, otp_data)

    # Send Email
    subject = "Your OTP for Password Reset"
    body = f"Hello {user.get('first_name', '')},\n\nYour OTP is: {otp}\nValid for {OTP_TTL_MINUTES} minutes.\n\nIf not requested, ignore this email."
    sent = send_email_via_sendgrid(email, subject, body)

    if sent:
        return jsonify({"message": "OTP sent successfully"}), 200
    return jsonify({"error": "Failed to send OTP"}), 500

# 2 Verify OTP
@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    otp = str(data.get("otp", "")).strip()

    if not email or not otp:
        return jsonify({"error": "Email and OTP are required"}), 400

    record = get_otp_from_cache(email)
    if not record:
        return jsonify({"error": "No OTP request found"}), 404

    # Check expiry
    if datetime.now(timezone.utc) > datetime.fromisoformat(record["expires_at"]):
        delete_otp_from_cache(email)
        return jsonify({"error": "OTP expired"}), 410

    if otp != record["otp"]:
        return jsonify({"error": "Invalid OTP"}), 400

    # OTP verified - create reset token
    reset_token = uuid.uuid4().hex
    reset_expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)
    record.update({
        "verified": True,
        "reset_token": reset_token,
        "reset_token_expires_at": reset_expires_at.isoformat()
    })
    save_otp_to_cache(email, record)

    return jsonify({
        "message": "OTP verified successfully",
        "reset_token": reset_token
    }), 200

# 3 Reset Password
@app.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    reset_token = data.get("reset_token", "").strip()
    new_password = data.get("new_password", "")
    confirm_password = data.get("confirm_password", "")

    if not all([email, reset_token, new_password, confirm_password]):
        return jsonify({"error": "All fields are required"}), 400

    if new_password != confirm_password:
        return jsonify({"error": "Passwords do not match"}), 400

    record = get_otp_from_cache(email)
    if not record or not record.get("verified"):
        return jsonify({"error": "Invalid or missing OTP verification"}), 400

    if record.get("reset_token") != reset_token:
        return jsonify({"error": "Invalid reset token"}), 401

    if datetime.now(timezone.utc) > datetime.fromisoformat(record.get("reset_token_expires_at", datetime.min.isoformat())):
        delete_otp_from_cache(email)
        return jsonify({"error": "Reset token expired"}), 410

    #  Hash new password using SHA256
    hashed = sha256(new_password.encode('utf-8')).hexdigest()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE active_directory SET password = %s WHERE lower(user_email) = %s",
        (hashed, email)
    )
    conn.commit()
    cur.close()
    conn.close()

    delete_otp_from_cache(email)
    return jsonify({"message": "Password updated successfully"}), 200

# === Run App ===
if __name__ == "__main__":
    app.run(debug=True)
