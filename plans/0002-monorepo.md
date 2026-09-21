---
kind: feature
status: in_progress
iteration: 1
max_iterations: 30
suggested_model: opus
suggested_effort: high
confirmed_model: opus
confirmed_effort: high
---

# 0002 — Монорепо: src/news, src/guard, src/shared

## Context

Свести два репозитория в один: `hk_bot` (новостной бот, живой, CT 100) и
`~/Documents/src/hk_guard` (модератор, CT 101, работает). `src/` получает подпапку на бота.

Раскладка `news/` + `guard/` + `shared/`; историю `hk_guard` не переносим (снапшот); мёртвый
скаффолд модератора чистим; папку `hk_guard` убираем.

**Требование: план исполняется полностью автоматически, без шагов пользователя.** Из этого
следуют два решения, снимающие бóльшую часть исходного риска:

- **Никаких новых GitHub-секретов.** Они понадобились бы только чтобы дать модератору CI-job,
  перезаписывающий `.env`. Не даём: `.env` на обоих контейнерах уже корректны, новостной
  продолжает пользоваться существующим `ENV_FILE`. Заодно исчезает главная опасность исходного
  плана — токен новостного бота в CT 101 дал бы два поллера на один токен, Telegram 409 и
  молчащий живой бот при `active` сервисе.
- **Выкатка не через CI.** `deploy.yml` срабатывает на push в main, а push требует согласия
  пользователя и блокируется хуком. Значит деплой идёт напрямую через `pct` по SSH скриптом
  `deploy.sh`. `deploy.yml` всё равно правим под новую раскладку, но план на него не опирается
  и его не ждёт.

**Шесть способов сломать живого бота молча** (разведка + состязательная проверка дизайна).
Все дают `active` сервис и зелёный CI:

1. **Файлы состояния.** Шесть команд строят путь как `__file__/../../<name>_state.json` → корень.
   Под `src/news/commands/` это станет `src/` → пустое состояние → **бот перепостит весь бэклог
   в живую группу**.
2. **`config_loader`.** `dirname/../config.json` из `src/shared/` укажет на `src/config.json`,
   а `load_config` глотает `FileNotFoundError` → `{"mappings": []}` → бот живёт и не постит.
3. **`load_commands()`.** Литерал `"commands."` зашит дважды — в `import_module` и в проверке
   `attr.__module__`. Починить только импорт → `[]` команд без ошибки.
4. **`deploy.yml:54`** пушит `src/helpers/rewrite_prompt.txt` жёстким путём: шаг упадёт после
   синка `.py`, не дойдя до перезаписи юнита — новый код под старым `ExecStart`.
5. **Юнит CT 101** сейчас написан `deploy.sh`-ем и указывает на `/root/hk_guard/src/bot.py`.
   Не переписать — значит вечно исполнять старый код в статусе `active`.
6. **`mock.patch` по строкам.** Если уцелеет хоть один `sys.path.insert`, файл станет импортируем
   под двумя именами, патч ляжет не на тот объект — тест пойдёт в реальную сеть и останется зелёным.

**Проверено:** `python3 -m src.news.bot` из корня работает (`runpy` кладёт CWD в `sys.path[0]`).
`/root/hk_bot` **не** git-клон, поэтому хендлер `/update` не может отработать в принципе, а его
«откат» восстанавливает файл, который после переезда никто не исполняет — мёртвый код, который
врёт. У `hk_guard` нет git-remote: его история существует только локально.
Старые плоские файлы на сервере CI никогда не удаляет — это и есть откат, шаг очистки не добавляем.

**suggested_model / effort:** `opus` / `high` — деплой живого бота, где ошибка проявляется тишиной.

## Goals

- Оба бота в `hk_bot`: `src/news/`, `src/guard/`, общее в `src/shared/`.
- Каждый бот деплоится в свой контейнер со своим токеном; изоляция прав не нарушена.
- Мёртвый скаффолд модератора удалён.
- Тесты обоих ботов гоняются одним `pytest` без конфликта имён.
- Весь план исполним без единого действия пользователя.

## Non-Goals

- Перенос git-истории `hk_guard` — снапшот.
- Новые GitHub-секреты, CI-job для модератора, объединение токенов или контейнеров.
- Рефакторинг логики ботов — только переезд и то, что он ломает.
- Деплой через CI: `deploy.yml` приводится в соответствие, но не используется как канал выкатки.

## Requirements

### Целевая раскладка

```
hk_bot/
  config.json  config.guard.json
  requirements.txt  requirements.guard.txt
  conftest.py            пустой, кладёт корень в sys.path
  deploy.sh              ./deploy.sh news | guard
  src/
    __init__.py
    shared/  __init__.py  paths.py  config_loader.py
    news/    __init__.py  bot.py  api/  commands/  helpers/
    guard/   __init__.py  bot.py  moderation.py
  tests/                 плоско, уникальные basename
```

### Импорты и запуск

