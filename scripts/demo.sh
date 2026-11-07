#!/usr/bin/env bash
# Единая точка входа сценария проверки. Только публичные API наших сервисов (через Gateway).
# Печатает каждый вызов и ответ, итоги пишет в demo-result.json.
set -euo pipefail
GW=${GW:-http://localhost:8000}
LOADER=${LOADER:-http://localhost:8003}
TOKEN=${GATEWAY_TOKEN:-change-me}

call() { echo ">>> $*"; curl -sS -H "Authorization: Bearer $TOKEN" "$@"; echo; }

wait_initial_load() {   # ждём окончания первичной загрузки (до ~15 минут)
  for _ in $(seq 1 180); do
    curl -s "$LOADER/status" | grep -q '"initial_done":true' && return 0
    sleep 5
  done
  echo "первичная загрузка не закончилась" >&2; return 1
}

wait_initial_load
call "$LOADER/status"      # ожидаем: 1000 компаний, 73 группы

# TODO по шагам из задания:
# 1. счётчики: 1000 компаний, 73 группы, 451 isBankClient
# 2. инкремент -> число новых версий SCD2
# 3. история компании из scd2_demo
# 4. карточка дважды + неизвестный ИНН: call "$GW/v1/companies/<inn>"  (404 COMPANY_NOT_FOUND)
# 5. группа: call "$GW/v1/companies/<inn>/group?onlyBankClients=true" и без фильтра
# 6. скоринг трёх ИНН: call "$GW/v1/companies/<inn>/scoring"
echo '{}' > demo-result.json
