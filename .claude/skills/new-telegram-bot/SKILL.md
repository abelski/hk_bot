---
name: new-telegram-bot
description: Bootstrap a new Telegram bot — preflight checks, interactive config interview, scaffold project files, create a Proxmox LXC container, deploy and start the bot as a systemd service, optionally set up GitHub CI/CD.
allowed-tools: Read, Edit, Write, Bash, AskUserQuestion, TodoWrite
---

You are an interactive guide that bootstraps a new Telegram bot from scratch. Walk the user through every step. Never do multiple phases silently — explain what you're doing, show results, and wait for confirmation before moving forward.

## Phases overview

0. **Preflight** — check local tools, Proxmox SSH, and give install instructions for anything missing
1. **Interview** — ask the user for all bot configuration values
2. **Scaffold** — write all project files locally from templates
3. **Create container** — create and start the Proxmox LXC
4. **Deploy** — push files, install deps, start systemd service
5. **GitHub CI/CD** *(optional)* — register a new runner instance, generate workflow, guide repo setup
6. **Verify** — confirm the bot is running, show logs

The skill templates are at `.claude/skills/new-telegram-bot/templates/`.

---

## Phase 0 — Preflight checks

Run all checks below **before** asking the user anything. Collect all results, then report them together. Do NOT stop at the first failure — check everything first.

### Check 1 — Python 3.10+

```bash
python3 --version
```

Pass: version is 3.10 or higher.
Fail → show:
```
Python 3.10+ is required.

macOS:   brew install python3
Ubuntu:  sudo apt-get install python3 python3-pip
```

### Check 2 — pip3

```bash
pip3 --version
```

Pass: any version printed.
Fail → show:
```
pip3 is not installed.

macOS:   brew install python3   (includes pip3)
Ubuntu:  sudo apt-get install python3-pip
```

### Check 3 — git

```bash
git --version
```

Pass: any version printed.
Fail → show:
```
git is not installed.

macOS:   brew install git   (or: xcode-select --install)
Ubuntu:  sudo apt-get install git
```

### Check 4 — GitHub CLI (gh)

```bash
gh --version
```

Pass: any version printed.
Fail → show:
```
GitHub CLI (gh) is not installed. It's needed for creating repos and getting runner tokens.

macOS:   brew install gh
Ubuntu:  (see https://cli.github.com/manual/installation)

After installing, authenticate:
  gh auth login
```

If `gh` is installed, also check authentication:
```bash
gh auth status
```

Not logged in → show:
```
GitHub CLI is installed but not authenticated. Run:
  gh auth login
```

### Check 5 — SSH access to Proxmox

```bash
ssh -o ConnectTimeout=5 -o BatchMode=yes root@192.168.0.31 "echo OK"
```

Pass: prints `OK`.
Fail → show:
```
Cannot SSH to Proxmox host at 192.168.0.31.

Possible fixes:
1. Make sure you're on the same network as the Proxmox host.
2. Check that your SSH key is added:   ssh-copy-id root@192.168.0.31
3. Or add manually: cat ~/.ssh/id_rsa.pub  →  paste into /root/.ssh/authorized_keys on the host.
```

### Check 6 — Existing containers (to suggest a free VMID)

Only run if Check 5 passed:
```bash
ssh root@192.168.0.31 "pct list"
```

Parse the output and note: which VMIDs are taken, what IPs are in use. You'll use this in the interview.

### Check 7 — Proxmox storage

Only run if Check 5 passed:
```bash
ssh root@192.168.0.31 "pvesm status | grep local"
```

Note available disk space. Warn if less than 5 GB free.

### Check 8 — Ubuntu template present

Only run if Check 5 passed:
```bash
ssh root@192.168.0.31 "ls /var/lib/vz/template/cache/ubuntu-jammy-20231124_arm64.tar.xz 2>/dev/null && echo FOUND || echo MISSING"
```

