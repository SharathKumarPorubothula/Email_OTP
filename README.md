🔐 Flask Forgot Password System (OTP + SendGrid + PostgreSQL)

A complete Forgot Password API built using Flask, PostgreSQL, and SendGrid, featuring secure OTP verification, password hashing, and token-based reset flow.
This project uses fakeredis for local OTP storage — no external Redis setup required!

🚀 Features

✅ Send OTP to registered email using SendGrid API
🔎 Verify OTP with expiry validation
🔄 Reset password securely using reset tokens
🧠 Uses fakeredis for OTP storage (simulates Redis locally)
💾 Stores user info in PostgreSQL
🔐 Passwords hashed using SHA256
🧰 Easy to test using Postman

🧰 Tech Stack
Component	Technology
Backend	Flask (Python)
Database	PostgreSQL
Email	SendGrid API
Caching	fakeredis
Hashing	SHA256

⚙️ Installation & Setup

Clone the repository

git clone https://github.com/<your-username>/flask-forgot-password.git
cd flask-forgot-password

Create a virtual environment

python -m venv venv
source venv/Scripts/activate  # On Windows
# or
source venv/bin/activate      # On macOS/Linux

Install dependencies

pip install flask psycopg2 fakeredis requests

Set your environment variables

export SENDGRID_API_KEY="SG.xxxxxxx"    # (Use your SendGrid key)
export FLASK_ENV=development

(On Windows PowerShell use set instead of export)

Update your PostgreSQL credentials
Edit the get_db_connection() function:

psycopg2.connect(
    host="localhost",
    user="postgres",
    password="your_password",
    port="5432",
    database="group_access"
)

Run the app

python app.py

Flask will start at http://127.0.0.1:5000

🧩 API Endpoints

1️⃣ /forgot-password → Send OTP
Method: POST
Description: Sends a 6-digit OTP to the user’s registered email.

Request Body (JSON):
{
  "email": "user@example.com"
}

Response:
{
  "message": "OTP sent successfully"
}

2️⃣ /verify-otp → Verify OTP
Method: POST
Description: Verifies the OTP sent to the user’s email and returns a reset token.

Request Body (JSON):
{
  "email": "user@example.com",
  "otp": "123456"
}

Response:
{
  "message": "OTP verified successfully",
  "reset_token": "b7e5f2a9a1e94b5f8cf2749ea0b9e420"
}

3️⃣ /reset-password → Reset Password
Method: POST
Description: Allows the user to set a new password using the reset token.

Request Body (JSON):
{
  "email": "user@example.com",
  "reset_token": "b7e5f2a9a1e94b5f8cf2749ea0b9e420",
  "new_password": "NewPassword@123",
  "confirm_password": "NewPassword@123"
}

Response:
{
  "message": "Password updated successfully"
}

🧪 Testing with Postman

Run your Flask app.
Open Postman.
Use these API routes in order:

POST /forgot-password → enter your registered email.
Check your terminal (if no SendGrid key, OTP prints there).
POST /verify-otp → enter email + OTP.
Copy reset_token from response.
POST /reset-password → enter new password + reset token.

📦 Folder Structure
flask-forgot-password/
│
├── app.py
├── templates/
│   └── login.html
├── README.md
└── requirements.txt

🧠 Notes

OTP expires in 10 minutes
Reset token expires in 15 minutes
SHA256 used for password hashing
fakeredis automatically clears data when the app restarts
