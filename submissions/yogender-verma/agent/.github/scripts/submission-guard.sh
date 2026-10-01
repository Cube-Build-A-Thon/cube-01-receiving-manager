#!/usr/bin/env bash
# Fails a PR unless (a) the branch is named after the PR author and
# (b) every changed file is inside submissions/<author>/.
# Inputs (env): AUTHOR, HEAD_REF, BASE_SHA, HEAD_SHA, ADMIN
# CHANGED_FILES may be set instead of BASE_SHA/HEAD_SHA (used for local testing).
set -euo pipefail

lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }

if [ "$(lower "$AUTHOR")" = "$(lower "$ADMIN")" ]; then
  echo "PR opened by the organiser account (@$ADMIN): guard skipped."
  exit 0
fi

fail=0

if [ "$(lower "$HEAD_REF")" != "$(lower "$AUTHOR")" ]; then
  echo "::error::Branch name '$HEAD_REF' does not match your GitHub username '$AUTHOR'."
  echo "Rename it:  git branch -m $AUTHOR && git push -u origin $AUTHOR   (then open a new PR from it)"
  fail=1
fi

if [ -z "${CHANGED_FILES:-}" ]; then
  CHANGED_FILES="$(git diff --name-only "$BASE_SHA...$HEAD_SHA")"
fi

prefix="submissions/$(lower "$AUTHOR")/"
outside=""
while IFS= read -r f; do
  [ -z "$f" ] && continue
  case "$(lower "$f")" in
    "$prefix"*) ;;
    *) outside="$outside$f"$'\n' ;;
  esac
done <<< "$CHANGED_FILES"

if [ -n "$outside" ]; then
  echo "::error::This PR changes files outside submissions/$AUTHOR/. Only your own folder may be changed:"
  printf '%s' "$outside" | sed 's/^/  /'
  echo "Undo them with:  git checkout origin/main -- <file>   then commit and push."
  fail=1
fi

if [ "$fail" -eq 0 ]; then
  echo "OK: branch '$HEAD_REF' and all changed files are inside $prefix"
fi
exit "$fail"
