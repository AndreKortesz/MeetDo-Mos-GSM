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
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
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
    yield
    print("MeetDo — остановлен")


app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)


# ── Helpers ──
def get_current_user(request: Request):
    """Получить текущего пользователя из сессии."""
    return request.session.get("user")


def require_auth(request: Request):
    """Проверить авторизацию, вернуть user или None."""
    user = get_current_user(request)
    return user


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
    """Обработка callback от Битрикс24 OAuth."""
    if not code:
        return RedirectResponse("/login")

    # Обмен code на access_token
    token_url = (
        f"https://{BITRIX_DOMAIN}/oauth/token/"
        f"?grant_type=authorization_code"
        f"&client_id={BITRIX_CLIENT_ID}"
        f"&client_secret={BITRIX_CLIENT_SECRET}"
        f"&redirect_uri={BITRIX_REDIRECT_URI}"
        f"&code={code}"
    )

    async with httpx.AsyncClient() as client:
        resp = await client.get(token_url)
        if resp.status_code != 200:
            return HTMLResponse("<h2>Ошибка авторизации</h2><p>Попробуйте снова</p><a href='/login'>Войти</a>", status_code=401)

        data = resp.json()
        access_token = data.get("access_token", "")

        if not access_token:
            return HTMLResponse("<h2>Ошибка токена</h2><a href='/login'>Войти</a>", status_code=401)

        # Получаем данные пользователя
        user_resp = await client.get(
            f"https://{BITRIX_DOMAIN}/rest/user.current.json",
            params={"auth": access_token}
        )

        if user_resp.status_code != 200:
            return HTMLResponse("<h2>Ошибка получения профиля</h2><a href='/login'>Войти</a>", status_code=401)

        user_data = user_resp.json().get("result", {})

        # Сохраняем в сессию
        request.session["user"] = {
            "id": user_data.get("ID"),
            "name": f"{user_data.get('NAME', '')} {user_data.get('LAST_NAME', '')}".strip(),
            "email": user_data.get("EMAIL", ""),
            "access_token": access_token,
        }

        print(f"✅ User logged in: {request.session['user']['name']} (ID: {request.session['user']['id']})")
        return RedirectResponse("/")


@app.get("/logout")
async def logout(request: Request):
    """Выход — очистка сессии."""
    request.session.clear()
    return RedirectResponse("/login")


@app.get("/api/me")
async def api_me(request: Request):
    """API: текущий пользователь (для фронтенда)."""
    user = require_auth(request)
    if not user:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "id": user["id"],
        "name": user["name"],
        "email": user.get("email", ""),
    }


# ── Static Files (React build) ──
# Vite собирает в dist/, FastAPI отдаёт статику оттуда

@app.get("/")
async def serve_root(request: Request):
    """Главная страница — проверка авторизации."""
    user = require_auth(request)
    if not user:
        return RedirectResponse("/login")
    return FileResponse("dist/index.html")


# Монтируем статику (JS, CSS, assets)
if os.path.exists("dist/assets"):
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")

# Fallback для SPA-роутинга
@app.get("/{path:path}")
async def serve_spa(request: Request, path: str):
    """SPA fallback — все маршруты отдают index.html."""
    # Пропускаем API и auth-маршруты
    if path.startswith(("api/", "login", "logout", "auth/")):
        return HTMLResponse("Not Found", status_code=404)

    user = require_auth(request)
    if not user:
        return RedirectResponse("/login")

    # Пробуем отдать файл из dist
    file_path = f"dist/{path}"
    if os.path.isfile(file_path):
        return FileResponse(file_path)

    return FileResponse("dist/index.html")
