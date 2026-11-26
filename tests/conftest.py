import asyncio
import importlib
import os
import sys
import tempfile
from typing import Dict
import httpx
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PORTS = {
    "gateway": 18000,
    "user": 18001,
    "restaurant": 18002,
    "order": 18003,
    "delivery": 18004,
    "rating": 18005,
    "report": 18006,
    "menu": 18007,
    "auth": 18008,
}

INTERNAL_KEY = "test-internal-key-microservices"
JWT_SECRET = "test-jwt-secret-key-microservices-123456"


def _load_isolated_service(service_dir: str, env_overrides: Dict[str, str]):
    old_env = {}
    for k, v in env_overrides.items():
        old_env[k] = os.environ.get(k)
        os.environ[k] = v

    for mod_name in list(sys.modules.keys()):
        if mod_name == "app" or mod_name.startswith("app."):
            del sys.modules[mod_name]

    sys.path.insert(0, service_dir)
    try:
        main_mod = importlib.import_module("app.main")
        fastapi_app = main_mod.app
        return {
            "app": fastapi_app,
            "db": sys.modules.get("app.core.database"),
            "models": sys.modules.get("app.models"),
            "security": sys.modules.get("app.security"),
            "constants": sys.modules.get("app.core.constants"),
        }
    finally:
        if service_dir in sys.path:
            sys.path.remove(service_dir)
        for k, prev in old_env.items():
            if prev is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = prev


class MultiServiceAsyncTransport(httpx.AsyncBaseTransport):
    def __init__(self, transports_by_origin: Dict[str, httpx.ASGITransport]):
        self._transports = transports_by_origin

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        origin = f"{request.url.scheme}://{request.url.host}:{request.url.port}"
        transport = self._transports.get(origin)
        if transport is None:
            raise httpx.ConnectError(f"Unknown test service origin: {origin}")
        return await transport.handle_async_request(request)


class MultiServiceSyncTransport(httpx.BaseTransport):
    def __init__(self, async_transport: MultiServiceAsyncTransport):
        self._async_transport = async_transport

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        async def _dispatch():
            resp = await self._async_transport.handle_async_request(request)
            content = await resp.aread()
            return httpx.Response(
                status_code=resp.status_code,
                headers=resp.headers,
                content=content,
                request=request,
            )

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(_dispatch())

        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, _dispatch()).result()


