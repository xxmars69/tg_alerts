# Soluție pentru Cron Exact la Fiecare 5 Minute

## Problema
GitHub Actions scheduled workflows nu rulează exact la timp - pot avea întârzieri de câteva minute sau mai mult.

## Soluții

### Opțiunea 1: Cron-Job.org (GRATUIT)
1. Mergi pe https://cron-job.org
2. Creează un cont gratuit
3. Adaugă un job nou:
   - **URL**: `https://api.github.com/repos/xxmars69/tg_alerts/actions/workflows/olx_alert.yml/dispatches`
   - **Method**: POST
   - **Headers**: 
     - `Authorization: token YOUR_GITHUB_TOKEN`
     - `Accept: application/vnd.github.v3+json`
   - **Body**: `{"ref":"main"}`
   - **Schedule**: `*/5 * * * *` (la fiecare 5 minute)

### Opțiunea 2: EasyCron (GRATUIT - limitat)
1. Mergi pe https://www.easycron.com
2. Creează un cont
3. Adaugă un cron job care face POST la GitHub API

### Opțiunea 3: GitHub Personal Access Token
Pentru a folosi servicii externe, ai nevoie de un GitHub Personal Access Token:
1. Mergi pe GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token (classic)
3. Bifează scope-ul `workflow`
4. Copiază token-ul

### Opțiunea 4: Păstrăm GitHub Actions dar acceptăm întârzierile
- Workflow-ul va rula aproximativ la fiecare 5 minute
- Poate avea întârzieri de 1-5 minute
- Este gratuit și nu necesită configurare externă

## Recomandare
Folosește **Cron-Job.org** (Opțiunea 1) - este gratuit, fiabil și rulează exact la timp.

