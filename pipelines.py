import os, json, requests
from pathlib import Path

class TelegramPipeline:
    def open_spider(self, spider):
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.token   = os.getenv("TELEGRAM_BOT_TOKEN")
        state        = Path("state.json")
        self.seen    = set(json.loads(state.read_text())) if state.exists() else set()
        
        # Sincronizăm seen set-ul cu cel din spider (dacă există)
        if hasattr(spider, 'seen'):
            # Unim ambele set-uri pentru a evita duplicatele
            self.seen.update(spider.seen)
            spider.seen.update(self.seen)

    def process_item(self, item, spider):
        # Verificare dublă: în pipeline și în spider
        if item["id"] not in self.seen:
            text = f"🆕 {item['title']} – {item['price'] or 'fără preț'}\n{item['link']}"
            try:
                requests.get(
                    f"https://api.telegram.org/bot{self.token}/sendMessage",
                    params={"chat_id": self.chat_id, "text": text},
                    timeout=10,
                )
                self.seen.add(item["id"])
                # Sincronizăm și în spider dacă există
                if hasattr(spider, 'seen'):
                    spider.seen.add(item["id"])
            except Exception as e:
                spider.logger.error(f"Failed to send Telegram message: {e}")
        return item

    def close_spider(self, spider):
        # Sincronizăm seen set-ul cu cel din spider înainte de salvare
        if hasattr(spider, 'seen'):
            self.seen.update(spider.seen)
        
        # Salvează ultimele 500 ID-uri
        Path("state.json").write_text(json.dumps(list(self.seen)[-500:]))
