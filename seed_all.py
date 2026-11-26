"""
Seeds all 8 separate microservice databases with demo data matching the original monolith:
  - auth_service.db       (auth credentials + login audit schema)
  - user_service.db       (user profiles + customer addresses)
  - restaurant_service.db (restaurants)
  - menu_service.db       (menu categories + menu items)
  - order_service.db      (initializes schema)
  - delivery_service.db   (initializes schema)
  - rating_service.db     (initializes schema)
  - report_service.db     (initializes schema)

Usage:
    python seed_all.py
"""
import json
import os
import subprocess
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(ROOT_DIR, "databases")
os.makedirs(DB_DIR, exist_ok=True)


def run_in_service(service_rel_path: str, db_filename: str, inline_script: str) -> str:
    service_dir = os.path.join(ROOT_DIR, service_rel_path)
    db_path = os.path.join(DB_DIR, db_filename).replace("\\", "/")
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    result = subprocess.run(
        [sys.executable, "-c", inline_script],
        cwd=service_dir,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


AUTH_SEED_SCRIPT = """
import json
from app.core.database import Base, engine, SessionLocal
from app.core.constants import UserRole
from app.security import get_password_hash
from app.models import AuthCredential

Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    seed_accounts = [
        ("admin@fooddelivery.com", "Admin@123", UserRole.ADMIN),
        ("owner1@fooddelivery.com", "Owner@123", UserRole.RESTAURANT_OWNER),
        ("owner2@fooddelivery.com", "Owner@123", UserRole.RESTAURANT_OWNER),
        ("agent1@fooddelivery.com", "Agent@123", UserRole.DELIVERY_AGENT),
        ("agent2@fooddelivery.com", "Agent@123", UserRole.DELIVERY_AGENT),
        ("customer1@fooddelivery.com", "Customer@123", UserRole.CUSTOMER),
        ("customer2@fooddelivery.com", "Customer@123", UserRole.CUSTOMER),
    ]
    if db.query(AuthCredential).filter(AuthCredential.email == "admin@fooddelivery.com").first():
        status = "SKIPPED"
    else:
        for email, pwd, role in seed_accounts:
            db.add(AuthCredential(email=email, password_hash=get_password_hash(pwd), role=role, is_active=True))
        db.commit()
        status = "SEEDED"

    id_map = {c.email: c.id for c in db.query(AuthCredential).all()}
    print(json.dumps({"status": status, "ids": id_map}))
finally:
    db.close()
"""

USER_SEED_TEMPLATE = """
import json
from app.core.database import Base, engine, SessionLocal
from app.core.constants import UserRole
from app.models import User, Address

Base.metadata.create_all(bind=engine)
id_map = json.loads({id_map_json!r})
db = SessionLocal()
try:
    if db.query(User).filter(User.email == "admin@fooddelivery.com").first():
        print("SKIPPED")
    else:
        profiles = [
            User(id=id_map["admin@fooddelivery.com"], email="admin@fooddelivery.com", full_name="Platform Admin", phone="+919876543210", role=UserRole.ADMIN, is_active=True),
            User(id=id_map["owner1@fooddelivery.com"], email="owner1@fooddelivery.com", full_name="Rajesh Sharma", phone="+919876543211", role=UserRole.RESTAURANT_OWNER, is_active=True),
            User(id=id_map["owner2@fooddelivery.com"], email="owner2@fooddelivery.com", full_name="Antonio Rossi", phone="+919876543212", role=UserRole.RESTAURANT_OWNER, is_active=True),
            User(id=id_map["agent1@fooddelivery.com"], email="agent1@fooddelivery.com", full_name="Suresh Kumar", phone="+919876543213", role=UserRole.DELIVERY_AGENT, is_active=True),
            User(id=id_map["agent2@fooddelivery.com"], email="agent2@fooddelivery.com", full_name="Ramesh Patel", phone="+919876543214", role=UserRole.DELIVERY_AGENT, is_active=True),
            User(id=id_map["customer1@fooddelivery.com"], email="customer1@fooddelivery.com", full_name="Aarav Verma", phone="+919876543215", role=UserRole.CUSTOMER, is_active=True),
            User(id=id_map["customer2@fooddelivery.com"], email="customer2@fooddelivery.com", full_name="Priya Nair", phone="+919876543216", role=UserRole.CUSTOMER, is_active=True),
        ]
        db.add_all(profiles)
        db.commit()

        addresses = [
            Address(user_id=id_map["customer1@fooddelivery.com"], line1="Flat 402, Green Heights", line2="100 Feet Road, Indiranagar", city="Bengaluru", pincode="560038", is_default=True),
            Address(user_id=id_map["customer1@fooddelivery.com"], line1="Office Block B, Tech Park", line2="Outer Ring Road", city="Bengaluru", pincode="560103", is_default=False),
            Address(user_id=id_map["customer2@fooddelivery.com"], line1="Villa 15, Palm Meadows", line2="Whitefield", city="Bengaluru", pincode="560066", is_default=True),
        ]
        db.add_all(addresses)
        db.commit()
        print("SEEDED")
finally:
    db.close()
"""

RESTAURANT_SEED_TEMPLATE = """
from datetime import time
from decimal import Decimal
from app.core.database import Base, engine, SessionLocal
from app.models import Restaurant

Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    rest1 = db.query(Restaurant).filter(Restaurant.owner_id == {owner1_id}).first()
    rest2 = db.query(Restaurant).filter(Restaurant.owner_id == {owner2_id}).first()
    if rest1 and rest2:
        print(f"SKIPPED:{{rest1.id}}:{{rest2.id}}")
    else:
        rest1 = Restaurant(owner_id={owner1_id}, name="Spice Junction", cuisine="North Indian", city="Bengaluru", address="12, 100 Feet Rd, Indiranagar", opens_at=time(9, 0), closes_at=time(23, 0), is_open=True, avg_rating=Decimal("0.00"))
        rest2 = Restaurant(owner_id={owner2_id}, name="Pizza Roma", cuisine="Italian", city="Bengaluru", address="45, Koramangala 4th Block", opens_at=time(11, 0), closes_at=time(23, 0), is_open=True, avg_rating=Decimal("0.00"))
        db.add_all([rest1, rest2])
        db.commit()
        print(f"SEEDED:{{rest1.id}}:{{rest2.id}}")
finally:
    db.close()
"""

MENU_SEED_TEMPLATE = """
from decimal import Decimal
from app.core.database import Base, engine, SessionLocal
from app.models import MenuCategory, MenuItem

Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    if db.query(MenuCategory).first():
        print("SKIPPED")
    else:
        cat_starters = MenuCategory(restaurant_id={rest1_id}, name="Starters", display_order=1)
        cat_mains = MenuCategory(restaurant_id={rest1_id}, name="Main Course", display_order=2)
        cat_beverages = MenuCategory(restaurant_id={rest1_id}, name="Beverages", display_order=3)
        cat_pizza = MenuCategory(restaurant_id={rest2_id}, name="Artisan Pizzas", display_order=1)
        cat_pasta = MenuCategory(restaurant_id={rest2_id}, name="Fresh Pastas", display_order=2)
        db.add_all([cat_starters, cat_mains, cat_beverages, cat_pizza, cat_pasta])
        db.commit()

        items = [
            MenuItem(restaurant_id={rest1_id}, category_id=cat_starters.id, name="Paneer Tikka", description="Chargrilled cottage cheese with aromatic spices", price=Decimal("220.00"), is_veg=True, is_available=True, is_deleted=False),
            MenuItem(restaurant_id={rest1_id}, category_id=cat_mains.id, name="Paneer Butter Masala", description="Rich cottage cheese curry with butter and cashews", price=Decimal("280.00"), is_veg=True, is_available=True, is_deleted=False),
            MenuItem(restaurant_id={rest1_id}, category_id=cat_mains.id, name="Butter Naan", description="Traditional clay oven flatbread layered with butter", price=Decimal("45.00"), is_veg=True, is_available=True, is_deleted=False),
            MenuItem(restaurant_id={rest1_id}, category_id=cat_mains.id, name="Hyderabadi Chicken Biryani", description="Fragrant basmati rice layered with spiced chicken", price=Decimal("340.00"), is_veg=False, is_available=True, is_deleted=False),
            MenuItem(restaurant_id={rest1_id}, category_id=cat_beverages.id, name="Sweet Mango Lassi", description="Chilled yogurt beverage made with Alphonso mangoes", price=Decimal("80.00"), is_veg=True, is_available=True, is_deleted=False),
            MenuItem(restaurant_id={rest1_id}, category_id=cat_starters.id, name="Seasonal Sweet Corn Chaat", description="Crispy corn tossed with chaat spices (Out of Stock)", price=Decimal("150.00"), is_veg=True, is_available=False, is_deleted=False),
            MenuItem(restaurant_id={rest2_id}, category_id=cat_pizza.id, name="Margherita Classica", description="San Marzano tomato sauce, fresh mozzarella, basil", price=Decimal("399.00"), is_veg=True, is_available=True, is_deleted=False),
            MenuItem(restaurant_id={rest2_id}, category_id=cat_pasta.id, name="Fettuccine Alfredo", description="Parmesan cream sauce with garlic and fresh herbs", price=Decimal("349.00"), is_veg=True, is_available=True, is_deleted=False),
        ]
        db.add_all(items)
        db.commit()
        print("SEEDED")
finally:
    db.close()
"""

INIT_SCHEMA_SCRIPT = """
from app.core.database import Base, engine
import app.models  # noqa: F401
Base.metadata.create_all(bind=engine)
print("TABLES:" + ",".join(sorted(Base.metadata.tables.keys())))
"""


def main():
    print("Seeding all 8 microservice databases...")
    auth_raw = run_in_service("services/auth-service", "auth_service.db", AUTH_SEED_SCRIPT)
    auth_info = json.loads(auth_raw)
    id_map = auth_info["ids"]
    print(f"  [auth-service]       auth_service.db       -> {auth_info['status']}")

    user_out = run_in_service(
        "services/user-service",
        "user_service.db",
        USER_SEED_TEMPLATE.format(id_map_json=json.dumps(id_map)),
    )
    print(f"  [user-service]       user_service.db       -> {user_out}")

    rest_out = run_in_service(
        "services/restaurant-service",
        "restaurant_service.db",
        RESTAURANT_SEED_TEMPLATE.format(
            owner1_id=id_map["owner1@fooddelivery.com"],
            owner2_id=id_map["owner2@fooddelivery.com"],
        ),
    )
    r_status, rest1_id, rest2_id = rest_out.split(":")
    print(f"  [restaurant-service] restaurant_service.db -> {r_status} (rest1={rest1_id}, rest2={rest2_id})")

    menu_out = run_in_service(
        "services/menu-service",
        "menu_service.db",
        MENU_SEED_TEMPLATE.format(rest1_id=rest1_id, rest2_id=rest2_id),
    )
    print(f"  [menu-service]       menu_service.db       -> {menu_out}")

    for svc, db_file in [
        ("services/order-service", "order_service.db"),
        ("services/delivery-service", "delivery_service.db"),
        ("services/rating-service", "rating_service.db"),
        ("services/report-service", "report_service.db"),
    ]:
        out = run_in_service(svc, db_file, INIT_SCHEMA_SCRIPT)
        print(f"  [{svc.split('/')[-1]:18s}] {db_file:21s} -> {out}")

    print("\nSeeded demo credentials:")
    print("  Admin      : admin@fooddelivery.com / Admin@123")
    print("  Owner 1    : owner1@fooddelivery.com / Owner@123 (Spice Junction)")
    print("  Owner 2    : owner2@fooddelivery.com / Owner@123 (Pizza Roma)")
    print("  Agent 1    : agent1@fooddelivery.com / Agent@123")
    print("  Agent 2    : agent2@fooddelivery.com / Agent@123")
    print("  Customer 1 : customer1@fooddelivery.com / Customer@123")
    print("  Customer 2 : customer2@fooddelivery.com / Customer@123")


if __name__ == "__main__":
    main()
