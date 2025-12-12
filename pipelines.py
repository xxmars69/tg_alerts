import os, json, requests
from pathlib import Path
from datetime import datetime

class TelegramPipeline:
    def open_spider(self, spider):
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.token   = os.getenv("TELEGRAM_BOT_TOKEN")
        self.state_file = Path("state.json")
        
        # Obținem categoria din spider
        self.category = getattr(spider, 'category', 'unknown')
        
        # Încărcăm state.json ca dicționar cu categorii
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                # Format nou: dicționar cu categorii
                if isinstance(data, dict):
                    self.state_data = data
                # Compatibilitate: format vechi (listă simplă)
                elif isinstance(data, list):
                    # Convertim format vechi în format nou
                    self.state_data = {"unknown": data}
                else:
                    self.state_data = {}
            except Exception as e:
                spider.logger.warning(f"Eroare la încărcarea state.json: {e}")
                self.state_data = {}
        else:
            self.state_data = {}
        
        # Obținem lista pentru categoria curentă
        category_list = self.state_data.get(self.category, [])
        if isinstance(category_list, list) and len(category_list) > 0:
            if isinstance(category_list[0], str):
                # Format vechi: doar ID-uri, convertim
                category_list = [{"id": id, "timestamp": datetime.now().isoformat()} for id in category_list]
            # Păstrăm doar ultimele 10 (cele mai noi)
            category_list = sorted(category_list, key=lambda x: x.get("timestamp", ""), reverse=True)[:10]
        else:
            category_list = []
        
        self.state_data[self.category] = category_list
        
        # Set pentru verificare rapidă
        self.seen = {item["id"] for item in category_list if isinstance(item, dict) and "id" in item}
        
        # Sincronizăm seen set-ul cu cel din spider (dacă există)
        if hasattr(spider, 'seen'):
            # Unim ambele set-uri pentru a evita duplicatele
            self.seen.update(spider.seen)
            spider.seen.update(self.seen)

    def process_item(self, item, spider):
        # Obținem categoria din item sau spider
        category = item.get("category") or getattr(spider, 'category', 'unknown')
        
        # Obținem lista pentru categoria respectivă
        category_list = self.state_data.get(category, [])
        
        # Verificare dublă: în pipeline și în spider
        if item["id"] not in self.seen:
            text = f"🆕 [{category.upper()}] {item['title']} – {item['price'] or 'fără preț'}\n{item['link']}"
            try:
                # Retry logic pentru Telegram API
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = requests.get(
                            f"https://api.telegram.org/bot{self.token}/sendMessage",
                            params={"chat_id": self.chat_id, "text": text},
                            timeout=10,
                        )
                        response.raise_for_status()
                        spider.logger.info(f"✅ Notificare trimisă pentru anunț {item['id']} ({category}): {item['title'][:50]}...")
                        break  # Success, exit retry loop
                    except requests.exceptions.RequestException as e:
                        if attempt < max_retries - 1:
                            spider.logger.warning(f"⚠️ Tentativă {attempt + 1}/{max_retries} eșuată pentru Telegram: {e}. Reîncercare...")
                            import time
                            time.sleep(2 ** attempt)  # Exponential backoff
                        else:
                            raise  # Re-raise on last attempt
                
                # Adăugăm anunțul nou în listă cu timestamp
                timestamp = item.get("created_time") or datetime.now().isoformat()
                category_list.append({"id": item["id"], "timestamp": timestamp})
                self.seen.add(item["id"])
                
                # Păstrăm doar ultimele 10 (cele mai noi) pentru categoria respectivă
                category_list = sorted(category_list, key=lambda x: x.get("timestamp", ""), reverse=True)[:10]
                self.state_data[category] = category_list
                
                # Actualizăm set-ul cu noile ID-uri
                self.seen = {item["id"] for item in category_list if isinstance(item, dict) and "id" in item}
                
                # Sincronizăm și în spider dacă există
                if hasattr(spider, 'seen'):
                    spider.seen.add(item["id"])
            except Exception as e:
                spider.logger.error(f"❌ Failed to send Telegram message for {item['id']}: {e}")
        else:
            spider.logger.debug(f"⏭️ Anunț {item['id']} deja văzut în categoria {category}, ignorat")
        return item

    def close_spider(self, spider):
        # Sincronizăm seen set-ul cu cel din spider înainte de salvare
        category = getattr(spider, 'category', 'unknown')
        category_list = self.state_data.get(category, [])
        
        if hasattr(spider, 'seen'):
            # Adăugăm ID-urile din spider care nu sunt deja în listă
            for sid in spider.seen:
                if sid not in self.seen:
                    category_list.append({"id": sid, "timestamp": datetime.now().isoformat()})
        
        # Păstrăm doar ultimele 10 cele mai noi anunțuri pentru categoria respectivă (sortate după timestamp)
        category_list = sorted(category_list, key=lambda x: x.get("timestamp", ""), reverse=True)[:10]
        self.state_data[category] = category_list
        
        # Salvează state.json cu toate categoriile
        self.state_file.write_text(json.dumps(self.state_data, indent=2))
        spider.logger.info(f"💾 Salvat state.json pentru categoria {category}: {len(category_list)} anunțuri")
