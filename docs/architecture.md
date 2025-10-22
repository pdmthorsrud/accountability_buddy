# Accountability Buddy Architecture Guide

This document provides a deep reference for how Accountability Buddy is put together, how the pieces interact at run time, and where to look in the repository for each responsibility.

---

## 1. System Overview

Accountability Buddy automates two daily voice check-ins (morning and evening) using the Vapi platform:

- **Morning Call** gathers the user's intentions for the day and stores structured outputs in Vapi.
- **Evening Call** retrieves the morning goals from Vapi, rewrites the evening assistant's prompt with those goals, and places a reflection call.
- **Manual Utilities** allow ad-hoc inspection of the last successful morning call.
- **Cron Orchestration** keeps the repository current (`git pull --ff-only`) and runs the appropriate script on schedule.
- **Container Bootstrap** installs dependencies, validates environment variables, and wires the cron jobs inside Docker.

Visual diagrams for this flow live in `docs/architecture_flow.md`.

---

## 2. Component Catalog

| Component | Responsibility | Location |
|-----------|----------------|----------|
| Morning Call Script | Validates environment configuration and initiates the morning Vapi call. | `make_morning_call.py` |
| Evening Call Script | Fetches prior morning goals, updates the evening assistant prompt, and initiates the evening call. | `make_evening_call.py` |
| Morning Goal Inspector | Lists structured outputs captured during the latest successful morning call. | `check_morning_goals.py` |
| Production Cron Setup | Installs Python dependencies, renders `/etc/cron.d/accountability-buddy`, ensures `git pull --ff-only` precedes each run, and starts cron in foreground. | `setup_production.sh` |
| Local/Docker Setup Check | Verifies required environment variables from `.env`, logs the results, and holds the container open for manual inspection. | `setup.sh` |
| Docker Compose Bootstrap | Builds the container, clones the repo using a GitHub token, and delegates to `setup_production.sh`. | `docker-compose.yml` |
| Logs | Runtime logs captured from cron-executed scripts. | `/var/log/*.log` in-container (mapped to `./logs` when volume mounted) |

External dependencies:

- **Vapi Python SDK (`vapi_server_sdk`)** for call management, assistant updates, and artifact retrieval.
- **GitHub** for fetching the latest revision during container start (and on every cron invocation).
- **Cron** for scheduling (`cron` service started by `setup_production.sh`).
Component dependency diagrams are collected in `docs/architecture_dependencies.md`.

---

## 3. Execution Environments

### 3.1 Docker Deployment (Recommended)

1. `docker-compose up -d` (see `docker-compose.yml`) starts a `python:3.9-slim` container.
2. Container installs `git` and `cron`, clones the repository using `${GITHUB_TOKEN}` into `/app/accountability_buddy`, and executes `./setup_production.sh`.
3. `setup_production.sh` installs Python dependencies, renders cron entries into `/etc/cron.d/accountability-buddy`, touches log files under `/var/log`, and starts `cron -f`.
4. Cron now owns both the morning and evening schedules. Each run starts by updating the repo (`git pull --ff-only`), then runs the appropriate script.

### 3.2 Manual / Local Execution

- Developers can run scripts directly after exporting the environment variables (`source .env`):
  - Morning call: `python make_morning_call.py`
  - Evening call: `python make_evening_call.py`
  - Inspect outputs: `python check_morning_goals.py`
- `setup.sh` can be invoked inside the container to confirm environment setup without scheduling calls. It logs to `/app/logs/setup_check.log` and keeps the container alive briefly for log inspection.

---

## 4. Configuration & Secrets

Environment variables (mirrored in `.env.template`):

| Variable | Used In | Purpose |
|----------|---------|---------|
| `GITHUB_TOKEN` | Docker entrypoint, `setup.sh` | Authenticated clone of private repository. |
| `GITHUB_REPO` (optional) | Docker entrypoint | Overrides the default `pdmthorsrud/accountability_buddy`. |
| `VAPI_API_TOKEN` | All Python scripts | Authenticates SDK requests to Vapi. |
| `MORNING_ASSISTANT_ID` | Morning/Evening scripts | Chooses the assistant responsible for the morning call. |
| `EVENING_ASSISTANT_ID` | Evening script | Assistant updated and used during the evening call. |
| `PHONE_NUMBER_ID` | Morning/Evening scripts | Vapi phone number that initiates the call. |
| `TARGET_PHONE_NUMBER` | Morning/Evening scripts | Destination phone number (E.164). |
| `MORNING_CALL_TIME` | `setup_production.sh`, cron | Cron expression for the morning job (default `0 8 * * *`). |
| `EVENING_CALL_TIME` | `setup_production.sh`, cron | Cron expression for the evening job (default `0 20 * * *`). |
| `TZ` | Docker environment | Controls cron timezone (default `Europe/Oslo`). |

Validation strategies:

- Python scripts immediately raise `ValueError` if required variables are absent.
- `setup.sh` logs missing values and prevents automatic cron setup, prompting manual correction.
- Cron file embeds environment values so each job inherits the correct configuration.

---

## 5. Operational Flows

### 5.1 Morning Call Flow (`make_morning_call.py`)

