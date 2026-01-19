#!/bin/bash
git status
if git status --porcelain | grep -q '^??'; then
  echo "Untracked files found. Staging and committing them."
  git config --global user.email 181243999+tna-da-bot@users.noreply.github.com
  git config --global user.name tna-da-bot
  git add -A
  git commit -m "Generate signature files"
  git push origin HEAD:$GITHUB_HEAD_REF
else
  echo "No untracked files found. Nothing to commit."
fi
