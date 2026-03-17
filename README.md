# MeetDo by Mos-GSM

Канбан-доска с саммари собраний для команды Mos-GSM.
Meet → Do: встретились → сделали.

Авторизация через Битрикс24 OAuth (svyaz.bitrix24.ru) — доступ только сотрудникам.

---

## Полная инструкция деплоя

### ШАГ 1. Создать репозиторий на GitHub

1. Зайти на https://github.com → нажать **"+"** → **New repository**
2. Название: `meetdo`
3. Visibility: **Private** (чтобы посторонние не видели)
4. НЕ ставить галочку «Add README» — у нас уже есть
5. Нажать **Create repository**

### ШАГ 2. Загрузить проект

Скачать архив `meetdo-mosgsm.tar.gz`, распаковать, и выполнить в терминале:

```bash
# Распаковать архив
tar -xzf meetdo-mosgsm.tar.gz
cd mosgsm-kanban

# Инициализировать git
git init
git add .
git commit -m "initial: MeetDo by Mos-GSM"

# Подключить репозиторий (замени на своё имя если другое)
git branch -M main
git remote add origin https://github.com/AndreKortesz/meetdo.git
git push -u origin main
```

> **Если нет git на компьютере:** можно загрузить через браузер.
> На странице пустого репозитория нажми **"uploading an existing file"**
> и перетащи ВСЕ файлы из распакованной папки.

### ШАГ 3. Зарегистрировать OAuth-приложение в Битрикс24

1. Зайти на https://svyaz.bitrix24.ru/devops/section/standard/
2. Нажать **«Добавить приложение»** → **«Серверное приложение»**
3. Заполнить:
   - **Название:** `MeetDo`
   - **URL приложения:** пока оставить пустым (заполним после Railway)
   - **URL для установки:** пока оставить пустым
   - **Права:** поставить галочку на **user** (пользователи)
4. Нажать **Сохранить**
5. **Скопировать и сохранить:**
   - `client_id` (Код приложения) — например: `local.67a1b2c3d4e5f6.12345678`
   - `client_secret` (Ключ приложения) — например: `abcdef1234567890...`

> Эти значения понадобятся в шаге 5.

### ШАГ 4. Создать проект на Railway

1. Зайти на https://railway.app (залогиниться через GitHub)
2. Нажать **New Project** → **Deploy from GitHub Repo**
3. Найти и выбрать репозиторий `meetdo`
4. Railway начнёт сборку автоматически (по Dockerfile)
5. Подождать пока статус станет **"Deployed"** (1-2 минуты)

**Получить домен:**
1. Нажать на сервис (карточка в проекте)
2. Вкладка **Settings** → секция **Networking**
3. Нажать **Generate Domain**
4. Получишь URL вида: `https://meetdo-production-xxxx.up.railway.app`
5. **Скопировать этот URL — он нужен дальше**

### ШАГ 5. Добавить переменные окружения в Railway

1. Нажать на сервис → вкладка **Variables**
2. Добавить (кнопка **New Variable**):

| Переменная | Значение | Где взять |
|---|---|---|
| `BITRIX_CLIENT_ID` | `local.67a1b2c3d4...` | Шаг 3 — код приложения |
| `BITRIX_CLIENT_SECRET` | `abcdef12345...` | Шаг 3 — ключ приложения |
| `BITRIX_REDIRECT_URI` | `https://meetdo-production-xxxx.up.railway.app/auth/callback` | Твой домен Railway + `/auth/callback` |
| `BITRIX_DOMAIN` | `svyaz.bitrix24.ru` | Твой домен Битрикс24 |
| `SESSION_SECRET` | любая длинная случайная строка | Можно сгенерировать: `openssl rand -hex 32` |

3. Нажать **Update Variables** (или Redeploy)

### ШАГ 6. Обновить URL в Битрикс24

Вернуться в настройки OAuth-приложения (Шаг 3) и обновить:

1. **URL для первоначальной установки:** `https://meetdo-production-xxxx.up.railway.app`
2. **Ссылка для перенаправления (redirect_uri):** `https://meetdo-production-xxxx.up.railway.app/auth/callback`
3. Сохранить

### ШАГ 7. Проверить

1. Открыть в браузере: `https://meetdo-production-xxxx.up.railway.app`
2. Тебя перебросит на страницу авторизации Битрикс24
3. Нажать **«Разрешить»**
4. Откроется MeetDo с канбан-доской
5. Проверить: если открыть URL в режиме инкогнито — снова попросит авторизацию

### ШАГ 8. Добавить ссылку в меню Битрикс24

**Вариант A — Быстрый (ссылка в меню):**
1. В Битрикс24 → левое меню → внизу **«Ещё»** → **«Настроить меню»**
2. Нажать **«Добавить пункт»**
3. Выбрать **«Ссылка»**
4. Название: `MeetDo`
5. Ссылка: `https://meetdo-production-xxxx.up.railway.app`
6. Сохранить

Теперь все сотрудники видят «MeetDo» в левом меню.

**Вариант B — Встроенный (iframe внутри Битрикс):**
1. Битрикс24 → в левом меню **«Разработчикам»** (или `/devops/`)
2. Открыть приложение MeetDo → раздел **«Встраивание»**
3. Добавить место встраивания: **«Левое меню»**
4. URL обработчика: `https://meetdo-production-xxxx.up.railway.app`
5. Сохранить → MeetDo отображается прямо внутри Битрикс24

---

## Структура проекта

```
meetdo/
├── server.py           # FastAPI: авторизация Bitrix24 + раздача React
├── requirements.txt    # Python-зависимости
├── Dockerfile          # Двухэтапная сборка (Node → Python)
├── railway.toml        # Конфиг Railway
├── .gitignore
├── index.html          # HTML-точка входа для Vite
├── package.json        # Node-зависимости для Vite/React
├── vite.config.js      # Конфиг сборки Vite
└── src/
    ├── main.jsx        # React bootstrap
    └── App.jsx         # Главный компонент (канбан + саммари)
```

## Как это работает

```
Пользователь → meetdo-xxx.up.railway.app
                    ↓
              FastAPI server.py
                    ↓
          Есть сессия? ──НЕТ──→ Редирект на svyaz.bitrix24.ru/oauth/
                ↓ ДА                          ↓
        Отдать dist/index.html         Пользователь нажимает «Разрешить»
            (React SPA)                       ↓
                                    Битрикс редиректит на /auth/callback
                                              ↓
                                    server.py получает access_token
                                    → запрашивает user.current
                                    → сохраняет в сессию
                                    → редирект на /
```

## Переменные окружения

| Переменная | Описание |
|---|---|
| `BITRIX_CLIENT_ID` | Код OAuth-приложения из Битрикс24 |
| `BITRIX_CLIENT_SECRET` | Секрет OAuth-приложения |
| `BITRIX_REDIRECT_URI` | `https://<домен>/auth/callback` |
| `BITRIX_DOMAIN` | `svyaz.bitrix24.ru` |
| `SESSION_SECRET` | Случайная строка для подписи сессий |
