"""
app.py — Flask application routes
This is the main entry point. It wires together all modules:
  config.py  → AWS SSM Parameter Store
  db.py      → Amazon RDS (MySQL) / SQLite
  storage.py → Amazon S3
  notify.py  → Amazon SNS
  logs.py    → Amazon CloudWatch Logs
"""

import os
import logging
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
    send_from_directory,
    abort,
)
from werkzeug.security import generate_password_hash, check_password_hash
from markupsafe import escape

from config import get_config
from logs import setup_logging
import db
import storage
import notify

# ── App setup ────────────────────────────────────────────────────────────

app = Flask(__name__)
cfg = get_config()
app.secret_key = cfg["secret_key"]
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload limit

logger = setup_logging(app)


# ── Auth helpers ─────────────────────────────────────────────────────────


def login_required(f):
    """Decorator: redirect to login if the user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorator: only allow users with role='admin'."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ── Template context ─────────────────────────────────────────────────────

@app.context_processor
def inject_user():
    """Make current user info and campus taxonomies available in all templates."""
    return {
        "current_user_id": session.get("user_id"),
        "current_email": session.get("email"),
        "current_role": session.get("role"),
        "CAMPUS_CATEGORIES": db.CATEGORIES,
        "CAMPUS_LOCATIONS": db.LOCATIONS,
    }


# ── Serve local uploads (LOCAL_DEV only) ─────────────────────────────────

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    """Serve uploaded files from the local uploads directory."""
    return send_from_directory(storage.UPLOAD_DIR, filename)


# ── Public pages ─────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Home page with executive hero, multi-filter search, and recent items."""
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    category = request.args.get("category", "").strip()
    location = request.args.get("location", "").strip()

    items = db.list_items(
        cfg,
        q=q or None,
        status=status or None,
        category=category or None,
        location=location or None,
    )
    for item in items:
        item["photo_url"] = storage.photo_url(cfg, item.get("photo_key"))
        item["ref_code"] = f"REF-LF-{item['id']:04d}"

    total_items = db.count_items(cfg)
    claimed_items = db.count_items_claimed(cfg)
    pending_claims = db.count_claims_pending(cfg)

    return render_template(
        "index.html",
        items=items,
        q=q,
        status=status,
        category=category,
        location=location,
        total_items=total_items,
        claimed_items=claimed_items,
        pending_claims=pending_claims,
    )


@app.route("/items")
def items_list():
    """List items with multi-faceted search and status/category/location filters."""
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    category = request.args.get("category", "").strip()
    location = request.args.get("location", "").strip()

    items = db.list_items(
        cfg,
        q=q or None,
        status=status or None,
        category=category or None,
        location=location or None,
    )
    for item in items:
        item["photo_url"] = storage.photo_url(cfg, item.get("photo_key"))
        item["ref_code"] = f"REF-LF-{item['id']:04d}"

    return render_template(
        "items.html",
        items=items,
        q=q,
        status=status,
        category=category,
        location=location,
    )


@app.route("/items/<int:item_id>")
def item_detail(item_id):
    """Detail page for a single item with claim form, QR code tag, and smart matches."""
    item = db.get_item(cfg, item_id)
    if not item:
        abort(404)

    item["photo_url"] = storage.photo_url(cfg, item.get("photo_key"))
    item["ref_code"] = f"REF-LF-{item['id']:04d}"
    reporter = db.get_user_by_id(cfg, item["reported_by"])

    # Smart Matching Algorithm (USP feature)
    matches = db.find_smart_matches(cfg, item, limit=3)
    for m in matches:
        m["photo_url"] = storage.photo_url(cfg, m.get("photo_key"))
        m["ref_code"] = f"REF-LF-{m['id']:04d}"

    return render_template(
        "item_detail.html",
        item=item,
        reporter=reporter,
        matches=matches,
    )