- Только пакетные импорты: `from src.shared.config_loader import load_config`,
  `from src.news.commands import load_commands`. Ни одного `sys.path.insert`, включая тесты.
- `WorkingDirectory=/root/<dir>`, `ExecStart=/usr/bin/python3 -m src.<bot>.bot`.
  Корень как рабочая директория нужен, чтобы `load_dotenv(".env")` продолжал резолвиться.
- Префикс в `load_commands()` — из `__name__` (не `__package__`, он на пути к deprecation),
  подставить **в оба** места.
- Под `-m` модуль бота грузится как `__main__`; нельзя нигде добавлять `import src.news.bot`,
  иначе появится второй объект модуля со своими глобалами.

### Пути и конфиги

- `src/shared/paths.py`: `ROOT = Path(__file__).resolve().parents[2]`. Через него идут все шесть
  файлов состояния и оба читателя конфига. Добавлять «ещё один `..`» в шести местах нельзя —
  это тот же баг, отложенный до следующего переезда.
- `windguru_command.py` имеет собственный `_CONFIG_PATH` — удалить, звать общий загрузчик.
- `*_state.json` лежат в git; ни один шаг деплоя не должен их пушить.
- Без аргумента `filename` в загрузчике: новостной читает `config.json`, а деплой модератора
  кладёт `config.guard.json` в контейнер **под именем `config.json`**. Одна кодовая ветка.
- `main()` каждого бота падает при старте, если конфиг пуст (нет `mappings` / нет `moderation`).
  Без этого «живёт и молчит» неотличимо от нормы.

### Тесты

- Плоская `tests/`, уникальные basename. Одинаковые имена дают `import file mismatch` на сборке.
- Все строки `mock.patch` — на пакетные пути.
- `tests/test_video_helper.py` сегодня без настройки путей и проходит лишь потому, что раньше
  отработал другой файл. Починить.
- Тест модератора читает `../config.json` — перенаправить на `config.guard.json`.
- Пустой `conftest.py` в корне, чтобы работал и голый `pytest`.

### Standing constraints (из `CLAUDE.md`)

- **Minimal changes** / **Simple architecture** / **New dependencies:** ask for consent first.
- **Unit tests:** Always write unit tests for new or modified logic.
- **Post-implementation checks:** verify the change works end-to-end.
- **Backward compatibility:** check who depends on a handler before changing it.
- **No duplicate pollers:** two pollers on one token cause Telegram 409.
- **Git safety:** commit freely; never `git push` without explicit in-session consent.

## Implementation

- [x] 1. `src/shared/{__init__,paths}.py` — `ROOT = Path(__file__).resolve().parents[2]`.
- [x] 2. `src/shared/config_loader.py` — из `src/config_loader.py`, путь через `ROOT`.
- [x] 3. `src/{__init__,news/__init__,guard/__init__}.py` — пустые маркеры; корневой `conftest.py`.
- [x] 4. `git mv` `src/bot.py` → `src/news/bot.py`; `src/{api,commands,helpers}` → `src/news/`.
- [x] 5. Все внутренние импорты → пакетные. Не забыть два ленивых импорта внутри функций:
      `helpers.video_helper` в `bot.py` и `config_loader` в методе `woo_command.py`.
- [x] 6. `src/news/commands/__init__.py` — префикс из `__name__` в обоих местах.
- [x] 7. Шесть команд с состоянием → `ROOT / "<name>_state.json"`.
- [x] 8. `windguru_command.py` — удалить свой `_CONFIG_PATH`, звать общий загрузчик.
- [x] 9. `src/news/bot.py` — удалить `/update`, `update_callback`, `_rollback`, `BOT_SCRIPT`,
      `BOT_BACKUP`, `BOT_REPO_URL` и регистрацию хендлеров. Мёртвый код: `/root/hk_bot` не
      git-клон. `/reload` остаётся.
- [x] 10. `src/news/bot.py` `main()` — падать, если в конфиге нет `mappings`.
- [x] 11. Перенести из `hk_guard`: `src/bot.py` → `src/guard/bot.py`,
      `src/moderation.py` → `src/guard/moderation.py`, `config.json` → `config.guard.json`.
      Скаффолд (`api/`, `commands/`, `helpers/`, `hello_command.py`, `config_loader.py`) не брать.
- [x] 12. `src/guard/bot.py` — вычистить неиспользуемое: `load_commands`, `_show_commands`,
      `command_callback`, `answer`, `answer_mention`, `_send_result`, `_build_media`,
      `_split_at_paragraph`, `_append_footer`, cron-планировщик, `/update`. Оставить `moderate`,
      `_scannable_text`, `_is_exempt`, `_is_anonymous_admin`, `_delete_notice`, `on_startup`,
      `/reload`, `main()`. Падать в `main()`, если нет ключа `moderation`.
