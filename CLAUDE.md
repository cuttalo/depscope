---
name: DepScope Platform
description: depscope.dev — Package Intelligence for AI Agents. VM 140, FastAPI+Next.js 16+PostgreSQL 17. API free, 17 ecosistemi (npm/pypi/cargo/go/maven/nuget/rubygems+10 altri), 14,700+ pacchetti, 402 vulnerabilita, 12 MCP tools, 3 verticali (package health + error->fix + compat matrix). Save tokens, save energy, ship safer code.
type: project
originSessionId: 21209a7e-7e4e-46e5-aa87-f1f2b0a39c02
---
## DepScope — Package Intelligence for AI Agents

**Concetto**: Facciamo il lavoro sporco UNA volta (aggregare registry + vulnerability data), e serviamo il risultato a milioni di agenti AI in millisecondi. Il valore è nei dati accumulati.

**URL**: https://depscope.dev
**Azienda**: Cuttalo srl, Via Paritaro 81, 74023 Grottaglie (TA), P.IVA IT03242390734

---

### INFRASTRUTTURA

**VM 140** — web-depscope
- IP: 10.10.0.140
- CPU: 2 core, RAM: 4GB (NOTA: serve stop+start da Proxmox per applicare, reboot non basta)
- Disco: 15GB (5.7GB usati)
- OS: Debian 13

**Stack**:
- Backend: FastAPI (Python 3.13) su porta 8000
- Frontend: Next.js 16 su porta 3000
- DB: PostgreSQL 17 (user depscope/${DB_PASSWORD})
- Cache: Redis
- Reverse proxy: Nginx (locale) → HAProxy (Proxmox :80)
- Process manager: PM2 (depscope-api + depscope-web)
- Venv Python: /home/deploy/depscope/.venv/

**Routing**: Client → Cloudflare → HAProxy (:80) → VM 140 Nginx (:80) → FastAPI (:8000) o Next.js (:3000)

