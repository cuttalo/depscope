#!/bin/bash
# Warm Cloudflare edge cache for the top N most-queried packages in the
# last 7 days. First request after cache-miss pays ~800ms; after this
# cron, top packages stay HIT (~20-50ms) for the next 6h.
#
# Warms both gzip and brotli variants (CF caches per Accept-Encoding).
#
# Rate-limited: ~0.5s between packages (safe under CF no-challenge threshold).
# Strategy: hit each of /api/check, /api/prompt, /api/latest for each
# top pkg × {gzip, br} so all three most-used endpoints stay warm
# for both encoding variants.
#
# Scheduled: cron daily 04:30 UTC (after top-200 selection is stable
# from today's usage).

set -euo pipefail

LOG=/var/log/depscope/cache_warmer.log

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

log "=== cache warmer START ==="

# Top 200 pkg queried in the last 7d, excluding bots and hallucinated 404s.
# Query returns ecosystem|name pairs.
PKG_LIST=$(sudo -u postgres psql depscope -tAc "
  SELECT ecosystem || '|' || package_name
  FROM api_usage
  WHERE created_at > NOW() - INTERVAL '7 days'
    AND status_code = 200
    AND agent_client NOT IN ('crawler', 'unknown')
    AND ecosystem IS NOT NULL AND ecosystem <> ''
    AND package_name IS NOT NULL AND package_name <> ''
  GROUP BY ecosystem, package_name
  ORDER BY COUNT(*) DESC
  LIMIT 200
")

COUNT=$(echo "$PKG_LIST" | grep -c '|' || true)
log "warming $COUNT packages on /api/check + /api/prompt + /api/latest × {gzip, br}"

SUCC=0
MISS=0
while IFS='|' read -r eco pkg; do
  [ -z "$eco" ] && continue
  for ep in check prompt latest; do
    # Warm both gzip and brotli variants — CF caches per Accept-Encoding.
    for enc in "gzip" "br"; do
      code=$(curl -s -o /dev/null -w '%{http_code}' \
             --max-time 10 \
             -H "Accept-Encoding: $enc" \
             -H "User-Agent: DepScope-CacheWarmer/1.0" \
             "https://depscope.dev/api/$ep/$eco/$pkg" || echo "000")
      if [ "$code" = "200" ]; then SUCC=$((SUCC+1)); else MISS=$((MISS+1)); fi
    done
  done
  sleep 0.5
done <<< "$PKG_LIST"

log "warmed: succ=$SUCC miss=$MISS (total_requests=$((SUCC+MISS)))"
log "=== cache warmer DONE ==="
