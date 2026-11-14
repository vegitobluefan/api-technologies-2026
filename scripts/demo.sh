#!/usr/bin/env bash
# Единая точка входа сценария проверки. Только публичные API наших сервисов (Gateway, /status, /sync).
# Печатает каждый вызов и ответ, итоги пишет в demo-result.json.
#
#   ./scripts/demo.sh
#   MOCK_SCENARIO=unavailable ./scripts/demo.sh
#   DEMO_HISTORY_INN=7700000001 DEMO_SCORING_INNS="7700000001 7700000002 7700000003" ./scripts/demo.sh
set -euo pipefail
GW=${GW:-http://localhost:8000}
LOADER=${LOADER:-http://localhost:8003}
ENRICH=${ENRICH:-http://localhost:8001}
TOKEN=${GATEWAY_TOKEN:-change-me}
PY=$(command -v python3 || command -v python)   # JSON разбираем питоном, jq не нужен
OUT=demo-result.json
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

call() { echo ">>> GET $1" >&2; curl -sS -H "Authorization: Bearer $TOKEN" "$1" | tee /dev/stderr; echo >&2; }
# jget FILE ВЫРАЖЕНИЕ: достать поле из JSON, например: jget a.json 'd["companies"]'
jget() { "$PY" -c "import json,sys; d=json.load(open(sys.argv[1])); v=$2; print(json.dumps(v) if isinstance(v,(dict,list)) else ('' if v is None else v))" "$1"; }

wait_initial_load() {   # ждём окончания первичной загрузки (до ~15 минут)
  for _ in $(seq 1 180); do
    curl -s "$LOADER/status" | grep -Eq '"initial_done": ?true' && return 0
    sleep 5
  done
  echo "первичная загрузка не закончилась" >&2; return 1
}

echo "=== 1. Первичная загрузка и счётчики"
wait_initial_load
curl -sS "$LOADER/status" > "$TMP/loader.json";  cat "$TMP/loader.json"; echo
curl -sS "$ENRICH/status" > "$TMP/enrich.json" || echo '{}' > "$TMP/enrich.json"; cat "$TMP/enrich.json"; echo

echo "=== 2. Инкремент: POST /sync"
curl -sS -X POST "$LOADER/sync" > "$TMP/sync.json"; cat "$TMP/sync.json"; echo
sleep 3   # даём Enrichment заметить новый last_sync_at
curl -sS "$LOADER/status" > "$TMP/loader2.json"

echo "=== 3. История компании"
HISTORY_INN=${DEMO_HISTORY_INN:-$(jget "$TMP/loader2.json" '(d.get("changed_inns") or [None])[0]')}
if [ -n "$HISTORY_INN" ]; then
  call "$ENRICH/v1/internal/companies/$HISTORY_INN/history" > "$TMP/history.json" || echo 'null' > "$TMP/history.json"
else
  echo "нет компаний с изменениями, историю не показываем"; echo 'null' > "$TMP/history.json"
fi

echo "=== 4. Карточка компании (шаг Павла)"
# TODO Павел: два запроса подряд (второй X-Cache: HIT) и неизвестный ИНН -> 404 COMPANY_NOT_FOUND

echo "=== 5. Группа компаний (шаг Павла)"
# TODO Павел: ?onlyBankClients=true и без фильтра

echo "=== 6. Скоринг трёх ИНН (шаг Фёдора)"
SCORING_INNS=${DEMO_SCORING_INNS:-$(jget "$TMP/loader2.json" '" ".join((d.get("changed_inns") or [])[:3])')}
echo '{}' > "$TMP/scores.json"
for inn in $SCORING_INNS; do
  call "$GW/v1/companies/$inn/scoring" > "$TMP/score_$inn.json" || true
  "$PY" - "$TMP/scores.json" "$TMP/score_$inn.json" "$inn" <<'EOF'
import json, sys
scores = json.load(open(sys.argv[1]))
try:
    body = json.load(open(sys.argv[2]))
except ValueError:
    body = {"code": "NO_RESPONSE"}
scores[sys.argv[3]] = body.get("probability", body.get("code"))
json.dump(scores, open(sys.argv[1], "w"))
EOF
done

echo "=== Итог -> $OUT"
"$PY" - "$TMP" "$OUT" "$HISTORY_INN" <<'EOF'
import json, sys
tmp, out, history_inn = sys.argv[1], sys.argv[2], sys.argv[3]
load = lambda name: json.load(open(f"{tmp}/{name}"))
loader, loader2, enrich, sync = load("loader.json"), load("loader2.json"), load("enrich.json"), load("sync.json")

def first(d, *names):            # имена полей /status у Enrichment ещё могут поменяться
    return next((d[n] for n in names if n in d), None)

result = {
    "companies": loader2.get("companies"),
    "groups": loader2.get("groups"),
    "bankClients": first(enrich, "bank_clients", "bankClients", "is_bank_client"),
    "snapshotCompanies": first(enrich, "companies", "snapshot_companies"),
    "initialVersions": loader2.get("initial_versions"),
    "versions": loader2.get("versions"),
    "newVersionsAfterIncrement": (loader2.get("versions") or 0) - (loader2.get("initial_versions") or 0),
    "syncCreated": sync.get("created"),
    "initialLoadedAt": loader2.get("initial_loaded_at"),
    "initialLoadSeconds": loader2.get("initial_duration_sec"),
    "lastSyncAt": loader2.get("last_sync_at"),
    "history": {"inn": history_inn or None, "versions": load("history.json")},
    "scores": load("scores.json"),
}
json.dump(result, open(out, "w"), ensure_ascii=False, indent=2)
print(json.dumps(result, ensure_ascii=False, indent=2))
EOF
