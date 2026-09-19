---
kind: feature
status: done
iteration: 0
max_iterations: 26
suggested_model: sonnet
suggested_effort: high
confirmed_model: null
confirmed_effort: null
uat_rounds: 0
max_uat_rounds: 3
---

# 0001 — Модератор-бот: удаление сообщений по правилам

## Context

В группе HateKite (`-4570601504`) сейчас работает только `hk_bot` — он постит новости по крону
и не читает сообщения участников. Нужна модерация: бот следит за сообщениями и при совпадении
с правилом (табуированное слово, regex-паттерн) удаляет сообщение и/или предупреждает в чате.

**Решение пользователя:** отдельный бот со своим токеном в **новом LXC-контейнере**, а не модуль
внутри `hk_bot`. Причина существенная: модератору нужны права админа на удаление и **выключенный
privacy mode** (иначе Telegram не отдаёт боту сообщения обычных участников). Давать это
новостному боту — лишнее расширение привилегий.

**Что уже есть и переиспользуется:**
- `.claude/skills/new-telegram-bot/` — полный бутстрап: шаблоны (`templates/src/bot.py`,
  `config_loader.py`, `api/*`, `bot.service.template`, `.github/workflows/deploy.yml.template`),
  интервью, создание LXC, деплой, systemd, self-hosted CI. Скаффолдит **в текущую директорию
  и создаёт новый git-репозиторий** — значит запускать его надо из новой пустой папки.
- `src/config_loader.py` (13 строк) — `load_config()` перечитывает `config.json` на каждый вызов.
  Кеша нет, и это фича: правки конфига применяются без рестарта. Шаблон содержит его копию.
- `src/bot.py:122 _whitelist_allowed` — готовая форма `get_chat_member` + `except Exception: pass`,
  по ней делается проверка «юзер — админ чата».
- Конвенции тестов (`tests/test_bot_handlers.py`): `pytest` + `@pytest.mark.asyncio`, Telegram-объекты
  собираются вручную из `MagicMock`/`AsyncMock` локальными фабриками `_make_update()`/`_make_context()`,
  глобалы патчатся по строковому пути (`patch("bot.ADMIN_ID", 42)`). `conftest.py` нет, каждый файл
  сам делает `sys.path.insert(0, "src")`.

**Данные сервера** (из `.claude/server_knowledge.md`): хост `192.168.0.31`, нода `raspberrypi`,
занят только CT `100` = `hk-bot-ct` @ `192.168.0.240`. Свободны VMID `101` и IP `192.168.0.241`.
Рабочий шаблон — `ubuntu-jammy-20231124_arm64.tar.xz` (Debian-шаблон на arm64 сломан).

**suggested_model / effort:** `sonnet` / `high` — реализуемая ralph-ом часть (чистый модуль
матчинга + один handler + тесты) хорошо шаблонизирована, но затрагивает диспетчеризацию сообщений
и проверку прав, где ошибка тихо ломает модерацию.

## Goals

- Бот удаляет сообщение в группе, если его текст (или подпись к медиа) совпал с правилом из конфига.
- Правила задаются в `config.json` двумя способами: список слов и список regex-паттернов.
- У каждого правила своё действие; при совпадении нескольких правил выполняется **самое строгое**.
- Админы чата и владелец (`ADMIN_ID`) под модерацию не попадают.
- Правки правил применяются без рестарта бота (как и весь остальной конфиг).
- Отредактированные сообщения проверяются так же, как новые.

## Non-Goals

- Счётчик нарушений, мут, бан, кик — пользователь их не выбрал. Лестница действий оставлена
  расширяемой, но состояние нарушителей не хранится.
- Модерация картинок, стикеров, файлов по содержимому — только текст и подписи.
- Защита от обхода через гомоглифы/leet (`х у й`, `xyй`, `н0га`). Нормализация базовая; это
  бесконечная гонка, и без реальных логов ложных пропусков её тюнить вслепую.
- Изменения в существующем `hk_bot` — репозиторий не трогаем вообще.
- Веб-интерфейс/команды для правки правил из чата — правила правятся в `config.json`.

## Requirements

### Формат правил (`config.json` нового бота)

```json
{
  "moderation": {
    "enabled": true,
    "chats": ["-4570601504"],
    "warn_ttl_seconds": 30,
    "rules": [
      {
        "name": "profanity",
        "words": ["хуй", "бля", "пизд"],
        "action": "delete_warn",
        "reason": "мат"
      },
      {
        "name": "spam-invites",
        "regex": ["(?i)t\\.me/\\+", "(?i)\\bbit\\.ly/"],
        "action": "delete",
        "reason": "спам-ссылка"
      },
      {
        "name": "caps",
        "regex": ["^[^a-zа-я]{40,}$"],
        "action": "warn",
        "reason": "капс"
      }
    ]
  }
}
```