@pytest.fixture(scope="session")
def microservices_cluster():
    """
    Loads all 8 microservices (each connected to its own isolated SQLite DB) + API Gateway
    and routes real httpx inter-service calls through pure ASGI transports (zero TCP sockets).
    """
    with tempfile.TemporaryDirectory(prefix="fd_ms_dbs_", ignore_cleanup_errors=True) as tmp_db_dir:
        db_paths = {
            "auth": os.path.join(tmp_db_dir, "auth_service.db"),
            "user": os.path.join(tmp_db_dir, "user_service.db"),
            "restaurant": os.path.join(tmp_db_dir, "restaurant_service.db"),
            "menu": os.path.join(tmp_db_dir, "menu_service.db"),
            "order": os.path.join(tmp_db_dir, "order_service.db"),
            "delivery": os.path.join(tmp_db_dir, "delivery_service.db"),
            "rating": os.path.join(tmp_db_dir, "rating_service.db"),
            "report": os.path.join(tmp_db_dir, "report_service.db"),
        }

        service_urls = {k: f"http://127.0.0.1:{v}" for k, v in PORTS.items()}

        common_env = {
            "JWT_SECRET_KEY": JWT_SECRET,
            "JWT_ALGORITHM": "HS256",
            "INTERNAL_API_KEY": INTERNAL_KEY,
            "AUTH_SERVICE_URL": service_urls["auth"],
            "USER_SERVICE_URL": service_urls["user"],
            "RESTAURANT_SERVICE_URL": service_urls["restaurant"],
            "MENU_SERVICE_URL": service_urls["menu"],
            "ORDER_SERVICE_URL": service_urls["order"],
            "DELIVERY_SERVICE_URL": service_urls["delivery"],
            "RATING_SERVICE_URL": service_urls["rating"],
            "REPORT_SERVICE_URL": service_urls["report"],
            "LOG_LEVEL": "WARNING",
        }

        specs = [
            ("auth", os.path.join(ROOT_DIR, "services", "auth-service"), db_paths["auth"]),
            ("user", os.path.join(ROOT_DIR, "services", "user-service"), db_paths["user"]),
            ("restaurant", os.path.join(ROOT_DIR, "services", "restaurant-service"), db_paths["restaurant"]),
            ("menu", os.path.join(ROOT_DIR, "services", "menu-service"), db_paths["menu"]),
            ("order", os.path.join(ROOT_DIR, "services", "order-service"), db_paths["order"]),
            ("delivery", os.path.join(ROOT_DIR, "services", "delivery-service"), db_paths["delivery"]),
            ("rating", os.path.join(ROOT_DIR, "services", "rating-service"), db_paths["rating"]),
            ("report", os.path.join(ROOT_DIR, "services", "report-service"), db_paths["report"]),
            ("gateway", os.path.join(ROOT_DIR, "api-gateway"), None),
        ]

        loaded = {}
        transports_by_origin: Dict[str, httpx.ASGITransport] = {}
        for key, svc_dir, db_path in specs:
            env = common_env.copy()
            env["SERVICE_PORT"] = str(PORTS[key])
            if db_path:
                env["DATABASE_URL"] = f"sqlite:///{db_path.replace(os.sep, '/')}"
            svc = _load_isolated_service(svc_dir, env)
            loaded[key] = svc
            if svc["db"] is not None:
                svc["db"].Base.metadata.create_all(bind=svc["db"].engine)
            transports_by_origin[service_urls[key]] = httpx.ASGITransport(app=svc["app"])

        # Seed Admin credential in auth_db and matching Admin profile in user_db
        auth_mod = loaded["auth"]
        auth_db = auth_mod["db"].SessionLocal()
        try:
            AuthCredential = auth_mod["models"].AuthCredential
            AuthRole = auth_mod["constants"].UserRole
            get_password_hash = auth_mod["security"].get_password_hash
            admin_cred = AuthCredential(
                email="admin@test.com",
                password_hash=get_password_hash("Admin@123"),
                role=AuthRole.ADMIN,
                is_active=True,
            )
            auth_db.add(admin_cred)
            auth_db.commit()
            auth_db.refresh(admin_cred)
            admin_id = admin_cred.id
        finally:
            auth_db.close()

        user_mod = loaded["user"]
        user_db = user_mod["db"].SessionLocal()
        try:
            User = user_mod["models"].User
            UserRole = user_mod["constants"].UserRole
            user_db.add(
                User(
                    id=admin_id,
                    email="admin@test.com",
                    full_name="Test Admin",
                    phone="+919999900000",
                    role=UserRole.ADMIN,
                    is_active=True,
                )
            )
            user_db.commit()
        finally:
            user_db.close()

        orig_client = httpx.Client
        orig_async_client = httpx.AsyncClient
        async_transport = MultiServiceAsyncTransport(transports_by_origin)
        sync_transport = MultiServiceSyncTransport(async_transport)

        class PatchedClient(orig_client):
            def __init__(self, *args, **kwargs):
                kwargs.setdefault("transport", sync_transport)
                super().__init__(*args, **kwargs)

        class PatchedAsyncClient(orig_async_client):
            def __init__(self, *args, **kwargs):
                kwargs.setdefault("transport", async_transport)
                super().__init__(*args, **kwargs)

        httpx.Client = PatchedClient
        httpx.AsyncClient = PatchedAsyncClient

        try:
            yield {
                "gateway_url": service_urls["gateway"],
                "service_urls": service_urls,
                "db_paths": db_paths,
                "internal_key": INTERNAL_KEY,
                "sync_transport": sync_transport,
            }
        finally:
            httpx.Client = orig_client
            httpx.AsyncClient = orig_async_client
            for key in ["auth", "user", "restaurant", "menu", "order", "delivery", "rating", "report"]:
                if loaded[key]["db"] is not None:
                    loaded[key]["db"].engine.dispose()


@pytest.fixture(scope="session")
def client(microservices_cluster):
    with httpx.Client(
        base_url=microservices_cluster["gateway_url"],
        transport=microservices_cluster["sync_transport"],
        timeout=15.0,
    ) as http_client:
        yield http_client
