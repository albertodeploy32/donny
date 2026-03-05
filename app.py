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
    odd = from_secrets("ODDS_API_KEY")  or os.environ.get("ODDS_API_KEY",  "")
    return af.strip(), odd.strip()

_env_af, _env_odds = _load_keys()

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Donny",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
#  CSS — Apple-inspired, dense, refined
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

*, html, body, [class*="css"] {
    font-family: 'Figtree', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif !important;
    -webkit-font-smoothing: antialiased;
    box-sizing: border-box;
}

.stApp {
    background: #000 !important;
    background-image:
        radial-gradient(ellipse 120% 60% at 50% -20%, rgba(28,28,30,0.95) 0%, #000 70%) !important;
}

[data-testid="stSidebar"] {
    background: #0a0a0a !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}
[data-testid="stSidebar"] * { color: #e5e5e7 !important; }

/* Hide Streamlit chrome */
#MainMenu, footer, header, [data-testid="stToolbar"] { visibility: hidden !important; }
.block-container { padding: 2rem 2.5rem 4rem !important; max-width: 1400px; }

/* ── Typography ── */
.app-wordmark {
    font-family: 'Figtree', sans-serif;
    font-weight: 800;
    font-size: 1.65rem;
    letter-spacing: -0.04em;
    color: #f5f5f7;
    display: inline-block;
}
.app-tagline {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    letter-spacing: 0.2em;
    color: rgba(255,255,255,0.22);
    text-transform: uppercase;
    margin-top: 2px;
}
.section-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.18em;
    color: rgba(255,255,255,0.2);
    text-transform: uppercase;
    margin-bottom: 10px;
    margin-top: 28px;
}

/* ── Table ── */
.match-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
}
.match-table thead tr th {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.57rem;
    letter-spacing: 0.16em;
    color: rgba(255,255,255,0.22);
    font-weight: 500;
    text-transform: uppercase;
    padding: 8px 12px 8px 12px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    white-space: nowrap;
    text-align: left;
}
.match-table tbody tr {
    transition: background 0.15s ease;
    cursor: pointer;
}
.match-table tbody tr:hover td {
    background: rgba(255,255,255,0.025) !important;
}
.match-table tbody tr td {
    padding: 11px 12px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    vertical-align: middle;
    background: transparent;
}
.match-table tbody tr.analyzed-row td {
    background: rgba(255,255,255,0.02);
}
.match-table tbody tr.analyzed-row td:first-child {
    border-left: 2px solid rgba(10,132,255,0.5);
}

/* ── Cell types ── */
.cell-time {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: rgba(255,255,255,0.35);
    white-space: nowrap;
}
.cell-league {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.08em;
    color: rgba(255,255,255,0.25);
    white-space: nowrap;
}
.cell-teams {
    font-family: 'Figtree', sans-serif;
    font-weight: 500;
    font-size: 0.88rem;
    color: rgba(255,255,255,0.85);
    white-space: nowrap;
}
.cell-teams .vs {
    color: rgba(255,255,255,0.18);
    font-weight: 300;
    margin: 0 6px;
    font-size: 0.78rem;
}
.cell-pct {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    font-weight: 500;
    text-align: center;
    white-space: nowrap;
}
.pct-green  { color: #32d74b; }
.pct-yellow { color: #ffd60a; }
.pct-red    { color: #ff453a; }
.pct-dim    { color: rgba(255,255,255,0.3); }

.cell-pick {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    font-weight: 700;
    white-space: nowrap;
}
.pick-green  { color: #30d158; }
.pick-yellow { color: #ffd60a; }
.pick-red    { color: #ff6961; }

.badge-value {
    display: inline-block;
    background: rgba(48,209,88,0.12);
    border: 1px solid rgba(48,209,88,0.28);
    border-radius: 4px;
    padding: 1px 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.55rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: #30d158;
    margin-left: 6px;
    vertical-align: middle;
}
.badge-nodata {
    display: inline-block;
    background: rgba(255,69,58,0.1);
    border: 1px solid rgba(255,69,58,0.2);
    border-radius: 4px;
    padding: 1px 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.55rem;
    color: rgba(255,69,58,0.7);
    letter-spacing: 0.08em;
}

.cell-xg {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: rgba(255,255,255,0.45);
    white-space: nowrap;
    text-align: center;
}
.xg-h { color: #0a84ff; font-weight: 600; }
.xg-a { color: #ff375f; font-weight: 600; }

.form-dot {
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 50%;
    margin: 0 1.5px;
    vertical-align: middle;
}
.fd-w { background: #32d74b; }
.fd-d { background: #ffd60a; }
.fd-l { background: #ff453a; }

/* ── Detail panel ── */
.detail-panel {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 22px 24px 20px;
    margin-top: 4px;
    margin-bottom: 16px;
}
.dp-title {
    font-family: 'Figtree', sans-serif;
    font-weight: 700;
    font-size: 1.05rem;
    color: rgba(255,255,255,0.85);
    margin-bottom: 16px;
}
.dp-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
    margin-bottom: 16px;
}
.dp-block {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    padding: 12px 14px;
}
.dp-block-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.57rem;
    letter-spacing: 0.16em;
    color: rgba(255,255,255,0.22);
    text-transform: uppercase;
    margin-bottom: 8px;
}
.dp-mkt-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
}
.dp-mkt-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: rgba(255,255,255,0.38);
}
.dp-mkt-pct {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    font-weight: 600;
}
.dp-bar-wrap {
    background: rgba(255,255,255,0.05);
    border-radius: 3px;
    height: 3px;
    margin-top: 3px;
    margin-bottom: 8px;
}
.dp-analysis {
    font-size: 0.8rem;
    color: rgba(255,255,255,0.45);
    line-height: 1.7;
    font-weight: 300;
}
.dp-edge-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 6px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
}

/* ── Summary strip ── */
.summary-strip {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    padding: 16px 20px;
    margin-top: 24px;
}
.summary-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 7px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.summary-row:last-child { border-bottom: none; }

/* ── Info / Warn boxes ── */
.info-box {
    background: rgba(10,132,255,0.07);
    border: 1px solid rgba(10,132,255,0.18);
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 0.8rem;
    color: rgba(255,255,255,0.5);
    margin-bottom: 14px;
}
.warn-box {
    background: rgba(255,214,10,0.06);
    border: 1px solid rgba(255,214,10,0.18);
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 0.8rem;
    color: rgba(255,255,255,0.45);
    margin-bottom: 14px;
}

/* ── Streamlit overrides ── */
.stButton > button {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    color: rgba(255,255,255,0.7) !important;
    border-radius: 8px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.68rem !important;
    letter-spacing: 0.1em !important;
    padding: 7px 16px !important;
}
.stButton > button:hover {
    background: rgba(255,255,255,0.09) !important;
    border-color: rgba(255,255,255,0.18) !important;
    color: #fff !important;
}
.stSelectbox > div > div,
.stTextInput > div > div {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
    color: #e5e5e7 !important;
    font-family: 'Figtree', sans-serif !important;
}
.stMultiSelect > div > div {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
}
.stSpinner > div { border-top-color: #0a84ff !important; }
div[data-testid="stExpander"] {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  COSTANTI
# ─────────────────────────────────────────────
LEAGUES = {
    "Serie A 🇮🇹":         {"id": 135, "color": "#0a84ff", "odds_key": "soccer_italy_serie_a",     "abbr": "SA"},
    "Premier League 🏴󠁧󠁢󠁥󠁮󠁧󠁿": {"id": 39,  "color": "#32d74b","odds_key": "soccer_epl",                "abbr": "EPL"},
    "La Liga 🇪🇸":          {"id": 140, "color": "#ff453a", "odds_key": "soccer_spain_la_liga",     "abbr": "LAL"},
    "Bundesliga 🇩🇪":       {"id": 78,  "color": "#ffd60a", "odds_key": "soccer_germany_bundesliga","abbr": "BUN"},
    "Ligue 1 🇫🇷":          {"id": 61,  "color": "#bf5af2", "odds_key": "soccer_france_ligue_one",  "abbr": "L1"},
}
FD_LEAGUE_MAP = {135: "SA", 39: "PL", 140: "PD", 78: "BL1", 61: "FL1"}
FD_BASE = "https://api.football-data.org/v4"
PREFERRED_BOOKMAKERS = ["pinnacle", "bet365", "williamhill", "unibet", "betfair"]
MAX_SCORELINE = 6

def current_season() -> int:
    now = datetime.now()
    return now.year if now.month >= 8 else now.year - 1

CURRENT_SEASON = current_season()

# ─────────────────────────────────────────────
#  POISSON ENGINE
# ─────────────────────────────────────────────
def poisson_prob(lam: float, k: int) -> float:
    if lam <= 0: return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

def build_score_matrix(lam_h: float, lam_a: float, max_g: int = MAX_SCORELINE) -> dict:
    return {(gh, ga): poisson_prob(lam_h, gh) * poisson_prob(lam_a, ga)
            for gh, ga in product(range(max_g + 1), range(max_g + 1))}

def compute_markets(matrix: dict) -> dict:
    p1  = sum(v for (gh, ga), v in matrix.items() if gh > ga)
    px  = sum(v for (gh, ga), v in matrix.items() if gh == ga)
    p2  = sum(v for (gh, ga), v in matrix.items() if gh < ga)
    po  = sum(v for (gh, ga), v in matrix.items() if gh + ga > 2)
    pgg = sum(v for (gh, ga), v in matrix.items() if gh > 0 and ga > 0)
    return {
        "p1":    round(p1 * 100, 1),
        "px":    round(px * 100, 1),
        "p2":    round(p2 * 100, 1),
        "over":  round(po * 100, 1),
        "under": round((1 - po) * 100, 1),
        "gg":    round(pgg * 100, 1),
        "nogg":  round((1 - pgg) * 100, 1),
    }

def compute_form_weight(results: list, n: int = 6) -> float:
    if not results: return 1.0
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

def best_suggestion(markets: dict, odds: dict, form_h: float, form_a: float, lam_h: float, lam_a: float):
    mapping = [
        ("1",    markets["p1"],    odds.get("home",    0)),
        ("X",    markets["px"],    odds.get("draw",    0)),
        ("2",    markets["p2"],    odds.get("away",    0)),
        ("O2.5", markets["over"],  odds.get("over25",  0)),
        ("U2.5", markets["under"], odds.get("under25", 0)),
        ("GG",   markets["gg"],    odds.get("gg",      0)),
        ("NoGG", markets["nogg"],  odds.get("nogg",    0)),
    ]
    candidates = []
    for label, prob, odd in mapping:
        ev = (prob / 100) * odd - (1 - prob / 100) if odd > 0 else -999
        candidates.append({
            "label": label, "prob": prob, "odd": odd,
            "value": value_bet(prob, odd), "ev": round(ev, 4),
            "implied": round(implied_prob(odd), 1),
            "edge": round(prob - implied_prob(odd), 1) if odd > 0 else 0,
        })
    candidates.sort(key=lambda x: (x["value"], x["ev"]), reverse=True)
    best = candidates[0]

    fh_str = "ottima" if form_h > 1.1 else ("nella norma" if form_h >= 0.9 else "in calo")
    fa_str = "ottima" if form_a > 1.1 else ("nella norma" if form_a >= 0.9 else "in calo")
    analysis = (
        f"Poisson stima {lam_h:.2f} gol attesi in casa, {lam_a:.2f} in trasferta. "
        f"Forma casa {fh_str} (×{form_h}), ospiti {fa_str} (×{form_a}). "
    )
    if best["value"]:
        analysis += f"Edge positivo su <strong>{best['label']}</strong>: +{best['edge']:.1f}pp (modello {best['prob']}% vs implicita {best['implied']}%). "
    else:
        analysis += f"Nessun value bet netto; giocata con confidenza più alta: <strong>{best['label']}</strong> ({best['prob']}%). "
    if markets["over"] > 60: analysis += "Alta probabilità Over 2.5. "
    if markets["gg"] > 65:   analysis += "Entrambe le squadre probabilmente a segno (GG). "
    return best, candidates, analysis

# ─────────────────────────────────────────────
#  API WRAPPERS
# ─────────────────────────────────────────────
def _af_headers(key: str) -> dict:
    return {"X-Auth-Token": key}

def get_fixtures(key: str, league_id: int, season: int, from_date: str, to_date: str) -> list:
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

def _average_odd(bookmakers: list, key_path: list, preferred: list) -> float:
    values = []
    bm_map = {bm["key"]: bm for bm in bookmakers}
    ordered = [bm_map[k] for k in preferred if k in bm_map] + \
              [bm for k, bm in bm_map.items() if k not in preferred]
    for bm in ordered[:6]:
        for market in bm.get("markets", []):
            if market["key"] == key_path[0]:
                for outcome in market.get("outcomes", []):
                    if outcome["name"] == key_path[1]:
                        try: values.append(float(outcome["price"]))
                        except: pass
    return round(sum(values) / len(values), 3) if values else 0.0

def get_odds_theoddsapi(key: str, sport_key: str, home_team: str, away_team: str, match_date: str) -> dict:
    r = requests.get(
        f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/",
        params={"apiKey": key, "regions": "eu", "markets": "h2h,totals,btts",
                "oddsFormat": "decimal", "dateFormat": "iso"},
        timeout=15,
    )
    r.raise_for_status()
    events = r.json()
    target_date = datetime.fromisoformat(match_date.replace("Z", "+00:00"))
    best_event  = None
    for ev in events:
        ev_home = ev.get("home_team", "").lower()
        ev_away = ev.get("away_team", "").lower()
        if (home_team[:5].lower() in ev_home or ev_home[:5] in home_team.lower()) and \
           (away_team[:5].lower() in ev_away or ev_away[:5] in away_team.lower()):
            try:
                ev_date = datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
                if abs((ev_date - target_date).total_seconds()) < 86400:
                    best_event = ev; break
            except: continue
    if not best_event: return {}
    bookmakers  = best_event.get("bookmakers", [])
    ev_home_name = best_event.get("home_team", home_team)
    ev_away_name = best_event.get("away_team", away_team)
    result = {}
    home_odd  = _average_odd(bookmakers, ["h2h",    ev_home_name], PREFERRED_BOOKMAKERS)
    draw_odd  = _average_odd(bookmakers, ["h2h",    "Draw"],       PREFERRED_BOOKMAKERS)
    away_odd  = _average_odd(bookmakers, ["h2h",    ev_away_name], PREFERRED_BOOKMAKERS)
    over_odd  = _average_odd(bookmakers, ["totals", "Over"],       PREFERRED_BOOKMAKERS)
    under_odd = _average_odd(bookmakers, ["totals", "Under"],      PREFERRED_BOOKMAKERS)
    gg_odd    = _average_odd(bookmakers, ["btts",   "Yes"],        PREFERRED_BOOKMAKERS)
    nogg_odd  = _average_odd(bookmakers, ["btts",   "No"],         PREFERRED_BOOKMAKERS)
    if home_odd:  result["home"]   = home_odd
    if draw_odd:  result["draw"]   = draw_odd
    if away_odd:  result["away"]   = away_odd
    if over_odd:  result["over25"] = over_odd
    if under_odd: result["under25"]= under_odd
    if gg_odd:    result["gg"]     = gg_odd
    if nogg_odd:  result["nogg"]   = nogg_odd
    return result

def get_best_odds(af_key: str, odds_key: str, fixture: dict, league_name: str) -> tuple[dict, str]:
    home_name  = fixture["teams"]["home"]["name"]
    away_name  = fixture["teams"]["away"]["name"]
    match_date = fixture["fixture"]["date"]
    sport_key  = LEAGUES[league_name]["odds_key"]
    if odds_key:
        try:
            odds = get_odds_theoddsapi(odds_key, sport_key, home_name, away_name, match_date)
            if odds: return odds, "OddsAPI"
        except: pass
    return {}, "—"

# ─────────────────────────────────────────────
#  DATA LAYER
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
    def avg(lst): return sum(lst) / len(lst) if lst else 1.35
    return avg(scored), avg(conceded)

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_and_analyze(af_key: str, odds_key: str, fixture: dict, league_id: int, league_name: str, season: int) -> dict:
    team_h = fixture["teams"]["home"]["id"]
    team_a = fixture["teams"]["away"]["id"]
    last_h = get_last_matches(af_key, team_h, last=10)
    last_a = get_last_matches(af_key, team_a, last=10)
    odds, odds_source = get_best_odds(af_key, odds_key, fixture, league_name)
    form_raw_h = extract_form(last_h, team_h)
    form_raw_a = extract_form(last_a, team_a)
    form_h     = compute_form_weight(form_raw_h)
    form_a     = compute_form_weight(form_raw_a)
    h_scored, h_conceded = goals_avg_from_matches(last_h, team_h, is_home=True)
    a_scored, a_conceded = goals_avg_from_matches(last_a, team_a, is_home=False)
    league_avg = (h_scored + a_scored) / 2
    att_h = h_scored   / league_avg if league_avg > 0 else 1.0
    def_a = a_conceded / league_avg if league_avg > 0 else 1.0
    att_a = a_scored   / league_avg if league_avg > 0 else 1.0
    def_h = h_conceded / league_avg if league_avg > 0 else 1.0
    lam_h = round(max(att_h * def_a * league_avg * form_h, 0.1), 3)
    lam_a = round(max(att_a * def_h * league_avg * form_a, 0.1), 3)
    matrix  = build_score_matrix(lam_h, lam_a)
    markets = compute_markets(matrix)
    best, candidates, analysis = best_suggestion(markets, odds, form_h, form_a, lam_h, lam_a)
    try:
        kickoff = datetime.fromisoformat(fixture["fixture"]["date"].replace("Z", "+00:00")).strftime("%d/%m %H:%M")
    except:
        kickoff = fixture["fixture"]["date"][:16]
    return {
        "match": fixture, "league_name": league_name, "kickoff": kickoff,
        "lam_home": lam_h, "lam_away": lam_a, "markets": markets,
        "odds": odds, "odds_source": odds_source, "best": best,
        "candidates": candidates, "analysis": analysis,
        "form_home": form_h, "form_away": form_a,
        "form_raw_home": form_raw_h, "form_raw_a": form_raw_a,
    }

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_fixtures_cached(key: str, league_id: int, season: int, from_date: str, to_date: str) -> list:
    return get_fixtures(key, league_id, season, from_date, to_date)

# ─────────────────────────────────────────────
#  HELPERS UI
# ─────────────────────────────────────────────
def pct_color_class(v: float) -> str:
    if v >= 60: return "pct-green"
    if v >= 45: return "pct-yellow"
    return "pct-red"

def pick_color_class(v: float) -> str:
    if v >= 60: return "pick-green"
    if v >= 45: return "pick-yellow"
    return "pick-red"

def form_html(form: list, n: int = 5) -> str:
    cls = {"W": "fd-w", "D": "fd-d", "L": "fd-l"}
    return "".join(f'<span class="form-dot {cls.get(r,"fd-d")}"></span>' for r in form[-n:])

def bar_html(pct: float, color: str) -> str:
    return (f'<div class="dp-bar-wrap"><div style="height:3px;border-radius:3px;'
            f'width:{min(pct,100)}%;background:{color};"></div></div>')

# ─────────────────────────────────────────────
#  DETAIL PANEL
# ─────────────────────────────────────────────
def render_detail_panel(result: dict):
    m       = result["match"]
    home    = m["teams"]["home"]["name"]
    away    = m["teams"]["away"]["name"]
    mkts    = result["markets"]
    odds    = result["odds"]
    lam_h   = result["lam_home"]
    lam_a   = result["lam_away"]
    best    = result["best"]
    cands   = result["candidates"]
    analysis= result["analysis"]
    frh     = result.get("form_raw_home", [])
    fra     = result.get("form_raw_a", [])

    market_config = [
        ("1 — Casa",      mkts["p1"],    "#0a84ff"),
        ("X — Pareggio",  mkts["px"],    "#bf5af2"),
        ("2 — Ospiti",    mkts["p2"],    "#ff375f"),
        ("Over 2.5",      mkts["over"],  "#32d74b"),
        ("Under 2.5",     mkts["under"], "#636366"),
        ("GG",            mkts["gg"],    "#30d158"),
        ("NoGG",          mkts["nogg"],  "#ff9f0a"),
    ]

    # Probabilità bars
    bars_html = ""
    for label, prob, color in market_config:
        p_cls = pct_color_class(prob)
        bars_html += f"""
        <div class="dp-mkt-row" style="margin-bottom:2px;">
            <span class="dp-mkt-label">{label}</span>
            <span class="dp-mkt-pct" style="color:{color};">{prob}%</span>
        </div>
        {bar_html(prob, color)}"""

    # Edge table
    edge_rows = ""
    for c in cands:
        if c["odd"] <= 0: continue
        ec = "#32d74b" if c["edge"] > 0 else ("#ff453a" if c["edge"] < 0 else "rgba(255,255,255,0.3)")
        vb = "●" if c["value"] else "○"
        edge_rows += f"""
        <div class="dp-edge-row">
            <span style="color:{'#32d74b' if c['value'] else 'rgba(255,255,255,0.25)'};">{vb}</span>
            <span style="color:rgba(255,255,255,0.6);min-width:46px;">{c['label']}</span>
            <span style="color:rgba(255,255,255,0.38);min-width:52px;">{c['prob']}%</span>
            <span style="color:rgba(255,255,255,0.25);min-width:52px;">{c['implied']}%</span>
            <span style="color:{ec};min-width:52px;font-weight:600;">{'+' if c['edge']>0 else ''}{c['edge']}pp</span>
            <span style="color:rgba(255,255,255,0.45);">×{c['odd']:.2f}</span>
        </div>"""

    xg_html = f"""
    <div style="display:flex;align-items:center;justify-content:space-around;padding:8px 0;">
        <div style="text-align:center;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;color:rgba(255,255,255,0.22);letter-spacing:0.12em;margin-bottom:4px;">{home[:12].upper()}</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:2rem;font-weight:700;color:#0a84ff;">{lam_h:.2f}</div>
        </div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:0.9rem;color:rgba(255,255,255,0.1);">—</div>
        <div style="text-align:center;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;color:rgba(255,255,255,0.22);letter-spacing:0.12em;margin-bottom:4px;">{away[:12].upper()}</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:2rem;font-weight:700;color:#ff375f;">{lam_a:.2f}</div>
        </div>
    </div>"""

    forma_html = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;">
        <div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;color:rgba(255,255,255,0.22);margin-bottom:5px;">{home[:14]}</div>
            {form_html(frh, 6)}
        </div>
        <div style="text-align:right;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;color:rgba(255,255,255,0.22);margin-bottom:5px;">{away[:14]}</div>
            {form_html(fra, 6)}
        </div>
    </div>"""

    conf_col = "#32d74b" if best["prob"] >= 60 else ("#ffd60a" if best["prob"] >= 45 else "#ff453a")
    ev_sign  = "+" if best["ev"] > 0 else ""
    vbadge   = '<span class="badge-value">VALUE BET</span>' if best["value"] else ""

    quota_block = ""
    if best["odd"] > 0:
        ev_col = "#32d74b" if best["ev"] > 0 else "#ff453a"
        quota_block = f"""
        <div style="margin-left:auto;text-align:right;">
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;color:rgba(255,255,255,0.22);">QUOTA &nbsp;</span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.9rem;font-weight:700;color:rgba(255,255,255,0.7);">×{best['odd']:.2f}</span>
            &nbsp;&nbsp;
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;color:rgba(255,255,255,0.22);">EV &nbsp;</span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.9rem;font-weight:700;color:{ev_col};">{ev_sign}{best['ev']:.3f}</span>
        </div>"""

    st.markdown(f"""
    <div class="detail-panel">
        <!-- CONSIGLIO PRINCIPALE -->
        <div style="display:flex;align-items:center;gap:16px;margin-bottom:18px;flex-wrap:wrap;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:1.9rem;font-weight:700;color:{conf_col};">{best['label']}</div>
            <div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;color:rgba(255,255,255,0.22);letter-spacing:0.12em;">CONFIDENZA</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:1rem;font-weight:600;color:{conf_col};">{best['prob']}%</div>
            </div>
            {vbadge}
            {quota_block}
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
            <!-- Gol attesi -->
            <div class="dp-block">
                <div class="dp-block-label">GOL ATTESI (POISSON)</div>
                {xg_html}
            </div>
            <!-- Forma -->
            <div class="dp-block">
                <div class="dp-block-label">FORMA RECENTE (ULT. 6)</div>
                {forma_html}
            </div>
            <!-- Probabilità -->
            <div class="dp-block">
                <div class="dp-block-label">PROBABILITÀ MERCATI</div>
                {bars_html}
            </div>
        </div>

        <!-- Edge analysis -->
        {'<div class="dp-block" style="margin-top:12px;"><div class="dp-block-label">EDGE ANALYSIS</div><div style="font-family:JetBrains Mono,monospace;font-size:0.57rem;color:rgba(255,255,255,0.18);display:flex;gap:12px;margin-bottom:6px;"><span style=min-width:46px;>TIPO</span><span style=min-width:52px;>MOD.</span><span style=min-width:52px;>IMPL.</span><span style=min-width:52px;>EDGE</span><span>QUOTA</span></div>' + edge_rows + '</div>' if odds else '<div class="warn-box">⚠️ Quote non disponibili — edge analysis disabilitata.</div>'}

        <!-- Analisi -->
        <div style="margin-top:12px;">
            <div class="dp-block-label">ANALISI</div>
            <div class="dp-analysis">{analysis}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  SIDEBAR — API keys
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="app-wordmark">donny</div><div class="app-tagline">FOOTBALL INTELLIGENCE</div>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown('<div class="section-label" style="margin-top:10px;">FOOTBALL-DATA.ORG</div>', unsafe_allow_html=True)
    if _env_af:
        ov = st.text_input("Sovrascrivi FD key", type="password", placeholder="caricata da env/secrets", label_visibility="collapsed")
        api_key = ov.strip() if ov.strip() else _env_af
    else:
        api_key = st.text_input("Football-Data key", type="password", placeholder="Incolla la chiave...", label_visibility="collapsed")

    st.markdown('<div class="section-label">THE ODDS API (opzionale)</div>', unsafe_allow_html=True)
    if _env_odds:
        ov2 = st.text_input("Sovrascrivi Odds key", type="password", placeholder="caricata da env/secrets", label_visibility="collapsed")
        odds_key = ov2.strip() if ov2.strip() else _env_odds
    else:
        odds_key = st.text_input("Odds API key", type="password", placeholder="Opzionale...", label_visibility="collapsed")

    st.markdown("---")
    st.markdown('<div class="section-label">CAMPIONATI</div>', unsafe_allow_html=True)
    selected_leagues = st.multiselect("", options=list(LEAGUES.keys()), default=list(LEAGUES.keys()), label_visibility="collapsed")

    st.markdown("---")
    st.markdown(f"""<div style="font-family:'JetBrains Mono',monospace;font-size:0.57rem;
    color:rgba(255,255,255,0.18);line-height:2;letter-spacing:0.08em;">
    MODELLO: POISSON + FORMA<br>STAGIONE: {CURRENT_SEASON}/{CURRENT_SEASON+1}<br>
    FINESTRA: +5 GIORNI<br><br>Previsioni statistiche,<br>non garanzie di risultato.</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────
col_logo, col_spacer = st.columns([4, 1])
with col_logo:
    st.markdown("""
    <div style="margin-bottom:28px;">
        <div class="app-wordmark">donny</div>
        <div class="app-tagline">FOOTBALL INTELLIGENCE · POISSON · VALUE BET</div>
    </div>
    """, unsafe_allow_html=True)

if not api_key:
    st.markdown("""
    <div class="info-box">
        🔑 Inserisci la <strong>Football-Data.org key</strong> nella sidebar per iniziare.
        Gratuita su football-data.org (piano Free: 10 req/min).
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

col_a, col_b, col_c = st.columns([1, 2, 2])
with col_a:
    load_btn = st.button("⚽  CARICA PARTITE", key="load")
with col_b:
    st.markdown(f"""<div style="font-family:'JetBrains Mono',monospace;font-size:0.68rem;
    color:rgba(255,255,255,0.3);padding-top:10px;">
    {today.strftime('%d/%m/%Y')} → {end_date.strftime('%d/%m/%Y')} · {len(selected_leagues)} campionati
    </div>""", unsafe_allow_html=True)

if "fixtures_by_league" not in st.session_state:
    st.session_state["fixtures_by_league"] = {}

if load_btn:
    st.session_state["fixtures_by_league"] = {}
    st.session_state.pop("analysis_results", None)
    with st.spinner("Recupero partite..."):
        for lg in selected_leagues:
            try:
                fxs = fetch_fixtures_cached(api_key, LEAGUES[lg]["id"], CURRENT_SEASON, from_str, to_str)
                st.session_state["fixtures_by_league"][lg] = fxs
            except Exception as e:
                err_str = str(e)
                if "403" in err_str: st.error(f"❌ {lg}: chiave non valida (403)")
                elif "401" in err_str: st.error(f"❌ {lg}: non autorizzata (401)")
                elif "429" in err_str: st.error(f"❌ {lg}: limite raggiunto (429)")
                else: st.error(f"❌ {lg}: {e}")

fixtures_map = st.session_state.get("fixtures_by_league", {})
all_fixtures = [(lg, f) for lg, fxs in fixtures_map.items() for f in fxs]

if not all_fixtures:
    if load_btn: st.warning("Nessuna partita trovata nella finestra selezionata.")
    st.stop()

# ─────────────────────────────────────────────
#  STEP 2: SELETTORE GIORNO
# ─────────────────────────────────────────────
by_day = defaultdict(list)
for lg, f in all_fixtures:
    try:
        day = datetime.fromisoformat(f["fixture"]["date"].replace("Z", "+00:00")).strftime("%A %d %B")
    except:
        day = f["fixture"]["date"][:10]
    by_day[day].append((lg, f))

st.markdown('<div class="section-label">GIORNO</div>', unsafe_allow_html=True)
col_day, col_info = st.columns([2, 3])
with col_day:
    selected_day = st.selectbox("", list(by_day.keys()), label_visibility="collapsed")

day_fixtures = by_day.get(selected_day, [])
st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  STEP 3: ANALIZZA TUTTO / SINGOLA
# ─────────────────────────────────────────────
if "analysis_results" not in st.session_state:
    st.session_state["analysis_results"] = {}

col_all, col_reset, _ = st.columns([1, 1, 4])
with col_all:
    analyze_all_btn = st.button("🔍 ANALIZZA TUTTO", key="all")
with col_reset:
    if st.button("✕ RESET", key="reset"):
        st.session_state["analysis_results"] = {}
        st.rerun()

if analyze_all_btn:
    prog = st.progress(0)
    for i, (lg, f) in enumerate(day_fixtures):
        fix_id = f["fixture"]["id"]
        home   = f["teams"]["home"]["name"]
        away   = f["teams"]["away"]["name"]
        try:
            with st.spinner(f"{home} vs {away}..."):
                res = fetch_and_analyze(api_key, odds_key, f, LEAGUES[lg]["id"], lg, CURRENT_SEASON)
                st.session_state["analysis_results"][fix_id] = res
        except Exception as e:
            st.error(f"Errore {home} vs {away}: {e}")
        prog.progress((i + 1) / len(day_fixtures))
    prog.empty()
    st.rerun()

# ─────────────────────────────────────────────
#  TABELLA PRINCIPALE
# ─────────────────────────────────────────────
st.markdown('<div class="section-label">PARTITE · ' + selected_day.upper() + ' · ' + str(len(day_fixtures)) + ' MATCH</div>', unsafe_allow_html=True)

# Header tabella
header = """
<table class="match-table">
<thead>
<tr>
  <th style="width:52px;">ORA</th>
  <th style="width:52px;">LEGA</th>
  <th>PARTITA</th>
  <th style="text-align:center;width:44px;">1</th>
  <th style="text-align:center;width:44px;">X</th>
  <th style="text-align:center;width:44px;">2</th>
  <th style="text-align:center;width:52px;">O2.5</th>
  <th style="text-align:center;width:52px;">GG</th>
  <th style="text-align:center;width:80px;">xG</th>
  <th style="text-align:center;width:80px;">FORMA</th>
  <th style="text-align:center;width:72px;">PICK</th>
  <th style="width:60px;"></th>
</tr>
</thead>
<tbody>
"""

rows_html = ""
for lg, f in day_fixtures:
    fix_id = f["fixture"]["id"]
    home   = f["teams"]["home"]["name"]
    away   = f["teams"]["away"]["name"]
    try:
        kickoff_t = datetime.fromisoformat(f["fixture"]["date"].replace("Z", "+00:00")).strftime("%H:%M")
    except:
        kickoff_t = "—"

    lcolor = LEAGUES[lg]["color"]
    abbr   = LEAGUES[lg]["abbr"]
    is_analyzed = fix_id in st.session_state["analysis_results"]
    row_cls = "analyzed-row" if is_analyzed else ""

    if is_analyzed:
        res  = st.session_state["analysis_results"][fix_id]
        mkts = res["markets"]
        best = res["best"]
        lam_h= res["lam_home"]
        lam_a= res["lam_away"]
        frh  = res.get("form_raw_home", [])
        fra  = res.get("form_raw_a", [])
        pc   = pick_color_class(best["prob"])
        vbadge = '<span class="badge-value">V</span>' if best["value"] else ""
        nodata = ""

        def pct_cell(v): return f'<span class="{pct_color_class(v)}">{v}%</span>'

        rows_html += f"""
        <tr class="{row_cls}" id="row_{fix_id}">
          <td><span class="cell-time">{kickoff_t}</span></td>
          <td><span class="cell-league" style="color:{lcolor};">{abbr}</span></td>
          <td><span class="cell-teams">{home}<span class="vs">vs</span>{away}</span></td>
          <td class="cell-pct">{pct_cell(mkts['p1'])}</td>
          <td class="cell-pct">{pct_cell(mkts['px'])}</td>
          <td class="cell-pct">{pct_cell(mkts['p2'])}</td>
          <td class="cell-pct">{pct_cell(mkts['over'])}</td>
          <td class="cell-pct">{pct_cell(mkts['gg'])}</td>
          <td class="cell-xg"><span class="xg-h">{lam_h:.2f}</span><span style="color:rgba(255,255,255,0.15);"> — </span><span class="xg-a">{lam_a:.2f}</span></td>
          <td style="text-align:center;">{form_html(frh,5)}<span style="color:rgba(255,255,255,0.1);font-family:'JetBrains Mono',monospace;font-size:0.55rem;margin:0 3px;">·</span>{form_html(fra,5)}</td>
          <td style="text-align:center;"><span class="cell-pick {pc}">{best['label']}</span>{vbadge}</td>
          <td></td>
        </tr>
        """
    else:
        rows_html += f"""
        <tr class="{row_cls}" id="row_{fix_id}">
          <td><span class="cell-time">{kickoff_t}</span></td>
          <td><span class="cell-league" style="color:{lcolor};">{abbr}</span></td>
          <td><span class="cell-teams">{home}<span class="vs">vs</span>{away}</span></td>
          <td class="cell-pct"><span class="pct-dim">—</span></td>
          <td class="cell-pct"><span class="pct-dim">—</span></td>
          <td class="cell-pct"><span class="pct-dim">—</span></td>
          <td class="cell-pct"><span class="pct-dim">—</span></td>
          <td class="cell-pct"><span class="pct-dim">—</span></td>
          <td class="cell-xg"><span style="color:rgba(255,255,255,0.15);">—</span></td>
          <td></td>
          <td></td>
          <td></td>
        </tr>
        """

st.markdown(header + rows_html + "</tbody></table>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  STEP 4: BOTTONI ANALISI SINGOLA + DETTAGLI
# ─────────────────────────────────────────────
st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)

for lg, f in day_fixtures:
    fix_id = f["fixture"]["id"]
    home   = f["teams"]["home"]["name"]
    away   = f["teams"]["away"]["name"]
    is_analyzed = fix_id in st.session_state["analysis_results"]

    col_btn, col_name, _ = st.columns([1, 3, 5])
    with col_btn:
        label = "🔄" if is_analyzed else "🔍"
        if st.button(f"{label} {home[:10]} vs {away[:10]}", key=f"btn_{fix_id}"):
            with st.spinner(f"Analisi in corso..."):
                try:
                    res = fetch_and_analyze(api_key, odds_key, f, LEAGUES[lg]["id"], lg, CURRENT_SEASON)
                    st.session_state["analysis_results"][fix_id] = res
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")

    if is_analyzed:
        with st.expander(f"📊 {home} vs {away} — dettaglio completo", expanded=False):
            render_detail_panel(st.session_state["analysis_results"][fix_id])

# ─────────────────────────────────────────────
#  RIEPILOGO FINALE
# ─────────────────────────────────────────────
analyzed_results = {fid: r for fid, r in st.session_state.get("analysis_results", {}).items()
                    if any(f["fixture"]["id"] == fid for _, f in day_fixtures)}

if analyzed_results:
    st.markdown('<div class="section-label" style="margin-top:32px;">RIEPILOGO GIORNATA</div>', unsafe_allow_html=True)
    summary_rows = ""
    for _, f in day_fixtures:
        fid = f["fixture"]["id"]
        if fid not in analyzed_results: continue
        res  = analyzed_results[fid]
        best = res["best"]
        home = f["teams"]["home"]["name"]
        away = f["teams"]["away"]["name"]
        lg   = res["league_name"]
        abbr = LEAGUES[lg]["abbr"]
        ko   = res["kickoff"]
        lcolor = LEAGUES[lg]["color"]
        pc = pick_color_class(best["prob"])
        vb = '<span class="badge-value">VALUE</span>' if best["value"] else ""
        quota_str = f"×{best['odd']:.2f}" if best["odd"] > 0 else "—"
        ev_str = ""
        if best["odd"] > 0:
            ev_col  = "#32d74b" if best["ev"] > 0 else "#ff453a"
            ev_sign = "+" if best["ev"] > 0 else ""
            ev_str  = f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.68rem;color:{ev_col};">{ev_sign}{best["ev"]:.3f}</span>'
        no_odds = '<span class="badge-nodata">NO ODDS</span>' if not res["odds"] else ""

        summary_rows += f"""
        <div class="summary-row">
            <div style="display:flex;align-items:center;gap:14px;min-width:0;">
                <span style="font-family:'JetBrains Mono',monospace;font-size:0.62rem;color:rgba(255,255,255,0.28);">{ko}</span>
                <span style="font-family:'JetBrains Mono',monospace;font-size:0.6rem;color:{lcolor};">{abbr}</span>
                <span style="font-family:'Figtree',sans-serif;font-weight:500;font-size:0.85rem;color:rgba(255,255,255,0.8);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{home} <span style="color:rgba(255,255,255,0.2);font-weight:300;">vs</span> {away}</span>
                {no_odds}
            </div>
            <div style="display:flex;align-items:center;gap:20px;flex-shrink:0;">
                {ev_str}
                <span style="font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:rgba(255,255,255,0.35);">{quota_str}</span>
                <span style="font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:rgba(255,255,255,0.3);">{best['prob']}%</span>
                <span style="font-family:'JetBrains Mono',monospace;font-size:1.05rem;font-weight:700;" class="{pc}">{best['label']}</span>
                {vb}
            </div>
        </div>"""

    st.markdown(f'<div class="summary-strip">{summary_rows}</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  FOOTER
# ─────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;font-family:'JetBrains Mono',monospace;font-size:0.55rem;
color:rgba(255,255,255,0.1);letter-spacing:0.12em;padding:32px 0 16px;">
DONNY · FOOTBALL INTELLIGENCE · POISSON + FORMA · DATI: FOOTBALL-DATA.ORG · USO RESPONSABILE
</div>
""", unsafe_allow_html=True)