Missing → show:
```
The Ubuntu Jammy arm64 template is missing from Proxmox.
Download it via the Proxmox UI: Datacenter → local storage → CT Templates → search "ubuntu-jammy".
Or via SSH:
  ssh root@192.168.0.31 "pveam download local ubuntu-22.04-standard_22.04-1_arm64.tar.zst"
(Check exact filename with: ssh root@192.168.0.31 "pveam available | grep ubuntu-jammy")
```

---

### After all checks

Print a summary table:

```
Preflight results
─────────────────────────────────────────
  Python 3.x         ✓ / ✗
  pip3               ✓ / ✗
  git                ✓ / ✗
  gh CLI             ✓ / ✗  (authenticated: yes/no)
  SSH to Proxmox     ✓ / ✗
  Existing CTs       VMID list
  Storage free       X GB
  Ubuntu template    ✓ / ✗
─────────────────────────────────────────
```

If any check failed: ask the user using `AskUserQuestion`:
> "Some prerequisites are missing (listed above). Have you installed everything and are ready to continue?"
> Options: "Yes, all fixed — continue" / "No, I need more help"

If they say "No, I need more help" — ask what specifically is blocking them and help them resolve it before proceeding.

If all checks passed: say "All checks passed. Let's configure your bot." and continue to Phase 1.

---

## Phase 1 — Interview

Ask all questions in **one** `AskUserQuestion` call. Show the context information you collected in Phase 0 (taken VMIDs, taken IPs) so the user can make informed choices.

Questions to ask:

1. **Bot name** (slug)
   Context: used as the service name, container hostname, and install path `/root/<name>`. Lowercase, hyphens ok.
   Example: `my-bot`

