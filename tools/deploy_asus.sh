#!/usr/bin/env bash
# Deploy what is pushed to origin/main to the live app on the ASUS (home server).
#
# Run on the XPS after `git push`. Code is edited on the XPS only; the ASUS clone runs what is pushed and is
# never edited by hand. The ASUS has no Node, so the web app is built here and copied over.
#
#   tools/deploy_asus.sh            deploy
#   tools/deploy_asus.sh --dry-run  print what it would do (reads the ASUS, changes nothing there)
#   tools/deploy_asus.sh --web      also rebuild and copy web/dist even if web/ did not change
#   tools/deploy_asus.sh --deps     also reinstall the Python dependencies even if pyproject.toml did not change
#
# Steps: refuse unless the XPS main is clean and equal to origin/main; on the ASUS `git pull --ff-only`;
# reinstall Python deps when pyproject.toml/uv.lock changed between the old and new ASUS HEAD; when web/
# changed, `npm --prefix web run build` here (at that same commit) and rsync web/dist over; restart the
# user unit; poll /api/me until 200, or fail with the last journal lines. No sudo, no secrets.
#
# Overrides (env): LINGUA_ASUS_HOST (asus-ubuntu), LINGUA_ASUS_DIR (dev/learn/lingua-agent, relative to the
# ASUS home), LINGUA_ASUS_URL (https://arashasus-ubuntu.tail58953c.ts.net), LINGUA_EXTRAS (api,voice,anthropic,openai),
# LINGUA_DEPLOY_TIMEOUT (seconds to wait for /api/me, 90).
set -euo pipefail

HOST="${LINGUA_ASUS_HOST:-asus-ubuntu}"
RDIR="${LINGUA_ASUS_DIR:-dev/learn/lingua-agent}"
URL="${LINGUA_ASUS_URL:-https://arashasus-ubuntu.tail58953c.ts.net}"
EXTRAS="${LINGUA_EXTRAS:-api,voice,anthropic,openai}"
TIMEOUT="${LINGUA_DEPLOY_TIMEOUT:-90}"
UNIT=lingua-agent

DRY=0 FORCE_WEB=0 FORCE_DEPS=0
for a in "$@"; do
  case "$a" in
    --dry-run|-n) DRY=1 ;;
    --web) FORCE_WEB=1 ;;
    --deps) FORCE_DEPS=1 ;;
    -h|--help) sed -n '2,21p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "deploy_asus: unknown option $a (see --help)" >&2; exit 2 ;;
  esac
done

say() { printf '\033[1m==>\033[0m %s\n' "$*"; }
die() { printf '\033[31mdeploy_asus: %s\033[0m\n' "$*" >&2; exit 1; }
# Run a step, or print it under --dry-run.
run() { if ((DRY)); then printf '    [dry-run] %s\n' "$*"; else "$@"; fi; }
# Remote shell in the ASUS repo dir. BatchMode: never prompt.
rsh() { ssh -o BatchMode=yes -o ConnectTimeout=10 "$HOST" "cd ~/$RDIR && $1"; }

cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"

