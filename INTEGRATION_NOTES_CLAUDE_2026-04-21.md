# MCP findings — integration notes

Branch: `fix/mcp-findings-20260421`
Author: Claude (stress test session 2026-04-21)

Scopo di questo documento: spiegare a chi farà il merge/cabling successivo quali
moduli standalone sono stati aggiunti, perché, e dove vanno agganciati in
`api/main.py`. I file modificati dall'altra sessione in parallelo NON sono
stati toccati per evitare conflitti.

## 1. `api/health.py` — fix scoring maturity (già integrato)

**Problema osservato nei test MCP**: pacchetti ancient & stabili (DBI CPAN dal
1994, wget Homebrew) ricevevano `maturity=0` perché le registry `cpan` e
`homebrew` espongono una sola versione. Risultato: health 32/100 "critical" su
DBI. Falso segnale.

**Fix**: `calculate_health_score` ora considera:
1. `version_count` (come prima)
2. uplift via `first_published` (≥10 anni → ≥15 punti)
3. floor via `last_published` per registry con storia limitata (version_count ≤ 1
   e nessun `first_published`)

Nessun cambio d'interfaccia. Test suggerito:
```bash
curl -s https://depscope.dev/api/check/cpan/DBI | jq '.health'
curl -s https://depscope.dev/api/check/homebrew/wget | jq '.health'
```

## 2. `api/historical_compromises.py` + `data/historical_compromises.json`

**Problema osservato**: `/check_malicious` restituisce `is_malicious: false` per
`colors`, `event-stream`, `ua-parser-js`, ecc. perché la release corrente è
pulita, ma questi pacchetti hanno un *reputational incident* documentato.
OSV non copre il caso perché la vuln è già risolta.

**API nuovo**:
```python
from api.historical_compromises import lookup as lookup_historical
hist = lookup_historical(ecosystem, package)   # -> dict | None
```

**Cabling consigliato** in `api/main.py`, endpoint `/check_malicious` (attualmente
~line 1376 nel branch parallelo):

```python
response = {"package": package, "ecosystem": ecosystem, "is_malicious": osv_hit}
hist = lookup_historical(ecosystem, package)
if hist:
    response["historical_compromise"] = hist
    # Non alterare is_malicious: l'OSV è la verità attuale.
return response
```

Stesso trattamento per `/ai_brief`: aggiungere una riga
`HISTORY: previously compromised <date> — <summary>` quando `hist` presente.

## 3. `api/stdlib_modules.py` + `data/stdlib_modules.json`

**Problema osservato**: `/ai_brief pypi/urllib2` → `HTTP 404 "Package 'urllib2'
not found"`. Il modulo è stdlib di Python 2, l'agente probabilmente stava
migrando codice legacy. Il 404 non insegna nulla e brucia un round-trip.

**API nuovo**:
```python
from api.stdlib_modules import lookup as lookup_stdlib
hint = lookup_stdlib(ecosystem, package)   # -> dict | None
# hint = {"kind": "python2_stdlib", "replacement": "...", "note": "..."}
```

**Cabling consigliato** all'inizio di `/check_package`, `/package_exists`,
`/ai_brief`, `/check/*`:

```python
hint = lookup_stdlib(ecosystem, package)
if hint:
    return {
        "package": package,
        "ecosystem": ecosystem,
        "exists": False,
        "is_stdlib": True,
        "hint": hint,
        "recommendation": {
            "action": "no_install_needed",
            "summary": f"{package} is a {hint['kind']} — {hint['replacement']}"
        }
    }
```

Questo trasforma un 404 in una risposta educativa (token-saving + anti-hallucination,
due dei tre pilastri).

## 4. Bug NON fissati in questa sessione (richiedono main.py)

| # | Bug | Nota |
|---|-----|------|
| 4a | `scan_project` ritorna `not_found` per `chart.js` e `tsx` | parser name npm non gestisce nomi con `.` o ≤ 3 lettere? Indagare in `api/main.py` `/api/scan`. |
| 4b | `get_scorecard` per `express` → `no repo linked` | metadata npm → GitHub resolver su `expressjs/express` non agganciato. Fix in `api/registries.py` npm metadata. |
| 4c | `swift/Alamofire latest_version=""` | parser Swift Package Manager tag. `api/registries.py` → fetch_swift. |
| 4d | `maven/log4j-core downloads_weekly=0` | Maven non espone download. Deve essere `None` non `0`. `api/registries.py` → fetch_maven. |
| 4e | `conda/pandas` 404 | conda-forge fallback rotto. `api/registries.py`. |

Propongo di farli in una sessione successiva, dopo che il branch parallelo è
mergiato in main.
