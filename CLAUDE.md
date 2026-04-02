# IPL 2026 Predictor — Development Guidelines

Rules Claude Code must follow in every session for this project.

---

## Git & Commits

- Commit messages must be written in **1st person** and (e.g. "Add live standings endpoint", "Fix calibration bucket logic", "Update feature engine to use 2026 form")
- Never commit personal or learning-oriented files — this includes `Ipl 2026 final project plan · MD` or any file that contains learning instructions, study notes, or personal commentary not relevant to the codebase
- Never commit raw data files (`.csv`) or model binaries (`.pkl`)
- Never commit `.env` — only `.env.example`
- Stage files explicitly by name — never `git add .` blindly

## Code Style

- Python: keep functions short and focused — one job per function
- Add comments only where logic is non-obvious, not on every line
- No speculative features — build only what is needed right now

## Project-Specific Rules

- The pre-match model uses 42 features — `models/feature_cols.json` is the source of truth
- The live model uses 18 features — `models/live_feature_cols.json` is the source of truth
- Always run from the project root (`d:/IPL Prediction`) — imports and file paths depend on it
- When restarting the API, kill the old process on port 8000 first

## Adding New Rules

Add new rules here as the project evolves. Keep them short and specific.
