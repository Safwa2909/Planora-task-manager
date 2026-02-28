from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from config import Config
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# -----------------------
# Database Connection
# -----------------------

def get_db_connection():
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    return conn

# -----------------------
# User Model
# -----------------------

class User(UserMixin):
    def __init__(self, id, username, email, password):
        self.id = id
        self.username = username
        self.email = email
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()

    if user:
        return User(user["id"], user["username"], user["email"], user["password"])
    return None

# -----------------------
# Routes
# -----------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, password)
            )
            conn.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))
        except:
            flash("Username or email already exists.", "danger")
        finally:
            conn.close()

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            user_obj = User(user["id"], user["username"], user["email"], user["password"])
            login_user(user_obj)
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials.", "danger")

    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection()
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC",
        (current_user.id,)
    ).fetchall()
    conn.close()

    today = datetime.today().date()

    todo_count = len([t for t in tasks if t["status"] == "todo"])
    progress_count = len([t for t in tasks if t["status"] == "progress"])
    done_count = len([t for t in tasks if t["status"] == "done"])

    return render_template(
        "dashboard.html",
        tasks=tasks,
        todo_count=todo_count,
        progress_count=progress_count,
        done_count=done_count,
        today=today
    )

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route("/add-task", methods=["POST"])
@login_required
def add_task():
    title = request.form["title"]
    description = request.form["description"]
    priority = request.form["priority"]
    due_date = request.form["due_date"]

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO tasks (user_id, title, description, priority, due_date) VALUES (?, ?, ?, ?, ?)",
        (current_user.id, title, description, priority, due_date)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))

@app.route("/delete-task/<int:task_id>")
@login_required
def delete_task(task_id):
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, current_user.id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))

@app.route("/update-status/<int:task_id>/<string:new_status>")
@login_required
def update_status(task_id, new_status):
    conn = get_db_connection()
    conn.execute(
        "UPDATE tasks SET status = ? WHERE id = ? AND user_id = ?",
        (new_status, task_id, current_user.id)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(debug=True)