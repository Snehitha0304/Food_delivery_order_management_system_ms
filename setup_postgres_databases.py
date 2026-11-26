"""
Creates all 8 separate microservice databases in your local PostgreSQL server
(so they immediately appear in pgAdmin 4), runs Alembic migrations on each DB,
seeds demo data, and writes each microservice's local `.env` (gitignored).

Usage:
    python setup_postgres_databases.py --password YOUR_PG_PASSWORD
    # or set PGPASSWORD env var and run:
    python setup_postgres_databases.py
"""
import argparse
import getpass
import json
import os
import subprocess
import sys
from urllib.parse import quote_plus
import psycopg2
from psycopg2 import sql

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

SERVICE_DBS = [
    ("auth-service", "auth_service_db", 8008),
    ("user-service", "user_service_db", 8001),
    ("restaurant-service", "restaurant_service_db", 8002),
    ("menu-service", "menu_service_db", 8007),
    ("order-service", "order_service_db", 8003),
    ("delivery-service", "delivery_service_db", 8004),
    ("rating-service", "rating_service_db", 8005),
    ("report-service", "report_service_db", 8006),
]

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
        db.add_all([
            Address(user_id=id_map["customer1@fooddelivery.com"], line1="Flat 402, Green Heights", line2="100 Feet Road, Indiranagar", city="Bengaluru", pincode="560038", is_default=True),
            Address(user_id=id_map["customer1@fooddelivery.com"], line1="Office Block B, Tech Park", line2="Outer Ring Road", city="Bengaluru", pincode="560103", is_default=False),
            Address(user_id=id_map["customer2@fooddelivery.com"], line1="Villa 15, Palm Meadows", line2="Whitefield", city="Bengaluru", pincode="560066", is_default=True),
        ])
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
    r1 = db.query(Restaurant).filter(Restaurant.owner_id == {owner1_id}).first()
    r2 = db.query(Restaurant).filter(Restaurant.owner_id == {owner2_id}).first()
    if r1 and r2:
        print(f"SKIPPED:{{r1.id}}:{{r2.id}}")
    else:
        r1 = Restaurant(owner_id={owner1_id}, name="Spice Junction", cuisine="North Indian", city="Bengaluru", address="12, 100 Feet Rd, Indiranagar", opens_at=time(9, 0), closes_at=time(23, 0), is_open=True, avg_rating=Decimal("0.00"))
        r2 = Restaurant(owner_id={owner2_id}, name="Pizza Roma", cuisine="Italian", city="Bengaluru", address="45, Koramangala 4th Block", opens_at=time(11, 0), closes_at=time(23, 0), is_open=True, avg_rating=Decimal("0.00"))
        db.add_all([r1, r2])
        db.commit()
        print(f"SEEDED:{{r1.id}}:{{r2.id}}")
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
        c1 = MenuCategory(restaurant_id={rest1_id}, name="Starters", display_order=1)
        c2 = MenuCategory(restaurant_id={rest1_id}, name="Main Course", display_order=2)
        c3 = MenuCategory(restaurant_id={rest1_id}, name="Beverages", display_order=3)
        c4 = MenuCategory(restaurant_id={rest2_id}, name="Artisan Pizzas", display_order=1)
        c5 = MenuCategory(restaurant_id={rest2_id}, name="Fresh Pastas", display_order=2)
        db.add_all([c1, c2, c3, c4, c5])
        db.commit()
        db.add_all([
            MenuItem(restaurant_id={rest1_id}, category_id=c1.id, name="Paneer Tikka", description="Chargrilled cottage cheese with aromatic spices", price=Decimal("220.00"), is_veg=True, is_available=True, is_deleted=False),
            MenuItem(restaurant_id={rest1_id}, category_id=c2.id, name="Paneer Butter Masala", description="Rich cottage cheese curry with butter and cashews", price=Decimal("280.00"), is_veg=True, is_available=True, is_deleted=False),
            MenuItem(restaurant_id={rest1_id}, category_id=c2.id, name="Butter Naan", description="Traditional clay oven flatbread layered with butter", price=Decimal("45.00"), is_veg=True, is_available=True, is_deleted=False),
            MenuItem(restaurant_id={rest1_id}, category_id=c2.id, name="Hyderabadi Chicken Biryani", description="Fragrant basmati rice layered with spiced chicken", price=Decimal("340.00"), is_veg=False, is_available=True, is_deleted=False),
            MenuItem(restaurant_id={rest1_id}, category_id=c3.id, name="Sweet Mango Lassi", description="Chilled yogurt beverage made with Alphonso mangoes", price=Decimal("80.00"), is_veg=True, is_available=True, is_deleted=False),
            MenuItem(restaurant_id={rest1_id}, category_id=c1.id, name="Seasonal Sweet Corn Chaat", description="Crispy corn tossed with chaat spices (Out of Stock)", price=Decimal("150.00"), is_veg=True, is_available=False, is_deleted=False),
            MenuItem(restaurant_id={rest2_id}, category_id=c4.id, name="Margherita Classica", description="San Marzano tomato sauce, fresh mozzarella, basil", price=Decimal("399.00"), is_veg=True, is_available=True, is_deleted=False),
            MenuItem(restaurant_id={rest2_id}, category_id=c5.id, name="Fettuccine Alfredo", description="Parmesan cream sauce with garlic and fresh herbs", price=Decimal("349.00"), is_veg=True, is_available=True, is_deleted=False),
        ])
        db.commit()
        print("SEEDED")