# ---- 1. the XPS side must be exactly what is pushed ------------------------------------------------------
refuse=()
branch=$(git symbolic-ref --short -q HEAD || echo DETACHED)
[[ $branch == main ]] || refuse+=("XPS is on '$branch', not main")
[[ -z $(git status --porcelain --untracked-files=no) ]] || refuse+=("XPS tree has uncommitted changes")
[[ -z $(git status --porcelain -- web | grep '^??' || true) ]] || refuse+=("untracked files under web/ would go into the build")
say "fetching origin"
git fetch -q origin main
NEW=$(git rev-parse origin/main)
[[ $(git rev-parse HEAD) == "$NEW" ]] || refuse+=("XPS main ($(git rev-parse --short HEAD)) != origin/main ($(git rev-parse --short "$NEW")): push or pull first")
if ((${#refuse[@]})); then
  for r in "${refuse[@]}"; do echo "  refuse: $r" >&2; done
  ((DRY)) || die "not deploying"
  say "(dry-run continues against origin/main $(git rev-parse --short "$NEW") to show the plan)"
fi

# ---- 2. where the ASUS is now -----------------------------------------------------------------------------
say "reading the ASUS ($HOST:~/$RDIR)"
read -r OLD asus_branch asus_dirty has_dist < <(rsh 'printf "%s %s %s %s\n" "$(git rev-parse HEAD)" "$(git symbolic-ref --short -q HEAD || echo DETACHED)" "$(git status --porcelain --untracked-files=no | wc -l)" "$([ -f web/dist/index.html ] && echo yes || echo no)"') \
  || die "cannot read the ASUS repo over ssh ($HOST)"
[[ $asus_branch == main ]] || die "ASUS clone is on '$asus_branch', not main"
[[ $asus_dirty == 0 ]] || die "ASUS clone has local edits ($asus_dirty files); it must never be edited by hand. Look before deploying."
git cat-file -e "$OLD^{commit}" 2>/dev/null || die "ASUS HEAD $OLD is unknown here; fetch first"
git merge-base --is-ancestor "$OLD" "$NEW" || die "ASUS HEAD $(git rev-parse --short "$OLD") is not an ancestor of origin/main; a fast-forward is impossible"

echo "    ASUS $(git log -1 --format='%h %s' "$OLD")"
echo "    new  $(git log -1 --format='%h %s' "$NEW")"
changed=$(git diff --name-only "$OLD" "$NEW")
n_changed=$(grep -c . <<<"$changed" || true)
echo "    $n_changed files changed"

need_deps=$FORCE_DEPS need_web=$FORCE_WEB npm_ci=0
grep -qxE 'pyproject\.toml|uv\.lock' <<<"$changed" && need_deps=1
grep -q '^web/' <<<"$changed" && need_web=1
[[ $has_dist == yes ]] || need_web=1
grep -qxE 'web/package(-lock)?\.json' <<<"$changed" && npm_ci=1
[[ -d web/node_modules ]] || npm_ci=1

if [[ $OLD == "$NEW" ]] && ((!need_deps && !need_web)); then
  say "the ASUS is already at $(git rev-parse --short "$NEW"); nothing to deploy"
  exit 0
fi
echo "    pull: $([[ $OLD == "$NEW" ]] && echo no || echo yes)  deps: $((need_deps)) web: $((need_web))"

# ---- 3. build the web app here, before touching the ASUS ---------------------------------------------------
if ((need_web)); then
  say "building web/ at $(git rev-parse --short "$NEW") on the XPS"
  ((npm_ci)) && run npm --prefix web ci
  run npm --prefix web run build
fi

# ---- 4. update the ASUS -------------------------------------------------------------------------------------
if [[ $OLD != "$NEW" ]]; then
  say "ASUS: git pull --ff-only"
  run rsh 'git pull --ff-only -q origin main'
  if ((!DRY)); then
    got=$(rsh 'git rev-parse HEAD')
    [[ $got == "$NEW" ]] || die "ASUS pulled to $got, expected $NEW (was origin/main pushed meanwhile?); not restarting"
  fi
fi

if ((need_deps)); then
  uv='$(command -v uv || echo ~/.local/bin/uv)'
  if git cat-file -e "$NEW:uv.lock" 2>/dev/null; then
    flags=$(tr ',' '\n' <<<"$EXTRAS" | sed 's/^/--extra /' | tr '\n' ' ')
    say "ASUS: uv sync --locked ($EXTRAS)"
    run rsh "\"$uv\" sync --locked $flags"
  else
    # No lock in the repo: refresh the editable install with the same extras the venv has.
    say "ASUS: uv pip install -e .[$EXTRAS]"
    run rsh "\"$uv\" pip install -q --python .venv/bin/python -e '.[$EXTRAS]'"
  fi
fi

if ((need_web)); then
  ((DRY)) || [[ -f web/dist/index.html ]] || die "web/dist/index.html missing after the build"
  say "copying web/dist to the ASUS"
  run rsync -a --delete --stats web/dist/ "$HOST:$RDIR/web/dist/"
fi

# ---- 5. restart and check -----------------------------------------------------------------------------------
say "ASUS: systemctl --user restart $UNIT"
run ssh -o BatchMode=yes "$HOST" "systemctl --user restart $UNIT"

say "waiting for $URL/api/me (up to ${TIMEOUT}s)"
if ((DRY)); then
  echo "    [dry-run] poll curl $URL/api/me until 200"
  say "dry-run done; nothing changed on the ASUS"
  if ((${#refuse[@]})); then echo "deploy_asus: a real run would refuse (see above)" >&2; exit 1; fi
  exit 0
fi
deadline=$((SECONDS + TIMEOUT)) code=000
while ((SECONDS < deadline)); do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$URL/api/me" || true)
  [[ $code == 200 ]] && break
  sleep 2
done
if [[ $code != 200 ]]; then
  echo "deploy_asus: $URL/api/me answered $code after ${TIMEOUT}s; last journal lines:" >&2
  ssh -o BatchMode=yes "$HOST" "systemctl --user --no-pager status $UNIT | head -5; journalctl --user -u $UNIT -n 40 --no-pager" >&2 || true
  die "deploy of $(git rev-parse --short "$NEW") is NOT healthy"
fi
say "deployed $(git rev-parse --short "$NEW") to $HOST: /api/me 200"
