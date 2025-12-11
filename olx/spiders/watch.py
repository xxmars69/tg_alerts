import os, hashlib, json, re, urllib.parse, scrapy
from pathlib import Path

SEARCH_URL = os.getenv("SEARCH_URL")
API_BASE   = "https://www.olx.ro/api/v1/offers/"

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
        # Încărcăm seen IDs pentru verificare rapidă
        state = Path("state.json")
        self.seen = set(json.loads(state.read_text())) if state.exists() else set()
        self.page_count = 0  # Contor pentru pagini
        self.max_pages = 1  # Maxim 1 pagină (optimizare)
        self.consecutive_seen = 0  # Contor pentru anunțuri consecutive deja văzute
        self.max_consecutive_seen = 10  # Oprește dacă 10 consecutive sunt deja văzute

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

        try:
            data = json.loads(response.text)
        except Exception as e:
            self.logger.error(f"Failed to parse OLX JSON: {e}")
            return

        items_in_page = 0
        new_items = 0
        
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
                    # Resetăm contorul când găsim unul nou
                    self.consecutive_seen = 0
                    new_items += 1
                    yield {"id": uid, "title": title, "price": price, "link": link}
                    # Adăugăm imediat în seen pentru a evita duplicatele în aceeași sesiune
                    self.seen.add(uid)

        self.logger.info(
            f"Pagina {self.page_count}: {items_in_page} anunțuri procesate, "
            f"{new_items} noi, {items_in_page - new_items} deja văzute"
        )

        # Verifică dacă trebuie să continuăm paginarea
        if self.consecutive_seen >= self.max_consecutive_seen:
            self.logger.info("Oprește paginarea: prea multe anunțuri consecutive deja văzute")
            return

        # Pagina următoare (doar dacă nu am atins limita)
        next_link = data.get("links", {}).get("next")
        if next_link and self.page_count < self.max_pages:
            yield scrapy.Request(
                next_link,
                callback=self.parse_api,
                meta={"page": self.page_count + 1}
            )
