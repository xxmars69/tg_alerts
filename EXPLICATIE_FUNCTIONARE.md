# Explicație Funcționare OLX Telegram Alert

## 🔄 Fluxul de lucru actual

### 1. **La fiecare 5 minute** (GitHub Actions)
- Workflow-ul pornește automat
- Restaurează `state.json` din cache (dacă există)
- Rulează **secvențial** toate cele 5 căutări

### 2. **Pentru fiecare căutare** (ex: Canon, Nikon, Sony, etc.)

#### A. **Început** (`pipelines.py` - `open_spider`)
```
1. Citește state.json (dacă există)
2. Încarcă toate ID-urile văzute într-un set Python (self.seen)
3. Exemplu: self.seen = {"12345", "67890", "11111", ...}
```

#### B. **Procesare anunțuri** (`watch.py` - `parse_api`)
```
1. Face request la API OLX pentru prima pagină (40 anunțuri)
2. Pentru fiecare anunț:
   - Extrage ID-ul anunțului
   - Verifică dacă ID-ul e în self.seen
   - Dacă NU e în seen → trimite la pipeline
   - Dacă DA e în seen → ignoră (l-a văzut deja)
3. Dacă există pagină următoare → face request pentru următoarea pagină
4. Repetă până când nu mai sunt pagini
```

#### C. **Pipeline** (`pipelines.py` - `process_item`)
```
1. Primește anunț nou (care nu e în self.seen)
2. Trimite mesaj Telegram
3. Adaugă ID-ul în self.seen (pentru a nu-l mai trimite)
```

#### D. **Finalizare** (`pipelines.py` - `close_spider`)
```
1. Salvează ultimele 500 ID-uri din self.seen în state.json
2. state.json este partajat între TOATE căutările
```

### 3. **După toate căutările**
- Salvează `state.json` în cache GitHub Actions
- Cache-ul este folosit la următorul run (după 5 minute)

## ⚠️ PROBLEMA IDENTIFICATĂ

### De ce poate dura 20+ minute pentru o căutare?

1. **Paginare completă**: 
   - Spider-ul parcurge TOATE paginile de rezultate
   - Dacă o căutare are 1000 de anunțuri = 25 pagini (40 anunțuri/pagină)
   - Fiecare pagină = 1 secundă delay (`DOWNLOAD_DELAY: 1`)
   - 25 pagini × 1 sec = 25 secunde minim
   - Plus timpul de procesare, request-uri Telegram, etc.

2. **Rulare secvențială**:
   ```
   Canon:  5 minute
   Nikon:  5 minute  
   Sony:   5 minute
   Aparat: 5 minute
   Camera: 5 minute
   ──────────────────
   TOTAL: 25 minute (dacă fiecare durează 5 min)
   ```

3. **State.json partajat**:
   - ✅ BINE: Evită duplicatele între căutări
   - ⚠️ PROBLEMĂ: Dacă Canon are 1000 anunțuri, le procesează pe toate
   - Chiar dacă majoritatea sunt deja în state.json, tot trebuie să facă request-uri

## 🔧 SOLUȚII POSIBILE

### Opțiunea 1: Limitează numărul de pagini
- Procesează doar primele 2-3 pagini (anunțurile cele mai noi)
- Modifică `parse_api` să oprească după N pagini

### Opțiunea 2: Optimizează verificarea
- Verifică mai devreme dacă anunțul e în seen
- Oprește paginarea dacă toate anunțurile dintr-o pagină sunt deja văzute

### Opțiunea 3: Rulează căutările în paralel
- Rulează toate căutările simultan (nu secvențial)
- Reduce timpul total de la 25 min la ~5 min

### Opțiunea 4: Folosește parametrul `min_id` din URL
- URL-urile tale au deja `min_id=297001087`
- Acest parametru spune OLX să returneze doar anunțuri mai noi decât acel ID
- Poate reduce semnificativ numărul de rezultate

## 📊 Exemplu concret

**Situație actuală:**
```
Run 1 (00:00):
  - Canon: procesează 1000 anunțuri, găsește 10 noi → 5 min
  - Nikon: procesează 800 anunțuri, găsește 5 noi → 4 min
  - Sony: procesează 1200 anunțuri, găsește 15 noi → 6 min
  - Aparat: procesează 2000 anunțuri, găsește 20 noi → 10 min
  - Camera: procesează 1500 anunțuri, găsește 8 noi → 7 min
  TOTAL: 32 minute

Run 2 (00:05) - dar Run 1 încă rulează!
  - Așteaptă ca Run 1 să se termine
  - Apoi pornește Run 2
```

**Problema:** Dacă un run durează mai mult de 5 minute, următorul run așteaptă (datorită `cancel-in-progress: false`).

## 💡 Recomandare

Cea mai bună soluție este **Opțiunea 4** - folosește `min_id` din URL-uri:
- URL-urile tale au deja `min_id` setat
- OLX va returna doar anunțuri mai noi decât acel ID
- Reduce drastic numărul de rezultate de procesat
- Mai rapid și mai eficient

Vrei să implementez una dintre aceste optimizări?

