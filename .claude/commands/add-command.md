You are adding a new bot command to the hk_bot project.

## Phase 1 — Clarify the command with the user

Before doing anything else, use `AskUserQuestion` to ask the user what the command should do. You must resolve all of the following before proceeding:

1. **What data does it fetch or compute?** (API, local file, system call, calculation?)
2. **What should the output look like?** (language, format, units, emoji?)
3. **Should it be scheduled via cron?** If yes — which recipient(s) and what schedule?
4. **Suggested NAME and LABEL** — propose one based on their description and confirm.

Ask only genuine blockers. If the user's description already answers something clearly, don't ask about it.

---

## Phase 2 — Explore (silent, no output yet)

Launch Explore subagents in parallel to collect everything needed before writing the plan:

- Read `src/commands/woo_command.py` — the canonical example (fetch, format, NAME/LABEL/run pattern)
- Read `src/commands/__init__.py` — how discovery works
- Read `config.json` — current recipients and mappings
- Read `tests/test_commands.py` — test pattern to follow

Collect: exact line numbers, import paths, existing recipient names, test class names already present.

---

## Phase 3 — Plan (use EnterPlanMode / ExitPlanMode)

Enter plan mode. Write the plan to `plans/command-<name>.md`. Exit plan mode for user approval.

The plan must follow the feature_analyst plan file structure:

```markdown
# Feature: <Name> Command

## Summary
## Decisions & Clarifications
## Scope
## Acceptance Criteria
## Affected Files
## Implementation Steps   ← one step per file, with exact code, line numbers, imports
## Data / Schema Changes  ← config.json additions if cron is needed
## Edge Cases & Risks
## Testing Plan
```

Each implementation step must be independently testable and contain enough detail that no further research is needed.

---

## Phase 4 — Implement

After plan approval:

1. Create `src/commands/<name>_command.py` following the rules below.
2. If cron is needed, add the mapping to `config.json`.
3. Add tests to `tests/test_commands.py`.
4. Run `python3 -m pytest tests/ -v` — all tests must pass before finishing.

---

## Command file rules

**Location:** `src/commands/<name>_command.py`
**Naming:** snake_case, always suffixed with `_command`.

Every module **must** expose exactly:

```python
NAME: str    # unique key — short, lowercase, no spaces; matches config.json "command" field
LABEL: str   # button text in the Telegram inline keyboard
async def run() -> str:   # returns the message text to send
```

All other functions are private (prefix with `_`). Do not import from other command modules — each command is self-contained.

**Template:**

```python
# src/commands/<name>_command.py

NAME = "<name>"
LABEL = "<Button Label>"


async def run() -> str:
    result = _fetch()
    if result is None:
        return "Could not fetch data, please try again later."
    return _format(result)


def _fetch():
    # synchronous I/O (requests, subprocess, etc.) is fine here
    ...


def _format(data) -> str:
    ...
```

**Auto-discovery:** `src/commands/__init__.py` scans the package with `pkgutil.iter_modules`. No registration needed — dropping the file is enough. A module is loaded only if it has `NAME`, `LABEL`, and `run`.

---

## config.json wiring (only if cron needed)

```json
{
  "recipients": {
    "my_group": "-100<chat_id>"     ← add if recipient doesn't exist yet
  },
  "mappings": [
    {
      "command": "<NAME>",
      "recipients": ["my_group"],
      "cron": "0 9 * * *"           ← 5-field crontab; omit key entirely to skip scheduling
    }
  ]
}
```

- `command` must match `NAME` exactly.
- Send `/reload` to the bot to apply config changes without restarting.

---

## Test pattern

```python
class Test<Name>Command:
    @pytest.mark.asyncio
    async def test_returns_formatted_result(self):
        from commands.<name>_command import run
        with patch("commands.<name>_command._fetch", return_value=<mock_data>), \
             patch("commands.<name>_command._format", return_value="formatted"):
            result = await run()
        assert result == "formatted"

    @pytest.mark.asyncio
    async def test_returns_error_when_fetch_fails(self):
        from commands.<name>_command import run
        with patch("commands.<name>_command._fetch", return_value=None):
            result = await run()
        assert "Could not fetch" in result

    def test_has_required_interface(self):
        import commands.<name>_command as cmd
        assert isinstance(cmd.NAME, str)
        assert isinstance(cmd.LABEL, str)
        assert callable(cmd.run)
```

**Canonical example:** `src/commands/woo_command.py`

---

## User's request

$ARGUMENTS
