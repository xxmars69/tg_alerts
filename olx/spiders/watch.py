# olx/spiders/watch.py
import os
import re
import json
import urllib.parse
import scrapy

API_BASE = "https://www.olx.ro/api/v1/offers/"

def build_api_url(src: str, offset=0, limit=40) -> str:
    """
    Transformă un URL OLX de căutare într-un apel API JSON corect.
    Păstrează parametrii existenți și setează offset/limit.
    """
    parsed = urllib.parse.urlparse(src)
    params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)

    # Dacă keyword-ul e în path ( /oferte/q-aparat%20foto/ ), extragem și suprascriem în 'query'
    m = re.search(r"/q-([^/]+)/", parsed.path)
    if m:
        params["query"] = [urllib.parse.unquote_plus(m.group(1))]

    # compat: vechiul 'q' -> 'query'
    if "q" in params and "query" not in params:
        params["query"] = params.pop("q")

    # paginate
    params["offset"] = [str(offset)]
    params["limit"]  = [str(limit)]

    return f"{API_BASE}?{urllib.parse.urlencode(params, doseq=True)}"


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

    def start_requests(self):
        """
        Citește linkurile din noile secrete:
        - SEARCH_URL_SONY
        - SEARCH_URL_CAMERA_FOTO
        - SEARCH_URL_APARAT_FOTO
        (și opțional SEARCH_URL)
        Acceptă și listă separată prin virgulă în oricare dintre ele.
        """
        env_names = [
            "SEARCH_URL_SONY",
            "SEARCH_URL_CAMERA_FOTO",
            "SEARCH_URL_APARAT_FOTO",
            "SEARCH_URL",  # opțional, dacă îl mai folosești
        ]

        urls = []
        for name in env_names:
            raw = os.getenv(name)
            if not raw:
                continue
            parts = [u.strip() for u in raw.split(",") if u.strip()]
            urls.extend(parts)

        # dedupe păstrând ordinea
        seen = set()
        final_urls = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                final_urls.append(u)

        if not final_urls:
            self.logger.error(
                "Nu am găsit niciun link în variabilele: %s",
                ", ".join(env_names),
            )
            return

        for u in final_urls:
            api_url = build_api_url(u, offset=0, limit=40)
            yield scrapy.Request(
                api_url,
                callback=self.parse_api,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0",
                },
            )

    def parse_api(self, response):
        # Parse JSON în siguranță
        try:
            data = json.loads(response.text)
        except Exception as e:
            self.logger.error(f"Failed to parse OLX JSON: {e}")
            return

        # Extragem itemele
        items = data.get("data") or []
        for offer in items:
            oid = offer.get("id")
            uid = str(oid) if oid is not None else None
            title = (offer.get("title") or "").strip()

            link = offer.get("url")
            if isinstance(link, str) and link.startswith("/"):
                link = urllib.parse.urljoin("https://www.olx.ro", link)

            p = offer.get("price") or {}
            price_val = p.get("display_value") or p.get("value") or ""
            currency  = p.get("currency") or ""
            price = f"{price_val} {currency}".strip() if (price_val or currency) else None

            if uid and title and link:
                yield {"id": uid, "title": title, "price": price, "link": link}

        # Paginare: links.next poate fi dict/list/str
        next_link = (data.get("links") or {}).get("next")
        if isinstance(next_link, dict):
            next_link = next_link.get("href")
        elif isinstance(next_link, (list, tuple)) and next_link:
            next_link = next_link[0]

        if isinstance(next_link, str) and next_link:
            yield scrapy.Request(
                response.urljoin(next_link),
                callback=self.parse_api,
                headers=response.request.headers,
            )
