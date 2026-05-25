import os
import logging
import hashlib
import json
import feedparser
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError
import asyncio

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ── CONFIG ────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN    = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID  = os.environ["TELEGRAM_CHAT_ID"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
CHECK_INTERVAL    = int(os.getenv("CHECK_INTERVAL", "900"))
SEEN_FILE         = "seen_items.json"

# ── RSS FEEDS PROFESIONALES ───────────────────────────────────────────────────
FEEDS = [
    # UFC / MMA internacionales
    {"url": "https://www.mmafighting.com/rss/current",     "tag": "🏆 UFC/MMA",      "category": "mma"},
    {"url": "https://mmajunkie.usatoday.com/feed",         "tag": "🏆 UFC/MMA",      "category": "mma"},
    {"url": "https://www.bloodyelbow.com/rss/current",     "tag": "🏆 UFC/MMA",      "category": "mma"},
    {"url": "https://www.ufc.com/rss/news",                "tag": "🏆 UFC",           "category": "mma"},
    {"url": "https://www.sherdog.com/rss/news.xml",        "tag": "🏆 UFC/MMA",      "category": "mma"},
    # PFL / Bellator
    {"url": "https://www.pflmma.com/news/rss",             "tag": "⚡ PFL/Bellator", "category": "mma"},
    # Boxeo internacional
    {"url": "https://www.boxingscene.com/rss.php",         "tag": "🥊 Boxeo",        "category": "boxing"},
    {"url": "https://www.ringtv.com/feed/",                "tag": "🥊 Boxeo",        "category": "boxing"},
    {"url": "https://www.espn.com/espn/rss/boxing/news",   "tag": "🥊 Boxeo",        "category": "boxing"},
    {"url": "https://www.badlefthook.com/rss/current",     "tag": "🥊 Boxeo",        "category": "boxing"},
    # Medios españoles
    {"url": "https://as.com/mas_deporte/mma/rss/",         "tag": "🇪🇸 MMA",         "category": "mma"},
    {"url": "https://as.com/mas_deporte/boxeo/rss/",       "tag": "🇪🇸 Boxeo",       "category": "boxing"},
    {"url": "https://www.marca.com/rss/boxeo.xml",         "tag": "🇪🇸 Boxeo",       "category": "boxing"},
]

# ── GOOGLE NEWS RSS — BÚSQUEDAS DINÁMICAS ─────────────────────────────────────
# Google News devuelve RSS por término de búsqueda, perfecto para eventos sin RSS propio
def gnews(query: str) -> str:
    from urllib.parse import quote
    return f"https://news.google.com/rss/search?q={quote(query)}&hl=es&gl=ES&ceid=ES:es"

GOOGLE_NEWS_FEEDS = [
    # Velada del Año — Ibai
    {"url": gnews("Velada del Año Ibai boxeo"),             "tag": "🎮 Velada",       "category": "streamer"},
    {"url": gnews("La Velada pelea confirmada"),            "tag": "🎮 Velada",       "category": "streamer"},
    # Jordi Wild
    {"url": gnews("Jordi Wild boxeo pelea"),                "tag": "🎙️ Wild Project", "category": "streamer"},
    {"url": gnews("The Wild Project combate"),              "tag": "🎙️ Wild Project", "category": "streamer"},
    # Creadores internacionales
    {"url": gnews("KSI boxing fight"),                      "tag": "🌍 Creators Box", "category": "streamer"},
    {"url": gnews("Logan Paul boxing"),                     "tag": "🌍 Creators Box", "category": "streamer"},
    {"url": gnews("Jake Paul boxing fight"),                "tag": "🌍 Creators Box", "category": "streamer"},
    {"url": gnews("MostlyHuman boxing fight"),              "tag": "🌍 Creators Box", "category": "streamer"},
    # MMA España general (promesas incluidas)
    {"url": gnews("MMA España peleador español UFC"),       "tag": "🇪🇸 MMA España",  "category": "mma"},
    {"url": gnews("boxeo español campeón mundial"),         "tag": "🇪🇸 Boxeo ES",    "category": "boxing"},
]

# ── PELEADORES ESPAÑOLES / HISPANOS ───────────────────────────────────────────
# Estrellas consolidadas
SPANISH_FIGHTERS_KNOWN = [
    # MMA top
    "topuria", "ilia topuria",
    # MMA promesas España
    "pascual", "ángel pascual", "angel pascual",
    "mozharov", "askar mozharov",
    "paredes", "jesús paredes",
    "roberto soldic",          # croata muy seguido en España vía KSW
    "marc diakiese",
    # Boxeo España
    "lejarraga", "kerman lejarraga",
    "jon fernandez", "jon fernández",
    "samuel carmona",
    "josé quiles", "jose quiles",
    "sandor martin", "sándor martin",   # campeón mundial súper ligero
    "gabriel escobar",
    "edgar berlanga",                   # puertorriqueño muy seguido en ES
    # Boxeo hispano top
    "canelo", "álvarez", "saul alvarez",
    "ryan garcia", "ryan garcía",
]

# Promesas / nombres a detectar por contexto
SPANISH_CONTEXT_KEYWORDS = [
    "peleador español", "boxeador español", "luchador español",
    "campeón español", "españa mma", "mma españa",
    "promesa española", "talento español",
    "español en ufc", "español en bellator",
    "español en el ufc", "debutará en ufc",
]

# ── STREAMERS / CREADORES ─────────────────────────────────────────────────────
STREAMER_NAMES = [
    "ibai", "velada del año", "la velada",
    "jordi wild", "the wild project",
    "ksi", "logan paul", "jake paul",
    "mostlyhuman", "inoxtag", "darreal",
    "plex", "rivers",                   # participantes frecuentes La Velada
    "carreravsroca", "viruzz", "perxitaa",
]

# Filtro estricto para streamers — solo noticias de peso
STREAMER_RELEVANT = [
    "pelea confirmada", "combate confirmado", "fight confirmed",
    "vs", "versus", "cartel", "fecha confirmada",
    "ganador", "ganó", "perdió", "resultado", "ko", "tko",
    "nocaut", "victoria", "derrota",
    "entrenamiento oficial", "camp de boxeo",
    "weigh-in", "pesaje", "contrato firmado",
]

# ── KEYWORDS PROFESIONALES ────────────────────────────────────────────────────
RELEVANT_KEYWORDS = [
    "wins", "loses", "defeats", "knockout", "ko", "tko", "submission",
    "decision", "unanimous", "split", "draw", "no contest", "stoppage",
    "gana", "pierde", "nocaut", "resultado", "victoria", "derrota",
    "ufc ", "fight night", "ppv", "main event", "co-main", "fight card",
    "bellator", "pfl", "velada", "evento", "card",
    "champion", "title", "belt", "interim", "unified", "undisputed",
    "campeón", "título", "cinturón", "campeonato",
    "signs", "contract", "deal", "signed", "released", "cut",
    "firma", "contrato", "acuerdo", "fichaje",
    "targeted", "in talks", "offered", "negotiating", "expected to",
    "sources say", "exclusive", "breaking",
    "retired", "retirement", "suspended", "banned", "doping",
    "injury", "injured", "surgery", "pulled", "canceled",
    "retiro", "suspendido", "lesión", "dopaje",
    "wbc", "wba", "ibf", "wbo", "matchroom", "top rank",
]

IRRELEVANT_KEYWORDS = [
    "podcast", "fantasy", "odds breakdown", "betting preview",
    "dfs picks", "daily fantasy", "bet on", "promo code",
    "best bets", "gambling", "casino", "watch party",
    "merchandise", "ticket sales",
]


# ── PERSISTENCIA ──────────────────────────────────────────────────────────────
def load_seen() -> set:
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen(seen: set):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


def item_id(entry) -> str:
    raw = (entry.get("id") or entry.get("link") or entry.get("title") or "")
    return hashlib.md5(raw.encode()).hexdigest()


# ── DETECCIÓN ─────────────────────────────────────────────────────────────────
def is_spanish_fighter(text: str) -> bool:
    tl = text.lower()
    return (
        any(f in tl for f in SPANISH_FIGHTERS_KNOWN) or
        any(k in tl for k in SPANISH_CONTEXT_KEYWORDS)
    )


def is_streamer_news(text: str) -> bool:
    tl = text.lower()
    return any(s in tl for s in STREAMER_NAMES)


def is_relevant(title: str, summary: str, category: str) -> bool:
    text = (title + " " + summary).lower()

    if any(kw in text for kw in IRRELEVANT_KEYWORDS):
        return False

    # Streamers: filtro más estricto
    if category == "streamer":
        return (
            is_streamer_news(text) and
            any(kw in text for kw in STREAMER_RELEVANT)
        )

    # MMA/Boxeo: prioridad peleadores españoles
    if is_spanish_fighter(text):
        return True

    return any(kw in text for kw in RELEVANT_KEYWORDS)


# ── IMAGEN ────────────────────────────────────────────────────────────────────
def get_image(entry) -> str | None:
    if hasattr(entry, "media_content") and entry.media_content:
        for m in entry.media_content:
            url = m.get("url", "")
            if m.get("medium") == "image" or url.endswith((".jpg", ".png", ".webp")):
                return url
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if "image" in enc.get("type", "") or enc.get("href", "").endswith((".jpg", ".png")):
                return enc.get("href") or enc.get("url")
    link = entry.get("link")
    if link:
        try:
            r = requests.get(link, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.text, "html.parser")
            og = soup.find("meta", property="og:image")
            if og and og.get("content"):
                return og["content"]
        except Exception:
            pass
    return None


def clean_summary(entry) -> str:
    raw = entry.get("summary") or entry.get("description") or ""
    soup = BeautifulSoup(raw, "html.parser")
    text = soup.get_text(separator=" ").strip()
    if len(text) > 500:
        text = text[:497].rsplit(" ", 1)[0] + "…"
    return text


# ── TRADUCCIÓN CON CLAUDE ─────────────────────────────────────────────────────
async def translate_news(title: str, summary: str, category: str) -> tuple[str, str]:
    # Detectar si ya está en español
    es_indicators = ["el ", "la ", "los ", "las ", "un ", "una ", "es ", "en ", "de ", "del "]
    combined = (title + " " + summary).lower()
    if sum(1 for i in es_indicators if i in combined) >= 4:
        return title, summary

    tone_hint = (
        "streamers y creators de contenido, con tono cercano y juvenil"
        if category == "streamer"
        else "deportes de combate, con tono periodístico directo"
    )

    prompt = f"""Eres un periodista deportivo español especializado en {tone_hint}.
Traduce el titular y resumen al español natural. Mantén nombres propios tal cual.
Responde SOLO con JSON sin backticks ni texto extra:
{{"titulo": "...", "resumen": "..."}}

TITULAR: {title}
RESUMEN: {summary}"""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=15,
        )
        raw    = resp.json()["content"][0]["text"].strip()
        raw    = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        return parsed.get("titulo", title), parsed.get("resumen", summary)
    except Exception as e:
        logger.warning(f"Traducción fallida: {e}")
        return title, summary