# ── Auth routes ──────────────────────────────────────────────────────────

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register a new student account with persona onboarding flow."""
    intent = request.args.get("intent", request.form.get("intent", "")).strip().lower()

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("register.html", intent=intent)

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("register.html", intent=intent)

        existing = db.get_user_by_email(cfg, email)
        if existing:
            flash("An account with that email already exists.", "error")
            return render_template("register.html", intent=intent)

        pw_hash = generate_password_hash(password)
        user_id = db.create_user(cfg, email, pw_hash)
        logger.info(f"New user registered: {email} (id={user_id}, intent={intent})")

        session["user_id"] = user_id
        session["email"] = email
        session["role"] = "student"
        flash("Account created! Welcome to the campus registry.", "success")

        # Smooth persona flow: redirect straight to relevant filing form
        if intent == "lost":
            return redirect(url_for("item_new", status="LOST"))
        elif intent == "found":
            return redirect(url_for("item_new", status="FOUND"))
        return redirect(url_for("index"))

    return render_template("register.html", intent=intent)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log in with email and password with persona onboarding flow."""
    intent = request.args.get("intent", request.form.get("intent", "")).strip().lower()

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        user = db.get_user_by_email(cfg, email)
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
            return render_template("login.html", intent=intent)

        session["user_id"] = user["id"]
        session["email"] = user["email"]
        session["role"] = user["role"]
        logger.info(f"User logged in: {email}")

        flash("Logged in successfully!", "success")

        # Smooth persona flow: redirect straight to relevant filing form
        if intent == "lost":
            return redirect(url_for("item_new", status="LOST"))
        elif intent == "found":
            return redirect(url_for("item_new", status="FOUND"))
        return redirect(url_for("index"))

    return render_template("login.html", intent=intent)


@app.route("/logout")
def logout():
    """Log out and clear the session."""
    email = session.get("email", "unknown")
    session.clear()
    logger.info(f"User logged out: {email}")
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# ── Item management ──────────────────────────────────────────────────────

@app.route("/items/new", methods=["GET", "POST"])
@login_required
def item_new():
    """Report a new lost or found item."""
    initial_status = request.args.get("status", "LOST").upper()
    if initial_status not in ("LOST", "FOUND"):
        initial_status = "LOST"

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        status = request.form.get("status", "LOST")
        category = request.form.get("category", "Other").strip()
        location = request.form.get("location", "Campus Grounds & Parking").strip()
        verification_question = request.form.get("verification_question", "").strip()

        if not title or not description:
            flash("Title and description are required.", "error")
            return render_template("item_new.html", initial_status=status)

        if status not in ("LOST", "FOUND"):
            flash("Invalid status.", "error")
            return render_template("item_new.html", initial_status=status)

        # Handle photo upload
        photo_key = None
        photo = request.files.get("photo")
        if photo and photo.filename:
            try:
                photo_key = storage.upload_photo(cfg, photo)
            except ValueError as e:
                flash(str(e), "error")
                return render_template("item_new.html", initial_status=status)

        item_id = db.create_item(
            cfg,
            title,
            description,
            status,
            photo_key,
            session["user_id"],
            category=category,
            location=location,
            verification_question=verification_question,
        )
        logger.info(
            f"Item created: '{title}' (id={item_id}, status={status}, cat={category}) by {session['email']}"
        )
        flash("Item reported successfully to the campus registry!", "success")
        return redirect(url_for("item_detail", item_id=item_id))

    return render_template("item_new.html", initial_status=initial_status)



# ── Claims ───────────────────────────────────────────────────────────────

