import streamlit as st
import requests
import math
import os
from datetime import datetime, timedelta
from itertools import product
from collections import defaultdict

# ─────────────────────────────────────────────
#  CARICAMENTO CHIAVI API
# ─────────────────────────────────────────────
def _load_keys() -> tuple[str, str]:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    def from_secrets(name):
        try:
            return st.secrets.get(name, "") or ""
        except Exception:
            return ""

    af  = from_secrets("FOOTBALL_DATA_KEY") or os.environ.get("FOOTBALL_DATA_KEY", "")
    odd = from_secrets("ODDS_API_KEY")       or os.environ.get("ODDS_API_KEY", "")
    return af.strip(), odd.strip()


_env_af, _env_odds = _load_keys()


# ─────────────────────────────────────────────
#  CONFIGURAZIONE PAGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Donny — Football Intelligence",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  CSS — font Apple (SF Pro via system-ui)
# ─────────────────────────────────────────────
st.markdown("""
<style>
:root {
    --font-ui:   -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    --font-mono: "SF Mono", "Fira Mono", "Cascadia Code", "Menlo", monospace;
    --bg:        #08090f;
    --bg2:       #0d0f1a;
    --border:    rgba(255,255,255,0.07);
    --border-hi: rgba(255,255,255,0.16);
    --text:      #e8eaf0;
    --muted:     rgba(255,255,255,0.30);
    --green:     #34c759;
    --yellow:    #ffd60a;
    --red:       #ff453a;
    --blue:      #0a84ff;
    --pink:      #ff375f;
}
html, body, [class*="css"] {
    font-family: var(--font-ui) !important;
    background-color: var(--bg) !important;
    color: var(--text) !important;
    -webkit-font-smoothing: antialiased;
}
.stApp {
    background: var(--bg) !important;
    background-image: radial-gradient(ellipse 80% 35% at 50% -5%,
        rgba(10,132,255,0.16) 0%, transparent 60%) !important;
}
[data-testid="stSidebar"] {
    background: var(--bg2) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }

.main-title {
    font-family: var(--font-ui);
    font-size: 2.2rem; font-weight: 700;
    letter-spacing: -0.03em; color: #f5f5f7; margin-bottom: 0;
}
.main-subtitle {
    font-family: var(--font-mono); font-size: 0.65rem;
    letter-spacing: 0.2em; color: var(--muted); margin-top: 5px; text-transform: uppercase;
}
.stat-label {
    font-family: var(--font-mono); font-size: 0.58rem;
    letter-spacing: 0.18em; color: var(--muted); text-transform: uppercase; margin-bottom: 10px;
}
.team-name {
    font-family: var(--font-ui); font-size: 1.15rem; font-weight: 600;
    letter-spacing: -0.01em; color: rgba(255,255,255,0.92);
}
.league-badge {
    font-family: var(--font-mono); font-size: 0.62rem;
    letter-spacing: 0.12em; color: var(--muted); text-transform: uppercase;
}
.match-card {
    background: rgba(255,255,255,0.025); border: 1px solid var(--border);
    border-radius: 16px; padding: 20px 22px; margin-bottom: 12px;
}
.match-card:hover { border-color: var(--border-hi); }
.match-card-selected {
    background: rgba(255,255,255,0.05); border: 1px solid var(--border-hi);
    border-radius: 16px; padding: 20px 22px; margin-bottom: 12px;
}
.stat-box {
    background: rgba(255,255,255,0.025); border: 1px solid var(--border);
    border-radius: 14px; padding: 15px 18px; margin-bottom: 10px;
}
.conf-high { color: var(--green);  font-family: var(--font-mono); font-weight: 700; font-size: 1.55rem; }
.conf-mid  { color: var(--yellow); font-family: var(--font-mono); font-weight: 700; font-size: 1.55rem; }
.conf-low  { color: var(--red);    font-family: var(--font-mono); font-weight: 700; font-size: 1.55rem; }
.value-tag {
    display: inline-block; background: rgba(52,199,89,0.12);
    border: 1px solid rgba(52,199,89,0.32); border-radius: 20px;
    padding: 2px 11px; font-family: var(--font-mono); font-size: 0.58rem;
    font-weight: 700; letter-spacing: 0.1em; color: var(--green);
}
.auto-badge {
    display: inline-block; background: rgba(10,132,255,0.12);
    border: 1px solid rgba(10,132,255,0.3); border-radius: 20px;
    padding: 2px 9px; font-family: var(--font-mono); font-size: 0.56rem;
    font-weight: 700; letter-spacing: 0.1em; color: var(--blue);
}
.prescreened-badge {
    display: inline-block; background: rgba(255,214,10,0.10);
    border: 1px solid rgba(255,214,10,0.28); border-radius: 20px;
    padding: 2px 9px; font-family: var(--font-mono); font-size: 0.56rem;
    font-weight: 700; letter-spacing: 0.1em; color: var(--yellow);
}
.no-odds-badge {
    display: inline-block; background: rgba(255,69,58,0.10);
    border: 1px solid rgba(255,69,58,0.28); border-radius: 20px;
    padding: 2px 9px; font-family: var(--font-mono); font-size: 0.56rem;
    font-weight: 700; letter-spacing: 0.1em; color: var(--red);
}
.dot-w { display:inline-block; width:9px; height:9px; border-radius:50%; background:var(--green);  margin:0 2px; }
.dot-d { display:inline-block; width:9px; height:9px; border-radius:50%; background:var(--yellow); margin:0 2px; }
.dot-l { display:inline-block; width:9px; height:9px; border-radius:50%; background:var(--red);    margin:0 2px; }
.odd-box {
    display: inline-flex; flex-direction: column; align-items: center;
    background: rgba(255,255,255,0.04); border: 1px solid var(--border);
    border-radius: 10px; padding: 7px 12px; margin: 3px; min-width: 54px;
}
.odd-box-hl {
    display: inline-flex; flex-direction: column; align-items: center;
    background: rgba(52,199,89,0.09); border: 1px solid rgba(52,199,89,0.3);
    border-radius: 10px; padding: 7px 12px; margin: 3px; min-width: 54px;
}
.odd-lbl    { font-family: var(--font-mono); font-size: 0.58rem; color: var(--muted); letter-spacing: 0.08em; }
.odd-val    { font-family: var(--font-mono); font-size: 0.92rem; font-weight: 700; color: rgba(255,255,255,0.88); }
.odd-val-hl { font-family: var(--font-mono); font-size: 0.92rem; font-weight: 700; color: var(--green); }
.prog-bar-wrap { background: rgba(255,255,255,0.06); border-radius: 4px; height: 4px; margin-top: 5px; }
.prog-bar-fill { height: 4px; border-radius: 4px; }
.info-box {
    background: rgba(10,132,255,0.07); border: 1px solid rgba(10,132,255,0.2);
    border-radius: 12px; padding: 13px 17px; font-size: 0.82rem;
    color: rgba(255,255,255,0.6); margin-bottom: 14px;
}
.warn-box {
    background: rgba(255,214,10,0.07); border: 1px solid rgba(255,214,10,0.2);
    border-radius: 12px; padding: 13px 17px; font-size: 0.82rem;
    color: rgba(255,255,255,0.6); margin-bottom: 14px;
}
.key-ok  { background: rgba(52,199,89,0.07);  border: 1px solid rgba(52,199,89,0.22);  border-radius: 10px; padding: 10px 13px; margin-bottom: 7px; }
.key-mis { background: rgba(255,69,58,0.07);  border: 1px solid rgba(255,69,58,0.22);  border-radius: 10px; padding: 10px 13px; margin-bottom: 7px; }
.xg-num-home { font-family: var(--font-mono); font-size: 2.4rem; font-weight: 800; color: var(--blue); }
.xg-num-away { font-family: var(--font-mono); font-size: 2.4rem; font-weight: 800; color: var(--pink); }
.xg-label    { font-family: var(--font-mono); font-size: 0.6rem; color: var(--muted); letter-spacing: 0.1em; margin-bottom: 3px; }
.recap-table { width: 100%; border-collapse: collapse; }
.recap-table th {
    font-family: var(--font-mono); font-size: 0.56rem; letter-spacing: 0.14em;
    color: var(--muted); font-weight: 400; text-align: left;
    padding: 6px 10px; border-bottom: 1px solid var(--border);
}
.recap-table td {
    font-family: var(--font-ui); font-size: 0.78rem;
    color: rgba(255,255,255,0.72); padding: 9px 10px;
    border-bottom: 1px solid rgba(255,255,255,0.04); vertical-align: middle;
}
.recap-match  { font-weight: 600; color: rgba(255,255,255,0.88); font-size: 0.8rem; }
.recap-pick   { font-family: var(--font-mono); font-weight: 700; font-size: 0.9rem; }
.recap-green  { color: var(--green); }
.recap-yellow { color: var(--yellow); }
.recap-red    { color: var(--red); }
.divider { border: none; border-top: 1px solid var(--border); margin: 16px 0; }
.stButton > button {
    background: rgba(255,255,255,0.05) !important; border: 1px solid var(--border-hi) !important;
    color: rgba(255,255,255,0.82) !important; border-radius: 12px !important;
    font-family: var(--font-mono) !important; font-size: 0.72rem !important;
    letter-spacing: 0.08em !important; padding: 9px 20px !important; width: 100% !important;
}
.stButton > button:hover {
    background: rgba(255,255,255,0.09) !important;
    border-color: rgba(255,255,255,0.26) !important; color: #fff !important;
}
.stSelectbox > div > div, .stTextInput > div > div {
    background: rgba(255,255,255,0.04) !important; border: 1px solid var(--border-hi) !important;
    border-radius: 10px !important; color: var(--text) !important;
}
.stSpinner > div { border-top-color: var(--green) !important; }
#MainMenu { visibility: hidden; } footer { visibility: hidden; } header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  COSTANTI
# ─────────────────────────────────────────────
LEAGUES = {
    "Serie A 🇮🇹":         {"id": 135, "color": "#0055d4", "odds_key": "soccer_italy_serie_a"},
    "Premier League 🏴󠁧󠁢󠁥󠁮󠁧󠁿":  {"id": 39,  "color": "#6600cc", "odds_key": "soccer_epl"},
    "La Liga 🇪🇸":          {"id": 140, "color": "#cc0000", "odds_key": "soccer_spain_la_liga"},
    "Bundesliga 🇩🇪":       {"id": 78,  "color": "#cc2200", "odds_key": "soccer_germany_bundesliga"},
    "Ligue 1 🇫🇷":          {"id": 61,  "color": "#003fa3", "odds_key": "soccer_france_ligue_one"},
}

def current_season() -> int:
    now = datetime.now()
    return now.year if now.month >= 8 else now.year - 1

CURRENT_SEASON         = current_season()
MAX_SCORELINE          = 6
PRESCREENING_THRESHOLD = 0.55
PREFERRED_BOOKMAKERS   = ["pinnacle", "bet365", "williamhill", "unibet", "betfair"]


# ─────────────────────────────────────────────
#  MOTORE POISSON
# ─────────────────────────────────────────────
def poisson_prob(lam: float, k: int) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def build_score_matrix(lam_h: float, lam_a: float, max_g: int = MAX_SCORELINE) -> dict:
    return {
        (gh, ga): poisson_prob(lam_h, gh) * poisson_prob(lam_a, ga)
        for gh, ga in product(range(max_g + 1), range(max_g + 1))
    }


def compute_markets(matrix: dict) -> dict:
    p1  = sum(v for (gh, ga), v in matrix.items() if gh > ga)
    px  = sum(v for (gh, ga), v in matrix.items() if gh == ga)
    p2  = sum(v for (gh, ga), v in matrix.items() if gh < ga)
    po  = sum(v for (gh, ga), v in matrix.items() if gh + ga > 2)
    pgg = sum(v for (gh, ga), v in matrix.items() if gh > 0 and ga > 0)
    return {
        "p1":    round(p1  * 100, 1),
        "px":    round(px  * 100, 1),
        "p2":    round(p2  * 100, 1),
        "over":  round(po  * 100, 1),
        "under": round((1 - po) * 100, 1),
        "gg":    round(pgg * 100, 1),
        "nogg":  round((1 - pgg) * 100, 1),
    }


def compute_form_weight(results: list, n: int = 6) -> float:
    if not results:
        return 1.0
    recent  = results[-n:]
    weights = [0.9 ** i for i in range(len(recent) - 1, -1, -1)]
    pts_map = {"W": 1.0, "D": 0.4, "L": 0.0}
    score   = sum(pts_map.get(r, 0.4) * w for r, w in zip(recent, weights))
    max_sc  = sum(weights)
    norm    = score / max_sc if max_sc > 0 else 0.5
    return round(0.7 + norm * 0.6, 4)


def value_bet(prob_pct: float, odd: float) -> bool:
    return odd > 0 and (prob_pct / 100) > (1 / odd)


def implied_prob(odd: float) -> float:
    return (1 / odd * 100) if odd > 0 else 0.0


def best_suggestion(markets: dict, odds: dict, form_h: float, form_a: float,
                    lam_h: float, lam_a: float):
    """
    Ritorna (best, candidates, analysis).
    Se le quote sono assenti → best=None, candidates=[], solo analisi contestuale.
    NESSUN consiglio di giocata viene emesso senza dati di mercato.
    """
    has_odds = any(odds.get(k, 0) > 0 for k in
                   ("home", "draw", "away", "over25", "under25", "gg", "nogg"))

    fh_str = "ottima" if form_h > 1.1 else "nella norma" if form_h >= 0.9 else "in calo"
    fa_str = "ottima" if form_a > 1.1 else "nella norma" if form_a >= 0.9 else "in calo"

    base = (
        f"Il modello Poisson stima **{lam_h:.2f}** gol attesi per la squadra di casa "
        f"e **{lam_a:.2f}** per gli ospiti. "
        f"Forma recente casa: {fh_str} (x{form_h}), "
        f"ospiti: {fa_str} (x{form_a}). "
    )

    if not has_odds:
        analysis = (
            base +
            "**Quote non disponibili** per questa partita: "
            "Donny non emette consigli senza dati di mercato. "
            "Verifica la disponibilità delle quote e rianalizza."
        )
        return None, [], analysis

    candidates = []
    mapping = [
        ("1",    markets["p1"],    odds.get("home",    0)),
        ("X",    markets["px"],    odds.get("draw",    0)),
        ("2",    markets["p2"],    odds.get("away",    0)),
        ("O2.5", markets["over"],  odds.get("over25",  0)),
        ("U2.5", markets["under"], odds.get("under25", 0)),
        ("GG",   markets["gg"],    odds.get("gg",      0)),
        ("NoGG", markets["nogg"],  odds.get("nogg",    0)),
    ]
    for label, prob, odd in mapping:
        ev = (prob / 100) * odd - (1 - prob / 100) if odd > 0 else -999
        candidates.append({
            "label":   label, "prob": prob, "odd": odd,
            "value":   value_bet(prob, odd), "ev": round(ev, 4),
            "implied": round(implied_prob(odd), 1),
            "edge":    round(prob - implied_prob(odd), 1) if odd > 0 else 0,
        })
    candidates.sort(key=lambda x: (x["value"], x["ev"]), reverse=True)
    best = candidates[0]

    analysis = base
    if best["value"]:
        analysis += (
            f"La giocata **{best['label']}** mostra un edge positivo di "
            f"**{best['edge']:.1f}pp** "
            f"(prob. modello {best['prob']}% vs quota implicita {best['implied']}%). "
        )
    else:
        analysis += (
            f"Nessun value bet netto rilevato. "
            f"Confidenza più alta su **{best['label']}** ({best['prob']}%). "
        )

    if markets["over"] > 60:
        analysis += "Alta probabilità di partita con molti gol (O2.5). "
    if markets["gg"] > 65:
        analysis += "Entrambe le squadre sono favorite a segnare (GG). "

    return best, candidates, analysis


# ─────────────────────────────────────────────
#  PRE-SCREENING (zero chiamate API)
# ─────────────────────────────────────────────
def prescreening_score(fixture: dict, league_name: str) -> float:
    score = 0.5
    league_weights = {
        "Serie A 🇮🇹": 0.05, "Premier League 🏴󠁧󠁢󠁥󠁮󠁧󠁿": 0.08,
        "La Liga 🇪🇸": 0.07, "Bundesliga 🇩🇪": 0.04, "Ligue 1 🇫🇷": 0.03,
    }
    score += league_weights.get(league_name, 0.0)
    try:
        dt = datetime.fromisoformat(fixture["fixture"]["date"].replace("Z", "+00:00"))
        if 19 <= dt.hour <= 22:   score += 0.07
        elif 14 <= dt.hour <= 18: score += 0.04
        days_away = (dt.replace(tzinfo=None) - datetime.utcnow()).days
        if days_away == 0:   score += 0.10
        elif days_away == 1: score += 0.05
    except Exception:
        pass
    top_clubs = {
        "real madrid", "barcelona", "manchester city", "manchester united",
        "liverpool", "chelsea", "arsenal", "tottenham", "juventus", "inter",
        "milan", "napoli", "roma", "lazio", "psg", "paris", "bayern", "borussia",
        "atletico", "sevilla", "benfica", "porto", "ajax",
    }
    home = fixture["teams"]["home"]["name"].lower()
    away = fixture["teams"]["away"]["name"].lower()
    for club in top_clubs:
        if club in home or club in away:
            score += 0.10; break
    derby_pairs = [
        ("inter", "milan"), ("roma", "lazio"), ("juventus", "torino"),
        ("manchester city", "manchester united"), ("arsenal", "chelsea"),
        ("liverpool", "everton"), ("real", "atletico"), ("barcelona", "espanyol"),
        ("psg", "marseille"), ("paris", "marseille"),
    ]
    for a, b in derby_pairs:
        if (a in home and b in away) or (b in home and a in away):
            score += 0.15; break
    return min(round(score, 3), 1.0)


# ─────────────────────────────────────────────
#  API — football-data.org
# ─────────────────────────────────────────────
FD_LEAGUE_MAP = {135: "SA", 39: "PL", 140: "PD", 78: "BL1", 61: "FL1"}
FD_BASE = "https://api.football-data.org/v4"

def _af_headers(key: str) -> dict:
    return {"X-Auth-Token": key}

def get_fixtures(key: str, league_id: int, season: int,
                 from_date: str, to_date: str) -> list:
    fd_code = FD_LEAGUE_MAP.get(league_id)
    if not fd_code: return []
    r = requests.get(
        f"{FD_BASE}/competitions/{fd_code}/matches",
        headers=_af_headers(key),
        params={"dateFrom": from_date, "dateTo": to_date, "status": "SCHEDULED,TIMED"},
        timeout=15,
    )
    r.raise_for_status()
    result = []
    for m in r.json().get("matches", []):
        result.append({
            "fixture": {"id": m["id"], "date": m["utcDate"], "status": {"short": "NS"}},
            "teams": {
                "home": {"id": m["homeTeam"]["id"], "name": m["homeTeam"]["name"]},
                "away": {"id": m["awayTeam"]["id"], "name": m["awayTeam"]["name"]},
            },
            "goals": {"home": None, "away": None},
        })
    return result

def get_last_matches(key: str, team_id: int, last: int = 10) -> list:
    r = requests.get(
        f"{FD_BASE}/teams/{team_id}/matches",
        headers=_af_headers(key),
        params={"status": "FINISHED", "limit": last},
        timeout=15,
    )
    r.raise_for_status()
    result = []
    for m in r.json().get("matches", []):
        hg = m.get("score", {}).get("fullTime", {}).get("home")
        ag = m.get("score", {}).get("fullTime", {}).get("away")
        result.append({
            "fixture": {"id": m["id"], "date": m["utcDate"], "status": {"short": "FT"}},
            "teams": {
                "home": {"id": m["homeTeam"]["id"], "name": m["homeTeam"]["name"]},
                "away": {"id": m["awayTeam"]["id"], "name": m["awayTeam"]["name"]},
            },
            "goals": {"home": hg, "away": ag},
        })
    return result


# ─────────────────────────────────────────────
#  API — The Odds API
# ─────────────────────────────────────────────
def _average_odd(bookmakers: list, key_path: list, preferred: list) -> float:
    values = []
    bm_map = {bm["key"]: bm for bm in bookmakers}
    ordered = ([bm_map[k] for k in preferred if k in bm_map] +
               [bm for k, bm in bm_map.items() if k not in preferred])
    for bm in ordered[:6]:
        for market in bm.get("markets", []):
            if market["key"] == key_path[0]:
                for outcome in market.get("outcomes", []):
                    if outcome["name"] == key_path[1]:
                        try: values.append(float(outcome["price"]))
                        except (ValueError, TypeError): pass
    return round(sum(values) / len(values), 3) if values else 0.0

def get_odds_theoddsapi(key: str, sport_key: str, home_team: str,
                        away_team: str, match_date: str) -> dict:
    r = requests.get(
        f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/",
        params={"apiKey": key, "regions": "eu", "markets": "h2h,totals,btts",
                "oddsFormat": "decimal", "dateFormat": "iso"},
        timeout=15,
    )
    r.raise_for_status()
    events      = r.json()
    target_date = datetime.fromisoformat(match_date.replace("Z", "+00:00"))
    best_event  = None
    for ev in events:
        ev_home = ev.get("home_team", "").lower()
        ev_away = ev.get("away_team", "").lower()
        if ((home_team[:5].lower() in ev_home or ev_home[:5] in home_team.lower()) and
                (away_team[:5].lower() in ev_away or ev_away[:5] in away_team.lower())):
            try:
                ev_date = datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
                if abs((ev_date - target_date).total_seconds()) < 86400:
                    best_event = ev; break
            except Exception:
                continue
    if not best_event: return {}
    bm           = best_event.get("bookmakers", [])
    ev_home_name = best_event.get("home_team", home_team)
    ev_away_name = best_event.get("away_team", away_team)
    result = {}
    for k, name in [("home", ev_home_name), ("draw", "Draw"), ("away", ev_away_name)]:
        v = _average_odd(bm, ["h2h", name], PREFERRED_BOOKMAKERS)
        if v: result[k] = v
    for k, name in [("over25", "Over"), ("under25", "Under")]:
        v = _average_odd(bm, ["totals", name], PREFERRED_BOOKMAKERS)
        if v: result[k] = v
    for k, name in [("gg", "Yes"), ("nogg", "No")]:
        v = _average_odd(bm, ["btts", name], PREFERRED_BOOKMAKERS)
        if v: result[k] = v
    return result

def get_odds_apifootball(key: str, fixture_id: int) -> dict:
    r = requests.get(
        "https://v3.football.api-sports.io/odds",
        headers=_af_headers(key),
        params={"fixture": fixture_id, "bookmaker": 8},
        timeout=15,
    )
    r.raise_for_status()
    resp = r.json().get("response", [])
    if not resp: return {}
    result = {}
    for bm in resp[0].get("bookmakers", []):
        for bet in bm.get("bets", []):
            name = bet.get("name", "")
            vals = {v["value"]: float(v["odd"]) for v in bet.get("values", [])}
            if name == "Match Winner":
                result["home"] = vals.get("Home", 0)
                result["draw"] = vals.get("Draw", 0)
                result["away"] = vals.get("Away", 0)
            elif "Goals Over/Under" in name and "2.5" in name:
                result["over25"]  = vals.get("Over", 0)
                result["under25"] = vals.get("Under", 0)
            elif name == "Both Teams Score":
                result["gg"]   = vals.get("Yes", 0)
                result["nogg"] = vals.get("No", 0)
    return result

def get_best_odds(af_key: str, odds_key: str, fixture: dict,
                  league_name: str) -> tuple[dict, str]:
    home_name  = fixture["teams"]["home"]["name"]
    away_name  = fixture["teams"]["away"]["name"]
    match_date = fixture["fixture"]["date"]
    fix_id     = fixture["fixture"]["id"]
    sport_key  = LEAGUES[league_name]["odds_key"]
    if odds_key:
        try:
            odds = get_odds_theoddsapi(odds_key, sport_key, home_name, away_name, match_date)
            if odds: return odds, "The Odds API"
        except Exception: pass
    try:
        odds = get_odds_apifootball(af_key, fix_id)
        if odds: return odds, "API-Football / Bet365"
    except Exception: pass
    return {}, "—"


# ─────────────────────────────────────────────
#  STATISTICHE
# ─────────────────────────────────────────────
def extract_form(matches: list, team_id: int) -> list:
    form = []
    for m in sorted(matches, key=lambda x: x["fixture"]["date"]):
        is_home = team_id == m["teams"]["home"]["id"]
        hg = m["goals"]["home"] or 0
        ag = m["goals"]["away"] or 0
        gs = hg if is_home else ag
        gc = ag if is_home else hg
        form.append("W" if gs > gc else ("L" if gs < gc else "D"))
    return form

def goals_avg_from_matches(matches: list, team_id: int, is_home: bool) -> tuple[float, float]:
    scored, conceded = [], []
    for m in matches:
        home_id = m["teams"]["home"]["id"]
        hg, ag  = m["goals"]["home"], m["goals"]["away"]
        if hg is None or ag is None: continue
        if is_home and team_id == home_id:
            scored.append(hg); conceded.append(ag)
        elif not is_home and team_id != home_id:
            scored.append(ag); conceded.append(hg)
    avg = lambda lst: sum(lst) / len(lst) if lst else 1.35
    return avg(scored), avg(conceded)


# ─────────────────────────────────────────────
#  ANALISI COMPLETA (cacheata)
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_and_analyze(af_key: str, odds_key: str, fixture: dict,
                      league_id: int, league_name: str, season: int) -> dict:
    team_h = fixture["teams"]["home"]["id"]
    team_a = fixture["teams"]["away"]["id"]
    last_h = get_last_matches(af_key, team_h, last=10)
    last_a = get_last_matches(af_key, team_a, last=10)
    odds, odds_source = get_best_odds(af_key, odds_key, fixture, league_name)
    form_raw_h = extract_form(last_h, team_h)
    form_raw_a = extract_form(last_a, team_a)
    form_h = compute_form_weight(form_raw_h)
    form_a = compute_form_weight(form_raw_a)
    h_sc, h_cc = goals_avg_from_matches(last_h, team_h, is_home=True)
    a_sc, a_cc = goals_avg_from_matches(last_a, team_a, is_home=False)
    league_avg = (h_sc + a_sc) / 2 or 1.35
    att_h = h_sc / league_avg;  def_a = a_cc / league_avg
    att_a = a_sc / league_avg;  def_h = h_cc / league_avg
    lam_h = round(max(att_h * def_a * league_avg * form_h, 0.1), 3)
    lam_a = round(max(att_a * def_h * league_avg * form_a, 0.1), 3)
    matrix  = build_score_matrix(lam_h, lam_a)
    markets = compute_markets(matrix)
    best, candidates, analysis = best_suggestion(markets, odds, form_h, form_a, lam_h, lam_a)
    try:
        kickoff = datetime.fromisoformat(
            fixture["fixture"]["date"].replace("Z", "+00:00")
        ).strftime("%d/%m %H:%M")
    except Exception:
        kickoff = fixture["fixture"]["date"][:16]
    return {
        "match": fixture, "league_name": league_name, "kickoff": kickoff,
        "lam_home": lam_h, "lam_away": lam_a,
        "markets": markets, "odds": odds, "odds_source": odds_source,
        "best": best, "candidates": candidates, "analysis": analysis,
        "form_home": form_h, "form_away": form_a,
        "form_raw_home": form_raw_h, "form_raw_away": form_raw_a,
    }

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_fixtures_cached(key: str, league_id: int, season: int,
                          from_date: str, to_date: str) -> list:
    return get_fixtures(key, league_id, season, from_date, to_date)


# ─────────────────────────────────────────────
#  HELPER UI
# ─────────────────────────────────────────────
def form_dots_html(form: list) -> str:
    cls = {"W": "dot-w", "D": "dot-d", "L": "dot-l"}
    return " ".join(f'<span class="{cls.get(r,"dot-d")}"></span>' for r in form[-6:])

def conf_class(c: float) -> str:
    return "conf-high" if c >= 65 else ("conf-mid" if c >= 48 else "conf-low")

def odd_box_html(label: str, value, hl: bool = False) -> str:
    cls = "odd-box-hl" if hl else "odd-box"
    vcl = "odd-val-hl" if hl else "odd-val"
    v   = f"{value:.2f}" if isinstance(value, float) and value > 0 else "—"
    return (f'<div class="{cls}"><span class="odd-lbl">{label}</span>'
            f'<span class="{vcl}">{v}</span></div>')

def progress_bar_html(prob: float, color: str) -> str:
    return (f'<div class="prog-bar-wrap">'
            f'<div class="prog-bar-fill" style="width:{min(prob,100)}%;background:{color};"></div>'
            f'</div>')

def key_status_html(loaded: bool, label: str, source: str = "") -> str:
    if loaded:
        return (f'<div class="key-ok"><span style="font-family:var(--font-mono);'
                f'font-size:0.63rem;color:var(--green);letter-spacing:0.1em;">✓ {label}</span><br>'
                f'<span style="font-family:var(--font-mono);font-size:0.68rem;'
                f'color:var(--muted);">{source}</span></div>')
    return (f'<div class="key-mis"><span style="font-family:var(--font-mono);'
            f'font-size:0.63rem;color:var(--red);letter-spacing:0.1em;">✗ {label}</span><br>'
            f'<span style="font-family:var(--font-mono);font-size:0.68rem;'
            f'color:var(--muted);">Non configurata</span></div>')


# ─────────────────────────────────────────────
#  RIEPILOGO RAPIDO
# ─────────────────────────────────────────────
def render_recap(analysis_results: dict):
    rows = sorted(analysis_results.values(), key=lambda x: x["kickoff"])
    if not rows:
        return

    with st.expander("⚡  Riepilogo — tutte le partite analizzate", expanded=True):
        st.markdown(
            '<div style="font-family:var(--font-mono);font-size:0.56rem;'
            'color:var(--muted);letter-spacing:0.16em;margin-bottom:12px;">'
            'SCEGLI LA TUA GIOCATA IN UN COLPO D\'OCCHIO</div>',
            unsafe_allow_html=True
        )
        rows_html = ""
        for r in rows:
            home    = r["match"]["teams"]["home"]["name"]
            away    = r["match"]["teams"]["away"]["name"]
            kickoff = r["kickoff"]
            best    = r["best"]
            league  = r["league_name"]

            if best is None:
                rows_html += f"""
                <tr>
                    <td style="color:var(--muted);font-family:var(--font-mono);
                               font-size:0.68rem;white-space:nowrap;">{kickoff}</td>
                    <td>
                        <span class="recap-match">{home}</span>
                        <span style="color:var(--muted);font-size:0.7rem;"> vs </span>
                        <span class="recap-match">{away}</span>
                        <br><span style="font-size:0.64rem;color:var(--muted);">{league}</span>
                    </td>
                    <td><span class="no-odds-badge">NO QUOTE</span></td>
                    <td colspan="3" style="color:var(--muted);font-size:0.7rem;
                                           font-style:italic;">Nessun consiglio</td>
                </tr>"""
                continue

            conf      = best["prob"]
            cc_css    = ("var(--green)" if conf >= 65 else
                         ("var(--yellow)" if conf >= 48 else "var(--red)"))
            edge      = best["edge"]
            edge_col  = "var(--green)" if edge > 0 else ("var(--red)" if edge < 0 else "var(--muted)")
            edge_str  = f"{'+' if edge > 0 else ''}{edge:.1f}pp"
            quota_str = f"x{best['odd']:.2f}" if best["odd"] > 0 else "—"
            vb_html   = '&nbsp;<span class="value-tag">VALUE</span>' if best["value"] else ""

            rows_html += f"""
            <tr>
                <td style="color:var(--muted);font-family:var(--font-mono);
                           font-size:0.68rem;white-space:nowrap;">{kickoff}</td>
                <td>
                    <span class="recap-match">{home}</span>
                    <span style="color:var(--muted);font-size:0.7rem;"> vs </span>
                    <span class="recap-match">{away}</span>
                    <br><span style="font-size:0.64rem;color:var(--muted);">{league}</span>
                </td>
                <td style="font-family:var(--font-mono);font-weight:700;
                           font-size:0.92rem;color:{cc_css};">
                    {best['label']}{vb_html}
                </td>
                <td style="font-family:var(--font-mono);font-size:0.76rem;
                           color:{cc_css};font-weight:700;">{conf}%</td>
                <td style="font-family:var(--font-mono);font-size:0.76rem;
                           color:rgba(255,255,255,0.55);">{quota_str}</td>
                <td style="font-family:var(--font-mono);font-size:0.76rem;
                           color:{edge_col};font-weight:600;">{edge_str}</td>
            </tr>"""

        st.markdown(f"""
        <div class="stat-box" style="padding:12px 14px;overflow-x:auto;">
            <table class="recap-table">
                <thead>
                    <tr>
                        <th>ORA</th><th>PARTITA</th><th>PICK</th>
                        <th>CONF.</th><th>QUOTA</th><th>EDGE</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  PANNELLO DETTAGLIO
# ─────────────────────────────────────────────
def render_detail_panel(result: dict):
    m          = result["match"]
    home       = m["teams"]["home"]["name"]
    away       = m["teams"]["away"]["name"]
    markets    = result["markets"]
    odds       = result["odds"]
    lam_h      = result["lam_home"]
    lam_a      = result["lam_away"]
    best       = result["best"]
    cands      = result["candidates"]
    analysis   = result["analysis"]
    form_raw_h = result["form_raw_home"]
    form_raw_a = result["form_raw_away"]
    odds_src   = result.get("odds_source", "—")

    # Header
    st.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">PARTITA</div>
        <div class="team-name">{home}
            <span style="color:var(--muted);font-size:0.9rem;font-weight:400;"> vs </span>
            {away}
        </div>
        <div style="margin-top:5px;">
            <span class="league-badge">{result['league_name']} · {result['kickoff']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Forma
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f'<div class="stat-box"><div class="stat-label">{home.upper()} — FORMA</div>'
            f'{form_dots_html(form_raw_h)}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(
            f'<div class="stat-box"><div class="stat-label">{away.upper()} — FORMA</div>'
            f'{form_dots_html(form_raw_a)}</div>', unsafe_allow_html=True)

    # Gol attesi
    st.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">GOL ATTESI (POISSON)</div>
        <div style="display:flex;justify-content:space-around;align-items:center;padding-top:6px;">
            <div style="text-align:center;">
                <div class="xg-label">{home.upper()}</div>
                <div class="xg-num-home">{lam_h:.2f}</div>
            </div>
            <div style="color:var(--muted);font-size:1.3rem;font-family:var(--font-mono);">—</div>
            <div style="text-align:center;">
                <div class="xg-label">{away.upper()}</div>
                <div class="xg-num-away">{lam_a:.2f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Mercati
    market_rows = [
        ("Vittoria Casa (1)",   markets["p1"],    "#0a84ff"),
        ("Pareggio (X)",        markets["px"],    "#8b5cf6"),
        ("Vittoria Ospiti (2)", markets["p2"],    "#ff375f"),
        ("Over 2.5",            markets["over"],  "#34c759"),
        ("Under 2.5",           markets["under"], "#636366"),
        ("GG",                  markets["gg"],    "#30d158"),
        ("NoGG",                markets["nogg"],  "#ff9f0a"),
    ]
    rows_html = ""
    for label, prob, color in market_rows:
        rows_html += f"""
        <div style="margin-bottom:9px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
                <span style="font-family:var(--font-ui);font-size:0.78rem;
                             color:rgba(255,255,255,0.5);">{label}</span>
                <span style="font-family:var(--font-mono);font-size:0.78rem;
                             font-weight:700;color:{color};">{prob}%</span>
            </div>
            {progress_bar_html(prob, color)}
        </div>"""
    st.markdown(
        f'<div class="stat-box"><div class="stat-label">PROBABILITÀ MERCATI</div>'
        f'{rows_html}</div>', unsafe_allow_html=True)

    # Quote + edge analysis (solo con dati di mercato)
    if odds and best is not None:
        boxes = (
            odd_box_html("1",    odds.get("home",    0), best["label"] == "1")  +
            odd_box_html("X",    odds.get("draw",    0), best["label"] == "X")  +
            odd_box_html("2",    odds.get("away",    0), best["label"] == "2")  +
            odd_box_html("O2.5", odds.get("over25",  0), markets["over"]  > 60) +
            odd_box_html("U2.5", odds.get("under25", 0))                        +
            odd_box_html("GG",   odds.get("gg",      0), markets["gg"]    > 60) +
            odd_box_html("NoGG", odds.get("nogg",    0))
        )
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">QUOTE — {odds_src.upper()}</div>
            <div style="display:flex;flex-wrap:wrap;">{boxes}</div>
        </div>
        """, unsafe_allow_html=True)

        edge_rows = ""
        for c in cands:
            if c["odd"] <= 0: continue
            ecol = "var(--green)" if c["edge"] > 0 else ("var(--red)" if c["edge"] < 0 else "var(--muted)")
            vb   = "🟢" if c["value"] else "⚪"
            edge_rows += f"""
            <tr>
                <td style="padding:5px 8px;font-family:var(--font-ui);font-size:0.76rem;
                           color:rgba(255,255,255,0.72);">{vb} {c['label']}</td>
                <td style="padding:5px 8px;font-family:var(--font-mono);font-size:0.74rem;
                           color:rgba(255,255,255,0.5);text-align:center;">{c['prob']}%</td>
                <td style="padding:5px 8px;font-family:var(--font-mono);font-size:0.74rem;
                           color:rgba(255,255,255,0.5);text-align:center;">{c['implied']}%</td>
                <td style="padding:5px 8px;font-family:var(--font-mono);font-size:0.74rem;
                           color:{ecol};text-align:center;font-weight:700;">
                    {'+' if c['edge']>0 else ''}{c['edge']}pp</td>
                <td style="padding:5px 8px;font-family:var(--font-mono);font-size:0.74rem;
                           color:rgba(255,255,255,0.5);text-align:right;">x{c['odd']:.2f}</td>
            </tr>"""

        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">EDGE ANALYSIS — POISSON VS QUOTA</div>
            <table style="width:100%;border-collapse:collapse;">
                <thead>
                    <tr style="border-bottom:1px solid var(--border);">
                        <th style="padding:5px 8px;font-family:var(--font-mono);font-size:0.56rem;
                                   color:var(--muted);font-weight:400;text-align:left;">MERCATO</th>
                        <th style="padding:5px 8px;font-family:var(--font-mono);font-size:0.56rem;
                                   color:var(--muted);font-weight:400;text-align:center;">PROB.</th>
                        <th style="padding:5px 8px;font-family:var(--font-mono);font-size:0.56rem;
                                   color:var(--muted);font-weight:400;text-align:center;">IMPL.</th>
                        <th style="padding:5px 8px;font-family:var(--font-mono);font-size:0.56rem;
                                   color:var(--muted);font-weight:400;text-align:center;">EDGE</th>
                        <th style="padding:5px 8px;font-family:var(--font-mono);font-size:0.56rem;
                                   color:var(--muted);font-weight:400;text-align:right;">QUOTA</th>
                    </tr>
                </thead>
                <tbody>{edge_rows}</tbody>
            </table>
        </div>
        """, unsafe_allow_html=True)

    # Consiglio principale — SOLO con quote
    if best is not None:
        conf     = best["prob"]
        cc       = conf_class(conf)
        conf_col = "#34c759" if conf >= 65 else ("#ffd60a" if conf >= 48 else "#ff453a")
        ev_col   = "#34c759" if best["ev"] > 0 else "#ff453a"
        ev_sign  = "+" if best["ev"] > 0 else ""
        ev_val   = f"{ev_sign}{best['ev']:.3f}"

        st.markdown(
            '<div class="stat-box" style="border-color:rgba(52,199,89,0.22);padding-bottom:6px;">'
            '<div class="stat-label">CONSIGLIO PRINCIPALE</div></div>',
            unsafe_allow_html=True)

        col_label, col_conf, col_quota, col_ev = st.columns([1, 2, 2, 2])
        with col_label:
            st.markdown(f'<div class="{cc}" style="margin-top:4px;">{best["label"]}</div>',
                        unsafe_allow_html=True)
        with col_conf:
            st.markdown(
                f'<div style="font-family:var(--font-mono);">'
                f'<div style="font-size:0.58rem;color:var(--muted);margin-bottom:2px;">CONFIDENZA</div>'
                f'<div style="font-size:1.05rem;font-weight:700;color:{conf_col};">{conf}%</div>'
                f'</div>', unsafe_allow_html=True)
        with col_quota:
            if best["odd"] > 0:
                st.markdown(
                    f'<div style="font-family:var(--font-mono);">'
                    f'<div style="font-size:0.58rem;color:var(--muted);margin-bottom:2px;">QUOTA</div>'
                    f'<div style="font-size:1.05rem;font-weight:700;'
                    f'color:rgba(255,255,255,0.82);">x{best["odd"]:.2f}</div>'
                    f'</div>', unsafe_allow_html=True)
        with col_ev:
            if best["odd"] > 0:
                st.markdown(
                    f'<div style="font-family:var(--font-mono);">'
                    f'<div style="font-size:0.58rem;color:var(--muted);margin-bottom:2px;">EV</div>'
                    f'<div style="font-size:1.05rem;font-weight:700;color:{ev_col};">{ev_val}</div>'
                    f'</div>', unsafe_allow_html=True)

        if best["value"]:
            st.markdown('<span class="value-tag">✦ VALUE BET</span>', unsafe_allow_html=True)

    # Analisi testuale — markdown nativo (bold **..** funziona correttamente)
    st.markdown(
        '<div class="stat-box" style="margin-top:10px;"><div class="stat-label">ANALISI</div></div>',
        unsafe_allow_html=True)
    st.markdown(analysis)


# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="margin-bottom:22px;">
        <div class="main-title" style="font-size:1.35rem;">donny</div>
        <div class="main-subtitle">Football Intelligence</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="stat-label" style="margin-bottom:5px;">FOOTBALL-DATA.ORG KEY</div>',
                unsafe_allow_html=True)
    st.markdown(key_status_html(bool(_env_af), "CHIAVE CARICATA", "da .env / Secrets"),
                unsafe_allow_html=True)
    if _env_af:
        _ov_af  = st.text_input("Override FD key", type="password",
                                placeholder="Lascia vuoto per usare quella caricata",
                                label_visibility="collapsed")
        api_key = _ov_af.strip() if _ov_af.strip() else _env_af
    else:
        api_key = st.text_input("Football-Data.org key", type="password",
                                placeholder="Incolla la tua chiave...",
                                label_visibility="collapsed")

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

    st.markdown('<div class="stat-label" style="margin-bottom:5px;">THE ODDS API KEY</div>',
                unsafe_allow_html=True)
    st.markdown(key_status_html(bool(_env_odds), "CHIAVE CARICATA", "da .env / Secrets"),
                unsafe_allow_html=True)
    if _env_odds:
        _ov_odds = st.text_input("Override Odds key", type="password",
                                 placeholder="Lascia vuoto per usare quella caricata",
                                 label_visibility="collapsed")
        odds_key = _ov_odds.strip() if _ov_odds.strip() else _env_odds
    else:
        odds_key = st.text_input("The Odds API key", type="password",
                                 placeholder="Opzionale — migliora le quote",
                                 label_visibility="collapsed")

    if not odds_key:
        st.markdown(
            '<div class="warn-box" style="margin-top:4px;font-size:0.74rem;">'
            '⚠ Senza Odds API le quote vengono cercate su API-Football (Bet365). '
            'Partite senza quote non ricevono consigli.</div>',
            unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="stat-label" style="margin-bottom:7px;">CAMPIONATI</div>',
                unsafe_allow_html=True)
    selected_leagues = st.multiselect(
        "Campionati", options=list(LEAGUES.keys()),
        default=list(LEAGUES.keys()), label_visibility="collapsed")

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="stat-label" style="margin-bottom:7px;">SOGLIA AUTO-ANALISI</div>',
                unsafe_allow_html=True)
    threshold = st.slider(
        "Soglia", min_value=0.40, max_value=0.90,
        value=PRESCREENING_THRESHOLD, step=0.05,
        label_visibility="collapsed",
        help="Partite sopra soglia vengono analizzate automaticamente")

    odds_mode = "The Odds API" if odds_key else "API-Football / Bet365"
    st.markdown(f"""
    <div style="font-family:var(--font-mono);font-size:0.54rem;color:var(--muted);
                line-height:2;letter-spacing:0.08em;margin-top:14px;">
    MODELLO: POISSON + FORMA<br>
    QUOTE: {odds_mode.upper()}<br>
    STAGIONE: {CURRENT_SEASON}/{CURRENT_SEASON+1}<br>
    FINESTRA: OGGI + 2 GIORNI<br>
    SOGLIA: {threshold:.2f}<br>
    ⚠ Stime statistiche, non garanzie
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:30px;">
    <div class="main-title">Donny — Football Intelligence</div>
    <div class="main-subtitle">Analisi Predittiva · Poisson · Forma Recente · Value Bet</div>
</div>
""", unsafe_allow_html=True)

