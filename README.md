# olx-telegram-alert

Bot automat care monitorizează anunțuri OLX și trimite notificări prin Telegram când apar anunțuri noi.

## 🚀 Caracteristici

- ✅ Monitorizează 5 căutări OLX simultan (Canon, Nikon, Sony, Aparat Foto, Camera Foto)
- ✅ Trimite notificări Telegram pentru anunțuri noi
- ✅ Evită duplicate folosind istoric (`state.json`)
- ✅ Rulează automat prin GitHub Actions (la fiecare 5 minute)
- ✅ Suportă paginare automată a rezultatelor OLX

## 📋 Cerințe

- Python 3.12+
- Cont Telegram cu Bot Token
- Chat ID Telegram unde să primești notificările

## 🔧 Instalare

1. **Clonează repository-ul:**
   ```bash
   git clone https://github.com/xxmars69/tg_alerts.git
   cd tg_alerts
   ```

2. **Instalează dependențele:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurează variabilele de mediu:**
   
   Creează un fișier `.env` în root-ul proiectului:
   ```env
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   TELEGRAM_CHAT_ID=your_telegram_chat_id_here
   
   SEARCH_URL_CANON=https://www.olx.ro/oferte/q-canon/...
   SEARCH_URL_NIKON=https://www.olx.ro/oferte/q-nikon/...
   SEARCH_URL_SONY=https://www.olx.ro/oferte/q-sony/...
   SEARCH_URL_APARAT_FOTO=https://www.olx.ro/oferte/q-aparat%20foto/...
   SEARCH_URL_CAMERA_FOTO=https://www.olx.ro/oferte/q-camera%20foto/...
   ```

## 🔍 Cum să obții URL-uri de căutare OLX

1. Mergi pe [olx.ro](https://www.olx.ro)
2. Fă o căutare pentru produsul dorit (ex: "Canon camera")
3. Aplică filtrele necesare (preț, locație, etc.)
4. Copiază URL-ul complet din bara de adrese
5. Adaugă URL-ul în fișierul `.env` la variabila corespunzătoare

**Exemplu:**
```
SEARCH_URL_CANON=https://www.olx.ro/oferte/q-canon/?min_id=297001087&reason=observed_search&search%5Border%5D=created_at%3Adesc
```

## 🏃 Rulare locală

### Windows (PowerShell):
```powershell
$env:TELEGRAM_BOT_TOKEN="your_token"
$env:TELEGRAM_CHAT_ID="your_chat_id"
$env:SEARCH_URL_CANON="https://www.olx.ro/oferte/q-canon/..."
scrapy crawl watch
```

### Cu fișier .env:
Instalează `python-dotenv`:
```bash
pip install python-dotenv
```

Apoi rulează:
```bash
scrapy crawl watch
```

## 📝 Variabile de mediu disponibile

| Variabilă | Descriere | Exemplu |
|-----------|-----------|---------|
| `TELEGRAM_BOT_TOKEN` | Token-ul botului Telegram | `123456789:ABCdef...` |
| `TELEGRAM_CHAT_ID` | ID-ul chat-ului Telegram | `123456789` |
| `SEARCH_URL_CANON` | URL pentru produse Canon | `https://www.olx.ro/oferte/q-canon/...` |
| `SEARCH_URL_NIKON` | URL pentru produse Nikon | `https://www.olx.ro/oferte/q-nikon/...` |
| `SEARCH_URL_SONY` | URL pentru produse Sony | `https://www.olx.ro/oferte/q-sony/...` |
| `SEARCH_URL_APARAT_FOTO` | URL pentru aparate foto | `https://www.olx.ro/oferte/q-aparat%20foto/...` |
| `SEARCH_URL_CAMERA_FOTO` | URL pentru camere foto | `https://www.olx.ro/oferte/q-camera%20foto/...` |

## 🤖 GitHub Actions

Proiectul rulează automat prin GitHub Actions la fiecare 5 minute. Workflow-ul este configurat în `.github/workflows/olx_alert.yml`.

Pentru a configura secrets pe GitHub:
1. Mergi la **Settings** → **Secrets and variables** → **Actions**
2. Adaugă toate variabilele de mediu necesare ca secrets:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `SEARCH_URL_CANON`
   - `SEARCH_URL_NIKON`
   - `SEARCH_URL_SONY`
   - `SEARCH_URL_APARAT_FOTO`
   - `SEARCH_URL_CAMERA_FOTO`

## 📁 Structură proiect

```
tg_alerts/
├── olx/
│   ├── spiders/
│   │   └── watch.py          # Spider-ul principal
│   ├── settings.py           # Configurări Scrapy
│   └── __init__.py
├── pipelines.py              # Pipeline pentru Telegram
├── requirements.txt          # Dependențe Python
├── scrapy.cfg                # Configurare Scrapy
├── .gitignore                # Fișiere ignorate de Git
└── README.md                 # Acest fișier
```

## 🔒 Securitate

- ❌ **NU** comita fișierul `.env` în Git (e deja în `.gitignore`)
- ✅ Folosește GitHub Secrets pentru variabilele sensibile
- ✅ Păstrează token-ul Telegram în siguranță

## 📊 Fișierul state.json

Botul păstrează un fișier `state.json` cu ID-urile anunțurilor deja văzute pentru a evita notificările duplicate. Ultimele 500 de ID-uri sunt păstrate.

## 🐛 Depanare

**Problema:** Nu primesc notificări Telegram
- Verifică că `TELEGRAM_BOT_TOKEN` și `TELEGRAM_CHAT_ID` sunt corecte
- Testează token-ul folosind: `https://api.telegram.org/bot<TOKEN>/getMe`

**Problema:** Nu găsește anunțuri
- Verifică că URL-urile de căutare sunt corecte și accesibile
- Verifică log-urile pentru erori: `scrapy crawl watch -s LOG_LEVEL=DEBUG`

**Problema:** Primesc notificări duplicate
- Șterge `state.json` pentru a reseta istoricul (va retrimite toate anunțurile)

## 📄 Licență

Acest proiect este open source.