- Правило содержит `words` и/или `regex`, обязательные `action` и `reason`.
- `chats` — список chat_id, где модерация активна. Пустой список = все чаты, где бот состоит.
- `enabled: false` полностью выключает модерацию, не трогая правила.

### Лестница действий (по возрастанию строгости)

| Ранг | `action` | Поведение |
|---|---|---|
| 1 | `warn` | сообщение остаётся, бот отвечает на него предупреждением |
| 2 | `delete` | сообщение удаляется молча |
| 3 | `delete_warn` | сообщение удаляется + в чат уходит предупреждение |

При совпадении нескольких правил берётся действие максимального ранга; `reason` — от правила,
которое это действие дало. Неизвестное значение `action` логируется и правило пропускается.

Текст предупреждения: `@username, сообщение удалено: <reason>` (для `warn` — «нарушение: <reason>»).
Предупреждение самоудаляется через `warn_ttl_seconds` секунд (`job_queue.run_once`), чтобы бот
сам не засорял чат.

### Матчинг

- **Нормализация** перед сравнением: `casefold()`, `ё` → `е`, удаление zero-width символов
  (`​-‍`, `﻿`), схлопывание пробелов.
- **`words`** компилируются в regex как `\b` + `re.escape(слово)` — совпадение **по началу слова
  с любым окончанием**. Это ловит словоформы (`хуй`, `хуёвый`, `хуем`) и не ловит ложное
  вхождение в середине (`страхую` не матчится на `хую`). Без `\b` это классический
  Scunthorpe-баг, и на русском он срабатывает часто.
- **`regex`** применяются как есть к нормализованному тексту. Битый паттерн (`re.error`)
  логируется и пропускается — бот не должен падать из-за опечатки в конфиге.
- Компиляция кешируется по содержимому блока `moderation` (модульный кеш «сырой JSON → скомпилированные
  правила»), иначе `load_config()` перекомпилирует regex на каждое сообщение. Горячая перезагрузка
  при этом сохраняется.
- Проверяются `message.text` и `message.caption`.

### Проверка исключений

`get_chat_member` вызывается **только после того, как правило уже совпало** — на чистых сообщениях
(99% трафика) лишних вызовов Telegram API нет.

- `user_id == ADMIN_ID` → пропустить.
- Статус в чате `administrator` / `creator` → пропустить.
- Ошибка запроса → модерировать (fail-closed для прав, не для бота).

### Отказ прав

Если `delete_message` падает (бот не админ / нет права «Удалять сообщения») — поймать
`TelegramError`, залогировать `warning` с chat_id. Не спамить админа на каждое сообщение.

### Standing constraints (из `CLAUDE.md` этого проекта)

- **Minimal changes:** Make the smallest possible change that achieves the goal. Avoid refactoring surrounding code.
- **Simple architecture:** Prefer the simplest solution. Do not introduce abstractions, layers, or patterns unless strictly necessary.
- **New dependencies:** Before adding any new tool, library, or external service, ask for consent first.
- **Unit tests:** Always write unit tests for new or modified logic.
- **Post-implementation checks:** After every implementation, verify the change works end-to-end (run tests, check logs, manually test the affected behaviour).
- **Backward compatibility:** Before changing a command or handler's behaviour, check who already depends on it.
- **No duplicate pollers:** Before starting the bot locally, check whether an instance is already running (locally or on the deployed container) — two pollers on the same token race and cause Telegram 409 conflicts. **Здесь особенно: у нового бота свой токен, но и его нельзя поднимать локально и на сервере одновременно.**
- **Git safety:** Commit locally whenever useful. Never `git push` without explicit, in-session user consent.

## Implementation

Работа делится на три фазы. **Фаза A выполняется интерактивно скиллом `new-telegram-bot`, а не
ralph-ом** — она требует токена от BotFather, SSH к Proxmox и создания контейнера. Ralph забирает
фазу B.

### Фаза A — бутстрап (интерактивно, скилл `new-telegram-bot`)

- [ ] 1. Создать пустую директорию `/Users/Artur_Belski/Documents/src/hk_mod_bot/` и запустить скилл
      `new-telegram-bot` **из неё** (не из `hk_bot` — Phase 2 пишет в cwd и затрёт `config.json`,
      `requirements.txt`, `src/bot.py`, `.github/workflows/deploy.yml` текущего репозитория).
