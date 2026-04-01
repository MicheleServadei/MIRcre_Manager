import os, re, time, requests, json, hashlib, threading
from playwright.sync_api import sync_playwright
from flask import Flask, render_template, jsonify, request

# ================= CONFIGURAZIONE =================
TMDB_API        = "add api here"
TELEGRAM_TOKEN  = "add the token here"
TELEGRAM_CHAT_ID= "add the id here"
DB_FILE         = "static/database.json"
SCAN_IN_PROGRESS= False
SCAN_DONE_FLAG  = False          # alzato quando lo scan finisce → frontend lo consuma
db_lock         = threading.Lock()

if not os.path.exists("static"):
    os.makedirs("static")

# ─────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────
def load_json(path):
    with db_lock:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

def save_json(path, data):
    with db_lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

# ─────────────────────────────────────────
# Pulizia titolo per TMDB
# ─────────────────────────────────────────
TECH_TAGS = (
    r"\b(2160p|1080p|720p|480p|4k|h265|h264|h263|x264|x265|hevc|avc|aac|ac3|dts|"
    r"eac3|ddp|atmos|truehd|flac|mp3|"
    r"ita|eng|fra|fre|chi|jpn|kor|spa|ger|rus|"
    r"subita|subeng|subFRE|subCHI|sub|"
    r"NUEng|NUeng|NUIta|nuita|nueng|"
    r"mircrew|iNTERNAL|TIGER|REAlDMDJ|realDMDJ|COSMO|CREW|"
    r"BDMUX|WEB-DL|WEBRip|BluRay|Bluray|BDRip|DVDRip|HDTV|"
    r"10bit|8bit|HDR|SDR|REMUX|EXTENDED|REPACK|PROPER|"
    r"FullHD|FullHD|SD|HD|FHD|UHD)\b"
)

def clean_title(raw):
    s = re.sub(r"\[.*?\]|\(.*?\)", "", raw)
    s = re.sub(TECH_TAGS, "", s, flags=re.IGNORECASE)
    s = s.split("-")[0].split("–")[0].strip()
    s = re.sub(r"[^a-zA-Z0-9\sàèéìòùÀÈÉÌÒÙ]", " ", s)
    return " ".join(s.split())

def normalize(title):
    t = title.lower().strip()
    return re.sub(r"[^a-z0-9\s]", "", t)

# ─────────────────────────────────────────
# Estrazione metadati dal post del forum
# ─────────────────────────────────────────
def extract_post_meta(page_content):
    """Estrae genere, durata, paese, regia dalla pagina del forum."""
    text = re.sub(r"<[^>]+>", " ", page_content)
    text = re.sub(r"\s+", " ", text)

    def find(patterns):
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                val = m.group(1).strip().strip(":").strip()
                # Prendi solo fino alla prima riga / pipe / prossimo campo
                val = re.split(r"\s{2,}|[\|•\n]", val)[0].strip()
                return val[:120]
        return None

    genere = find([
        r"GENERE\s*[:\-]?\s*([A-Za-zÀ-ÿ ,/&]+)",
        r"Genere\s*[:\-]?\s*([A-Za-zÀ-ÿ ,/&]+)",
    ])
    durata = find([r"DURATA\s*[:\-]?\s*([\d\s\w\.]+Min\.?)", r"Durata\s*[:\-]?\s*([\d]+\s*[Mm]in)"])
    paese  = find([r"PAESE\s*[:\-]?\s*([A-Za-z ,/]+)", r"Paese\s*[:\-]?\s*([A-Za-z ,/]+)"])
    regia  = find([r"REGIA\s*[:\-]?\s*([A-Za-zÀ-ÿ ,\.]+)", r"Regia\s*[:\-]?\s*([A-Za-zÀ-ÿ ,\.]+)"])

    # Dimensione file
    dim = "N/D"
    dm = re.search(r"DIMENSIONE\s*[:\-]?\s*([\d,\.]+\s*G[Bb])", text, re.IGNORECASE) or \
         re.search(r"(\d+[.,]?\d*\s*[GM]B)", text, re.IGNORECASE)
    if dm:
        dim = dm.group(1).strip()

    return {
        "genere": genere,
        "durata": durata,
        "paese": paese,
        "regia": regia,
        "dim": dim,
    }

