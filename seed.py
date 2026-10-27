"""
seed.py — Seed the database with sample data
Run with: LOCAL_DEV=1 python seed.py
Creates 1 admin user, 2 student users, and 8 sample items.
"""

import os
os.environ.setdefault("LOCAL_DEV", "1")

from werkzeug.security import generate_password_hash
from config import get_config
import db

cfg = get_config()

# Force a fresh connection
db._conn = None
db._get_conn(cfg)

print("Seeding database...")

# ── Users ────────────────────────────────────────────────────────────────
admin_pw = generate_password_hash("admin123")
student1_pw = generate_password_hash("student123")
student2_pw = generate_password_hash("student456")

# Check if admin already exists
existing = db.get_user_by_email(cfg, "admin@campus.edu")
if not existing:
    db.create_user(cfg, "admin@campus.edu", admin_pw, role="admin")
    print("  Created admin: admin@campus.edu / admin123")
else:
    print("  Admin already exists, skipping.")

existing = db.get_user_by_email(cfg, "alice@campus.edu")
if not existing:
    db.create_user(cfg, "alice@campus.edu", student1_pw, role="student")
    print("  Created student: alice@campus.edu / student123")

existing = db.get_user_by_email(cfg, "bob@campus.edu")
if not existing:
    db.create_user(cfg, "bob@campus.edu", student2_pw, role="student")
    print("  Created student: bob@campus.edu / student456")

# Get user IDs
admin = db.get_user_by_email(cfg, "admin@campus.edu")
alice = db.get_user_by_email(cfg, "alice@campus.edu")
bob = db.get_user_by_email(cfg, "bob@campus.edu")

# ── Items ────────────────────────────────────────────────────────────────
sample_items = [
    {
        "title": "Blue Hydroflask Water Bottle",
        "description": "Navy blue 32oz Hydroflask with stickers on it. Lost near the science building on Monday.",
        "status": "LOST",
        "category": "Accessories & Bottles",
        "location": "Science Hall",
        "verification_question": "What brand of stickers are attached to the front?",
        "photo_key": None,
        "reported_by": alice["id"],
    },
    {
        "title": "MacBook Pro Charger (USB-C)",
        "description": "Apple 67W USB-C charger found in Library Room 204. Has a small scratch on the plug.",
        "status": "FOUND",
        "category": "Electronics",
        "location": "Central Library",
        "verification_question": "What cable length or color is attached to the charging brick?",
        "photo_key": None,
        "reported_by": bob["id"],
    },
    {
        "title": "Black Northface Backpack",
        "description": "Lost my black Northface Borealis backpack in the cafeteria. Contains textbooks and a calculator.",
        "status": "LOST",
        "category": "Bags & Backpacks",
        "location": "Student Center & Canteen",
        "verification_question": "What specific textbook titles are inside the main compartment?",
        "photo_key": None,
        "reported_by": alice["id"],
    },
    {
        "title": "AirPods Pro (2nd Gen)",
        "description": "Found a pair of AirPods Pro in their case near the gym entrance. Case has a keychain attached.",
        "status": "FOUND",
        "category": "Electronics",
        "location": "Sports & Gym Complex",
        "verification_question": "What character or charm is on the case keychain?",
        "photo_key": None,
        "reported_by": bob["id"],
    },
    {
        "title": "Student ID Card — Priya Sharma",
        "description": "Found a student ID card belonging to Priya Sharma (CS department) in the parking lot.",
        "status": "FOUND",
        "category": "ID & Cards",
        "location": "Campus Grounds & Parking",
        "verification_question": "What is the graduation year or roll number suffix on the card?",
        "photo_key": None,
        "reported_by": alice["id"],
    },
    {
        "title": "Red Umbrella",
        "description": "Lost a red compact umbrella in the auditorium during the Friday seminar. Has a wooden handle.",
        "status": "LOST",
        "category": "Accessories & Bottles",
        "location": "Main Auditorium",
        "verification_question": "Is the handle curved or straight, and does it have an elastic wrist loop?",
        "photo_key": None,
        "reported_by": bob["id"],
    },
    {
        "title": "TI-84 Plus Graphing Calculator",
        "description": "Found a TI-84 Plus graphing calculator in Room 301 of the engineering building. Has initials 'RK' on back.",
        "status": "FOUND",
        "category": "Electronics",
        "location": "Engineering Complex",
        "verification_question": "What color is the slide case cover?",
        "photo_key": None,
        "reported_by": alice["id"],
    },
    {
        "title": "Denim Jacket (Levi's)",
        "description": "Lost my Levi's denim jacket at the basketball court. Size M, has a small patch on the left sleeve.",
        "status": "LOST",
        "category": "Clothing & Apparel",
        "location": "Sports & Gym Complex",
        "verification_question": "What image is depicted on the left sleeve embroidered patch?",
        "photo_key": None,
        "reported_by": bob["id"],
    },
]

# Check if items already seeded
existing_items = db.list_items(cfg)
if len(existing_items) == 0:
    for item_data in sample_items:
        db.create_item(
            cfg,
            item_data["title"],
            item_data["description"],
            item_data["status"],
            item_data["photo_key"],
            item_data["reported_by"],
            category=item_data["category"],
            location=item_data["location"],
            verification_question=item_data["verification_question"],
        )
    print(f"  Created {len(sample_items)} sample items.")
else:
    # Backfill categories and locations on existing items if they default to None or General
    print(f"  Updating existing items with categories and locations...")
    for idx, item in enumerate(existing_items):
        if idx < len(sample_items):
            s = sample_items[idx]
            db._execute(
                cfg,
                "UPDATE items SET category = %s, location = %s, verification_question = %s WHERE id = %s",
                (s["category"], s["location"], s["verification_question"], item["id"]),
            )
    print(f"  Updated existing items with taxonomy details.")

print("\nDone! You can now run the app with: LOCAL_DEV=1 python app.py")
print("Admin login: admin@campus.edu / admin123")
print("Student login: alice@campus.edu / student123")

