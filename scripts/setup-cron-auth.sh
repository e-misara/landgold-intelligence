#!/bin/bash
# Cron'un GitHub'a push edebilmesi için PAT setup

echo "🔐 GitHub Personal Access Token Setup"
echo ""
echo "1. github.com → Settings → Developer settings"
echo "2. Personal access tokens (classic) → Generate new"
echo "3. Note: tradia-deploy"
echo "4. Expiration: 1 year"
echo "5. Scope: repo (sadece bu)"
echo "6. Generate, kopyala"
echo ""
echo "Token'ı buraya yapıştır (görünmeyecek):"
read -s GITHUB_TOKEN
echo ""

if [[ ! "$GITHUB_TOKEN" =~ ^ghp_ ]]; then
    echo "❌ Geçersiz token (ghp_ ile başlamalı)"
    exit 1
fi

# Repo adını otomatik bul
REPO_URL=$(git remote get-url origin)
REPO_PATH=$(echo "$REPO_URL" | sed -E 's|.*github.com[:/](.+)\.git|\1|')

# Yeni URL token ile
NEW_URL="https://e-misara:${GITHUB_TOKEN}@github.com/${REPO_PATH}.git"

git remote set-url origin "$NEW_URL"

echo "✅ Remote güncellendi"
echo "✅ Cron artık push yapabilir"
echo ""
echo "Test:"
git remote -v | sed 's/ghp_[^@]*/***/'