2. **Telegram bot token**
   Context: get one from [@BotFather](https://t.me/BotFather) — send `/newbot`, follow the prompts.
   Format: `123456789:ABCdef...`

3. **Admin Telegram user ID**
   Context: your numeric Telegram ID. Find it by messaging [@userinfobot](https://t.me/userinfobot).
   Example: `123456789`

4. **Container VMID**
   Context: show the taken VMIDs from Phase 0. Suggest the next free one.
   Example: if 100 is taken, suggest 101.

5. **Container IP address**
   Context: show the IPs already in use from `pct list`. Must be in the `192.168.0.x/24` range.
   Example: `192.168.0.241`

6. **GROQ API key** *(optional)*
   Context: free tier available at https://console.groq.com. Used for optional AI text rewriting.
   Enter `none` to skip.

7. **Set up GitHub CI/CD?**
   Context: auto-deploys the bot on every `git push`. Requires creating a GitHub repo and doing a one-time runner registration on the Proxmox host.
   Options: `yes` / `no`

8. **GitHub repo URL** *(only ask if answer to 7 is yes)*
   Context: the repo you'll create for this bot.
   Example: `https://github.com/yourname/my-bot`

After collecting answers, confirm back to the user:

```
Configuration summary
──────────────────────────────────────────
  Bot name:       <value>
  Container:      CT <VMID> at <IP>
  Bot dir:        /root/<name>
  Service name:   <name>
  GitHub CI/CD:   yes/no
──────────────────────────────────────────
Proceed?
```

Use `AskUserQuestion`: "Does this look right?" → "Yes, proceed" / "No, let me change something"

If they want changes, ask what to change and loop back.

After confirmation, define:
- `BOT_NAME` = slug
- `BOT_DIR` = `/root/{BOT_NAME}`
- `SERVICE_NAME` = `{BOT_NAME}`
- `VMID` = container ID
- `CONTAINER_IP` = IP address
- `SETUP_GITHUB_CI` = true/false

---

## Phase 2 — Scaffold project

Tell the user: "Creating project files locally..."

Read all template files from `.claude/skills/new-telegram-bot/templates/` and write them to the **current working directory**.

### Files to copy verbatim

| Source (skill folder) | Destination (cwd) |
|-----------------------|-------------------|
| `templates/src/config_loader.py` | `src/config_loader.py` |
| `templates/src/api/__init__.py` | `src/api/__init__.py` |
| `templates/src/api/abstract_request_command.py` | `src/api/abstract_request_command.py` |
| `templates/src/api/abstract_cron_command.py` | `src/api/abstract_cron_command.py` |
| `templates/src/api/abstract_news_command.py` | `src/api/abstract_news_command.py` |
| `templates/src/api/abstract_command_parameter.py` | `src/api/abstract_command_parameter.py` |
| `templates/src/commands/__init__.py` | `src/commands/__init__.py` |
| `templates/src/helpers/__init__.py` | `src/helpers/__init__.py` |
| `templates/requirements.txt` | `requirements.txt` |
| `templates/config.json` | `config.json` |

### Files requiring substitution

**`src/bot.py`** — read `templates/src/bot.py`, replace:
- `{{BOT_NAME}}` → `BOT_NAME`
- `{{BOT_DIR}}` → `BOT_DIR`
- `{{SERVICE_NAME}}` → `SERVICE_NAME`

**`src/commands/hello_command.py`** — read `templates/src/commands/hello_command.py`, replace:
- `{{BOT_NAME}}` → `BOT_NAME`

**`.env`** — write directly (do not read from template):
```
TELEGRAM_BOT_TOKEN=<user value>
ADMIN_ID=<user value>
BOT_DIR=<BOT_DIR>
BOT_SERVICE=<SERVICE_NAME>
BOT_REPO_URL=<repo URL or empty>
GROQ_API_KEY=<groq key or empty>
```

**`{SERVICE_NAME}.service`** — read `templates/bot.service.template`, replace:
- `{{BOT_NAME}}` → `BOT_NAME`
- `{{BOT_DIR}}` → `BOT_DIR`

### Verify scaffolding

After writing all files:
```bash
find src -type f | sort
```

Print the file list to the user and say "Project files created. Here's what was generated:"

---

## Phase 3 — Create Proxmox LXC container

Tell the user: "Creating container CT {VMID} on the Proxmox host..."

**Step 1** — Verify VMID is free:
```bash
ssh root@192.168.0.31 "pct list"
```
If VMID appears in output — stop, tell the user, ask them to pick a different VMID.

**Step 2** — Create the container:
```bash
ssh root@192.168.0.31 "pct create {VMID} local:vztmpl/ubuntu-jammy-20231124_arm64.tar.xz \
  --hostname {BOT_NAME} \
  --memory 256 \
  --rootfs local:4 \
  --net0 name=eth0,bridge=vmbr0,ip={CONTAINER_IP}/24,gw=192.168.0.1 \
  --unprivileged 1 \
  --features nesting=1 \
  --ostype ubuntu \
  --cores 1"
```
Expected: no output means success.

**Step 3** — Start the container:
```bash
ssh root@192.168.0.31 "pct start {VMID}"
sleep 5
```

**Step 4** — Confirm it started:
```bash
ssh root@192.168.0.31 "pct status {VMID}"
```
Expected: `status: running`

**Step 5** — Install Python:
```bash
ssh root@192.168.0.31 "pct exec {VMID} -- bash -c 'apt-get update -q && apt-get install -y python3 python3-pip'"
```
This takes ~30 seconds. Tell the user you're installing Python inside the container.

**Step 6** — Create directory structure:
```bash
ssh root@192.168.0.31 "pct exec {VMID} -- mkdir -p {BOT_DIR}/src/api {BOT_DIR}/src/commands/helpers {BOT_DIR}/src/helpers"
```

Tell the user: "Container CT {VMID} is ready at {CONTAINER_IP}."

---

## Phase 4 — Deploy

Tell the user: "Deploying bot files to the container..."

**Step 1** — Push all source files using the pattern:
```bash
scp <local_file> root@192.168.0.31:/tmp/<filename>
ssh root@192.168.0.31 "pct push {VMID} /tmp/<filename> {BOT_DIR}/<dest_path>"
```

Files to push:

| Local | Container path |
|-------|---------------|
| `requirements.txt` | `{BOT_DIR}/requirements.txt` |
| `config.json` | `{BOT_DIR}/config.json` |
| `.env` | `{BOT_DIR}/.env` |
| `src/bot.py` | `{BOT_DIR}/src/bot.py` |
| `src/config_loader.py` | `{BOT_DIR}/src/config_loader.py` |
| `src/api/__init__.py` | `{BOT_DIR}/src/api/__init__.py` |
| `src/api/abstract_request_command.py` | `{BOT_DIR}/src/api/abstract_request_command.py` |
| `src/api/abstract_cron_command.py` | `{BOT_DIR}/src/api/abstract_cron_command.py` |
| `src/api/abstract_news_command.py` | `{BOT_DIR}/src/api/abstract_news_command.py` |
| `src/api/abstract_command_parameter.py` | `{BOT_DIR}/src/api/abstract_command_parameter.py` |
| `src/commands/__init__.py` | `{BOT_DIR}/src/commands/__init__.py` |
| `src/commands/hello_command.py` | `{BOT_DIR}/src/commands/hello_command.py` |
| `src/helpers/__init__.py` | `{BOT_DIR}/src/helpers/__init__.py` |

**Step 2** — Install Python dependencies inside the container:
```bash
ssh root@192.168.0.31 "pct exec {VMID} -- pip3 install -r {BOT_DIR}/requirements.txt"
```
If this fails with a PEP 668 "externally managed" error, retry with `--break-system-packages`.
This takes ~60 seconds. Tell the user you're installing dependencies.

**Step 3** — Install systemd service:
```bash
scp {SERVICE_NAME}.service root@192.168.0.31:/tmp/{SERVICE_NAME}.service
ssh root@192.168.0.31 "pct push {VMID} /tmp/{SERVICE_NAME}.service /etc/systemd/system/{SERVICE_NAME}.service"
ssh root@192.168.0.31 "pct exec {VMID} -- systemctl daemon-reload"
ssh root@192.168.0.31 "pct exec {VMID} -- systemctl enable {SERVICE_NAME}"
ssh root@192.168.0.31 "pct exec {VMID} -- systemctl start {SERVICE_NAME}"
```

---

## Phase 5 — GitHub CI/CD (skip entirely if `SETUP_GITHUB_CI` is false)

Explain to the user: "The existing runner on the Proxmox host is registered to a specific repo and won't pick up jobs from a new one. We need to register a new runner instance for your repo. The runner binary is already installed — this just takes a minute."

### Step 1 — Get a registration token

Tell the user:
```
You need a GitHub runner registration token for your new repo.

Option A (automatic — requires gh CLI):
  Run this locally:
  gh api repos/<owner>/<repo> -X POST /actions/runners/registration-token --jq '.token'

Option B (manual):
  1. Go to https://github.com/<owner>/<repo>/settings/actions/runners
  2. Click "New self-hosted runner"
  3. Copy the token from the --token argument shown on the page

The token expires in 1 hour.
```

Ask the user with `AskUserQuestion`: "Paste your runner registration token:"
(free text input via "Other")

Store as `RUNNER_TOKEN`.

### Step 2 — Create runner instance on Proxmox host

Reuse the existing runner binaries — no download needed:
```bash
ssh root@192.168.0.31 "
  mkdir -p /root/actions-runner-{BOT_NAME} &&
  cd /root/actions-runner-{BOT_NAME} &&
  ln -sf /root/actions-runner/bin . &&
  ln -sf /root/actions-runner/externals . &&
  cp /root/actions-runner/config.sh . &&
  cp /root/actions-runner/run.sh . &&
  cp /root/actions-runner/runsvc.sh . &&
  cp /root/actions-runner/svc.sh . &&
  cp /root/actions-runner/env.sh .
"
```

### Step 3 — Configure and register

```bash
ssh root@192.168.0.31 "
  cd /root/actions-runner-{BOT_NAME} &&
  ./config.sh \
    --url {GITHUB_REPO_URL} \
    --token {RUNNER_TOKEN} \
    --name {BOT_NAME}-runner \
    --unattended
"
```

### Step 4 — Install as systemd service and start

```bash
ssh root@192.168.0.31 "cd /root/actions-runner-{BOT_NAME} && ./svc.sh install && ./svc.sh start"
```

Verify:
```bash
ssh root@192.168.0.31 "systemctl is-active \$(systemctl list-units --type=service | grep {BOT_NAME}-runner | awk '{print \$1}')"
```

Expected: `active`

### Step 5 — Generate the workflow file

Read `templates/.github/workflows/deploy.yml.template`, replace all of:
- `{{VMID}}` → `VMID`
- `{{BOT_NAME}}` → `BOT_NAME`
- `{{BOT_DIR}}` → `BOT_DIR`
- `{{SERVICE_NAME}}` → `SERVICE_NAME`

Write result to `.github/workflows/deploy.yml`.

### Step 6 — Remaining manual steps

Print:
```
──────────────────────────────────────────────────────────
  GitHub CI/CD — final manual steps
──────────────────────────────────────────────────────────

1. Create the GitHub repo (if not done yet):
     gh repo create <repo-name> --private

2. Initialise git and push:
     git init
     git add .
     git commit -m "initial commit"
     git remote add origin {GITHUB_REPO_URL}
     git push -u origin main

   Note: .env is in .gitignore — it will NOT be pushed.

3. Add the ENV_FILE secret (replaces .env on each deploy):
     gh secret set ENV_FILE < .env
   Or manually: repo → Settings → Secrets → Actions → New secret
     Name:  ENV_FILE
     Value: paste the contents of your .env file

After this, every push to main automatically deploys to CT {VMID}.
The bot will send you a Telegram message with the commit SHA when deploy completes.
──────────────────────────────────────────────────────────
```

Also make sure `.env` is in `.gitignore`. Write a `.gitignore` if one doesn't exist:
```
.env
__pycache__/
*.pyc
*.pyo
_work/
```

---

## Phase 6 — Verify

Tell the user: "Checking that the bot started correctly..."

```bash
sleep 5
ssh root@192.168.0.31 "pct exec {VMID} -- systemctl is-active {SERVICE_NAME}"
ssh root@192.168.0.31 "pct exec {VMID} -- journalctl -u {SERVICE_NAME} -n 30 --no-pager"
```

**If active:**
```
──────────────────────────────────────────────────────────
  Bot is running!

  Container:   CT {VMID} ({BOT_NAME}) at {CONTAINER_IP}
  Service:     {SERVICE_NAME} — active
  Bot dir:     {BOT_DIR}

  Next steps:
  • Open Telegram, message your bot, or mention it in a group
  • Add commands in src/commands/ — drop a .py file and send /reload
  • Edit config.json to add recipients and cron schedules, then /reload
  • Logs: ssh root@192.168.0.31 "pct exec {VMID} -- journalctl -u {SERVICE_NAME} -f"
──────────────────────────────────────────────────────────
```

**If failed:**
Show the last 50 log lines and help the user debug:
```bash
ssh root@192.168.0.31 "pct exec {VMID} -- journalctl -u {SERVICE_NAME} -n 50 --no-pager"
```

Common failures and fixes:

| Log contains | Likely cause | Fix |
|---|---|---|
| `TELEGRAM_BOT_TOKEN not set` | `.env` not pushed or empty | Re-push `.env` with `pct push` |
| `InvalidToken` | Token has wrong format | Check token in `.env` — must contain `:` |
| `ModuleNotFoundError` | pip install failed or incomplete | Re-run pip install step |
| `FileNotFoundError: config.json` | config.json missing | Re-push config.json |
| `Address already in use` | Another bot running on same token | Stop the other process |

---

## General constraints

- Never commit `.env` to git
- Never push to git without explicit user consent
- Service file goes inside the container, not on the Proxmox host
- Always use `ubuntu-jammy-20231124_arm64.tar.xz` — the Debian template is broken on this arm64 Proxmox
- Container is unprivileged (matches CT 100 pattern)
- Each new bot repo needs its own runner registration — the runner at `/root/actions-runner/` is repo-scoped; reuse its binaries via symlinks
