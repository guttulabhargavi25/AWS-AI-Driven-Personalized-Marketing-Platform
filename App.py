from flask import Flask, render_template, request, redirect, url_for, session, abort
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from ai_engine import calculate_engagement_score, recommend_channel

app = Flask(__name__)
app.secret_key = "marketing_secret_key"
DB_NAME = "marketing.db"

# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            target TEXT,
            status TEXT,
            channel TEXT,
            start_date TEXT,
            end_date TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            engagement_score INTEGER DEFAULT 0,
            preferred_channel TEXT
        )
    """)

    conn.commit()
    conn.close()

create_tables()

# ---------------- AUTH DECORATORS ----------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get("role") not in allowed_roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ---------------- ROUTES ----------------

@app.route("/")
def index():
    return render_template("index.html")

# ---------- AUTH ----------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        role = request.form["role"].lower()   # admin / marketer / staff

        if role not in ["admin", "marketer", "staff"]:
            return render_template("signup.html", error="Invalid role")

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (email, password, role) VALUES (?, ?, ?)",
                (email, password, role)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            return render_template("signup.html", error="User already exists")
        finally:
            conn.close()

        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            # ✅ SET SESSION PROPERLY
            session["logged_in"] = True
            session["email"] = user["email"]
            session["role"] = user["role"]  #lower case

            return redirect(url_for("dashboard"))

        return "Invalid credentials"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------- DASHBOARD ----------

@app.route("/dashboard")
@login_required
def dashboard():
    print("DASHBOARD SESSION:", session)  # DEBUG

    return render_template(
        "dashboard.html",
        role=session["role"],
        email=session["email"]
    )
# ---------- ADMIN ----------

@app.route("/admin")
@role_required(["admin"])
def admin():
    conn = get_db()
    users = conn.execute("SELECT email, role FROM users").fetchall()
    conn.close()
    return render_template("admin.html", users=users)

# ---------- CAMPAIGN ----------

@app.route("/campaign", methods=["GET", "POST"])
@login_required
def campaign():
    if request.method == "POST":
        name = request.form["name"]
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]

        # AI recommendation
        engagement_level, score = calculate_engagement_score(4, 3)
        channel = recommend_channel(engagement_level)

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO campaigns (name, channel, start_date, end_date, status)
            VALUES (?, ?, ?, ?, ?)
        """, (name, channel, start_date, end_date, "Active"))

        conn.commit()
        conn.close()

        return redirect(url_for("campaign_history"))

    return render_template("campaign.html")

@app.route("/campaign_history")
@login_required
def campaign_history():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, channel, start_date, end_date, status
        FROM campaigns
        ORDER BY id DESC
    """)
    campaigns = cur.fetchall()

    conn.close()
    return render_template("campaign_history.html", campaigns=campaigns)

@app.route("/customer", methods=["GET", "POST"])
@login_required
def customer():
    conn = get_db()

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]

        opens = int(request.form["opens"])
        clicks = int(request.form["clicks"])

        engagement_score, preferred_channel = calculate_engagement_score(opens, clicks)
        # 💾 STORE AI OUTPUT
        conn.execute("""
            INSERT INTO customers 
            (name, email, phone, engagement_score, preferred_channel)
            VALUES (?, ?, ?, ?, ?)
        """, (name, email, phone,engagement_score, preferred_channel))

        conn.commit()

    customers = conn.execute("SELECT * FROM customers").fetchall()
    conn.close()

    return render_template("customer.html", customers=customers)

@app.route("/delete_campaign/<int:id>", methods=["POST"])
@role_required(["admin"])
def delete_campaign(id):
    conn = get_db()
    conn.execute("DELETE FROM campaigns WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("campaign_history"))

# ---------- ERROR ----------

@app.errorhandler(403)
def forbidden(e):
    return "<h2>403 - Access Denied</h2>", 403

if __name__ == "__main__":
    app.run(debug=True)
