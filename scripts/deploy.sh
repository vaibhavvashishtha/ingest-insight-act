#!/usr/bin/env bash
# Run on the Hostinger VPS to deploy / update the demo.
# Pulls latest main, rebuilds changed images, restarts the stack.
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env.production ]]; then
  echo "✗ .env.production not found. Copy .env.production.example and fill it in."
  exit 1
fi

echo "==> Pulling latest"
git fetch origin
git reset --hard origin/main

echo "==> Building images (incremental)"
docker compose -f docker-compose.prod.yml --env-file .env.production build

echo "==> Applying any new migrations"
# Postgres auto-runs /docker-entrypoint-initdb.d on first init only — for updates,
# manually run new migrations:
for migration in migrations/*.sql; do
  filename=$(basename "$migration")
  # Skip the initial schema (already loaded on volume init)
  [[ "$filename" == "001_initial_schema.sql" ]] && continue
  echo "  applying $filename"
  docker compose -f docker-compose.prod.yml --env-file .env.production exec -T db \
    psql -U "$(grep ^POSTGRES_USER .env.production | cut -d= -f2)" \
         -d "$(grep ^POSTGRES_DB .env.production | cut -d= -f2)" \
    < "$migration"
done

echo "==> Restarting services"
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --remove-orphans

echo "==> Status"
docker compose -f docker-compose.prod.yml ps

echo ""
echo "✓ Deploy complete. Check logs with:"
echo "    docker compose -f docker-compose.prod.yml logs -f"