if not api_key:
    st.markdown("""
    <div class="info-box">
        🔑 Inserisci la tua <strong>Football-Data.org key</strong> nella sidebar per iniziare.<br>
        Piano gratuito disponibile su <strong>football-data.org</strong> (10 req/min).<br><br>
        Opzionale: <strong>The Odds API key</strong> su <strong>the-odds-api.com</strong>
        (500 req/mese free) per quote aggregate da più bookmaker EU.<br>
        <strong>Senza quote Donny non emette consigli di giocata.</strong>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

if not selected_leagues:
    st.warning("Seleziona almeno un campionato nella sidebar.")
    st.stop()


# ─────────────────────────────────────────────
#  CARICA FIXTURE (finestra 2 giorni)
# ─────────────────────────────────────────────
today    = datetime.now()
end_date = today + timedelta(days=2)
from_str = today.strftime("%Y-%m-%d")
to_str   = end_date.strftime("%Y-%m-%d")

odds_src_label = "The Odds API (media EU)" if odds_key else "API-Football / Bet365"
st.markdown(f"""
<div class="info-box">
    📅 <strong>{today.strftime('%d/%m/%Y')}</strong> → <strong>{end_date.strftime('%d/%m/%Y')}</strong>
    &nbsp;·&nbsp; {len(selected_leagues)} campionati &nbsp;·&nbsp;
    Quote: <strong>{odds_src_label}</strong>
</div>
""", unsafe_allow_html=True)

col_load, _ = st.columns([1, 3])
with col_load:
    load_btn = st.button("⚽  CARICA PARTITE", key="load")

if "fixtures_by_league" not in st.session_state:
    st.session_state["fixtures_by_league"] = {}

if load_btn:
    st.session_state["fixtures_by_league"] = {}
    st.session_state.pop("analysis_results", None)
    st.session_state.pop("prescreening_done", None)
    with st.spinner("Recupero partite..."):
        for lg in selected_leagues:
            try:
                fxs = fetch_fixtures_cached(api_key, LEAGUES[lg]["id"], CURRENT_SEASON, from_str, to_str)
                st.session_state["fixtures_by_league"][lg] = fxs
            except Exception as e:
                err = str(e)
                if "403" in err:   st.error(f"❌ {lg}: chiave non valida (403).")
                elif "401" in err: st.error(f"❌ {lg}: non autorizzata (401).")
                elif "429" in err: st.error(f"❌ {lg}: limite raggiunto (429). Riprova domani.")
                else:              st.error(f"❌ {lg}: {e}")

fixtures_map = st.session_state.get("fixtures_by_league", {})
all_fixtures = [(lg, f) for lg, fxs in fixtures_map.items() for f in fxs]

if not all_fixtures:
    if load_btn:
        st.warning("Nessuna partita trovata nella finestra selezionata.")
    st.stop()


# ─────────────────────────────────────────────
#  PRE-SCREENING + AUTO-ANALISI
# ─────────────────────────────────────────────
if "analysis_results"   not in st.session_state: st.session_state["analysis_results"]   = {}
if "prescreening_done"  not in st.session_state: st.session_state["prescreening_done"]  = False

prescreened = [(lg, f, prescreening_score(f, lg)) for lg, f in all_fixtures]

to_auto = [
    (lg, f) for lg, f, score in prescreened
    if score >= threshold and f["fixture"]["id"] not in st.session_state["analysis_results"]
]

if to_auto and not st.session_state["prescreening_done"]:
    with st.spinner(f"Analisi automatica di {len(to_auto)} partite..."):
        prog = st.progress(0)
        for i, (lg, f) in enumerate(to_auto):
            try:
                res = fetch_and_analyze(api_key, odds_key, f, LEAGUES[lg]["id"], lg, CURRENT_SEASON)
                st.session_state["analysis_results"][f["fixture"]["id"]] = res
            except Exception:
                pass
            prog.progress((i + 1) / len(to_auto))
        prog.empty()
    st.session_state["prescreening_done"] = True
    st.rerun()


# ─────────────────────────────────────────────
#  RIEPILOGO RAPIDO (in cima)
# ─────────────────────────────────────────────
if st.session_state["analysis_results"]:
    render_recap(st.session_state["analysis_results"])
    st.markdown('<hr class="divider">', unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  LISTA PARTITE PER GIORNO
# ─────────────────────────────────────────────
st.markdown('<div class="stat-label" style="margin-bottom:10px;">PARTITE DISPONIBILI</div>',
            unsafe_allow_html=True)

by_day = defaultdict(list)
for lg, f, score in prescreened:
    try:
        day = datetime.fromisoformat(f["fixture"]["date"].replace("Z", "+00:00")).strftime("%A %d %B")
    except Exception:
        day = f["fixture"]["date"][:10]
    by_day[day].append((lg, f, score))

selected_day = st.selectbox("Giorno", list(by_day.keys()), label_visibility="collapsed")
day_fixtures = by_day.get(selected_day, [])
n_auto_today = sum(1 for _, f, s in day_fixtures if s >= threshold)

st.markdown(
    f'<div style="font-family:var(--font-mono);font-size:0.6rem;color:var(--muted);'
    f'letter-spacing:0.12em;margin-bottom:12px;">'
    f'{len(day_fixtures)} PARTITE · {selected_day.upper()} · {n_auto_today} AUTO-ANALIZZATE</div>',
    unsafe_allow_html=True)

for lg, f, pre_score in day_fixtures:
    fix_id      = f["fixture"]["id"]
    home        = f["teams"]["home"]["name"]
    away        = f["teams"]["away"]["name"]
    lcolor      = LEAGUES[lg]["color"]
    is_analyzed = fix_id in st.session_state["analysis_results"]
    is_auto     = pre_score >= threshold
    card_cls    = "match-card-selected" if is_analyzed else "match-card"

    try:
        kickoff = datetime.fromisoformat(
            f["fixture"]["date"].replace("Z", "+00:00")).strftime("%H:%M")
    except Exception:
        kickoff = "??:??"

    if is_analyzed and is_auto:
        badge_html = '<span class="auto-badge">AUTO-ANALIZZATA</span>'
    elif is_auto:
        badge_html = '<span class="prescreened-badge">PRESCREENED</span>'
    else:
        badge_html = (f'<span style="font-family:var(--font-mono);font-size:0.54rem;'
                      f'color:var(--muted);">score {pre_score:.2f}</span>')

    # Card statica
    st.markdown(f"""
    <div class="{card_cls}">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap;">
            <div style="width:7px;height:7px;border-radius:50%;background:{lcolor};
                        box-shadow:0 0 6px {lcolor}99;flex-shrink:0;"></div>
            <span class="league-badge">{lg} · {kickoff}</span>
            <span style="margin-left:auto;">{badge_html}</span>
        </div>
        <div style="display:flex;align-items:center;justify-content:space-between;">
            <div class="team-name">{home}</div>
            <div style="font-family:var(--font-mono);font-size:0.7rem;
                        color:var(--muted);padding:0 12px;">VS</div>
            <div class="team-name" style="text-align:right;">{away}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Risultato analisi (separato — nessun HTML annidato dinamico)
    if is_analyzed:
        res  = st.session_state["analysis_results"][fix_id]
        best = res["best"]
        if best is not None:
            conf     = best["prob"]
            cc       = conf_class(conf)
            conf_col = "#34c759" if conf >= 65 else ("#ffd60a" if conf >= 48 else "#ff453a")
            vb_tag   = '<span class="value-tag">VALUE BET</span>' if best["value"] else ""
            src      = res.get("odds_source", "")
            src_span = (f'<span style="font-family:var(--font-mono);font-size:0.56rem;'
                        f'color:var(--muted);">{src}</span>') if src else ""
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:12px;'
                f'margin:-6px 0 8px 0;padding:0 2px;flex-wrap:wrap;">'
                f'<div class="{cc}">{best["label"]}</div>'
                f'<div style="font-family:var(--font-mono);font-size:0.68rem;'
                f'color:{conf_col};">{conf}% confidenza</div>'
                f'{vb_tag}&nbsp;{src_span}</div>',
                unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="margin:-6px 0 8px 0;padding:0 2px;">'
                '<span class="no-odds-badge">NESSUN CONSIGLIO — QUOTE ASSENTI</span>'
                '</div>',
                unsafe_allow_html=True)

    col_btn, _ = st.columns([1, 4])
    with col_btn:
        btn_label = "🔄 RIANALIZZA" if is_analyzed else "🔍 ANALIZZA"
        if st.button(btn_label, key=f"analyze_{fix_id}"):
            with st.spinner(f"Analisi {home} vs {away}..."):
                try:
                    res = fetch_and_analyze(
                        api_key, odds_key, f, LEAGUES[lg]["id"], lg, CURRENT_SEASON)
                    st.session_state["analysis_results"][fix_id] = res
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")

    if is_analyzed:
        with st.expander("📊 Dettaglio analisi", expanded=False):
            render_detail_panel(st.session_state["analysis_results"][fix_id])

    st.markdown('<div style="height:2px;"></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  FOOTER
# ─────────────────────────────────────────────
st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;font-family:var(--font-mono);font-size:0.52rem;
            color:rgba(255,255,255,0.1);letter-spacing:0.12em;padding-bottom:18px;">
DONNY — FOOTBALL INTELLIGENCE · POISSON + FORMA RECENTE<br>
DATI: FOOTBALL-DATA.ORG · QUOTE: THE ODDS API / BET365 · USO RESPONSABILE
</div>
""", unsafe_allow_html=True)