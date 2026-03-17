"""
MeetDo by Mos-GSM
Backend: FastAPI + Bitrix24 OAuth
Деплой: GitHub → Railway
"""

import os
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
import httpx

# ── Config ──
BITRIX_CLIENT_ID = os.environ.get("BITRIX_CLIENT_ID", "")
BITRIX_CLIENT_SECRET = os.environ.get("BITRIX_CLIENT_SECRET", "")
BITRIX_REDIRECT_URI = os.environ.get("BITRIX_REDIRECT_URI", "")
BITRIX_DOMAIN = os.environ.get("BITRIX_DOMAIN", "svyaz.bitrix24.ru")
SESSION_SECRET = os.environ.get("SESSION_SECRET", secrets.token_hex(32))


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("✅ MeetDo by Mos-GSM — запущен")
    print(f"   BITRIX_DOMAIN: {BITRIX_DOMAIN}")
    print(f"   BITRIX_CLIENT_ID: {BITRIX_CLIENT_ID[:20]}..." if BITRIX_CLIENT_ID else "   ⚠️ BITRIX_CLIENT_ID не задан!")
    print(f"   BITRIX_REDIRECT_URI: {BITRIX_REDIRECT_URI}")
    yield
    print("MeetDo — остановлен")


app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)


# ── Helpers ──
def get_current_user(request: Request):
    return request.session.get("user")


async def exchange_code_for_user(code: str, request: Request):
    """Обмен OAuth code на токен и получение данных пользователя."""
    token_url = (
        f"https://{BITRIX_DOMAIN}/oauth/token/"
        f"?grant_type=authorization_code"
        f"&client_id={BITRIX_CLIENT_ID}"
        f"&client_secret={BITRIX_CLIENT_SECRET}"
        f"&redirect_uri={BITRIX_REDIRECT_URI}"
        f"&code={code}"
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(token_url)
            print(f"   Token exchange: status={resp.status_code}")

            if resp.status_code != 200:
                print(f"   ❌ Token error: {resp.text[:200]}")
                return None

            data = resp.json()
            access_token = data.get("access_token", "")

            if not access_token:
                print(f"   ❌ No access_token in response: {data}")
                return None

            # Получаем данные пользователя
            user_resp = await client.get(
                f"https://{BITRIX_DOMAIN}/rest/user.current.json",
                params={"auth": access_token}
            )

            if user_resp.status_code != 200:
                print(f"   ❌ User fetch error: {user_resp.text[:200]}")
                return None

            user_data = user_resp.json().get("result", {})

            user = {
                "id": user_data.get("ID"),
                "name": f"{user_data.get('NAME', '')} {user_data.get('LAST_NAME', '')}".strip(),
                "email": user_data.get("EMAIL", ""),
                "access_token": access_token,
            }

            # Сохраняем в сессию
            request.session["user"] = user
            print(f"✅ User logged in: {user['name']} (ID: {user['id']})")
            return user

    except Exception as e:
        print(f"   ❌ Exception during auth: {e}")
        return None


# ── Auth Routes ──

@app.get("/login")
async def login():
    """Редирект на Битрикс24 OAuth."""
    auth_url = (
        f"https://{BITRIX_DOMAIN}/oauth/authorize/"
        f"?client_id={BITRIX_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={BITRIX_REDIRECT_URI}"
    )
    return RedirectResponse(auth_url)


@app.get("/auth/callback")
async def auth_callback(request: Request, code: str = ""):
    """Обработка callback от Битрикс24 OAuth (если redirect_uri = /auth/callback)."""
    if not code:
        return RedirectResponse("/login")

    user = await exchange_code_for_user(code, request)
    if not user:
        return HTMLResponse(
            "<h2>Ошибка авторизации</h2><p>Не удалось войти. Попробуйте снова.</p>"
            "<a href='/login'>Войти</a>",
            status_code=401
        )
    return RedirectResponse("/")


@app.get("/logout")
async def logout(request: Request):
    """Выход — очистка сессии."""
    request.session.clear()
    return RedirectResponse("/login")


@app.get("/api/me")
async def api_me(request: Request):
    """API: текущий пользователь."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"authenticated": False})
    return JSONResponse({
        "authenticated": True,
        "id": user["id"],
        "name": user["name"],
        "email": user.get("email", ""),
    })


# ── Static Files ──

@app.get("/")
async def serve_root(request: Request):
    """Главная страница. Обрабатывает и OAuth callback (code в query)."""
    # Битрикс24 может вернуть code на корень (если redirect_uri = корень)
    code = request.query_params.get("code")
    if code:
        user = await exchange_code_for_user(code, request)
        if user:
            return RedirectResponse("/")
        return HTMLResponse(
            "<h2>Ошибка авторизации</h2><a href='/login'>Попробовать снова</a>",
            status_code=401
        )

    # Проверка авторизации
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login")

    return FileResponse("dist/index.html")


# Монтируем статику (JS, CSS, assets)
if os.path.exists("dist/assets"):
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")


# Fallback для SPA
@app.get("/{path:path}")
async def serve_spa(request: Request, path: str):
    """SPA fallback."""
    if path.startswith(("api/", "login", "logout", "auth/")):
        return HTMLResponse("Not Found", status_code=404)

    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login")

    file_path = f"dist/{path}"
    if os.path.isfile(file_path):
        return FileResponse(file_path)

    return FileResponse("dist/index.html")