**Dominio**: depscope.dev (OVH, ordine #248666504, 10.49€/anno)
**Cloudflare Zone**: 664e55136e4ac133233903ca1165b0ad (SSL flexible)
**DNS**: A record depscope.dev → 91.134.4.25 (proxied)

---

### FILE STRUTTURA

```
/home/deploy/depscope/
├── api/                    # Backend FastAPI
│   ├── main.py            # App principale, tutti gli endpoint
│   ├── config.py          # Configurazione
│   ├── database.py        # Pool PostgreSQL (asyncpg)
│   ├── cache.py           # Redis cache + rate limiting
│   ├── registries.py      # Fetch da 17 registries (npm/pypi/cargo/go/maven/nuget/rubygems+10 altri) + OSV vulns
│   ├── health.py          # Calcolo health score algoritmico
│   ├── auth.py            # Magic link auth
│   └── payments.py        # Stripe (predisposto, non attivo)
├── config/                 # Credenziali (chmod 600)
│   ├── stripe.json        # Stripe test keys (Cuttalo srl)
│   └── fic.json           # Fatture in Cloud (Cuttalo srl)
├── scripts/
│   ├── preprocess.py      # Pre-cache top 250+ pacchetti (cron 6h)
│   ├── alerts.py          # Monitoring anomalie (cron 15min)
│   ├── daily_report.py    # Report email giornaliero (cron 8:00)
│   └── seed_popular.py    # Seed iniziale (vecchio, usa preprocess)
├── frontend/               # Next.js 16
│   ├── app/
│   │   ├── page.tsx       # Homepage con search
│   │   ├── layout.tsx     # Layout + JSON-LD + cookie banner
│   │   ├── admin/         # Dashboard admin (auth API key)
│   │   ├── api-docs/      # Documentazione API
│   │   ├── stats/         # Stats pubbliche (numeri nascosti sotto 10K)
│   │   ├── contact/       # Contatto + dati Cuttalo srl
│   │   ├── privacy/       # Privacy policy GDPR
│   │   ├── popular/       # Top pacchetti SSR
│   │   ├── ecosystems/    # Hub per ecosistema SSR
│   │   ├── compare/       # Compare packages SSR
│   │   ├── pkg/           # Pagine individuali pacchetto SSR (273+)
│   │   └── sitemap.ts     # Sitemap dinamica (292 URL)
│   └── public/
│       ├── robots.txt     # Permissivo per AI crawler
│       └── llms.txt       # AI agent discovery file
├── mcp-server/             # MCP Server (pubblicato su npm)
│   ├── index.js
│   ├── package.json
│   └── smithery.yaml
├── ecosystem.config.js     # PM2 config
└── run.py                  # Entry point API
```

---

### API ENDPOINTS (tutti free, no auth, 200 req/min)

| Endpoint | Metodo | Scopo |
|----------|--------|-------|
| `/api/check/{eco}/{pkg}` | GET | Check completo: health, vulns, recommendation |
| `/api/latest/{eco}/{pkg}` | GET | Solo versione latest (velocissimo) |
| `/api/exists/{eco}/{pkg}` | GET | Esiste sì/no |
| `/api/health/{eco}/{pkg}` | GET | Solo health score 0-100 |
| `/api/vulns/{eco}/{pkg}` | GET | Vulnerabilità (filtrate a latest version) |
| `/api/versions/{eco}/{pkg}` | GET | Lista versioni |
| `/api/compare/{eco}/{a},{b},{c}` | GET | Compara 2-10 pacchetti |
| `/api/scan` | POST | Audit intero progetto (max 100 pkg) |
| `/api/search/{eco}?q=...` | GET | Cerca pacchetti per keyword |
| `/api/alternatives/{eco}/{pkg}` | GET | Alternative a deprecati |
| `/api/now` | GET | Data/ora UTC corrente |
| `/api/prompt/{eco}/{pkg}` | GET | LLM-optimized plain text (~74% token reduction) |
| `/api/trending` | GET | Pacchetti trending pubblici |
| `/api/history/{eco}/{pkg}` | GET | Health history 90 giorni (Level 2) |
| `/api/tree/{eco}/{pkg}` | GET | Dependency tree con health (Level 2) |
| `/api/bundle/{eco}/{pkg}` | GET | Bundle size min+gzip (Level 2) |
| `/api/types/{eco}/{pkg}` | GET | TypeScript quality (Level 2) |
| `/api/licenses/{eco}/{pkg}` | GET | License audit (Level 2) |
| `/api/error?code=X` | GET | Error -> Fix DB lookup (Vertical 2) |
| `/api/error/resolve` | POST | Resolve stack trace -> fix verificato (Vertical 2) |
| `/api/compat?packages=...` | GET | Stack compatibility matrix (Vertical 3) |
| `/api/bugs/{eco}/{pkg}` | GET | Known bugs per versione, non-CVE (Vertical 4) |
| `/api/stats` | GET | Stats pubbliche (numeri nascosti sotto 10K) |
| `/api/sitemap-packages` | GET | Lista pacchetti per sitemap |
| `/api/admin/dashboard` | GET | Dashboard admin (auth required) |
| `/api/admin/stats` | GET | Stats complete admin (auth required) |
| `/.well-known/ai-plugin.json` | GET | ChatGPT plugin discovery |
| `/openapi-gpt.json` | GET | OpenAPI pulito per GPT Actions (8 endpoint) |
| `/badge/{eco}/{pkg}` | GET | Health score badge SVG (per README/docs) |
| `/badge/score/{eco}/{pkg}` | GET | Score-only badge SVG (compatto) |

**Ecosistemi** (17): npm, pypi, cargo, go, composer, maven, nuget, rubygems, pub, hex, swift, cocoapods, cpan, hackage, cran, conda, homebrew

---

### HEALTH SCORE (algoritmico, 0-100)

| Segnale | Max | Fonte |
|---------|-----|-------|
| Maintenance | 25 | Giorni dall'ultimo release |
| Security | 25 | CVE da OSV (filtrate a latest) |
| Popularity | 20 | Download settimanali |
| Maturity | 15 | Numero versioni totali |
| Community | 15 | Numero maintainer |

**Recommendation actions** (priorità: critical > deprecated > high > low_health):
- safe_to_use, update_required, use_with_caution, find_alternative, do_not_use

---

### CREDENZIALI & AUTH

**Database**: postgresql://depscope:REDACTED@localhost:5432/depscope
**Redis**: redis://localhost:6379/0
**Email**: depscope@cuttalo.com / REDACTED_SEE_MEMORY
**Admin API Key**: REDACTED_SEE_MEMORY
**Auth system**: LIVE — magic link login + API keys user-scoped (ds_live_xxx / ds_test_xxx) per higher limits e usage analytics. Pubblico resta free e no-auth.
**Admin Dashboard**: https://depscope.dev/admin
**npm Token**: REDACTED_SEE_MEMORY
**npm Username**: depscope (email: arch.vincenzo.rubino@gmail.com)
**Stripe**: test mode, config in /home/deploy/depscope/config/stripe.json
**FIC**: Cuttalo srl, config in /home/deploy/depscope/config/fic.json
**Roundcube**: depscope@cuttalo.com accessibile da posta.cuttalo.com (identity #18 di admin)

---

### CRON JOBS (crontab di deploy@10.10.0.140)

| Schedule | Script | Cosa fa |
|----------|--------|---------|
| Ogni 6h | preprocess.py | Pre-cache top 250+ pacchetti in Redis + PostgreSQL |
| Ogni 15min | alerts.py | Controlla API/DB/disk/RAM/PM2, email se anomalie |
| 6:00 UTC (8:00 Roma) | daily_report.py | Report giornaliero email con KPI |

**Alert email a**: vincenzo@cuttalo.com + arch.vincenzo.rubino@gmail.com
**Report email a**: stessi destinatari

---

### DISTRIBUZIONE & MARKETING

| Canale | URL/Stato |
|--------|-----------|
| Website | https://depscope.dev (292 URL indicizzabili) |
| GPT Store | "DepScope" — LIVE, chiama API reali |
| npm | https://www.npmjs.com/package/depscope-mcp |
| RapidAPI | Pubblicato |
| GitHub main | https://github.com/cuttalo/depscope |
| GitHub MCP | https://github.com/cuttalo/depscope |
| Show HN | Pubblicato |
| Dev.to | Articolo pubblicato |
| Reddit | u/Depscope (account nuovo, karma da accumulare) |
| PR awesome-mcp-servers | #4920 in attesa |
| PR public-apis | #5879 in attesa |
| GSC | Connesso, sitemap inviata |
| mcp.so / smithery.ai | Da submittere (repo GitHub pronto) |

---

### STRATEGIA

- **Tutto gratis** per accumulare dati e utenti
- Stats pubbliche nascoste sotto 10.000 chiamate (threshold in api/main.py e frontend/app/stats)
- Monetizzazione futura con Piano Plus quando c'è massa critica
- Target primario: agenti AI (Claude Code, Cursor, ChatGPT, Windsurf)
- Target secondario: dev che usano curl/script per verificare dipendenze
- Il valore è nel database di pacchetti + alternative + health score accumulato nel tempo

---

### NOTE OPERATIVE

- **PM2 startup**: configurato, ma dopo stop+start VM serve `pm2 start ecosystem.config.js`
- **RAM 4GB**: il template cloud-init non applica la RAM al reboot, serve `qm stop 140 && qm start 140`
- **Next.js standalone**: dopo ogni build copiare `.next/static` in `.next/standalone/.next/static` + `public/`
- **Nginx config**: /etc/nginx/sites-available/depscope (route per /api/, /badge/, /docs, /.well-known/, /openapi-gpt.json)
- **HAProxy config**: /etc/haproxy/haproxy.cfg (host_depscope → backend web-depscope → 10.10.0.140:80)
- **Redis flush**: `redis-cli FLUSHALL` per invalidare cache dopo modifiche al backend
- **Alternatives curate: tabella **alternatives** (177 pair curate: 156 real + 21 builtin su npm/pypi/cargo) — dict legacy in main.py conservato come fallback, non piu letto

**Why:** Il mercato degli agenti AI coding esplode. Chi fornisce "intelligence" sulle dipendenze come servizio gratuito accumula dati e posizione. Nessun competitor fa tutto insieme su 17 ecosistemi (package health + error->fix + compat matrix + 12 MCP tools). Posizionamento: save tokens, save energy, ship safer code.
**How to apply:** Sempre lavorare su VM 140 via SSH deploy@10.10.0.140. Backend in api/, frontend in frontend/. Test con curl dopo ogni modifica.
