# AI News TG Bot

Бот собирает новости про нейросети из проверенных зарубежных источников за сутки, переводит на русский (Google Translate) и публикует в указанный Telegram-канал.

## Источники

Первоисточники (tier 1): OpenAI, Anthropic, Google DeepMind, Google AI Blog, Hugging Face, Meta AI, Microsoft AI.
СМИ про ИИ (tier 2): MIT Tech Review, The Verge, TechCrunch, VentureBeat, Ars Technica.

Список редактируется в [config.py](config.py).

## Что делает (за один запуск)

1. Параллельно скачивает RSS всех источников.
2. Отсекает новости старше `LOOKBACK_HOURS` (по умолчанию 24).
3. Фильтрует по AI-ключевикам (на случай, если в фиде есть нерелевантное).
4. Отбрасывает то, что уже публиковали (SQLite в `data/posts.db`).
5. Сортирует: tier 1 → tier 2, внутри — по свежести; берёт топ `MAX_POSTS_PER_RUN`.
6. Переводит заголовок и краткое описание на русский.
7. Публикует шапку дайджеста + каждый пост отдельным сообщением (3 сек пауза между ними).

## Локальный запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# отредактируйте .env: BOT_TOKEN, CHANNEL_ID
python main.py
```

## Подготовка бота и канала

1. У [@BotFather](https://t.me/BotFather) создайте бота → получите `BOT_TOKEN`.
2. Создайте канал, добавьте бота администратором с правом «Публикация сообщений».
3. `CHANNEL_ID` — `@username` для публичного канала или числовой ID для приватного (узнаётся через [@userinfobot](https://t.me/userinfobot), переслав в него любое сообщение из канала; для канала ID начинается с `-100`).

## Деплой через GitHub Actions (рекомендуется)

Самый простой вариант для задачи "раз в день":

1. Закоммитьте проект в репозиторий на GitHub.
2. Settings → Secrets and variables → Actions → New repository secret:
   - `BOT_TOKEN` — токен от BotFather
   - `CHANNEL_ID` — ID/username канала
3. Workflow [`.github/workflows/daily.yml`](.github/workflows/daily.yml) уже настроен на запуск **каждый день в 15:00 UTC (18:00 МСК)**.
4. Меняется в файле, в строке `cron: "0 15 * * *"` ([cron-синтаксис](https://crontab.guru/)).
5. Запустить вручную для проверки: Actions → Daily AI News Digest → Run workflow.

База `posts.db` кешируется между запусками через `actions/cache` — антидубликат сохраняется.

## Деплой на Render / Fly.io / Railway

Используйте [Dockerfile](Dockerfile). Бот — не сервис, а cron-задача:

- **Render**: создайте «Cron Job», команда `python main.py`, расписание `0 15 * * *`.
- **Fly.io**: `fly machine run` + `[deploy.schedule]` в `fly.toml`.
- **Railway**: добавьте Cron Schedule в настройках сервиса.

Не забудьте задать переменные окружения `BOT_TOKEN`, `CHANNEL_ID`. Для дедупликации нужен persistent volume под `/app/data`.

## Настройки (`.env`)

| Переменная           | Значение по умолчанию | Описание                                                  |
|----------------------|-----------------------|-----------------------------------------------------------|
| `BOT_TOKEN`          | —                     | Токен от BotFather                                        |
| `CHANNEL_ID`         | —                     | `@username` или числовой ID канала                        |
| `MAX_POSTS_PER_RUN`  | `8`                   | Лимит постов за один запуск                               |
| `LOOKBACK_HOURS`     | `24`                  | Окно "новых" новостей в часах                             |

## Хотите более качественную адаптацию (не дословный перевод)?

Текущий `GoogleTranslatorBackend` — дословный перевод. Если потом захотите краткие пересказы в едином стиле, замените на LLM-бэкенд:

1. Добавьте в [src/translator.py](src/translator.py) класс `ClaudeBackend` (или `OpenAIBackend`), реализующий `Translator` Protocol.
2. Поменяйте `get_translator()`, чтобы возвращал нужный.

Cтоимость для ~10 постов в день на Claude Haiku 4.5 — несколько центов в месяц.

## Структура проекта

```
.
├── config.py              # источники, ключевые слова, env
├── main.py                # пайплайн: collect → filter → translate → send
├── src/
│   ├── collector.py       # параллельная загрузка RSS, парсинг
│   ├── filter.py          # фильтры по дате/ключевикам, сортировка
│   ├── translator.py      # абстракция перевода (Google по умолчанию)
│   ├── storage.py         # SQLite-антидубликат
│   ├── formatter.py       # HTML-шаблон поста для TG
│   └── telegram_sender.py # aiogram-обёртка с rate-limit handling
├── data/posts.db          # создаётся автоматически
├── Dockerfile
├── requirements.txt
└── .github/workflows/daily.yml
```
