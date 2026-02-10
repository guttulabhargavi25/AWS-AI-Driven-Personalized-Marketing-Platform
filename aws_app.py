from flask import Flask, render_template, request, redirect, url_for, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import boto3
import uuid
import os
from botocore.exceptions import ClientError

# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)
app.secret_key = "marketing_secret_key"

app.config["SESSION_PERMANENT"] = True

# =========================================================
# AWS CONFIG
# =========================================================

AWS_REGION = "us-east-1"
#SNS topic is pre-created in AWS (Production)
# This application ONLY publishes messages to the topic.
 """
    Publishes a message to AWS SNS.

    - Topic must already exist in AWS.
    - App does not create or manage SNS topics.
    - Permissions are provided via IAM Role.
    """
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
# Replace with your actual SNS Topic ARN in AWS
sns = boto3.client("sns", region_name=AWS_REGION)

users_table = dynamodb.Table("users")
campaigns_table = dynamodb.Table("campaigns")
customers_table = dynamodb.Table("customers")

# =========================================================
# SNS HELPER
# =========================================================

def send_notification(subject, message):
      """
    Publishes a notification message to AWS SNS.

    Design Notes:
    - SNS topic lifecycle is NOT handled by this application.
    - The topic must already exist in the target AWS account.
    - This function ONLY publishes messages.
    - Permissions are provided via IAM Role attached to EC2 / EB.

    This design follows AWS best practices by separating
    application logic from infrastructure provisioning.
    """


    if not SNS_TOPIC_ARN:
        return
    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message
        )
    except ClientError as e:
        print("SNS error:", e)

# =========================================================
# AI ENGINE
# =========================================================

def calculate_engagement_score(opens, clicks):
    score = (opens * 10) + (clicks * 20)
    return score, recommend_channel(score)

def recommend_channel(score):
    if score >= 80:
        return "Email"
    elif score >= 40:
        return "SMS"
    return "Push Notification"

# =========================================================
# AUTH DECORATORS
# =========================================================

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get("role") not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator

# =========================================================
# ROUTES
# =========================================================

@app.route("/")
def index():
    return render_template("index.html")

# ---------------- SIGNUP ----------------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        role = request.form["role"].lower()

        try:
            users_table.put_item(
                Item={"email": email, "password": password, "role": role},
                ConditionExpression="attribute_not_exists(email)"
            )
        except Exception:
            return render_template("signup.html", error="User already exists")

        # AUTO LOGIN (FIX)
        session.clear()
        session.permanent = True
        session["logged_in"] = True
        session["email"] = email
        session["role"] = role

        send_notification("New User Signup", f"{email} registered as {role}")

        return redirect(url_for("dashboard"))

    return render_template("signup.html")

# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        response = users_table.get_item(Key={"email": email})
        user = response.get("Item")

        if user and check_password_hash(user["password"], password):
            session.clear()
            session.permanent = True
            session["logged_in"] = True
            session["email"] = email
            session["role"] = user["role"]

            send_notification("User Login", f"{email} logged in")

            return redirect(url_for("dashboard"))

        return "Invalid credentials"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
@login_required
def dashboard():
     print("DASHBOARD SESSION:", session)  # DEBUG

     return render_template(
        "dashboard.html",
        role=session["role"],
        email=session["email"]
    )

# ---------------- ADMIN ----------------

@app.route("/admin")
@login_required
@role_required(["admin"])
def admin():
    users = users_table.scan().get("Items", [])
    return render_template("admin.html", users=users)

# ---------------- CAMPAIGN ----------------

@app.route("/campaign", methods=["GET", "POST"])
@login_required
def campaign():
    if request.method == "POST":
        score, channel = calculate_engagement_score(4, 3)
        name = request.form["name"]

        campaigns_table.put_item(
            Item={
                "id": str(uuid.uuid4()),
                "name": name,
                "channel": channel,
                "start_date": request.form["start_date"],
                "end_date": request.form["end_date"],
                "status": "Active"
            }
        )

        send_notification("New Campaign", f"{name} via {channel}")

        return redirect(url_for("campaign_history"))

    return render_template("campaign.html")

@app.route("/campaign_history")
@login_required
def campaign_history():
    campaigns = campaigns_table.scan().get("Items", [])
    return render_template("campaign_history.html", campaigns=campaigns)

@app.route("/delete_campaign/<string:id>", methods=["POST"])
@login_required
@role_required(["admin"])
def delete_campaign(id):
    campaigns_table.delete_item(Key={"id": id})
    return redirect(url_for("campaign_history"))

# ---------------- CUSTOMER ----------------

@app.route("/customer", methods=["GET", "POST"])
@login_required
def customer():
    if request.method == "POST":
        score, channel = calculate_engagement_score(
            int(request.form["opens"]),
            int(request.form["clicks"])
        )

        name = request.form["name"]

        customers_table.put_item(
            Item={
                "id": str(uuid.uuid4()),
                "name": name,
                "email": request.form["email"],
                "phone": request.form["phone"],
                "engagement_score": score,
                "preferred_channel": channel
            }
        )

        send_notification("New Customer", f"{name} prefers {channel}")

    customers = customers_table.scan().get("Items", [])
    return render_template("customer.html", customers=customers)

# ---------------- ERROR ----------------

@app.errorhandler(403)
def forbidden(e):
    return "<h2>403 - Access Denied</h2>", 403

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)

