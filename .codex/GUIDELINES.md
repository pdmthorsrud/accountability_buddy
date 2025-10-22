# Accountability Buddy Development Guidelines

These conventions codify the patterns already present in the repository so new work stays consistent while leaving room for sensible evolution.

## 1. File Naming & Organisation
- **Python modules** adopt lower case snake case that mirrors their responsibility (`make_morning_call.py`, `check_morning_goals.py`). Continue using descriptive verbs to signal script intent; this keeps CLI entry points discoverable.
- **Shell scripts** use snake case with `_production` or similar qualifiers when the lifecycle differs (`setup.sh` vs `setup_production.sh`), making it clear which flow runs inside containers.
- **Documentation** stays in `.md` files even when containing Mermaid diagrams (`docs/architecture_flow.md`) so GitHub renders them inline.
- **Environment files**:
  - `.env.example` documents the minimal set for local usage without secrets.
  - `.env.template` expands to Docker needs (GitHub token, timezone). Copy to `.env` per deployment target, never commit populated `.env`.
- **Auxiliary assets** like sample CSVs live at repo root (`pd_accountability_buddy_numbers.csv`) for quick inspection; prefer a dedicated `data/` folder if new datasets grow.

**Quick reference**
- New CLI entry point → `new_feature.py`
- Shared helpers (if introduced) → place under `accountability/` package-style folder to avoid cluttering root scripts.

## 2. Code Style Patterns
- **Environment access**: Load secrets at the top of each script via `os.environ.get(...)` and immediately validate with a fail-fast guard (`if not all([...]): raise ValueError(...)`). This prevents partially configured runs and matches `make_morning_call.py`.
- **API clients**: Instantiate `Vapi` once (`client = Vapi(token=VAPI_API_TOKEN)`) and reuse it; keep additional helpers pure functions that accept the client if refactoring.
- **Error handling**: Prefer explicit validation and clear console messaging over silent failures. Raise exceptions for configuration issues and use conditional logging for operational misses (e.g., no structured outputs found in `make_evening_call.py`).
- **Logging & output**: Use `print` statements with separators (e.g., `print("=" * 50)`) rather than introducing logging frameworks; cron captures stdout/stderr to log files, so plain prints keep troubleshooting simple.
- **Naming**: Constants derived from environment variables stay uppercase; runtime variables use descriptive snake case (`successful_calls`, `goals_text`) to aid readability.
- **Comments**: Inline comments highlight intent behind non-trivial conditionals or loops, as seen when filtering calls in `make_evening_call.py`. Avoid restating obvious code; explain decision boundaries instead.
- **Prompt templates**: Store multi-line prompts in triple-quoted strings and make the user-facing rationale explicit inside the prompt (see the evening prompt block). Maintain this style to keep edits ergonomic and copyable.

## 3. Documentation Style
- **README structure**: Lead with a one-paragraph summary, follow with feature bullets (emojis welcome for emphasis), then stepwise setup instructions using fenced code blocks tagged with the relevant shell language (` ```bash `, ` ```cron `).
- **Architecture docs** (`docs/architecture.md`) favour numbered sections, tables for component catalogs, and cross-links to diagrams; keep additions consistent to preserve scannability.
- **Mermaid diagrams** live in fenced code blocks with the `mermaid` info string inside `.md` files, enabling GitHub’s native renderer. Do not introduce `.mmd` files.
- **Examples**: Present CLI usage as runnable snippets (e.g., `python make_evening_call.py`). When adding new commands, show the exact sequence a user should type, not pseudocode.
- **Tone**: Friendly and informative; emoji are used sparingly to highlight key flows (🌅 morning, 🌙 evening) but are not mandatory. Use them when they reinforce daypart context.

## 4. Configuration Patterns
- **Templates**: Document every environment variable in `.env.example` and `.env.template`; if a new variable is optional, leave it commented with guidance.
- **Variable naming**: Uppercase snake case, using explicit domain hints (`MORNING_ASSISTANT_ID` over a generic `ASSISTANT_ID`). Follow Vapi terminology where possible for easier cross-reference with their dashboard.
- **Runtime evaluation**: Shell scripts expose env vars explicitly in cron via heredoc lines (see `setup_production.sh`). When adding new variables, write them into the cron file so scheduled jobs inherit them.
- **Docker conventions**: Base image keeps slim Python, install only necessary packages (`git`, `cron`), and chain commands with `&&` to fail fast. Maintain `set -e` at the top of shell scripts to abort on errors.
- **Cron documentation**: Any new schedules should note their human-readable meaning in comments, mirroring the examples inside `.env.template`.

## 5. Project-Specific Practices
- **Morning flow**: `make_morning_call.py` must stay lightweight—validate configuration, initiate the call, and exit. Avoid embedding heavy logic so cron runs remain deterministic.
- **Evening flow**: Always refresh evening assistant context with the latest goals before placing the call. The flow (`list` → filter → `get` → prompt templating → `assistants.update` → `calls.create`) should remain intact; if you augment it (e.g., storing summaries), do so after the structured outputs are captured to preserve call fidelity.
- **Structured outputs**: Treat Vapi as the source of truth. If you add local persistence, capture and store the structured output string as-is to keep parity with what the assistant hears.
- **Data files**: Sample datasets belong in plain CSV with headers; version-control only redacted/test data.
- **Prompt tone**: Keep evening prompts supportive, non-judgmental, and succinct. Document any prompt evolution inline so other contributors know the behavioural intent.

## 6. Development Workflow
- **Dependencies**: Update `requirements.txt` when adding libraries; `setup_production.sh` installs from it at deployment time, so missing pins cause runtime issues.
- **Feature additions**: Start from a script prototype under the repo root, refactor into reusable modules if the surface area grows. When introducing shared helpers, encapsulate them in a package directory and update existing scripts to import them to avoid duplicated logic.
- **Testing**: No automated test suite exists; validate changes by running the relevant CLI script against a staging assistant/number. Document manual test steps in PR descriptions or supporting docs.
- **Version control**: Cron runs a `git pull --ff-only` before each scheduled script. Keep mainline history fast-forwardable (avoid `--force`) so production cron continues to sync without intervention.
- **Operational checks**: Use `python check_morning_goals.py` to verify structured outputs post-change, and tail `/var/log/*_call.log` when troubleshooting Docker deployments.
- **Docs hygiene**: Any AI-assisted or manual coding session should reassess whether architecture notes, README, or this guideline need updates; keep documentation current when behaviour changes so future automation stays in sync.

**Workflow quick reference**
- Install deps locally: `pip install -r requirements.txt`
- Run morning flow: `python make_morning_call.py`
- Run evening flow: `python make_evening_call.py`
- Verify env inside container: `./setup.sh` (logs to `/app/logs/setup_check.log`)
- Redeploy cron config after env change: rerun `setup_production.sh` or recreate the Docker container.
