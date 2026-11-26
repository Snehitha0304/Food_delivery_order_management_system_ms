"""
Launch all 6 Food Delivery microservices + the API Gateway locally.
Each microservice connects to its own isolated database under ./databases/.

Usage:
    python start_all.py
"""
import os
import signal
import subprocess
import sys
import time

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(ROOT_DIR, "databases")
os.makedirs(DB_DIR, exist_ok=True)

SERVICES = [
    ("auth-service", os.path.join(ROOT_DIR, "services", "auth-service"), 8008, "auth_service.db"),
    ("user-service", os.path.join(ROOT_DIR, "services", "user-service"), 8001, "user_service.db"),
    ("restaurant-service", os.path.join(ROOT_DIR, "services", "restaurant-service"), 8002, "restaurant_service.db"),
    ("menu-service", os.path.join(ROOT_DIR, "services", "menu-service"), 8007, "menu_service.db"),
    ("order-service", os.path.join(ROOT_DIR, "services", "order-service"), 8003, "order_service.db"),
    ("delivery-service", os.path.join(ROOT_DIR, "services", "delivery-service"), 8004, "delivery_service.db"),
    ("rating-service", os.path.join(ROOT_DIR, "services", "rating-service"), 8005, "rating_service.db"),
    ("report-service", os.path.join(ROOT_DIR, "services", "report-service"), 8006, "report_service.db"),
    ("api-gateway", os.path.join(ROOT_DIR, "api-gateway"), 8000, None),
]


def main():
    procs = []
    print("Starting Food Delivery Microservices Architecture...")
    for name, cwd, port, db_file in SERVICES:
        env = os.environ.copy()
        env["SERVICE_PORT"] = str(port)
        has_local_env = os.path.exists(os.path.join(cwd, ".env"))
        if db_file and not has_local_env:
            db_path = os.path.join(DB_DIR, db_file).replace("\\", "/")
            env.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

        cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)]
        proc = subprocess.Popen(cmd, cwd=cwd, env=env)
        procs.append((name, proc))
        db_info = " -> DB: from .env (PostgreSQL)" if (db_file and has_local_env) else (f" -> DB: databases/{db_file}" if db_file else " -> Reverse Proxy")
        print(f"  [STARTED] {name:20s} on http://127.0.0.1:{port}{db_info}")

    print("\nAll services launched!")
    print("  API Gateway Swagger UI : http://127.0.0.1:8000/docs")
    print("  Aggregated Health Check: http://127.0.0.1:8000/health")
    print("Press Ctrl+C to stop all services.\n")

    def shutdown(signum, frame):
        print("\nStopping all microservices...")
        for name, proc in procs:
            proc.terminate()
        for name, proc in procs:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            for name, proc in procs:
                if proc.poll() is not None:
                    print(f"[WARN] {name} exited unexpectedly with code {proc.returncode}")
            time.sleep(2)
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
