#!/usr/bin/env bash
# Быстрая проверка: отвечают ли сервисы и сколько загрузил Loader.
for p in 8000 8001 8002 8003 8004 8005; do
  printf 'localhost:%s/health -> ' "$p"
  curl -s -m 3 "http://localhost:$p/health" || printf 'DOWN'
  echo
done
echo "loader status:"; curl -s -m 3 http://localhost:8003/status; echo