- [x] 13. `requirements.guard.txt` — только `python-telegram-bot[job-queue]==21.7` и
      `python-dotenv==1.0.1`. У CT 101 256МБ RAM и 4ГБ диска, `faster-whisper` туда нельзя.
- [x] 14. Тесты: уникальные basename, убрать **все** `sys.path.insert`, импорты и строки
      `mock.patch` на пакетные, починить `test_video_helper.py`, перенести тесты модератора,
      их конфиг → `config.guard.json`.
- [x] 15. Новый тест: каталог файла состояния каждой команды равен корню репозитория —
      механическая защита от перепоста бэклога.
- [x] 16. `deploy.sh` — принимает `news|guard`, пушит `src/__init__.py` + `src/shared/` +
      `src/<bot>/` + свой конфиг и requirements, **пишет свой systemd-юнит** с новым `ExecStart`,
      рестартует сервис, печатает `is-active`. Для guard конфиг кладётся как `config.json`.
- [x] 17. `.github/workflows/deploy.yml` — привести к новой раскладке: `ExecStart` на
      `-m src.news.bot`, `find` по `src/shared src/news` с `-o -name '*.txt'` вместо отдельного
      шага для `rewrite_prompt.txt`, `src/__init__.py` явной строкой, `paths:`-фильтр на
      новостной бот. Секреты не трогаем.
- [x] 18. Документация: `CLAUDE.md` (секция Architecture вдобавок описывает несуществующий
      Proxmox-MCP — переписать под реальность), `README.md`, `specs/*.md`,
      `.claude/skills/{run-hk-bot,tune-prompt,feature_analyst}/`, `.claude/commands/*.md`,
      `.claude/settings.json` (allowlist с `src/bot.py`), `.gitignore`
      (`src/__pycache__/` не ловит подкаталоги). Перенести `hk_guard/.claude/server_knowledge.md`
      разделом в местный.
- [x] 19. `.claude/skills/run-hk-bot/smoke.sh` — на пакетный запуск обоих ботов.
- [ ] 20. Выкатка: `bash deploy.sh guard`, затем `bash deploy.sh news`. Модератор первым —
      он дешевле в откате, и его успех подтверждает, что схема запуска рабочая.
- [ ] 21. Архивировать историю модератора: `git -C ~/Documents/src/hk_guard bundle create
      ~/Documents/src/hk_guard-history.bundle --all`, проверить `git bundle verify`, и только
      после успешной проверки удалить каталог. Бандл обязателен: remote у `hk_guard` нет,
      его шесть коммитов существуют только локально.

## Validation

- [ ] `python3 -m pytest tests/ -q`
- [ ] Голый `pytest tests/ -q` тоже проходит (корневой `conftest.py`)
- [ ] Каждый тестовый файл проходит по отдельности (ловит зависимость от порядка сбора)
- [ ] `python3 -c "import src.news.bot, src.guard.bot"`
- [ ] `load_commands()` возвращает 9, а не 0
- [ ] Путь каждого `*_state.json` резолвится в корень, не в `src/`
- [ ] Файлы состояния в корне не обнулились: `git status --porcelain *_state.json` пуст
- [ ] `grep -rn "sys.path.insert" tests/ src/` — пусто
- [ ] `grep -rn "src/bot.py" .github/ .claude/ specs/ README.md CLAUDE.md` — пусто
- [ ] Smoke: `bash .claude/skills/run-hk-bot/smoke.sh`
- [ ] Оба сервиса `active`; `journalctl -u hk-bot` и `-u hk-guard` без трейсбеков
- [ ] `ExecStart` в юнитах обоих контейнеров указывает на `-m src.<bot>.bot`
- [ ] У новостного в логах видно планирование cron-задач; у модератора стартовое сообщение
      сообщает ненулевое число правил
- [ ] `git bundle verify ~/Documents/src/hk_guard-history.bundle` — ок

## Definition of Done

Локальный интерпретатор — `.venv/bin/python` (у системного `python3` нет зависимостей).

Эталон до переезда: **127 тестов, 9 команд** (`facebook hkr iksurfmag instagram kitegirl
surfr windguru woo youtube`). После переезда тестов должно стать больше (приедут ~47 от
модератора), а команд — ровно 9.

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -c "import src.news.bot, src.guard.bot"
.venv/bin/python -c "from src.news.commands import load_commands; assert len(load_commands()) == 9, len(load_commands())"
test -z "$(git status --porcelain -- '*_state.json')"
! grep -rn "sys.path.insert" tests/ src/
```

## Откат

Старые плоские файлы на сервере остаются — `deploy.sh` только пушит, никогда не удаляет:

```bash
ssh root@192.168.0.31 "pct exec 100 -- bash -c 'sed -i \"s|-m src.news.bot|/root/hk_bot/src/bot.py|\" \
  /etc/systemd/system/hk-bot.service && systemctl daemon-reload && systemctl restart hk-bot'"
```

Шаг очистки старого дерева на сервере намеренно не добавляется — он бы убил этот откат.