1. **Startup**: Cron or manual invocation runs inside the repo directory.
2. **Refresh Code**: Cron wrapper performs `git pull --ff-only`; failures abort the script to avoid running stale code.
3. **Environment Validation**: Script ensures all required variables exist.
4. **Vapi Client Init**: `client = Vapi(token=VAPI_API_TOKEN)`.
5. **Call Creation**: `client.calls.create` is invoked with the morning assistant ID, phone number ID, and target customer number.
6. **Output**: Console/log displays call metadata (ID, status, number). No local state is stored; Vapi records the session and structured outputs.

### 5.2 Evening Call Flow (`make_evening_call.py`)

1. **Startup & Refresh**: Runs under cron (with preceding `git pull`) or manually.
2. **Environment Validation**: Ensures morning/evening assistant IDs plus phone configuration are present.
3. **Fetch Call History**: `client.calls.list()` retrieves recent calls.
4. **Filter Morning Calls**: Filters for `status == 'ended'`, matching `TARGET_PHONE_NUMBER`, and the morning assistant ID.
5. **Locate Structured Outputs**: For each candidate, fetch the full call (`client.calls.get(id=call.id)`) and inspect `artifact.structured_outputs`.
6. **Build Evening Prompt**: Embeds the goals text into a tailored prompt with instructions for tone and flow.
7. **Update Evening Assistant**: `client.assistants.update` rewrites the assistant's `model.messages[0].content` using the prompt.
8. **Place Evening Call**: `client.calls.create` uses the updated evening assistant to call the same target number.
9. **Logging**: The prompt, assistant update status, and call metadata are printed to stdout (captured in `/var/log/evening_call.log` when run via cron).

Error handling:

- If no successful morning calls exist, the script prints diagnostics and exits without placing a call.
- If no structured outputs are available yet, it reports the count of successful calls inspected.

### 5.3 Morning Goal Inspection Flow (`check_morning_goals.py`)

1. **Manual Invocation**: Typically run by a developer or operator.
2. **Fetch & Filter Calls**: Same filtering logic as the evening script.
3. **Display Structured Outputs**: Prints the artifact contents to stdout, allowing quick confirmation of morning goals without triggering a new call.

### 5.4 Cron Job Lifecycle (`setup_production.sh`)

1. **Dependency Installation**: `pip install -r requirements.txt` inside the repo ensures the Vapi SDK is available.
2. **Cron File Rendering**: Writes `/etc/cron.d/accountability-buddy` with:
   - Exported environment values.
   - A controlled `PATH`.
   - Morning and evening entries using `cd "$APP_DIR" && { git pull --ff-only && python3 make_*.py; }`.
3. **Permissions & Logs**: Applies `0644` to the cron file; `touch`es `/var/log/morning_call.log` and `/var/log/evening_call.log` with world-writable permissions for cron output.
4. **Activation**: Installs the cron file via `crontab /etc/cron.d/accountability-buddy`.
5. **Service Start**: Launches `cron -f` to keep the container running and stream logs to stdout.

---

## 6. Data & State

- **Persistent State**: None stored locally by default. All conversational artifacts and structured outputs live in Vapi.
- **Logs**: Morning/evening cron runs append to `/var/log/morning_call.log` and `/var/log/evening_call.log` (volume-mountable to `./logs` when using Docker).
- **Configuration State**: `.env` provides secrets and scheduling; cron embeds those values at rendering time, so updating environment variables requires rerunning `setup_production.sh` (or recreating the container).

---

## 7. Observability & Troubleshooting

- **Check Cron Activity**: View `/var/log/morning_call.log` or `/var/log/evening_call.log` for successful runs or errors (e.g., failed `git pull`, missing env vars, Vapi SDK errors).
- **Inspect Latest Morning Goals**: Run `python check_morning_goals.py` locally or inside the container (after `docker exec -it accountability-buddy bash`).
- **Verify Environment**: Execute `./setup.sh` to log which variables are present; review `/app/logs/setup_check.log`.
- **Vapi Dashboard**: Use Vapi's web UI to confirm call status, structured outputs, and assistant configuration if the scripts succeed but behavior is unexpected.

---

## 8. Extension Points

- **Alternative Call Logic**: Modify `make_morning_call.py` to send additional metadata or optional context without affecting cron setup.
- **Evening Prompt Customization**: Update the templated string in `make_evening_call.py` with new tone, structure, or follow-up questions.
- **Additional Schedules**: Extend `setup_production.sh` to add more cron jobs (e.g., midday reminders) by appending to the heredoc.
- **State Storage**: Integrate a database or filesystem cache if you need to persist call summaries locally; wire it into the scripts before the Vapi calls.

---

## 9. Change Impact Hotspots

- `setup_production.sh`: Governs cron behavior, log paths, and dependency installation. Any change affects both morning and evening automation.
- `make_evening_call.py`: Houses the most logic (structured output parsing, assistant update). Regressions here can break evening calls even if morning calls succeed.
- `docker-compose.yml`: Affects bootstrap, dependency availability, and file paths inside the container.

Use this map to quickly target the relevant file when diagnosing issues or planning enhancements.