# ── FORMATO MENSAJE ───────────────────────────────────────────────────────────
def format_message(title: str, summary: str, link: str, tag: str,
                   is_spanish: bool, category: str) -> str:
    flag = ""
    if is_spanish and category != "streamer":
        flag = " 🇪🇸"
    elif category == "streamer":
        flag = " 🎥"

    lines = [f"{tag}{flag}", f"*{title}*"]
    if summary:
        lines.append(f"\n{summary}")
    if link:
        lines.append(f"\n🔗 [Leer más]({link})")
    return "\n".join(lines)


# ── ENVÍO ─────────────────────────────────────────────────────────────────────
async def send_news(bot: Bot, title: str, summary: str, link: str,
                    tag: str, image: str | None, is_spanish: bool, category: str):
    text = format_message(title, summary, link, tag, is_spanish, category)
    try:
        if image:
            await bot.send_photo(
                chat_id=TELEGRAM_CHAT_ID,
                photo=image,
                caption=text,
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=False,
            )
        logger.info(f"✅ [{category.upper()}] {title[:65]}")
    except TelegramError as e:
        logger.error(f"Telegram error: {e}")


# ── PROCESO DE FEEDS ──────────────────────────────────────────────────────────
async def process_feed(bot: Bot, feed_cfg: dict, seen: set) -> int:
    url      = feed_cfg["url"]
    tag      = feed_cfg["tag"]
    category = feed_cfg["category"]
    count    = 0
    try:
        parsed = feedparser.parse(url)
        for entry in parsed.entries:
            eid = item_id(entry)
            if eid in seen:
                continue
            seen.add(eid)

            raw_title   = entry.get("title", "")
            raw_summary = clean_summary(entry)
            link        = entry.get("link", "")

            if not is_relevant(raw_title, raw_summary, category):
                logger.debug(f"⏭  [{category}] {raw_title[:55]}")
                continue

            combined   = (raw_title + " " + raw_summary).lower()
            is_spanish = is_spanish_fighter(combined)
            title, summary = await translate_news(raw_title, raw_summary, category)
            image = get_image(entry)

            await send_news(bot, title, summary, link, tag, image, is_spanish, category)
            count += 1
            await asyncio.sleep(2)

    except Exception as e:
        logger.error(f"Error feed {url}: {e}")
    return count