@app.route("/items/<int:item_id>/claim", methods=["POST"])
@login_required
def claim_item(item_id):
    """Submit a claim on an item with optional security verification answer."""
    item = db.get_item(cfg, item_id)
    if not item:
        abort(404)

    if item["status"] == "CLAIMED":
        flash("This item has already been marked as claimed.", "warning")
        return redirect(url_for("item_detail", item_id=item_id))

    message = request.form.get("message", "").strip()
    verification_answer = request.form.get("verification_answer", "").strip()

    if not message:
        flash("Please provide details supporting your claim.", "error")
        return redirect(url_for("item_detail", item_id=item_id))

    claim_id = db.create_claim(
        cfg,
        item_id,
        session["user_id"],
        message,
        verification_answer=verification_answer,
    )
    logger.info(
        f"Claim created: claim_id={claim_id} on item_id={item_id} by {session['email']}"
    )

    # Send notification
    try:
        notify.notify_claim(cfg, item, session["email"])
    except Exception as e:
        logger.error(f"Failed to send claim notification: {e}")

    flash("Your claim has been recorded! Campus administration will review your verification details.", "success")
    return redirect(url_for("item_detail", item_id=item_id))


# ── Admin ────────────────────────────────────────────────────────────────

@app.route("/admin")
@admin_required
def admin():
    """Admin dashboard with stats, claims audit, and administrative controls."""
    total_items = db.count_items(cfg)
    pending_claims = db.count_claims_pending(cfg)
    claimed_items = db.count_items_claimed(cfg)
    claims = db.list_claims(cfg)
    return render_template(
        "admin.html",
        total_items=total_items,
        pending_claims=pending_claims,
        claimed_items=claimed_items,
        claims=claims,
    )


@app.route("/admin/claims/<int:claim_id>/<action>", methods=["POST"])
@admin_required
def admin_claim_action(claim_id, action):
    """Approve or reject a claim."""
    if action not in ("approve", "reject"):
        abort(400)

    claim = db.get_claim(cfg, claim_id)
    if not claim:
        abort(404)

    if action == "approve":
        db.update_claim_status(cfg, claim_id, "APPROVED")
        db.update_item_status(cfg, claim["item_id"], "CLAIMED")
        logger.info(f"Claim {claim_id} APPROVED by admin {session['email']}")
        flash("Claim approved! Item has been officially designated as CLAIMED.", "success")
    else:
        db.update_claim_status(cfg, claim_id, "REJECTED")
        logger.info(f"Claim {claim_id} REJECTED by admin {session['email']}")
        flash("Claim was rejected.", "info")

    return redirect(url_for("admin"))


@app.route("/admin/export/csv")
@admin_required
def admin_export_csv():
    """Export all claims and audit records to CSV (USP Feature)."""
    import csv
    import io
    from flask import Response

    claims = db.list_claims(cfg)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Claim ID",
        "Item ID",
        "Item Title",
        "Category",
        "Location",
        "Claimer Email",
        "Claim Status",
        "Date Submitted",
        "Verification Question",
        "Claimant Answer",
        "Message",
    ])

    for c in claims:
        writer.writerow([
            c.get("id"),
            c.get("item_id"),
            c.get("item_title"),
            c.get("item_category", "General"),
            c.get("item_location", "Campus Grounds"),
            c.get("claimer_email"),
            c.get("status"),
            c.get("created_at"),
            c.get("item_verification_question", ""),
            c.get("verification_answer", ""),
            c.get("message", ""),
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=campus_lost_found_audit.csv"},
    )



# ── Utility routes ───────────────────────────────────────────────────────

@app.route("/health")
def health():
    """Health check endpoint for load balancers and monitoring."""
    return "ok"


@app.route("/simulate-error")
def simulate_error():
    """Simulate an error to test CloudWatch alarms."""
    logger.error("SIMULATED ERROR — this is a test for CloudWatch alarm triggering")
    raise RuntimeError("Simulated 500 error for CloudWatch alarm demo")


@app.errorhandler(403)
def forbidden(e):
    """Custom 403 page."""
    return render_template("error.html", code=403, message="Access denied."), 403


@app.errorhandler(404)
def not_found(e):
    """Custom 404 page."""
    return render_template("error.html", code=404, message="Page not found."), 404


@app.errorhandler(500)
def server_error(e):
    """Custom 500 page."""
    logger.error(f"Internal server error: {e}")
    return render_template("error.html", code=500, message="Something went wrong."), 500


# ── Main ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Local development mode
    app.run(debug=True, host="0.0.0.0", port=5000)
