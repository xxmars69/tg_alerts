import os, json, requests
from pathlib import Path
from datetime import datetime

class TelegramPipeline:
    def open_spider(self, spider):
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.token   = os.getenv("TELEGRAM_BOT_TOKEN")
        self.state_file = Path("state.json")
        
        self.category = getattr(spider, 'category', 'unknown')
        
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                if isinstance(data, dict):
                    self.state_data = data
                elif isinstance(data, list):
                    self.state_data = {"unknown": data}
                else:
                    self.state_data = {}
            except Exception as e:
                spider.logger.warning(f"Eroare la încărcarea state.json: {e}")
                self.state_data = {}
        else:
            self.state_data = {}
        
        category_list = self.state_data.get(self.category, [])
        if isinstance(category_list, list) and len(category_list) > 0:
            if isinstance(category_list[0], str):
                category_list = [{"id": id, "timestamp": datetime.now().isoformat()} for id in category_list]
            category_list = sorted(category_list, key=lambda x: x.get("timestamp", ""), reverse=True)[:100]
        else:
            category_list = []
        
        self.state_data[self.category] = category_list
        
        self.seen = {item["id"] for item in category_list if isinstance(item, dict) and "id" in item}
        
        if hasattr(spider, 'seen'):
            self.seen.update(spider.seen)
            spider.seen.update(self.seen)

    def process_item(self, item, spider):
        category = item.get("category") or getattr(spider, 'category', 'unknown')
        
        category_list = self.state_data.get(category, [])
        
        if item["id"] not in self.seen:
            text = f"🆕 [{category.upper()}] {item['title']} – {item['price'] or 'fără preț'}\n{item['link']}"
            try:
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
                        break
                    except requests.exceptions.RequestException as e:
                        if attempt < max_retries - 1:
                            spider.logger.warning(f"⚠️ Tentativă {attempt + 1}/{max_retries} eșuată pentru Telegram: {e}. Reîncercare...")
                            import time
                            time.sleep(2 ** attempt)
                        else:
                            raise
                
                timestamp = item.get("created_time") or datetime.now().isoformat()
                category_list.append({"id": item["id"], "timestamp": timestamp})
                self.seen.add(item["id"])
                
                category_list = sorted(category_list, key=lambda x: x.get("timestamp", ""), reverse=True)[:100]
                self.state_data[category] = category_list
                
                self.seen = {item["id"] for item in category_list if isinstance(item, dict) and "id" in item}
                
                if hasattr(spider, 'seen'):
                    spider.seen.add(item["id"])
            except Exception as e:
                spider.logger.error(f"❌ Failed to send Telegram message for {item['id']}: {e}")
        else:
            spider.logger.debug(f"⏭️ Anunț {item['id']} deja văzut în categoria {category}, ignorat")
        return item

    def close_spider(self, spider):
        category = getattr(spider, 'category', 'unknown')
        category_list = self.state_data.get(category, [])
        
        if hasattr(spider, 'seen'):
            for sid in spider.seen:
                if sid not in self.seen:
                    category_list.append({"id": sid, "timestamp": datetime.now().isoformat()})
        
        category_list = sorted(category_list, key=lambda x: x.get("timestamp", ""), reverse=True)[:100]
        self.state_data[category] = category_list
        
        self.state_file.write_text(json.dumps(self.state_data, indent=2))
        spider.logger.info(f"💾 Salvat state.json pentru categoria {category}: {len(category_list)} anunțuri")
