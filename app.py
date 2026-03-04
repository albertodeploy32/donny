import streamlit as st
import requests
import math
import os
from datetime import datetime, timedelta
from itertools import product
from collections import defaultdict

# ─────────────────────────────────────────────
#  CARICAMENTO CHIAVI API
#  Priorità: Streamlit Secrets → .env → input manuale
# ─────────────────────────────────────────────
def _load_keys() -> tuple[str, str]:
    """Ritorna (api_football_key, odds_api_key). Stringa vuota se non trovata."""
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

    af  = from_secrets("API_FOOTBALL_KEY")  or os.environ.get("API_FOOTBALL_KEY",  "")
    odd = from_secrets("ODDS_API_KEY")       or os.environ.get("ODDS_API_KEY",       "")
    return af.strip(), odd.strip()


_env_af, _env_odds = _load_keys()


# ─────────────────────────────────────────────
#  CONFIGURAZIONE PAGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Donny - Football Intelligence",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&family=DM+Mono:wght@400;500;700&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family:'DM Sans',sans-serif; background-color:#080b12!important; color:#e8eaf0!important; }
.stApp {
    background:#080b12!important;
    background-image:radial-gradient(ellipse 90% 40% at 50% -10%, rgba(20,50,110,0.35) 0%, transparent 65%)!important;
}
[data-testid="stSidebar"] { background:#0d1120!important; border-right:1px solid rgba(255,255,255,0.05)!important; }
[data-testid="stSidebar"] * { color:#e8eaf0!important; }

.main-title { font-family:'Playfair Display',serif; font-size:2.4rem; font-weight:800; letter-spacing:-0.02em; color:#f0f2f8; margin-bottom:0; }
.main-subtitle { font-family:'DM Mono',monospace; font-size:0.7rem; letter-spacing:0.18em; color:rgba(255,255,255,0.28); margin-top:4px; }

.match-card { background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07); border-radius:18px; padding:22px 24px; margin-bottom:14px; }
.match-card:hover { border:1px solid rgba(255,255,255,0.14); }
.match-card-selected { background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.18); border-radius:18px; padding:22px 24px; margin-bottom:14px; }

.league-badge { font-family:'DM Mono',monospace; font-size:0.65rem; letter-spacing:0.14em; color:rgba(255,255,255,0.35); text-transform:uppercase; }
.team-name { font-family:'Playfair Display',serif; font-size:1.25rem; font-weight:700; color:rgba(255,255,255,0.92); }

.conf-high { color:#4ade80; font-family:'DM Mono',monospace; font-weight:700; font-size:1.6rem; }
.conf-mid  { color:#facc15; font-family:'DM Mono',monospace; font-weight:700; font-size:1.6rem; }
.conf-low  { color:#f87171; font-family:'DM Mono',monospace; font-weight:700; font-size:1.6rem; }

.value-tag { display:inline-block; background:rgba(74,222,128,0.13); border:1px solid rgba(74,222,128,0.3); border-radius:20px; padding:2px 12px; font-family:'DM Mono',monospace; font-size:0.6rem; font-weight:700; letter-spacing:0.12em; color:#4ade80; }

.dot-w { display:inline-block; width:10px; height:10px; border-radius:50%; background:#4ade80; margin:0 2px; }
.dot-d { display:inline-block; width:10px; height:10px; border-radius:50%; background:#facc15; margin:0 2px; }
.dot-l { display:inline-block; width:10px; height:10px; border-radius:50%; background:#f87171; margin:0 2px; }

.stat-box { background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07); border-radius:14px; padding:16px 18px; margin-bottom:12px; }
.stat-label { font-family:'DM Mono',monospace; font-size:0.6rem; letter-spacing:0.14em; color:rgba(255,255,255,0.28); text-transform:uppercase; margin-bottom:10px; }

.odd-box    { display:inline-flex; flex-direction:column; align-items:center; background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.07); border-radius:10px; padding:8px 14px; margin:4px; min-width:58px; }
.odd-box-hl { display:inline-flex; flex-direction:column; align-items:center; background:rgba(74,222,128,0.10); border:1px solid rgba(74,222,128,0.3); border-radius:10px; padding:8px 14px; margin:4px; min-width:58px; }
.odd-lbl    { font-family:'DM Mono',monospace; font-size:0.6rem; color:rgba(255,255,255,0.35); letter-spacing:0.1em; }
.odd-val    { font-family:'DM Mono',monospace; font-size:0.95rem; font-weight:700; color:rgba(255,255,255,0.88); }
.odd-val-hl { font-family:'DM Mono',monospace; font-size:0.95rem; font-weight:700; color:#4ade80; }

.prog-bar-wrap { background:rgba(255,255,255,0.06); border-radius:4px; height:5px; margin-top:6px; }
.prog-bar-fill { height:5px; border-radius:4px; }

.divider { border:none; border-top:1px solid rgba(255,255,255,0.06); margin:18px 0; }

.stButton > button {
    background:rgba(255,255,255,0.06)!important; border:1px solid rgba(255,255,255,0.12)!important;
    color:rgba(255,255,255,0.85)!important; border-radius:12px!important;
    font-family:'DM Mono',monospace!important; font-size:0.75rem!important;
    letter-spacing:0.1em!important; padding:10px 22px!important; width:100%!important;
}
.stButton > button:hover { background:rgba(255,255,255,0.1)!important; border-color:rgba(255,255,255,0.22)!important; color:#fff!important; }

.stSelectbox>div>div, .stTextInput>div>div {
    background:rgba(255,255,255,0.04)!important; border:1px solid rgba(255,255,255,0.1)!important;
    border-radius:10px!important; color:#e8eaf0!important;
}
.stSpinner>div { border-top-color:#4ade80!important; }
#MainMenu { visibility:hidden; } footer { visibility:hidden; } header { visibility:hidden; }

.xg-num-home { font-family:'DM Mono',monospace; font-size:2.6rem; font-weight:800; color:#60a5fa; }
.xg-num-away { font-family:'DM Mono',monospace; font-size:2.6rem; font-weight:800; color:#f472b6; }
.xg-label    { font-family:'DM Mono',monospace; font-size:0.65rem; color:rgba(255,255,255,0.3); letter-spacing:0.12em; margin-bottom:4px; }

.info-box { background:rgba(96,165,250,0.08); border:1px solid rgba(96,165,250,0.2); border-radius:12px; padding:14px 18px; font-size:0.82rem; color:rgba(255,255,255,0.6); margin-bottom:16px; }
.warn-box { background:rgba(250,204,21,0.08); border:1px solid rgba(250,204,21,0.2); border-radius:12px; padding:14px 18px; font-size:0.82rem; color:rgba(255,255,255,0.6); margin-bottom:16px; }

.key-ok  { background:rgba(74,222,128,0.08); border:1px solid rgba(74,222,128,0.2); border-radius:10px; padding:10px 14px; margin-bottom:8px; }
.key-mis { background:rgba(248,113,113,0.08); border:1px solid rgba(248,113,113,0.2); border-radius:10px; padding:10px 14px; margin-bottom:8px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  COSTANTI
# ─────────────────────────────────────────────
LEAGUES = {
    "Serie A 🇮🇹":        {"id": 135, "color": "#0066cc", "odds_key": "soccer_italy_serie_a"},
    "Premier League 🏴󠁧󠁢󠁥󠁮󠁧󠁿": {"id": 39,  "color": "#3d195b", "odds_key": "soccer_epl"},
    "La Liga 🇪🇸":         {"id": 140, "color": "#ee0000", "odds_key": "soccer_spain_la_liga"},
    "Bundesliga 🇩🇪":      {"id": 78,  "color": "#d00027", "odds_key": "soccer_germany_bundesliga"},
    "Ligue 1 🇫🇷":         {"id": 61,  "color": "#004494", "odds_key": "soccer_france_ligue_one"},
}

CURRENT_SEASON = 2024
MAX_SCORELINE  = 6

# Bookmaker preferiti per The Odds API (ordine di priorità)
PREFERRED_BOOKMAKERS = ["pinnacle", "bet365", "williamhill", "unibet", "betfair"]


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
    p1   = sum(v for (gh, ga), v in matrix.items() if gh > ga)
    px   = sum(v for (gh, ga), v in matrix.items() if gh == ga)
    p2   = sum(v for (gh, ga), v in matrix.items() if gh < ga)
    po   = sum(v for (gh, ga), v in matrix.items() if gh + ga > 2)
    pgg  = sum(v for (gh, ga), v in matrix.items() if gh > 0 and ga > 0)
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
    """Probabilità implicita dalla quota (senza margine)."""
    return (1 / odd * 100) if odd > 0 else 0.0


def best_suggestion(markets: dict, odds: dict, form_h: float, form_a: float, lam_h: float, lam_a: float):
    candidates = []
    mapping = [
        ("1",    markets["p1"],   odds.get("home",    0)),
        ("X",    markets["px"],   odds.get("draw",    0)),
        ("2",    markets["p2"],   odds.get("away",    0)),
        ("O2.5", markets["over"], odds.get("over25",  0)),
        ("U2.5", markets["under"],odds.get("under25", 0)),
        ("GG",   markets["gg"],   odds.get("gg",      0)),
        ("NoGG", markets["nogg"], odds.get("nogg",    0)),
    ]
    for label, prob, odd in mapping:
        ev = (prob / 100) * odd - (1 - prob / 100) if odd > 0 else -999
        candidates.append({
            "label": label, "prob": prob, "odd": odd,
            "value": value_bet(prob, odd), "ev": round(ev, 4),
            "implied": round(implied_prob(odd), 1),
            "edge":    round(prob - implied_prob(odd), 1) if odd > 0 else 0,
        })
    candidates.sort(key=lambda x: (x["value"], x["ev"]), reverse=True)
    best = candidates[0]

    fh_str = "ottima" if form_h > 1.1 else "nella norma" if form_h >= 0.9 else "in calo"
    fa_str = "ottima" if form_a > 1.1 else "nella norma" if form_a >= 0.9 else "in calo"
    analysis = (
        f"Il modello Poisson stima {lam_h:.2f} gol attesi in casa e {lam_a:.2f} in trasferta. "
        f"La forma recente della squadra di casa è {fh_str} (×{form_h}), "
        f"quella degli ospiti è {fa_str} (×{form_a}). "
    )
    if best["value"]:
        edge = best["edge"]
        analysis += (
            f"La giocata **{best['label']}** mostra un edge positivo di {edge:.1f}pp "
            f"(prob. stimata {best['prob']}% vs prob. implicita quota {best['implied']}%). "
        )
    else:
        analysis += f"Nessun value bet netto rilevato; la giocata con confidenza più alta è **{best['label']}** ({best['prob']}%). "

    if markets["over"] > 60:
        analysis += "Alta probabilità di partita con molti gol (O2.5). "
    if markets["gg"] > 65:
        analysis += "Entrambe le squadre hanno alta probabilità di segnare (GG). "

    return best, candidates, analysis


# ─────────────────────────────────────────────
#  API-FOOTBALL — wrapper
# ─────────────────────────────────────────────
def _af_headers(key: str) -> dict:
    return {"x-apisports-key": key}


def get_fixtures(key: str, league_id: int, season: int, from_date: str, to_date: str) -> list:
    r = requests.get(
        "https://v3.football.api-sports.io/fixtures",
        headers=_af_headers(key),
        params={"league": league_id, "season": season, "from": from_date,
                "to": to_date, "status": "NS", "timezone": "Europe/Rome"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("response", [])


def get_team_stats(key: str, team_id: int, league_id: int, season: int) -> dict:
    r = requests.get(
        "https://v3.football.api-sports.io/teams/statistics",
        headers=_af_headers(key),
        params={"team": team_id, "league": league_id, "season": season},
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("response", {})


def get_last_matches(key: str, team_id: int, last: int = 10) -> list:
    r = requests.get(
        "https://v3.football.api-sports.io/fixtures",
        headers=_af_headers(key),
        params={"team": team_id, "last": last, "status": "FT"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("response", [])


def get_odds_apifootball(key: str, fixture_id: int) -> dict:
    """Quote da API-Football (Bet365 bookmaker ID 8). Usato come fallback."""
    r = requests.get(
        "https://v3.football.api-sports.io/odds",
        headers=_af_headers(key),
        params={"fixture": fixture_id, "bookmaker": 8},
        timeout=15,
    )
    r.raise_for_status()
    resp = r.json().get("response", [])
    if not resp:
        return {}
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
                result["over25"]  = vals.get("Over",  0)
                result["under25"] = vals.get("Under", 0)
            elif name == "Both Teams Score":
                result["gg"]   = vals.get("Yes", 0)
                result["nogg"] = vals.get("No",  0)
    return result


# ─────────────────────────────────────────────
#  THE ODDS API — wrapper
# ─────────────────────────────────────────────
def _average_odd(bookmakers: list, key_path: list, preferred: list) -> float:
    """
    Calcola la media delle quote tra i bookmaker disponibili.
    Naviga key_path nella struttura outcomes per estrarre il valore.
    """
    values = []
    bm_map = {bm["key"]: bm for bm in bookmakers}
    # Prima prova i preferiti, poi tutti gli altri
    ordered = [bm_map[k] for k in preferred if k in bm_map] + \
              [bm for k, bm in bm_map.items() if k not in preferred]
    for bm in ordered[:6]:  # max 6 bookmaker per la media
        for market in bm.get("markets", []):
            if market["key"] == key_path[0]:
                for outcome in market.get("outcomes", []):
                    if outcome["name"] == key_path[1]:
                        try:
                            values.append(float(outcome["price"]))
                        except (ValueError, TypeError):
                            pass
    if not values:
        return 0.0
    avg = sum(values) / len(values)
    return round(avg, 3)


def get_odds_theoddsapi(
    key: str,
    sport_key: str,
    home_team: str,
    away_team: str,
    match_date: str,
) -> dict:
    """
    Recupera e aggrega quote da The Odds API per una partita specifica.
    Ritorna le quote medie tra i bookmaker europei principali.
    sport_key: es. "soccer_italy_serie_a"
    """
    r = requests.get(
        f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/",
        params={
            "apiKey":  key,
            "regions": "eu",
            "markets": "h2h,totals,btts",
            "oddsFormat": "decimal",
            "dateFormat":  "iso",
        },
        timeout=15,
    )
    r.raise_for_status()
    events = r.json()

    # Trova l'evento corrispondente (home + away + data entro 24h)
    target_date = datetime.fromisoformat(match_date.replace("Z", "+00:00"))
    best_event  = None
    for ev in events:
        ev_home = ev.get("home_team", "").lower()
        ev_away = ev.get("away_team", "").lower()
        # Match fuzzy sul nome squadra (primi 5 caratteri)
        if (home_team[:5].lower() in ev_home or ev_home[:5] in home_team.lower()) and \
           (away_team[:5].lower() in ev_away or ev_away[:5] in away_team.lower()):
            try:
                ev_date = datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
                if abs((ev_date - target_date).total_seconds()) < 86400:
                    best_event = ev
                    break
            except Exception:
                continue

    if not best_event:
        return {}

    bookmakers = best_event.get("bookmakers", [])
    result     = {}

    # 1X2
    h = _average_odd(bookmakers, ["h2h", home_team], PREFERRED_BOOKMAKERS)
    # The Odds API usa i nomi reali delle squadre come outcome
    # Proviamo col nome originale dell'evento
    ev_home_name = best_event.get("home_team", home_team)
    ev_away_name = best_event.get("away_team", away_team)

    home_odd = _average_odd(bookmakers, ["h2h", ev_home_name], PREFERRED_BOOKMAKERS)
    draw_odd = _average_odd(bookmakers, ["h2h", "Draw"],        PREFERRED_BOOKMAKERS)
    away_odd = _average_odd(bookmakers, ["h2h", ev_away_name], PREFERRED_BOOKMAKERS)

    if home_odd: result["home"]  = home_odd
    if draw_odd: result["draw"]  = draw_odd
    if away_odd: result["away"]  = away_odd

    # Over/Under 2.5
    over_odd  = _average_odd(bookmakers, ["totals", "Over"],  PREFERRED_BOOKMAKERS)
    under_odd = _average_odd(bookmakers, ["totals", "Under"], PREFERRED_BOOKMAKERS)
    if over_odd:  result["over25"]  = over_odd
    if under_odd: result["under25"] = under_odd

    # GG / NoGG
    gg_odd   = _average_odd(bookmakers, ["btts", "Yes"], PREFERRED_BOOKMAKERS)
    nogg_odd = _average_odd(bookmakers, ["btts", "No"],  PREFERRED_BOOKMAKERS)
    if gg_odd:   result["gg"]   = gg_odd
    if nogg_odd: result["nogg"] = nogg_odd

    return result


# ─────────────────────────────────────────────
#  ORCHESTRATORE QUOTE
#  The Odds API (primario) → API-Football (fallback)
# ─────────────────────────────────────────────
def get_best_odds(
    af_key: str,
    odds_key: str,
    fixture: dict,
    league_name: str,
) -> tuple[dict, str]:
    """
    Ritorna (odds_dict, source_label).
    Tenta The Odds API se la chiave è disponibile,
    altrimenti cade su API-Football/Bet365.
    """
    home_name  = fixture["teams"]["home"]["name"]
    away_name  = fixture["teams"]["away"]["name"]
    match_date = fixture["fixture"]["date"]
    fix_id     = fixture["fixture"]["id"]
    sport_key  = LEAGUES[league_name]["odds_key"]

    if odds_key:
        try:
            odds = get_odds_theoddsapi(odds_key, sport_key, home_name, away_name, match_date)
            if odds:
                return odds, "The Odds API (media bookmaker EU)"
        except Exception:
            pass  # fallback silenzioso

    # Fallback: API-Football / Bet365
    try:
        odds = get_odds_apifootball(af_key, fix_id)
        if odds:
            return odds, "API-Football / Bet365"
    except Exception:
        pass

    return {}, "Nessuna quota disponibile"


# ─────────────────────────────────────────────
#  PARSING STATISTICHE
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


def compute_lambda(stats_team: dict, stats_opp: dict, is_home: bool, league_avg: float = 1.35) -> float:
    venue     = "home" if is_home else "away"
    opp_venue = "away" if is_home else "home"
    try:
        scored   = float(stats_team.get("goals", {}).get("for",     {}).get("average", {}).get(venue,     None) or league_avg)
        conceded = float(stats_opp .get("goals", {}).get("against", {}).get("average", {}).get(opp_venue, None) or league_avg)
    except (TypeError, ValueError):
        scored = conceded = league_avg

    att = scored   / league_avg if league_avg > 0 else 1.0
    dfs = conceded / league_avg if league_avg > 0 else 1.0
    return max(round(att * dfs * league_avg, 3), 0.1)


# ─────────────────────────────────────────────
#  ANALISI COMPLETA (cacheata per sessione)
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_and_analyze(af_key: str, odds_key: str, fixture: dict, league_id: int, league_name: str, season: int) -> dict:
    fix_id  = fixture["fixture"]["id"]
    team_h  = fixture["teams"]["home"]["id"]
    team_a  = fixture["teams"]["away"]["id"]

    stats_h   = get_team_stats(af_key, team_h, league_id, season)
    stats_a   = get_team_stats(af_key, team_a, league_id, season)
    last_h    = get_last_matches(af_key, team_h, last=10)
    last_a    = get_last_matches(af_key, team_a, last=10)

    odds, odds_source = get_best_odds(af_key, odds_key, fixture, league_name)

    form_raw_h = extract_form(last_h, team_h)
    form_raw_a = extract_form(last_a, team_a)
    form_h     = compute_form_weight(form_raw_h)
    form_a     = compute_form_weight(form_raw_a)

    def league_avg_from_stats(s, venue):
        try:
            return float(s["goals"]["for"]["average"][venue] or 1.35)
        except Exception:
            return 1.35

    league_avg = (league_avg_from_stats(stats_h, "home") + league_avg_from_stats(stats_a, "away")) / 2

    lam_h = round(compute_lambda(stats_h, stats_a, is_home=True,  league_avg=league_avg) * form_h, 3)
    lam_a = round(compute_lambda(stats_a, stats_h, is_home=False, league_avg=league_avg) * form_a, 3)

    matrix  = build_score_matrix(lam_h, lam_a)
    markets = compute_markets(matrix)
    best, candidates, analysis = best_suggestion(markets, odds, form_h, form_a, lam_h, lam_a)

    try:
        kickoff = datetime.fromisoformat(fixture["fixture"]["date"].replace("Z", "+00:00")).strftime("%d/%m %H:%M")
    except Exception:
        kickoff = fixture["fixture"]["date"][:16]

    return {
        "match":        fixture,
        "league_name":  league_name,
        "kickoff":      kickoff,
        "lam_home":     lam_h,
        "lam_away":     lam_a,
        "markets":      markets,
        "odds":         odds,
        "odds_source":  odds_source,
        "best":         best,
        "candidates":   candidates,
        "analysis":     analysis,
        "form_home":    form_h,
        "form_away":    form_a,
        "form_raw_home": form_raw_h,
        "form_raw_away": form_raw_a,
    }


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_fixtures_cached(key: str, league_id: int, season: int, from_date: str, to_date: str) -> list:
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
    v   = f"{value:.2f}" if isinstance(value, float) and value > 0 else (str(value) if value else "—")
    return f'<div class="{cls}"><span class="odd-lbl">{label}</span><span class="{vcl}">{v}</span></div>'

def progress_bar_html(prob: float, color: str) -> str:
    return (f'<div class="prog-bar-wrap">'
            f'<div class="prog-bar-fill" style="width:{min(prob,100)}%;background:{color};"></div></div>')

def key_status_html(loaded: bool, label: str, source: str = "") -> str:
    if loaded:
        return (f'<div class="key-ok">'
                f'<span style="font-family:\'DM Mono\',monospace;font-size:0.65rem;color:#4ade80;letter-spacing:0.1em;">✓ {label}</span><br>'
                f'<span style="font-family:\'DM Mono\',monospace;font-size:0.7rem;color:rgba(255,255,255,0.35);">{source}</span></div>')
    else:
        return (f'<div class="key-mis">'
                f'<span style="font-family:\'DM Mono\',monospace;font-size:0.65rem;color:#f87171;letter-spacing:0.1em;">✗ {label}</span><br>'
                f'<span style="font-family:\'DM Mono\',monospace;font-size:0.7rem;color:rgba(255,255,255,0.35);">Non configurata</span></div>')


# ─────────────────────────────────────────────
#  PANNELLO DETTAGLIO
# ─────────────────────────────────────────────
def render_detail_panel(result: dict):
    m        = result["match"]
    home     = m["teams"]["home"]["name"]
    away     = m["teams"]["away"]["name"]
    markets  = result["markets"]
    odds     = result["odds"]
    lam_h    = result["lam_home"]
    lam_a    = result["lam_away"]
    best     = result["best"]
    cands    = result["candidates"]
    analysis = result["analysis"]
    form_raw_h = result["form_raw_home"]
    form_raw_a = result["form_raw_away"]
    odds_src   = result.get("odds_source", "—")
    conf       = best["prob"]
    cc         = conf_class(conf)

    # Header partita
    st.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">PARTITA</div>
        <div class="team-name">{home} <span style="color:rgba(255,255,255,0.22);font-size:1rem"> vs </span> {away}</div>
        <div style="margin-top:6px;">
            <span class="league-badge">{result['league_name']} · {result['kickoff']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Forma
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<div class="stat-box"><div class="stat-label">{home.upper()} — FORMA</div>{form_dots_html(form_raw_h)}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-box"><div class="stat-label">{away.upper()} — FORMA</div>{form_dots_html(form_raw_a)}</div>', unsafe_allow_html=True)

    # Gol attesi
    st.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">GOL ATTESI (POISSON)</div>
        <div style="display:flex;justify-content:space-around;align-items:center;padding-top:6px;">
            <div style="text-align:center;"><div class="xg-label">{home.upper()}</div><div class="xg-num-home">{lam_h:.2f}</div></div>
            <div style="color:rgba(255,255,255,0.15);font-size:1.4rem;font-family:'DM Mono',monospace;">—</div>
            <div style="text-align:center;"><div class="xg-label">{away.upper()}</div><div class="xg-num-away">{lam_a:.2f}</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Mercati
    market_rows = [
        ("Vittoria Casa (1)",  markets["p1"],    "#60a5fa"),
        ("Pareggio (X)",       markets["px"],    "#a78bfa"),
        ("Vittoria Ospiti (2)",markets["p2"],    "#f472b6"),
        ("Over 2.5",           markets["over"],  "#34d399"),
        ("Under 2.5",          markets["under"], "#94a3b8"),
        ("GG",                 markets["gg"],    "#4ade80"),
        ("NoGG",               markets["nogg"],  "#fb923c"),
    ]
    rows_html = ""
    for label, prob, color in market_rows:
        rows_html += f"""
        <div style="margin-bottom:10px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                <span style="font-family:'DM Mono',monospace;font-size:0.75rem;color:rgba(255,255,255,0.5);">{label}</span>
                <span style="font-family:'DM Mono',monospace;font-size:0.75rem;font-weight:700;color:{color};">{prob}%</span>
            </div>
            {progress_bar_html(prob, color)}
        </div>"""
    st.markdown(f'<div class="stat-box"><div class="stat-label">PROBABILITÀ MERCATI</div>{rows_html}</div>', unsafe_allow_html=True)

    # Quote
    if odds:
        boxes = (
            odd_box_html("1",    odds.get("home",    0), best["label"] == "1")    +
            odd_box_html("X",    odds.get("draw",    0), best["label"] == "X")    +
            odd_box_html("2",    odds.get("away",    0), best["label"] == "2")    +
            odd_box_html("O2.5", odds.get("over25",  0), markets["over"]  > 60)   +
            odd_box_html("U2.5", odds.get("under25", 0))                          +
            odd_box_html("GG",   odds.get("gg",      0), markets["gg"]    > 60)   +
            odd_box_html("NoGG", odds.get("nogg",    0))
        )
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">QUOTE — {odds_src.upper()}</div>
            <div style="display:flex;flex-wrap:wrap;">{boxes}</div>
        </div>
        """, unsafe_allow_html=True)

        # Tabella edge per ogni mercato
        edge_rows = ""
        for c in cands:
            if c["odd"] <= 0:
                continue
            edge_color = "#4ade80" if c["edge"] > 0 else ("#f87171" if c["edge"] < 0 else "rgba(255,255,255,0.4)")
            vb = "🟢" if c["value"] else "⚪"
            edge_rows += f"""
            <tr>
                <td style="padding:5px 8px;font-family:'DM Mono',monospace;font-size:0.75rem;color:rgba(255,255,255,0.7);">{vb} {c['label']}</td>
                <td style="padding:5px 8px;font-family:'DM Mono',monospace;font-size:0.75rem;color:rgba(255,255,255,0.5);text-align:center;">{c['prob']}%</td>
                <td style="padding:5px 8px;font-family:'DM Mono',monospace;font-size:0.75rem;color:rgba(255,255,255,0.5);text-align:center;">{c['implied']}%</td>
                <td style="padding:5px 8px;font-family:'DM Mono',monospace;font-size:0.75rem;color:{edge_color};text-align:center;font-weight:700;">{'+' if c['edge']>0 else ''}{c['edge']}pp</td>
                <td style="padding:5px 8px;font-family:'DM Mono',monospace;font-size:0.75rem;color:rgba(255,255,255,0.5);text-align:right;">×{c['odd']:.2f}</td>
            </tr>"""

        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">EDGE ANALYSIS (POISSON VS QUOTA)</div>
            <table style="width:100%;border-collapse:collapse;">
                <thead>
                    <tr style="border-bottom:1px solid rgba(255,255,255,0.07);">
                        <th style="padding:5px 8px;font-family:'DM Mono',monospace;font-size:0.6rem;color:rgba(255,255,255,0.25);font-weight:400;text-align:left;">MERCATO</th>
                        <th style="padding:5px 8px;font-family:'DM Mono',monospace;font-size:0.6rem;color:rgba(255,255,255,0.25);font-weight:400;text-align:center;">PROB.</th>
                        <th style="padding:5px 8px;font-family:'DM Mono',monospace;font-size:0.6rem;color:rgba(255,255,255,0.25);font-weight:400;text-align:center;">IMPL.</th>
                        <th style="padding:5px 8px;font-family:'DM Mono',monospace;font-size:0.6rem;color:rgba(255,255,255,0.25);font-weight:400;text-align:center;">EDGE</th>
                        <th style="padding:5px 8px;font-family:'DM Mono',monospace;font-size:0.6rem;color:rgba(255,255,255,0.25);font-weight:400;text-align:right;">QUOTA</th>
                    </tr>
                </thead>
                <tbody>{edge_rows}</tbody>
            </table>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="warn-box">⚠️ Quote non disponibili per questa partita. Il valore di value bet non può essere calcolato.</div>', unsafe_allow_html=True)

    # Consiglio
    conf_col = "#4ade80" if conf >= 65 else ("#facc15" if conf >= 48 else "#f87171")
    vt = '<span class="value-tag">VALUE BET</span>' if best["value"] else ""
    quota_html = f"""
    <div>
        <div style="font-family:'DM Mono',monospace;font-size:0.65rem;color:rgba(255,255,255,0.3);">QUOTA</div>
        <div style="font-family:'DM Mono',monospace;font-size:1.1rem;font-weight:700;color:rgba(255,255,255,0.8);">×{best['odd']:.2f}</div>
    </div>""" if best["odd"] > 0 else ""

    st.markdown(f"""
    <div class="stat-box" style="border-color:rgba(74,222,128,0.2);">
        <div class="stat-label">CONSIGLIO PRINCIPALE {vt}</div>
        <div style="display:flex;align-items:center;gap:20px;margin-top:8px;">
            <div class="{cc}">{best['label']}</div>
            <div>
                <div style="font-family:'DM Mono',monospace;font-size:0.65rem;color:rgba(255,255,255,0.3);">CONFIDENZA</div>
                <div style="font-family:'DM Mono',monospace;font-size:1.1rem;font-weight:700;color:{conf_col};">{conf}%</div>
            </div>
            {quota_html}
            <div>
                <div style="font-family:'DM Mono',monospace;font-size:0.65rem;color:rgba(255,255,255,0.3);">EV</div>
                <div style="font-family:'DM Mono',monospace;font-size:1.1rem;font-weight:700;color:{'#4ade80' if best['ev']>0 else '#f87171'};">{'+'if best['ev']>0 else ''}{best['ev']:.3f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Analisi testuale
    st.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">ANALISI</div>
        <p style="font-size:0.82rem;color:rgba(255,255,255,0.58);line-height:1.75;margin:0;">{analysis}</p>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="margin-bottom:24px;">
        <div class="main-title" style="font-size:1.5rem;">donny</div>
        <div class="main-subtitle">FOOTBALL INTELLIGENCE</div>
    </div>
    """, unsafe_allow_html=True)

    # ── API-FOOTBALL KEY ──
    st.markdown('<div class="stat-label" style="margin-bottom:6px;">API-FOOTBALL KEY</div>', unsafe_allow_html=True)
    st.markdown(key_status_html(bool(_env_af), "CHIAVE CARICATA", "da .env / Secrets"), unsafe_allow_html=True)
    if _env_af:
        _ov_af = st.text_input("Sovrascrivi API-Football key", type="password", placeholder="Lascia vuoto per usare quella caricata", label_visibility="collapsed")
        api_key = _ov_af.strip() if _ov_af.strip() else _env_af
    else:
        api_key = st.text_input("API-Football key", type="password", placeholder="Incolla la tua chiave...", label_visibility="collapsed")

    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)

    # ── THE ODDS API KEY ──
    st.markdown('<div class="stat-label" style="margin-bottom:6px;">THE ODDS API KEY</div>', unsafe_allow_html=True)
    st.markdown(key_status_html(bool(_env_odds), "CHIAVE CARICATA", "da .env / Secrets"), unsafe_allow_html=True)
    if _env_odds:
        _ov_odds = st.text_input("Sovrascrivi The Odds API key", type="password", placeholder="Lascia vuoto per usare quella caricata", label_visibility="collapsed")
        odds_key = _ov_odds.strip() if _ov_odds.strip() else _env_odds
    else:
        odds_key = st.text_input("The Odds API key", type="password", placeholder="Opzionale — migliora le quote", label_visibility="collapsed")

    if not odds_key:
        st.markdown('<div class="warn-box" style="margin-top:4px;">⚠️ Senza questa chiave le quote vengono prese da API-Football (Bet365 solo). Con The Odds API si usa la media tra più bookmaker EU per un edge più preciso.</div>', unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    st.markdown('<div class="stat-label" style="margin-bottom:8px;">CAMPIONATI</div>', unsafe_allow_html=True)
    selected_leagues = st.multiselect("Campionati", options=list(LEAGUES.keys()), default=list(LEAGUES.keys()), label_visibility="collapsed")

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    st.markdown('<div class="stat-label" style="margin-bottom:8px;">STAGIONE</div>', unsafe_allow_html=True)
    season = st.selectbox("Stagione", [2024, 2023], label_visibility="collapsed")

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    odds_mode = "The Odds API (media EU)" if odds_key else "API-Football / Bet365"
    st.markdown(f"""
    <div style="font-family:'DM Mono',monospace;font-size:0.58rem;color:rgba(255,255,255,0.18);line-height:1.9;letter-spacing:0.08em;">
    MODELLO: POISSON + FORMA<br>
    STATISTICHE: API-FOOTBALL<br>
    QUOTE: {odds_mode.upper()}<br>
    FINESTRA: +5 GIORNI<br><br>
    Le previsioni sono stime<br>
    statistiche, non garanzie.
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  HEADER PRINCIPALE
# ─────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:36px;">
    <div class="main-title">Donny — Football Intelligence</div>
    <div class="main-subtitle">ANALISI PREDITTIVA · POISSON · FORMA RECENTE · VALUE BET</div>
</div>
""", unsafe_allow_html=True)

if not api_key:
    st.markdown("""
    <div class="info-box">
        🔑 Inserisci la tua <strong>API-Football key</strong> nella sidebar per iniziare.<br>
        Chiave gratuita su <strong>api-football.com</strong> (100 richieste/giorno).<br><br>
        Opzionale: <strong>The Odds API key</strong> su <strong>the-odds-api.com</strong>
        (500 req/mese free) per quote aggregate da più bookmaker europei.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

if not selected_leagues:
    st.warning("Seleziona almeno un campionato nella sidebar.")
    st.stop()


# ─────────────────────────────────────────────
#  STEP 1: CARICA PARTITE
# ─────────────────────────────────────────────
today    = datetime.now()
end_date = today + timedelta(days=5)
from_str = today.strftime("%Y-%m-%d")
to_str   = end_date.strftime("%Y-%m-%d")

odds_src_label = "The Odds API (media bookmaker EU)" if odds_key else "API-Football / Bet365"
st.markdown(f"""
<div class="info-box">
    📅 <strong>{today.strftime('%d/%m/%Y')}</strong> → <strong>{end_date.strftime('%d/%m/%Y')}</strong>
    &nbsp;·&nbsp; {len(selected_leagues)} campionati
    &nbsp;·&nbsp; Quote: <strong>{odds_src_label}</strong>
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
    with st.spinner("Recupero partite in corso..."):
        for lg in selected_leagues:
            try:
                fxs = fetch_fixtures_cached(api_key, LEAGUES[lg]["id"], season, from_str, to_str)
                st.session_state["fixtures_by_league"][lg] = fxs
            except Exception as e:
                st.error(f"Errore {lg}: {e}")

fixtures_map = st.session_state.get("fixtures_by_league", {})
all_fixtures = [(lg, f) for lg, fxs in fixtures_map.items() for f in fxs]

if not all_fixtures:
    if load_btn:
        st.warning("Nessuna partita trovata nella finestra selezionata.")
    st.stop()


# ─────────────────────────────────────────────
#  STEP 2: SELEZIONE E ANALISI
# ─────────────────────────────────────────────
st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown('<div class="stat-label" style="margin-bottom:12px;">PARTITE DISPONIBILI</div>', unsafe_allow_html=True)

by_day = defaultdict(list)
for lg, f in all_fixtures:
    try:
        day = datetime.fromisoformat(f["fixture"]["date"].replace("Z", "+00:00")).strftime("%A %d %B")
    except Exception:
        day = f["fixture"]["date"][:10]
    by_day[day].append((lg, f))

selected_day = st.selectbox("Giorno", list(by_day.keys()), label_visibility="collapsed")
day_fixtures = by_day.get(selected_day, [])

st.markdown(f"""
<div style="font-family:'DM Mono',monospace;font-size:0.65rem;color:rgba(255,255,255,0.28);
            letter-spacing:0.12em;margin-bottom:14px;">{len(day_fixtures)} PARTITE · {selected_day.upper()}</div>
""", unsafe_allow_html=True)

if "analysis_results" not in st.session_state:
    st.session_state["analysis_results"] = {}

for lg, f in day_fixtures:
    fix_id = f["fixture"]["id"]
    home   = f["teams"]["home"]["name"]
    away   = f["teams"]["away"]["name"]
    try:
        kickoff = datetime.fromisoformat(f["fixture"]["date"].replace("Z", "+00:00")).strftime("%H:%M")
    except Exception:
        kickoff = "??:??"

    lcolor      = LEAGUES[lg]["color"]
    is_analyzed = fix_id in st.session_state["analysis_results"]
    card_cls    = "match-card-selected" if is_analyzed else "match-card"

    result_html = ""
    if is_analyzed:
        res  = st.session_state["analysis_results"][fix_id]
        best = res["best"]
        conf = best["prob"]
        cc   = conf_class(conf)
        vt   = '<span class="value-tag">VALUE BET</span>' if best["value"] else ""
        src  = res.get("odds_source", "")
        src_html = f'<span style="font-family:\'DM Mono\',monospace;font-size:0.6rem;color:rgba(255,255,255,0.22);">quote: {src}</span>' if src else ""
        result_html = f"""
        <div style="display:flex;align-items:center;gap:14px;margin-top:12px;flex-wrap:wrap;">
            <div class="{cc}">{best['label']}</div>
            <div style="font-family:'DM Mono',monospace;font-size:0.7rem;color:rgba(255,255,255,0.35);">{conf}% confidenza</div>
            {vt} {src_html}
        </div>"""

    st.markdown(f"""
    <div class="{card_cls}">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
            <div style="width:8px;height:8px;border-radius:50%;background:{lcolor};box-shadow:0 0 7px {lcolor}88;flex-shrink:0;"></div>
            <span class="league-badge">{lg} · {kickoff}</span>
        </div>
        <div style="display:flex;align-items:center;justify-content:space-between;">
            <div class="team-name">{home}</div>
            <div style="font-family:'DM Mono',monospace;font-size:0.75rem;color:rgba(255,255,255,0.18);padding:0 14px;">VS</div>
            <div class="team-name" style="text-align:right;">{away}</div>
        </div>
        {result_html}
    </div>
    """, unsafe_allow_html=True)

    col_btn, _ = st.columns([1, 4])
    with col_btn:
        if st.button("🔄 RIANALIZZA" if is_analyzed else "🔍 ANALIZZA", key=f"analyze_{fix_id}"):
            with st.spinner(f"Analisi {home} vs {away}..."):
                try:
                    res = fetch_and_analyze(api_key, odds_key, f, LEAGUES[lg]["id"], lg, season)
                    st.session_state["analysis_results"][fix_id] = res
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")

    if is_analyzed:
        with st.expander("📊 Dettaglio analisi", expanded=True):
            render_detail_panel(st.session_state["analysis_results"][fix_id])

    st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  FOOTER
# ─────────────────────────────────────────────
st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;font-family:'DM Mono',monospace;font-size:0.58rem;
            color:rgba(255,255,255,0.12);letter-spacing:0.12em;padding-bottom:24px;">
DONNY — FOOTBALL INTELLIGENCE · POISSON + FORMA RECENTE<br>
DATI: API-FOOTBALL.COM · QUOTE: THE ODDS API / BET365 · USO RESPONSABILE
</div>
""", unsafe_allow_html=True)
