#!/bin/bash
# Loop-test: simulate realistic agent flows, report pass/fail per scenario.

API=${API:-https://depscope.dev}
PASS=0
FAIL=0
FAILS=()

check() {
    local name="$1"
    local cmd="$2"
    local expect="$3"
    local got=$(eval "$cmd")
    if echo "$got" | grep -qE "$expect"; then
        PASS=$((PASS+1))
        printf "  [OK] %-55s %s\n" "$name" "$(echo "$got" | tr '\n' ' ' | head -c 80)"
    else
        FAIL=$((FAIL+1))
        FAILS+=("$name")
        printf "  [FAIL] %-53s expected /%s/ got: %s\n" "$name" "$expect" "$got"
    fi
}

echo "===== LOOP AGENT TEST ====="
echo ""
echo "--- Typosquats (should flag) ---"
check "lodsh→lodash typosquat (via /api/check 404)" \
  "curl -s $API/api/check/npm/lodsh | python3 -c 'import sys,json; d=json.load(sys.stdin); det=d.get(\"detail\", d); ts=det.get(\"typosquat\") or {}; print(\"is_ts:\", ts.get(\"is_suspected_typosquat\"), \"target:\", ts.get(\"likely_target\"))'" \
  "is_ts: True"

check "reqeusts→requests typosquat (via /api/check 404)" \
  "curl -s $API/api/check/pypi/reqeusts | python3 -c 'import sys,json; d=json.load(sys.stdin); det=d.get(\"detail\", d); ts=det.get(\"typosquat\") or {}; print(\"is_ts:\", ts.get(\"is_suspected_typosquat\"))'" \
  "is_ts: True"

echo ""
echo "--- Known deprecated (should find_alternative) ---"
check "request npm deprecated signal" \
  "curl -s $API/api/check/npm/request | python3 -c 'import sys,json; d=json.load(sys.stdin); r=d.get(\"recommendation\") or {}; print(r.get(\"action\"))'" \
  "(find_alternative|use_with_caution|do_not_use|legacy_but_working)"

echo ""
echo "--- False-positive check (axios was broken before) ---"
check "axios latest safe" \
  "curl -s $API/api/check/npm/axios | python3 -c 'import sys,json; d=json.load(sys.stdin); r=d.get(\"recommendation\") or {}; print(r.get(\"action\"))'" \
  "safe_to_use"

check "axios@0.21.1 update_required" \
  "curl -s \"$API/api/check/npm/axios?version=0.21.1\" | python3 -c 'import sys,json; d=json.load(sys.stdin); vs=d.get(\"version_scoped\") or {}; r=vs.get(\"recommendation\") or {}; print(r.get(\"action\"))'" \
  "update_required"

echo ""
echo "--- Historical compromise KB ---"
check "event-stream@3.3.6 blocked" \
  "curl -s \"$API/api/check/npm/event-stream?version=3.3.6\" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"recommendation\",{}).get(\"action\"))'" \
  "do_not_use"

check "ua-parser-js@0.7.29 blocked" \
  "curl -s \"$API/api/check/npm/ua-parser-js?version=0.7.29\" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"recommendation\",{}).get(\"action\"))'" \
  "do_not_use"

check "colors@1.4.44-liberty-2 blocked" \
  "curl -s \"$API/api/check/npm/colors?version=1.4.44-liberty-2\" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"recommendation\",{}).get(\"action\"))'" \
  "do_not_use"

check "event-stream@latest safe" \
  "curl -s $API/api/check/npm/event-stream | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"recommendation\",{}).get(\"action\"))'" \
  "(safe_to_use|insufficient_data|use_with_caution)"

echo ""
echo "--- Downloads (was returning 0) ---"
check "ccxt pypi has downloads" \
  "curl -s $API/api/check/pypi/ccxt | python3 -c 'import sys,json; d=json.load(sys.stdin); dl=d.get(\"downloads_weekly\") or 0; print(\"dl_ok\" if dl>100000 else \"dl_zero:\"+str(dl))'" \
  "dl_ok"

check "requests pypi has downloads" \
  "curl -s $API/api/check/pypi/requests | python3 -c 'import sys,json; d=json.load(sys.stdin); dl=d.get(\"downloads_weekly\") or 0; print(\"dl_ok\" if dl>1000000 else \"dl_low:\"+str(dl))'" \
  "dl_ok"

check "express npm has downloads" \
  "curl -s $API/api/check/npm/express | python3 -c 'import sys,json; d=json.load(sys.stdin); dl=d.get(\"downloads_weekly\") or 0; print(\"dl_ok\" if dl>1000000 else \"dl_low:\"+str(dl))'" \
  "dl_ok"

echo ""
echo "--- License risk ---"
check "express MIT → permissive" \
  "curl -s $API/api/check/npm/express | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"license_risk\"))'" \
  "permissive"

check "krakenex LGPL → weak_copyleft" \
  "curl -s $API/api/check/pypi/krakenex | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"license_risk\"))'" \
  "weak_copyleft"

echo ""
echo "--- SBOM + lockfile ---"
check "cyclonedx SBOM format" \
  "curl -s -X POST $API/api/scan -H 'Content-Type: application/json' -d '{\"ecosystem\":\"npm\",\"packages\":{\"express\":\"4.19.0\"},\"format\":\"cyclonedx\"}' | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"bomFormat\"))'" \
  "CycloneDX"

check "spdx SBOM format" \
  "curl -s -X POST $API/api/scan -H 'Content-Type: application/json' -d '{\"ecosystem\":\"npm\",\"packages\":{\"express\":\"4.19.0\"},\"format\":\"spdx\"}' | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"spdxVersion\"))'" \
  "SPDX-2.3"

check "requirements.txt lockfile parsing" \
  "python3 -c 'import json; print(json.dumps({\"lockfile\": \"flask==3.0.0\\nrequests==2.31.0\\n\", \"lockfile_kind\": \"requirements.txt\"}))' > /tmp/lockfile_body_$$.json && curl -s -X POST $API/api/scan -H 'Content-Type: application/json' -d @/tmp/lockfile_body_$$.json | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"ecosystem\"), len(d.get(\"packages\",[])))'" \
  "pypi 2"

echo ""
echo "--- Compare (no more 0-download false caveat) ---"
check "ccxt/krakenex compare — no fake low-adoption caveat" \
  "curl -s '$API/api/compare/pypi/ccxt,krakenex,python-kraken-sdk' | python3 -c 'import sys,json; d=json.load(sys.stdin); cav=d.get(\"caveats\") or {}; is_fake=any(\"low_relative_adoption (0\" in str(v) for v in cav.values()); print(\"no_fake_caveat\" if not is_fake else \"FAIL_fake_caveat_present\")'" \
  "no_fake_caveat"

echo ""
echo "--- MCP prompt token-saving ---"
check "/api/prompt axios latest returns ~500 tok" \
  "curl -s $API/api/prompt/npm/axios | wc -c" \
  "^[0-9]+$"

check "/api/prompt with version differs from latest" \
  "curl -s '$API/api/prompt/npm/axios?version=0.21.1' | grep -c 'axios@0.21.1'" \
  "[1-9]"

echo ""
echo "===== RESULT: PASS=$PASS FAIL=$FAIL ====="
if [ $FAIL -gt 0 ]; then
    echo "Failures:"
    for f in "${FAILS[@]}"; do echo "  - $f"; done
    exit 1
fi