# ─────────────────────────────────────────
# TMDB
# ─────────────────────────────────────────
def get_tmdb_data(title, year=None):
    sq = clean_title(title)
    if not sq:
        return _empty_tmdb(title)

    params = f"api_key={TMDB_API}&query={requests.utils.quote(sq)}&language=it-IT"
    if year and year.isdigit():
        params += f"&year={year}"

    try:
        r = requests.get(f"https://api.themoviedb.org/3/search/movie?{params}", timeout=10).json()
        results = r.get("results", [])

        # Prefer results with poster
        with_poster = [m for m in results if m.get("poster_path")]
        candidates = with_poster or results

        if candidates:
            m = candidates[0]
            # Get genres from TMDB
            genres = []
            if m.get("genre_ids"):
                genres = _tmdb_genre_names(m["genre_ids"])

            return {
                "poster": f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get("poster_path") else None,
                "backdrop": f"https://image.tmdb.org/t/p/w780{m['backdrop_path']}" if m.get("backdrop_path") else None,
                "rating": round(float(m.get("vote_average", 0)), 1),
                "nome": m.get("title", sq),
                "overview": m.get("overview", ""),
                "data_uscita": m.get("release_date", "")[:4] if m.get("release_date") else "N/D",
                "release_date_full": m.get("release_date", ""),
                "tmdb_id": m.get("id"),
                "generi_tmdb": genres,
            }
    except Exception as e:
        print(f"[TMDB] Errore per '{title}': {e}")

    return _empty_tmdb(sq)

def _empty_tmdb(title):
    return {"poster": None, "backdrop": None, "rating": 0.0, "nome": title,
            "overview": "", "data_uscita": "N/D", "release_date_full": "",
            "tmdb_id": None, "generi_tmdb": []}

# Mappa ID generi TMDB → nomi
TMDB_GENRES = {
    28:"Azione", 12:"Avventura", 16:"Animazione", 35:"Commedia", 80:"Crime",
    99:"Documentario", 18:"Drammatico", 10751:"Famiglia", 14:"Fantasy",
    36:"Storia", 27:"Horror", 10402:"Musica", 9648:"Mistero", 10749:"Romantico",
    878:"Fantascienza", 10770:"TV Movie", 53:"Thriller", 10752:"Guerra", 37:"Western"
}

def _tmdb_genre_names(ids):
    return [TMDB_GENRES[i] for i in ids if i in TMDB_GENRES]

# ─────────────────────────────────────────
# Telegram
# ─────────────────────────────────────────
def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        print(f"[TELEGRAM] {e}")

def notify_new_movie(movie):
    qualita = ", ".join(movie.get("versioni", {}).keys())
    generi = ", ".join(movie.get("generi_tmdb") or [])
    msg = (
        f"🎬 <b>Nuovo film su MirCrew!</b>\n\n"
        f"📽 <b>{movie['nome']}</b> ({movie.get('data_uscita','N/D')})\n"
        f"⭐ Rating: {movie.get('rating', 0)}\n"
        f"🎭 Generi: {generi or 'N/D'}\n"
        f"📦 Qualità: {qualita}"
    )
    send_telegram(msg)

