#!/bin/bash
set -e

echo "🚀 Starting EmoScreen deployment"

# Always work from project root
cd /var/www/EmoScreen

echo "📥 Pulling latest code"
git pull origin main

echo "🐍 Activating virtual environment"
source /var/www/venv/bin/activate

echo "📦 Installing dependencies"
pip install --upgrade pip
pip install -r requirements.txt

echo "🗄 Running migrations"
python manage.py migrate --noinput --fake-initial

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
sudo systemctl restart gunicorn-EmoScreen_new

echo "✅ Deployment finished successfully"
