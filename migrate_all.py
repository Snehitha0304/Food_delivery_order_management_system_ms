"""
Run Alembic migrations (`upgrade head`) across all 8 microservices,
targeting each service's dedicated database.

Usage:
    python migrate_all.py
"""
import os
import subprocess
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(ROOT_DIR, "databases")
os.makedirs(DB_DIR, exist_ok=True)

SERVICES = [
    ("auth-service", "auth_service.db"),
    ("user-service", "user_service.db"),
    ("restaurant-service", "restaurant_service.db"),
    ("menu-service", "menu_service.db"),
    ("order-service", "order_service.db"),
    ("delivery-service", "delivery_service.db"),
    ("rating-service", "rating_service.db"),
    ("report-service", "report_service.db"),
]


def main():
    print("Running Alembic migrations across all 8 microservices...")
    for svc_name, db_file in SERVICES:
        svc_dir = os.path.join(ROOT_DIR, "services", svc_name)
        env = os.environ.copy()
        db_path = os.path.join(DB_DIR, db_file).replace("\\", "/")
        env.setdefault("DATABASE_URL", f"sqlite:///{db_path}")
        res = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=svc_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            print(f"  [FAILED] {svc_name}: {res.stderr or res.stdout}")
            sys.exit(res.returncode)
        print(f"  [OK]     {svc_name:20s} -> {db_file} migrated to head")
    print("All 8 microservice databases migrated successfully!")


if __name__ == "__main__":
    main()