- [ ] 2. Создать нового бота в BotFather, получить токен. В интервью скилла: slug `hk-mod-bot`,
      VMID `101`, IP `192.168.0.241`, `ADMIN_ID` — тот же, что в `.env` у `hk_bot`,
      GROQ-ключ — `none` (модератору не нужен).
- [ ] 3. **В BotFather: `/setprivacy` → Disable** для нового бота. Без этого Telegram не отдаёт
      боту сообщения обычных участников и модерация молча не работает — это самая частая причина
      «бот ничего не делает».
- [ ] 4. Добавить бота в группу `-4570601504` и выдать права админа с галкой «Удалять сообщения».
- [ ] 5. Дождаться, пока скилл поднимет LXC, задеплоит hello-world и подтвердит `systemctl is-active`.

### Фаза B — логика модерации (ralph-implement, в репозитории `hk_mod_bot`)

- [ ] 6. `src/moderation.py` (новый) — чистый модуль без Telegram-зависимостей:
      `normalize(text)`, `compile_rules(moderation_cfg)` (с модульным кешем по сырому JSON),
      `find_action(text, rules) -> (action, reason) | None` (возвращает самое строгое совпадение).
      Именно здесь живёт вся тестируемая логика.
- [ ] 7. `config.json` — добавить блок `moderation` по схеме из Requirements, со стартовым набором
      правил (мат + спам-инвайты). Список слов — плейсхолдерный, пользователь дополнит.
- [ ] 8. `src/bot.py` — добавить `_is_exempt(bot, chat_id, user_id)` по форме `_whitelist_allowed`
      (`get_chat_member`, статусы `administrator`/`creator`, плюс `ADMIN_ID`).
- [ ] 9. `src/bot.py` — добавить `moderate(update, context)`: взять `text or caption`, проверить
      `enabled` и `chats`, вызвать `find_action`, при совпадении проверить `_is_exempt`, затем
      выполнить действие (`delete_message` в `try/except TelegramError`, предупреждение через
      `reply_text` + `job_queue.run_once` на самоудаление).
- [ ] 10. `src/bot.py` — зарегистрировать в `main()`:
      `MessageHandler((filters.TEXT | filters.CAPTION) & filters.ChatType.GROUPS, moderate)`
      с `filters.UpdateType.MESSAGES | filters.UpdateType.EDITED_MESSAGE` (правка сообщения —
      очевидный обход) и `block=False`, чтобы модерация не задерживала остальные handler-ы.
- [ ] 11. `src/bot.py` — удалить неиспользуемый модератором скаффолд: `src/commands/hello_command.py`,
      вызовы планировщика cron-`mappings` и путь отправки медиа. Оставить `/update`, `/reload`,
      `config_loader`, systemd/CI. *(Опциональный пункт — если предпочтительнее не трогать
      сгенерированный скаффолд, этот шаг можно вычеркнуть без последствий для остального плана.)*
- [ ] 12. `tests/test_moderation.py` (новый) — юнит-тесты чистой логики: нормализация, совпадение
      по началу слова, отсутствие ложного срабатывания на `страхую`, regex-правило, битый regex
      не роняет загрузку, выбор самого строгого действия из нескольких совпадений, кеш компиляции
      инвалидируется при смене конфига.
- [ ] 13. `tests/test_bot_handlers.py` — тесты handler-а в конвенции репозитория (ручные
      `MagicMock`/`AsyncMock`): чистое сообщение не удаляется, грязное удаляется, админ чата и
      `ADMIN_ID` не модерируются, `moderation.enabled: false` отключает всё, чат вне `chats`
      игнорируется, падение `delete_message` не роняет handler.

### Фаза C — выкатка и проверка на живом чате (интерактивно)

- [ ] 14. Закоммитить локально, задеплоить (`git push` — **только с явного согласия пользователя
      в сессии**; хук `block-git-push.sh` это и так блокирует).
- [ ] 15. Проверить на живой группе: тестовое сообщение с запрещённым словом от обычного аккаунта
      удаляется, от админа — нет. Проверить `journalctl -u hk-mod-bot`.
- [ ] 16. Записать в `.claude/server_knowledge.md` нового репозитория VMID/IP/имя сервиса и грабли
      (privacy mode, права на удаление).

## Validation

- [ ] Unit tests: `python3 -m pytest tests/ -q` (в репозитории `hk_mod_bot`)
- [ ] Smoke: бот стартует с фейковым токеном и печатает `Bot started`
- [ ] Edge case: `страхую` **не** удаляется правилом со словом `хуй` (проверка `\b`-границы)
- [ ] Edge case: сообщение, попавшее одновременно под `warn`-правило и `delete_warn`-правило,
      обрабатывается как `delete_warn`
