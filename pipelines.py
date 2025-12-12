import os, json, requests
from pathlib import Path
from datetime import datetime

class TelegramPipeline:
    def open_spider(self, spider):
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.token   = os.getenv("TELEGRAM_BOT_TOKEN")
        state        = Path("state.json")
        
        # Încărcăm state.json ca listă de dicționare cu ID și timestamp
        if state.exists():
            try:
                data = json.loads(state.read_text())
                # Compatibilitate: dacă e listă simplă de ID-uri, convertim
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], str):
                    # Format vechi: doar ID-uri
                    self.seen_list = [{"id": id, "timestamp": datetime.now().isoformat()} for id in data]
                else:
                    # Format nou: listă de dicționare
                    self.seen_list = data if isinstance(data, list) else []
            except:
                self.seen_list = []
        else:
            self.seen_list = []
        
        # Păstrăm doar ultimele 10 (cele mai noi)
        self.seen_list = sorted(self.seen_list, key=lambda x: x.get("timestamp", ""), reverse=True)[:10]
        
        # Set pentru verificare rapidă
        self.seen = {item["id"] for item in self.seen_list}
        
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
                # Adăugăm anunțul nou în listă cu timestamp
                timestamp = item.get("created_time") or datetime.now().isoformat()
                self.seen_list.append({"id": item["id"], "timestamp": timestamp})
                self.seen.add(item["id"])
                
                # Păstrăm doar ultimele 10 (cele mai noi)
                self.seen_list = sorted(self.seen_list, key=lambda x: x.get("timestamp", ""), reverse=True)[:10]
                # Actualizăm set-ul cu noile ID-uri
                self.seen = {item["id"] for item in self.seen_list}
                
                # Sincronizăm și în spider dacă există
                if hasattr(spider, 'seen'):
                    spider.seen.add(item["id"])
            except Exception as e:
                spider.logger.error(f"Failed to send Telegram message: {e}")
        return item

    def close_spider(self, spider):
        # Sincronizăm seen set-ul cu cel din spider înainte de salvare
        if hasattr(spider, 'seen'):
            # Adăugăm ID-urile din spider care nu sunt deja în listă
            for sid in spider.seen:
                if sid not in self.seen:
                    self.seen_list.append({"id": sid, "timestamp": datetime.now().isoformat()})
        
        # Păstrăm doar ultimele 10 cele mai noi anunțuri (sortate după timestamp)
        self.seen_list = sorted(self.seen_list, key=lambda x: x.get("timestamp", ""), reverse=True)[:10]
        
        # Salvează doar ultimele 10 anunțuri (cele mai noi)
        Path("state.json").write_text(json.dumps(self.seen_list, indent=2))
