import os, json, re, urllib.parse, scrapy
from pathlib import Path
from datetime import datetime, timedelta

SEARCH_URL = os.getenv("SEARCH_URL")
API_BASE   = "https://www.olx.ro/api/v1/offers/"

def get_category_from_url(url: str) -> str:
    """Extrage categoria din URL (canon, nikon, sony, aparat_foto, camera_foto)"""
    url_lower = url.lower()
    if "canon" in url_lower:
        return "canon"
    elif "nikon" in url_lower:
        return "nikon"
    elif "sony" in url_lower:
        return "sony"
    elif "aparat%20foto" in url_lower or "aparat-foto" in url_lower or "aparat foto" in url_lower:
        return "aparat_foto"
    elif "camera%20foto" in url_lower or "camera-foto" in url_lower or "camera foto" in url_lower:
        return "camera_foto"
    else:
        return "unknown"

def build_api_url(src: str, offset=0, limit=40) -> str:
    """Transformă un URL OLX de căutare într-un apel API JSON corect (query=…)."""
    parsed = urllib.parse.urlparse(src)
    params = urllib.parse.parse_qs(parsed.query)

    # Dacă keyword-ul e în path ( /q-ps%20vita/ ), extragem și suprascriem
    m = re.search(r"/q-([^/]+)/", parsed.path)
    if m:
        params["query"] = [urllib.parse.unquote_plus(m.group(1))]

    # API-ul nu recunoaște vechiul „q", doar „query"
    if "q" in params and "query" not in params:
        params["query"] = params.pop("q")

    # PĂSTRĂM min_id dacă există (pentru a reduce rezultatele la anunțuri noi)
    # min_id este deja în params dacă e în URL-ul original, nu-l ștergem

    # FORȚĂM sortarea pe "cele mai noi" (newest first)
    params["sort"] = ["created_at:desc"]
    if "order" in params:
        params.pop("order")
    if "search[order]" in params:
        params.pop("search[order]")

    # Paginare
    params["offset"] = [str(offset)]
    params["limit"]  = [str(limit)]

    # Construim URL final
    query = urllib.parse.urlencode({k: v[0] for k, v in params.items()})
    return f"{API_BASE}?{query}"

