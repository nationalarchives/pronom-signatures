#!/bin/bash
git status
if git status --porcelain | grep -q '^??'; then
  echo "Untracked files found. Staging and committing them."
  git config --global user.email 181243999+tna-da-bot@users.noreply.github.com
  git config --global user.name tna-da-bot
  git add -A
  git commit -m "Generate signature files"
  target_branch="${GITHUB_HEAD_REF:-${GITHUB_REF_NAME:-}}"
  if [[ -z "$target_branch" ]]; then
    echo "Unable to determine the branch to push to." >&2
    exit 1
  fi
  git push origin "HEAD:refs/heads/$target_branch"
else
  echo "No untracked files found. Nothing to commit."
fi
