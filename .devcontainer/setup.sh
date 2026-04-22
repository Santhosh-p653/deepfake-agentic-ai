#!/bin/bash
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀  deepfake-agentic-ai  Codespace Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "📦 Installing system dependencies..."
apt-get update -qq && apt-get install -y libmagic1
# --- 1. Copy .env if it doesn't exist ---
if [ ! -f .env ]; then
  echo "📋 Creating .env from .env.example..."
  cp .env.example .env
  # Set dev defaults so docker compose works immediately
  sed -i 's/your_db/deepfake_dev/' .env
  sed -i 's/your_user/devuser/' .env
  sed -i 's/your_passsword/devpassword/' .env
  sed -i 's|postgresql+psycopg2://user:password@db:5432/dbname|postgresql+psycopg2://devuser:devpassword@db:5432/deepfake_dev|' .env
  echo "✅ .env ready"
fi

# --- 2. Install requirements for all services ---
for service in api agents ml; do
  if [ -f "$service/requirements.txt" ]; then
    echo "📦 Installing $service/requirements.txt..."
    pip install --quiet -r "$service/requirements.txt"
  fi
done

# --- 3. Spin up all services via Docker Compose ---
echo "🐳 Starting Docker Compose (api, agents, ml, db)..."
docker compose up -d --build

echo ""
echo "✅ All services are up!"
echo "   API     → http://localhost:8000"
echo "   Agents  → http://localhost:8123"
echo "   DB      → localhost:5432"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
