---
  Accountability Buddy - Project Context

  Quick Summary

  Accountability Buddy is an automated accountability system that uses Vapi (AI voice platform) to conduct daily morning and evening check-in phone
  calls. It helps users set daily intentions, track goals, and review progress—all via natural voice conversations. Optionally syncs all check-ins to an
  Obsidian vault on GitHub.

  ---
  What It Does (High Level)

  1. Morning Call: AI calls user at scheduled time, asks about daily plans/intentions, extracts goals as structured data
  2. Evening Call: AI retrieves morning goals, calls user to review what was accomplished, captures reflections
  3. Obsidian Sync (optional): Writes goals and reflections to markdown files in a GitHub-hosted Obsidian vault
  4. Fully Automated: Runs hands-off via Docker with cron scheduling

  ---
  Tech Stack

  | Component        | Technology                     |
  |------------------|--------------------------------|
  | Language         | Python 3.9+                    |
  | Voice Platform   | Vapi (vapi.ai)                 |
  | SDK              | vapi_server_sdk                |
  | Scheduling       | Cron (inside Docker or native) |
  | Deployment       | Docker Compose                 |
  | Optional Storage | GitHub-hosted Obsidian vault   |
  | Scripts          | Bash (setup/bootstrap)         |

  ---
  Project Structure

  accountability_buddy/
  ├── make_morning_call.py      # Morning call orchestration + Obsidian sync
  ├── make_evening_call.py      # Evening call + goal retrieval + prompt update + sync
  ├── check_morning_goals.py    # CLI to inspect last morning's structured outputs
  ├── vapi_polling.py           # Polling utilities, cron parsing, datetime handling
  ├── obsidian_git_sync.py      # Git operations + Obsidian markdown file management
  ├── test_obsidian_sync.py     # Manual testing for Obsidian integration
  ├── setup_production.sh       # Docker cron setup + dependency installation
  ├── setup.sh                  # Local environment validation
  ├── docker-compose.yml        # Container orchestration
  ├── requirements.txt          # Dependencies (vapi_server_sdk)
  ├── .env.template             # Environment variable template
  └── docs/                     # Architecture documentation

  ---
  Architecture & Data Flow

  Morning Call Flow

  1. Load environment variables
  2. Initialize Vapi client
  3. Create outbound call via Vapi API (morning assistant)
  4. Poll Vapi for call completion + structured output
  5. Parse goals from structured output artifact
  6. If Obsidian enabled: Create markdown entry in vault
  7. Log completion

  Evening Call Flow

  1. Load environment + polling config
  2. Find today's morning call with structured outputs
  3. Extract goals list from morning call artifact
  4. Update evening assistant's system prompt with specific goals
  5. Create outbound call (evening assistant)
  6. Poll for evening structured output
  7. Parse completion status + reflections
  8. If Obsidian enabled: Update vault with checkmarks, completion %, reflections
  9. Log completion

  Obsidian Sync Flow

  1. Clone vault repo from GitHub (with token auth)
  2. Create/update markdown files:
     - Accountability/Daily Logs/{YYYY-MM-DD}-accountability.md
     - Daily Notes/{YYYY-MM-DD}.md (embed reference)
  3. YAML frontmatter with metadata (dates, IDs, completion rate)
  4. Commit and push changes
  5. Cleanup temp directory

  ---
  Key Modules

  vapi_polling.py

  - wait_for_structured_output(): Polls Vapi for completed calls with structured outputs
  - find_structured_call(): Single-pass search for matching call
  - cron_reference_time(): Parses cron expression to find scheduled time
  - parse_vapi_datetime(): Normalizes Vapi datetime responses

  obsidian_git_sync.py

  - ObsidianGitSync: Class managing git clone/commit/push operations
  - parse_goals_from_vapi_output(): Extracts goals from nested structured output
  - create_morning_entry(): Generates markdown with YAML frontmatter
  - update_evening_entry(): Updates file with completion status and reflections

  make_evening_call.py

  - _build_evening_prompt(): Constructs prompt with morning goals embedded
  - _parse_evening_results(): Derives completion flags from evening output

  ---
  Environment Variables

  Required

  VAPI_API_TOKEN              # Vapi API token
  MORNING_ASSISTANT_ID        # Vapi morning assistant ID
  EVENING_ASSISTANT_ID        # Vapi evening assistant ID
  PHONE_NUMBER_ID             # Vapi phone number ID
  TARGET_PHONE_NUMBER         # User's phone (E.164: +1234567890)

  Optional - Scheduling

  MORNING_CALL_TIME           # Cron expression (default: "0 8 * * *")
  EVENING_CALL_TIME           # Cron expression (default: "0 20 * * *")
  TZ                          # Timezone (default: "Europe/Oslo")

  Optional - Obsidian

  OBSIDIAN_ENABLED            # "true" to enable (default: "false")
  OBSIDIAN_REPO_URL           # HTTPS URL to vault repo
  OBSIDIAN_GITHUB_TOKEN       # GitHub token for vault access
  OBSIDIAN_GIT_USER_NAME      # Git commit author name
  OBSIDIAN_GIT_USER_EMAIL     # Git commit author email

  Optional - Polling

  VAPI_POLL_INTERVAL_SECONDS  # Poll interval (default: 5.0)
  VAPI_POLL_TIMEOUT_SECONDS   # Timeout (default: 0 = infinite)
  VAPI_CALL_TIME_TOLERANCE_MINUTES  # Time window for matching (default: 120)

  ---
  External Integrations

  Vapi (vapi.ai)

  - Purpose: AI voice platform for outbound calls
  - Operations: calls.create(), calls.list(), calls.get(), assistants.update()
  - Data: Call status, structured outputs (goals/reflections), timestamps

  GitHub

  - Purpose: Host Obsidian vault repository
  - Operations: Clone, commit, push via git CLI
  - Auth: Personal access token with repo scope

  ---
  Deployment

  Docker (Recommended)

  # 1. Create .env from .env.template
  # 2. Start container
  docker-compose up -d
  # Container auto-installs deps, configures cron, runs forever

  Local/Manual

  python -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  source .env
  python make_morning_call.py   # or make_evening_call.py

  ---
  Key Design Decisions

  1. Command-driven architecture: Each script is self-contained and idempotent
  2. Polling with tolerance: Handles Vapi latency and clock skew gracefully
  3. Cron-anchored timing: Polls relative to scheduled time, not current time
  4. Optional Obsidian: Gracefully skips if not configured
  5. Git pull before execution: Cron always pulls latest code before running
  6. Structured output extraction: Uses Vapi's built-in structured output feature for reliable goal parsing

  ---
  Approximate Codebase Size

  - ~1,800 lines of Python/Bash across 9 main files
  - Single external dependency: vapi_server_sdk

  ---
  File Quick Reference

  | File                   | Lines | Purpose                               |
  |------------------------|-------|---------------------------------------|
  | make_morning_call.py   | ~113  | Morning call orchestration            |
  | make_evening_call.py   | ~271  | Evening call + goal injection         |
  | vapi_polling.py        | ~249  | Polling utilities + datetime handling |
  | obsidian_git_sync.py   | ~425  | Git ops + markdown generation         |
  | check_morning_goals.py | ~69   | Goal inspection CLI                   |
  | setup_production.sh    | ~85   | Docker cron setup                     |

  ---
