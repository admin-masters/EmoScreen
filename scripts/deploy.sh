#!/bin/bash
set -euo pipefail

DEPLOY_ROOT="${DEPLOY_ROOT:-/var/www/EmoScreen}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-Staging}"
DEPLOY_ENV="${DEPLOY_ENV:-staging}"
VENV_PATH="${VENV_PATH:-/var/www/venv}"
SERVICE_NAME="${SERVICE_NAME:-gunicorn-EmoScreen_new}"

if [ "${DEPLOY_ENV}" = "staging" ]; then
  DJANGO_DEBUG="${DJANGO_DEBUG:-true}"
  ALLOWED_HOSTS="${ALLOWED_HOSTS:-127.0.0.1,localhost,emo.stage.cpdinclinic.co.in}"
  CSRF_TRUSTED_ORIGINS="${CSRF_TRUSTED_ORIGINS:-https://emo.stage.cpdinclinic.co.in}"
  FORCE_HTTPS="${FORCE_HTTPS:-true}"
else
  DJANGO_DEBUG="${DJANGO_DEBUG:-false}"
  ALLOWED_HOSTS="${ALLOWED_HOSTS:-emo.cpdinclinic.co.in,www.emo.cpdinclinic.co.in}"
  CSRF_TRUSTED_ORIGINS="${CSRF_TRUSTED_ORIGINS:-https://emo.cpdinclinic.co.in,https://www.emo.cpdinclinic.co.in}"
  FORCE_HTTPS="${FORCE_HTTPS:-true}"
fi

echo "🚀 Starting EmoScreen ${DEPLOY_ENV} deployment"

# Always work from project root
cd "${DEPLOY_ROOT}"

echo "📥 Pulling latest ${DEPLOY_BRANCH} code"
git fetch origin "${DEPLOY_BRANCH}"
if git show-ref --verify --quiet "refs/heads/${DEPLOY_BRANCH}"; then
  git checkout "${DEPLOY_BRANCH}"
else
  git checkout -b "${DEPLOY_BRANCH}" "origin/${DEPLOY_BRANCH}"
fi
git pull --ff-only origin "${DEPLOY_BRANCH}"

echo "⚙️ Writing deployment environment"
cat > .deploy_env <<EOF
DEPLOY_ENV=${DEPLOY_ENV}
DJANGO_DEBUG=${DJANGO_DEBUG}
ALLOWED_HOSTS=${ALLOWED_HOSTS}
CSRF_TRUSTED_ORIGINS=${CSRF_TRUSTED_ORIGINS}
FORCE_HTTPS=${FORCE_HTTPS}
EOF

echo "🐍 Activating virtual environment"
source "${VENV_PATH}/bin/activate"

echo "📦 Installing dependencies"
pip install --upgrade pip
pip install -r requirements.txt

echo "🗄 Running migrations"
python manage.py migrate --noinput --fake-initial

if [ "${DEPLOY_ENV}" = "staging" ]; then
  if [ -f "emoscreen_config_schema.xlsx" ]; then
    echo "🌱 Seeding paid form configuration"
    python manage.py ingest_paid_emoscreen_config emoscreen_config_schema.xlsx
  else
    echo "⚠️ Paid form workbook missing; skipping paid config seed"
  fi
fi

echo "🎨 Collecting static files"
python manage.py collectstatic --noinput

# =====================================================
# 🔽 INGESTION COMMANDS CAN BE ADDED BELOW 🔽
# =====================================================
# Example:
# python manage.py ingest_data
# python scripts/custom_ingest.py
# =====================================================

echo "🔄 Restarting Gunicorn"
sudo systemctl restart "${SERVICE_NAME}"

echo "✅ ${DEPLOY_ENV} deployment finished successfully"