# ─────────────────────────────────────────
# SCRAPER
# ─────────────────────────────────────────
def run_scraper():
    global SCAN_IN_PROGRESS, SCAN_DONE_FLAG
    if SCAN_IN_PROGRESS:
        print("[SCRAPER] Già in corso, skip.")
        return

    SCAN_IN_PROGRESS = True
    SCAN_DONE_FLAG   = False
    print("[SCRAPER] Avvio scan...")

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp("http://localhost:9222")
            except Exception as e:
                print(f"[SCRAPER] Chrome non raggiungibile: {e}")
                SCAN_IN_PROGRESS = False
                return

            ctx  = browser.contexts[0]
            page = ctx.pages[0] if ctx.pages else ctx.new_page()

            try:
                page.goto("https://mircrew-releases.org/releases/?cat=26", timeout=60000)
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception as e:
                print(f"[SCRAPER] Errore lista: {e}")
                SCAN_IN_PROGRESS = False
                return

            links = [a.get_attribute("href") for a in page.query_selector_all("a.topictitle")
                     if a.get_attribute("href")][:35]
            print(f"[SCRAPER] {len(links)} link trovati.")

            for idx, l in enumerate(links):
                try:
                    db = load_json(DB_FILE)
                    full_url = "https://mircrew-releases.org" + l.replace("./..", "").replace("./", "/")

                    try:
                        page.goto(full_url, timeout=30000)
                        page.wait_for_load_state("domcontentloaded", timeout=10000)
                    except:
                        print(f"[SCRAPER] Timeout {full_url}")
                        continue

                    # Titolo dalla pagina
                    try:
                        h2 = page.query_selector("h2")
                        raw_h2 = h2.inner_text().replace("Guarda l'argomento - ", "").strip() if h2 else ""
                    except:
                        raw_h2 = ""

                    if not raw_h2:
                        continue

                    # Qualità
                    qualita = "4K 2160p" if any(x in raw_h2.upper() for x in ["2160", "4K"]) else "1080p"

                    # Metadati dal post (genere, dimensione, ecc.)
                    try:
                        html_content = page.content()
                        post_meta = extract_post_meta(html_content)
                    except:
                        post_meta = {"genere": None, "durata": None, "paese": None, "regia": None, "dim": "N/D"}

                    # Anno dal titolo per migliorare match TMDB
                    year_match = re.search(r"\b(20\d{2}|19\d{2})\b", raw_h2)
                    year = year_match.group(1) if year_match else None

                    # Dati TMDB
                    info = get_tmdb_data(raw_h2, year)

                    # Merge generi: TMDB + forum
                    generi = info.get("generi_tmdb") or []
                    if post_meta.get("genere") and not generi:
                        # Parsa generi dal forum come fallback
                        generi = [g.strip() for g in re.split(r"[,/]", post_meta["genere"]) if g.strip()]

                    # Chiave deduplicazione
                    movie_key = f"tmdb_{info['tmdb_id']}" if info.get("tmdb_id") else \
                                hashlib.md5(normalize(info["nome"]).encode()).hexdigest()

                    is_new = movie_key not in db

                    if is_new:
                        db[movie_key] = {
                            **info,
                            "generi_tmdb": generi,
                            "regia": post_meta.get("regia"),
                            "durata": post_meta.get("durata"),
                            "paese": post_meta.get("paese"),
                            "versioni": {},
                            "last_added": time.time(),
                        }
                    else:
                        # Aggiorna generi se mancavano prima
                        if not db[movie_key].get("generi_tmdb") and generi:
                            db[movie_key]["generi_tmdb"] = generi
                        if not db[movie_key].get("regia") and post_meta.get("regia"):
                            db[movie_key]["regia"] = post_meta["regia"]
                        if not db[movie_key].get("backdrop") and info.get("backdrop"):
                            db[movie_key]["backdrop"] = info["backdrop"]

                    dim = post_meta["dim"]
                    existing_url = db[movie_key]["versioni"].get(qualita, {}).get("url", "")
                    if existing_url != full_url:
                        db[movie_key]["versioni"][qualita] = {"url": full_url, "dim": dim}

                    save_json(DB_FILE, db)

                    if is_new:
                        notify_new_movie(db[movie_key])
                        print(f"[SCRAPER] ✓ Nuovo: {info['nome']} ({qualita})")
                    else:
                        print(f"[SCRAPER] ~ Già noto: {info['nome']}")

                except Exception as e:
                    print(f"[SCRAPER] Errore link {idx}: {e}")
                    continue

    except Exception as e:
        print(f"[SCRAPER] Errore critico: {e}")

    SCAN_IN_PROGRESS = False
    SCAN_DONE_FLAG   = True      # ← segnala al frontend che è finito
    print("[SCRAPER] Scan completato.")