async def check_all_feeds(bot: Bot, seen: set) -> int:
    total = 0
    all_feeds = FEEDS + GOOGLE_NEWS_FEEDS
    for feed_cfg in all_feeds:
        total += await process_feed(bot, feed_cfg, seen)
    save_seen(seen)
    return total


# ── MAIN ──────────────────────────────────────────────────────────────────────
async def main():
    bot  = Bot(token=TELEGRAM_TOKEN)
    seen = load_seen()

    logger.info("🤖 Bot MMA, Boxeo & Streamers España iniciado")
    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=(
            "🤖 *Bot Deportes de Combate — España* activo\n\n"
            "📡 Cubriendo:\n"
            "🏆 UFC + PFL/Bellator\n"
            "🥊 Boxeo mundial (WBC/WBA/IBF/WBO)\n"
            "🎮 La Velada del Año · Jordi Wild\n"
            "🌍 KSI · Logan Paul · Jake Paul\n"
            "🇪🇸 Peleadores españoles e hispanos\n\n"
            "Noticias traducidas al español en tiempo real ✅"
        ),
        parse_mode=ParseMode.MARKDOWN,
    )

    while True:
        logger.info("🔍 Revisando todos los feeds…")
        n = await check_all_feeds(bot, seen)
        logger.info(f"   {n} noticias nuevas enviadas")
        await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
