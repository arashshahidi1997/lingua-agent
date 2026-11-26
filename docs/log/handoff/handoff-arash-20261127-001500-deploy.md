---
title: "lingua: one-command deploy to the ASUS (tools/deploy_asus.sh), vite proxy on :8001"
date: 2026-11-27
timestamp: 20261127-001500
tags: [handoff]
series: deploy
branch: "main"
status: open
git_commit: "2f56361"
refs: [tools/deploy_asus.sh, docs/mobile-https.md, web/vite.config.ts]
---

# lingua: one-command deploy to the ASUS

## Done (2f56361, not pushed)
- `tools/deploy_asus.sh` (run on the XPS after a push). Refuses unless XPS main is clean (tracked files, plus no
  untracked files under `web/`) and equals `origin/main` after a fetch. Reads the ASUS HEAD over ssh, refuses if
  the ASUS clone has local edits, is off main, or cannot fast-forward. Then:
  - builds `web/` on the XPS first (`npm ci` too when package files changed or node_modules is missing) when
    `web/` changed between ASUS HEAD and origin/main, when the ASUS has no `web/dist/index.html`, or with `--web`;
  - `git pull --ff-only` on the ASUS and checks it landed on the expected commit;
  - deps when `pyproject.toml`/`uv.lock` changed or `--deps`: the repo tracks **no uv.lock**, so a plain
    `uv sync` would write one on the ASUS and could drop extras; the script instead runs
    `uv pip install -e '.[api,voice,anthropic,openai]'` (the extras the ASUS venv has, `LINGUA_EXTRAS`
    overrides). If a uv.lock is ever tracked it switches to `uv sync --locked --extra …`;
  - `rsync -a --delete web/dist/` to the ASUS, `systemctl --user restart lingua-agent`, polls `/api/me` until
    200 (90 s, `LINGUA_DEPLOY_TIMEOUT`), otherwise prints `status` + 40 journal lines and exits 1.
  - `--dry-run` reads the ASUS but changes nothing; if a real run would refuse it still shows the plan
    against origin/main and exits 1. Nothing to deploy → exits 0 without restarting.
- `web/vite.config.ts`: `/api` proxy target = `LINGUA_API_URL` or `http://127.0.0.1:8001`. Checked: vite
  proxies to 127.0.0.1:8001 (ECONNREFUSED there with no dev server running, as expected).
- `docs/mobile-https.md`: hand-typed deploy line and the "shipping an update" block replaced by the script;
  one line on XPS dev (:8001).

## Verified
- Dry-run only (no real deploy): ASUS is at efe9ee6, origin/main 28f8c08 (11 files, no web/ or pyproject
  change → pull + restart). XPS main is ahead of origin (56f2b19 + this commit), so a real run refuses now.
- Remote `uv` resolves (0.13.7); `rsync` exists on the ASUS; live `/api/me` 200 from the XPS.
- pytest all pass, ruff clean, `npm --prefix web run build` and `lint` clean.

## Open / decisions for Arash
1. Push main (manager commits + 2f56361), then run the first real deploy: `tools/deploy_asus.sh --dry-run`,
   then `tools/deploy_asus.sh`. It restarts the live app (seconds of downtime).
2. Note: the ASUS `web/dist` predates the move; the first real deploy rebuilds only if web/ changed since
   efe9ee6. Pass `--web` once if in doubt whether the ASUS dist matches its commit.
3. Optional: tell infra (inf-manager) its plan §2.1 deploy line can point at `tools/deploy_asus.sh`.