# ─────────────────────────────────────────
# FLASK
# ─────────────────────────────────────────
app = Flask(__name__)

@app.route("/")
def index():
    db = load_json(DB_FILE)
    movies = list(db.values())

    trending, upcoming = [], []
    try:
        trending = requests.get(
            f"https://api.themoviedb.org/3/trending/movie/week?api_key={TMDB_API}&language=it-IT",
            timeout=8).json().get("results", [])[:20]
    except:
        pass
    try:
        upcoming = requests.get(
            f"https://api.themoviedb.org/3/movie/upcoming?api_key={TMDB_API}&language=it-IT&region=IT",
            timeout=8).json().get("results", [])[:20]
    except:
        pass

    # Raccoglie tutti i generi presenti nel db per i filtri
    all_genres = sorted({g for m in movies for g in (m.get("generi_tmdb") or []) if g})

    return render_template(
        "index.html",
        recenti=sorted(movies, key=lambda x: x.get("last_added", 0), reverse=True),
        trending=trending,
        upcoming=upcoming,
        all_movies=sorted(movies, key=lambda x: x.get("nome", "").lower()),
        all_genres=all_genres,
    )

@app.route("/api/status")
def api_status():
    global SCAN_DONE_FLAG
    done = SCAN_DONE_FLAG
    if done:
        SCAN_DONE_FLAG = False   # consumato: il frontend lo legge una sola volta
    return jsonify({"scanning": SCAN_IN_PROGRESS, "just_finished": done})

@app.route("/api/scan", methods=["POST"])
def api_scan():
    if SCAN_IN_PROGRESS:
        return jsonify({"ok": False, "msg": "Scan già in corso..."})
    threading.Thread(target=run_scraper, daemon=True).start()
    return jsonify({"ok": True, "msg": "Scan avviato!"})

@app.route("/api/movies")
def api_movies():
    db = load_json(DB_FILE)
    movies = list(db.values())

    # Filtri
    quality = request.args.get("quality", "all")
    genre   = request.args.get("genre", "all")
    q       = request.args.get("q", "").lower().strip()
    sort    = request.args.get("sort", "recent")

    if quality != "all":
        movies = [m for m in movies if quality in m.get("versioni", {})]
    if genre != "all":
        movies = [m for m in movies if genre in (m.get("generi_tmdb") or [])]
    if q:
        movies = [m for m in movies if q in m.get("nome", "").lower()]

    # Ordinamento
    if sort == "recent":
        movies = sorted(movies, key=lambda x: x.get("last_added", 0), reverse=True)
    elif sort == "rating":
        movies = sorted(movies, key=lambda x: x.get("rating", 0), reverse=True)
    elif sort == "az":
        movies = sorted(movies, key=lambda x: x.get("nome", "").lower())
    elif sort == "release":
        movies = sorted(movies,
                        key=lambda x: x.get("release_date_full") or x.get("data_uscita") or "",
                        reverse=True)

    # Paginazione
    page     = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 24))
    total    = len(movies)
    start    = (page - 1) * per_page

    return jsonify({
        "movies": movies[start:start + per_page],
        "total": total,
        "page": page,
        "pages": max(1, (total + per_page - 1) // per_page),
    })

@app.route("/api/genres")
def api_genres():
    db = load_json(DB_FILE)
    genres = sorted({g for m in db.values() for g in (m.get("generi_tmdb") or []) if g})
    return jsonify(genres)

if __name__ == "__main__":
    threading.Thread(target=run_scraper, daemon=True).start()
    app.run(port=5000, debug=False)