finally:
    db.close()
"""


def run_cmd_in_service(svc_name: str, db_url: str, args: list[str]) -> str:
    svc_dir = os.path.join(ROOT_DIR, "services", svc_name)
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    res = subprocess.run(args, cwd=svc_dir, env=env, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"[{svc_name}] Command failed:\n{res.stderr or res.stdout}")
    return res.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description="Create, migrate, and seed all 8 PostgreSQL databases for pgAdmin.")
    parser.add_argument("--host", default=os.environ.get("PGHOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PGPORT", "5432")))
    parser.add_argument("--user", default=os.environ.get("PGUSER", "postgres"))
    parser.add_argument("--password", default=os.environ.get("PGPASSWORD"))
    parser.add_argument("--write-env", action="store_true", help="Write local .env files for each microservice pointing to PostgreSQL")
    args = parser.parse_args()

    password = args.password or getpass.getpass(f"Enter PostgreSQL password for {args.user}@{args.host}:{args.port}: ")
    encoded_pw = quote_plus(password)

    print(f"Connecting to PostgreSQL at {args.host}:{args.port} as '{args.user}'...")
    conn = psycopg2.connect(host=args.host, port=args.port, user=args.user, password=password, dbname="postgres")
    conn.autocommit = True
    cur = conn.cursor()

    for svc_name, db_name, _ in SERVICE_DBS:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        if cur.fetchone():
            print(f"  [EXISTS]  Database '{db_name}' ({svc_name})")
        else:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
            print(f"  [CREATED] Database '{db_name}' ({svc_name})")

    cur.close()
    conn.close()

    print("\nRunning Alembic migrations on all 8 PostgreSQL databases...")
    db_urls = {}
    for svc_name, db_name, port in SERVICE_DBS:
        db_url = f"postgresql+psycopg2://{args.user}:{encoded_pw}@{args.host}:{args.port}/{db_name}"
        db_urls[svc_name] = db_url
        run_cmd_in_service(svc_name, db_url, [sys.executable, "-m", "alembic", "upgrade", "head"])
        print(f"  [MIGRATED] {svc_name:20s} -> {db_name}")

        if args.write_env:
            env_path = os.path.join(ROOT_DIR, "services", svc_name, ".env")
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(f"SERVICE_NAME={svc_name}\nSERVICE_PORT={port}\nDATABASE_URL={db_url}\n")

    print("\nSeeding demo data into PostgreSQL databases...")
    auth_info = json.loads(run_cmd_in_service("auth-service", db_urls["auth-service"], [sys.executable, "-c", AUTH_SEED_SCRIPT]))
    id_map = auth_info["ids"]
    print(f"  [auth-service]       auth_db       -> {auth_info['status']}")

    user_out = run_cmd_in_service("user-service", db_urls["user-service"], [sys.executable, "-c", USER_SEED_TEMPLATE.format(id_map_json=json.dumps(id_map))])
    print(f"  [user-service]       user_db       -> {user_out}")

    rest_out = run_cmd_in_service(
        "restaurant-service",
        db_urls["restaurant-service"],
        [sys.executable, "-c", RESTAURANT_SEED_TEMPLATE.format(owner1_id=id_map["owner1@fooddelivery.com"], owner2_id=id_map["owner2@fooddelivery.com"])],
    )
    r_status, rest1_id, rest2_id = rest_out.split(":")
    print(f"  [restaurant-service] restaurant_db -> {r_status}")

    menu_out = run_cmd_in_service("menu-service", db_urls["menu-service"], [sys.executable, "-c", MENU_SEED_TEMPLATE.format(rest1_id=rest1_id, rest2_id=rest2_id)])
    print(f"  [menu-service]       menu_db       -> {menu_out}")

    print("\nDone! Refresh 'Databases' in pgAdmin 4 to see all 8 databases:")
    for _, db_name, _ in SERVICE_DBS:
        print(f"  - {db_name}")


if __name__ == "__main__":
    main()