- [ ] Edge case: битый regex в конфиге логируется и пропускается, остальные правила работают
- [ ] Edge case: админ чата пишет запрещённое слово — сообщение остаётся
- [ ] Edge case: отредактированное сообщение с запрещённым словом удаляется
- [ ] Manual: на живой группе сообщение удаляется, `journalctl -u hk-mod-bot` без ошибок

## Definition of Done

```bash
python3 -m pytest tests/ -q
```

## UAT verification

**Instrument:** запускается из корня репозитория `hk_mod_bot`, токен и сеть не нужны.

```python
import sys, json
sys.path.insert(0, 'src')
from moderation import compile_rules, find_action

cfg = {
    "enabled": True,
    "chats": [],
    "rules": [
        {"name": "profanity", "words": ["хуй"], "action": "delete_warn", "reason": "мат"},
        {"name": "caps",      "regex": ["!{3,}"], "action": "warn",      "reason": "капс"},
        {"name": "invites",   "regex": ["t\\.me/\\+"], "action": "delete", "reason": "спам"},
    ],
}
rules = compile_rules(cfg)
for text in ["привет всем", "ты хуй", "страхую машину", "что!!!", "что!!! и хуй", "t.me/+abc"]:
    print(repr(text), "->", find_action(text, rules))
```

**Scenarios:**
1. Прогнать инструмент как есть и записать вывод для каждой из шести строк.
2. Заменить список строк на `["ХУЙ", "хуёвый", "страхую"]` и прогнать снова.
3. Добавить в `rules` правило с заведомо битым паттерном `{"name":"bad","regex":["([a-z"],"action":"delete","reason":"x"}` и прогнать снова.

**Acceptance criteria:** (только наблюдаемое поведение)
- [ ] `"привет всем"` не даёт никакого действия
- [ ] `"ты хуй"` даёт действие удаления с предупреждением и причиной «мат»
- [ ] `"страхую машину"` не даёт никакого действия
- [ ] `"что!!!"` даёт действие-предупреждение без удаления
- [ ] `"что!!! и хуй"` даёт удаление с предупреждением, а не просто предупреждение
- [ ] `"t.me/+abc"` даёт тихое удаление с причиной «спам»
- [ ] `"ХУЙ"` и `"хуёвый"` дают то же действие, что `"ты хуй"`; `"страхую"` по-прежнему ничего
- [ ] с битым паттерном в конфиге инструмент не падает, а остальные правила продолжают срабатывать

## Верификация плана (как проверить, что сделано правильно)

1. `python3 -m pytest tests/ -q` в `hk_mod_bot` — зелёный.
2. UAT-прогон выше — все критерии выполнены.
3. На живой группе: обычный аккаунт пишет запрещённое слово → сообщение исчезает, приходит
   самоудаляющееся предупреждение; админ пишет то же слово → сообщение остаётся.
4. `journalctl -u hk-mod-bot -n 50` — нет `TelegramError` про права.

## Примечания по процессу

- Этот файл — рабочая копия plan mode. После утверждения он копируется в
  `hk_bot/plans/0001-moderation-bot.md` (нумерация с `0001` — `plans/` пуст), откуда его читает
  `ralph-implement`.
- В `specs/` конвенция в этом проекте **уже принята** (`specs/README.md` + спеки по компонентам),
  поэтому после завершения фазы B имеет смысл прогнать `spec-writer` по новому компоненту —
  но в репозитории `hk_mod_bot`, а не здесь.
- `CLAUDE.md:23` ссылается на `./deployment/deploy.sh`, которого не существует, и описывает
  Proxmox-MCP-архитектуру, которой в репозитории нет. К этой задаче отношения не имеет, но стоит
  почистить отдельным коммитом.


---

## Post-implementation corrections

Two claims in this plan turned out to be wrong; recorded so the plan is not read as accurate.

1. **"`\b` + стем ловит словоформы (`хуй`, `хуёвый`, `хуем`)"** — false twice over.
   Russian inflection mutates the stem's final letter, so `хуй` never matches `хуёвый`; and
   more importantly мат is *prefix*-productive (`нахуй`, `заебал`, `охуеть`, `нихуя`), and a
   prefix belongs to the same orthographic word, so a bare `\b` anchor missed the dominant
   register entirely. Fixed by allowing one optional known prefix after the boundary.

2. **Phase A was planned as a `new-telegram-bot` skill run.** In practice the skill's template
   `bot.py` was scaffolded manually and the container created directly, because the skill is
   an interactive walkthrough and its template lacks the httpx log suppression that keeps the
   bot token out of `journalctl`.

Implementation lives in a separate repository at `~/Documents/src/hk_guard` (CT 101,
`192.168.0.241`, service `hk-guard`), not in this one.
