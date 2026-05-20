---
description: "Set up the local development environment step by step. Verifies prerequisites, installs dependencies, and starts the app."
---

# Local Development Setup

Walk me through setting up this project for local development. Check each prerequisite and fix anything that's missing.

## Steps

1. **Check prerequisites** — verify these are installed:
   - Python 3.11+ (`python --version`)
   - uv (`uv --version`)
   - Node.js 18+ (`node --version`)
   - pnpm (`pnpm --version`)
   - Docker (`docker --version`)

2. **Set up environment** — copy `.env.example` to `.env` if it doesn't exist.

3. **Install Python dependencies**:
   ```bash
   cd py/apps/app-template && uv pip install -e .[dev]
   ```

4. **Install TypeScript dependencies**:
   ```bash
   cd ts && pnpm install
   ```

5. **Run tests** to verify everything works:
   ```bash
   cd py/apps/app-template && uv run pytest tests/ -v
   ```

6. **Start the app**:
   - Option A (Docker): `docker compose up --build`
   - Option B (Direct): Start backend + frontend separately

7. **Verify** — backend health check + frontend loads.

## Tone
Be encouraging and precise. If something is missing, give me the exact install command for macOS.