class WatchJsonSpider(scrapy.Spider):
    name = "watch"
    custom_settings = {
        "ITEM_PIPELINES": {"pipelines.TelegramPipeline": 300},
        "DOWNLOAD_DELAY": 1,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
        "HTTPERROR_ALLOWED_CODES": [429],  # Allow rate limit errors to be retried
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
            ),
            "Accept": "application/json",
        },
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Identifică categoria din SEARCH_URL
        self.category = get_category_from_url(SEARCH_URL or "")
        self.logger.info(f"🔍 Categoria identificată: {self.category}")
        
        # Încărcăm seen IDs pentru categoria respectivă
        state = Path("state.json")
        if state.exists():
            try:
                data = json.loads(state.read_text())
                # Format nou: dicționar cu categorii
                if isinstance(data, dict):
                    category_data = data.get(self.category, [])
                    if isinstance(category_data, list) and len(category_data) > 0:
                        if isinstance(category_data[0], str):
                            # Format vechi: doar ID-uri
                            self.seen = set(category_data)
                        else:
                            # Format nou: listă de dicționare cu ID și timestamp
                            self.seen = {item["id"] for item in category_data if isinstance(item, dict) and "id" in item}
                    else:
                        self.seen = set()
                # Compatibilitate: format vechi (listă simplă)
                elif isinstance(data, list):
                    if len(data) > 0 and isinstance(data[0], str):
                        self.seen = set(data)
                    else:
                        self.seen = {item["id"] for item in data if isinstance(item, dict) and "id" in item}
                else:
                    self.seen = set()
            except Exception as e:
                self.logger.warning(f"Eroare la încărcarea state.json: {e}")
                self.seen = set()
        else:
            self.seen = set()
        
        self.page_count = 0
        self.max_pages = 3
        self.consecutive_seen = 0
        self.max_consecutive_seen = 20
        
        self.min_time = datetime.now() - timedelta(minutes=10)

    def start_requests(self):
        # Resetăm contoarele la începutul fiecărei căutări
        self.page_count = 0
        self.consecutive_seen = 0
        yield scrapy.Request(
            build_api_url(SEARCH_URL, offset=0, limit=40),
            callback=self.parse_api,
            meta={"page": 1}
        )

    def parse_api(self, response):
        self.page_count += 1
        
        # Verifică dacă am depășit limita de pagini
        if self.page_count > self.max_pages:
            self.logger.info(f"Limită de {self.max_pages} pagină atinsă. Oprește paginarea.")
            return

        # Verifică status code
        if response.status != 200:
            self.logger.warning(f"Status code {response.status} pentru {response.url}")
            # Retry automat dacă e configurat
            return

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse OLX JSON: {e}. Response: {response.text[:200]}")
            return
        except Exception as e:
            self.logger.error(f"Unexpected error parsing response: {e}")
            return

        items_in_page = 0
        new_items = 0
        skipped_old = 0  # Contor pentru anunțuri prea vechi
        
        for offer in data.get("data", []):
            uid = str(offer.get("id"))
            title = offer.get("title", "").strip()
            link = offer.get("url")
            price = (
                offer["price"]["value"]["display"]
                if offer.get("price") and offer["price"].get("value")
                else None
            )
            
            if uid and title and link:
                items_in_page += 1
                
                offer_time = None
                date_fields = ["created_time", "created_at", "createdTime", "createdAt", "date", "published_at", "publishedAt", "last_refresh_time", "lastRefreshTime"]
                for date_field in date_fields:
                    value = offer.get(date_field)
                    if not value and isinstance(offer, dict):
                        for key in offer.keys():
                            if key.lower() == date_field.lower():
                                value = offer[key]
                                break
                    if value:
                        try:
                            if isinstance(value, (int, float)):
                                offer_time = datetime.fromtimestamp(value / 1000 if value > 1e10 else value)
                            elif isinstance(value, str):
                                for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"]:
                                    try:
                                        offer_time = datetime.strptime(value.split("+")[0].split("Z")[0], fmt)
                                        break
                                    except:
                                        continue
                            if offer_time:
                                break
                        except Exception as e:
                            self.logger.debug(f"Failed to parse date field {date_field}: {e}")
                            continue
                
                if not offer_time:
                    skipped_old += 1
                    self.logger.warning(f"Anunț {uid}: nu s-a putut determina data publicării, ignorat. Câmpuri disponibile: {list(offer.keys())[:10]}")
                    continue
                elif offer_time < self.min_time:
                    skipped_old += 1
                    age_minutes = (datetime.now() - offer_time).total_seconds() / 60
                    self.logger.debug(f"Anunț {uid} ignorat: prea vechi ({age_minutes:.1f} min, minim: {self.min_time.strftime('%H:%M:%S')})")
                    continue
                
                # Verifică dacă e deja văzut
                if uid in self.seen:
                    self.consecutive_seen += 1
                    self.logger.debug(f"Anunț {uid} deja văzut. Consecutive seen: {self.consecutive_seen}")
                    
                    # Dacă 10 consecutive sunt deja văzute, oprește
                    if self.consecutive_seen >= self.max_consecutive_seen:
                        self.logger.info(
                            f"Oprește paginarea: {self.consecutive_seen} anunțuri consecutive "
                            f"deja văzute (limită: {self.max_consecutive_seen})"
                        )
                        return
                else:
                    self.consecutive_seen = 0
                    new_items += 1
                    age_minutes = (datetime.now() - offer_time).total_seconds() / 60
                    self.logger.info(f"✅ Anunț nou {uid}: {title[:50]}... (vârstă: {age_minutes:.1f} min)")
                    yield {
                        "id": uid, 
                        "title": title, 
                        "price": price, 
                        "link": link, 
                        "created_time": offer_time.isoformat() if offer_time else datetime.now().isoformat(),
                        "category": self.category
                    }
                    self.seen.add(uid)

        self.logger.info(
            f"Pagina {self.page_count}: {items_in_page} anunțuri procesate, "
            f"{new_items} noi (din ultimele 10 min), {items_in_page - new_items - skipped_old} deja văzute, "
            f"{skipped_old} prea vechi (ignorate), timp minim: {self.min_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # Verifică dacă trebuie să continuăm paginarea
        if self.consecutive_seen >= self.max_consecutive_seen:
            self.logger.info("Oprește paginarea: prea multe anunțuri consecutive deja văzute")
            return

        # Pagina următoare (doar dacă nu am atins limita)
        next_link = data.get("links", {}).get("next")
        if next_link and self.page_count < self.max_pages:
            if isinstance(next_link, dict):
                next_url = next_link.get("href") or next_link.get("url") or next_link.get("link")
            else:
                next_url = next_link
            
            if next_url:
                yield scrapy.Request(
                    next_url,
                    callback=self.parse_api,
                    meta={"page": self.page_count + 1}
                )
