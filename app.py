import streamlit as st
import requests
import math
import os
import time
import pandas as pd
import plotly.graph_objects as go
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
#  PAGE CONFIG & CSS
# ─────────────────────────────────────────────
st.set_page_config(page_title="Donny | Football Intelligence", page_icon="⚽", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

*, html, body, [class*="css"] {
    font-family: 'Figtree', sans-serif !important;
    -webkit-font-smoothing: antialiased;
}

.stApp {
    background: #050505 !important;
    background-image: radial-gradient(circle at 50% -20%, #1a1a1a 0%, #050505 80%) !important;
}

/* Typography */
.app-wordmark { font-weight: 800; font-size: 1.8rem; letter-spacing: -0.04em; color: #fff; }
.app-tagline { font-family: 'JetBrains Mono', monospace !important; font-size: 0.65rem; letter-spacing: 0.2em; color: rgba(255,255,255,0.3); text-transform: uppercase; }
.section-label { font-family: 'JetBrains Mono', monospace !important; font-size: 0.6rem; letter-spacing: 0.15em; color: #0a84ff; text-transform: uppercase; margin: 25px 0 10px; }

/* Table Styling */
.match-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
.match-table th { font-family: 'JetBrains Mono', monospace !important; font-size: 0.6rem; color: rgba(255,255,255,0.3); text-align: left; padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); }
.match-table td { padding: 12px 10px; border-bottom: 1px solid rgba(255,255,255,0.05); color: #eee; font-size: 0.85rem; }
.analyzed-row { background: rgba(10, 132, 255, 0.03); border-left: 3px solid #0a84ff; }

/* Badges */
.badge-value { background: rgba(48,209,88,0.15); color: #32d74b; padding: 2px 6px; border-radius: 4px; font-size: 0.6rem; font-weight: 700; font-family: 'JetBrains Mono'; }
.pct-green { color: #32d74b; font-weight: 600; }
.pct-yellow { color: #ffd60a; }
.pct-red { color: #ff453a; }

/* Custom Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  COSTANTI & ENGINE
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
CURRENT_SEASON = datetime.now().year if datetime.now().month >= 8 else datetime.now().year - 1

def poisson_prob(lam: float, k: int) -> float:
    if lam <= 0: return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

def build_refined_matrix(lam_h: float, lam_a: float, max_g: int = 5):
    matrix = {}
    for gh, ga in product(range(max_g + 1), range(max_g + 1)):
        matrix[(gh, ga)] = poisson_prob(lam_h, gh) * poisson_prob(lam_a, ga)
    return matrix

# ─────────────────────────────────────────────
#  API HELPERS (Con Throttling)
# ─────────────────────────────────────────────
def _af_get(endpoint: str, key: str, params: dict = None):
    # Rispetto del rate limit (10 req/min -> 1 ogni 6s teorici, ma Streamlit usa cache)
    headers = {"X-Auth-Token": key}
    r = requests.get(f"{FD_BASE}/{endpoint}", headers=headers, params=params, timeout=15)
    if r.status_code == 429:
        st.warning("⏱️ Rate limit raggiunto. Attendo 10 secondi...")
        time.sleep(10)
        return _af_get(endpoint, key, params)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=3600)
def get_team_stats(key: str, team_id: int, last: int = 12):
    data = _af_get(f"teams/{team_id}/matches", key, {"status": "FINISHED", "limit": last})
    matches = data.get("matches", [])
    
    stats = {"h_scored": [], "h_conceded": [], "a_scored": [], "a_conceded": [], "form": []}
    for m in matches:
        is_home = m["homeTeam"]["id"] == team_id
        gh = m["score"]["fullTime"]["home"]
        ga = m["score"]["fullTime"]["away"]
        
        if gh is None or ga is None: continue
        
        res = "D"
        if (is_home and gh > ga) or (not is_home and ga > gh): res = "W"
        elif (is_home and gh < ga) or (not is_home and ga < gh): res = "L"
        stats["form"].append(res)
        
        if is_home:
            stats["h_scored"].append(gh); stats["h_conceded"].append(ga)
        else:
            stats["a_scored"].append(ga); stats["a_conceded"].append(gh)
            
    return stats

# ─────────────────────────────────────────────
#  CORE ANALYSIS
# ─────────────────────────────────────────────
def compute_form_weight(results: list) -> float:
    if not results: return 1.0
    recent = results[-6:]
    pts = {"W": 3, "D": 1, "L": 0}
    score = sum(pts.get(r, 1) for r in recent)
    max_pts = len(recent) * 3
    # Ritorna un moltiplicatore tra 0.8 e 1.2
    return 0.8 + (score / max_pts) * 0.4

def analyze_match(af_key: str, odds_key: str, fixture: dict, league_name: str):
    h_id, a_id = fixture["teams"]["home"]["id"], fixture["teams"]["away"]["id"]
    
    # Throttling preventivo per evitare 429 durante loop
    time.sleep(0.5) 
    
    h_stats = get_team_stats(af_key, h_id)
    a_stats = get_team_stats(af_key, a_id)
    
    # Medie gol (Modello Casa/Fuori)
    # Se mancano dati, usiamo una media campionato standard 1.35
    avg_h_score = sum(h_stats["h_scored"]) / len(h_stats["h_scored"]) if h_stats["h_scored"] else 1.4
    avg_h_conc  = sum(h_stats["h_conceded"]) / len(h_stats["h_conceded"]) if h_stats["h_conceded"] else 1.1
    avg_a_score = sum(a_stats["a_scored"]) / len(a_stats["a_scored"]) if a_stats["a_scored"] else 1.1
    avg_a_conc  = sum(a_stats["a_conceded"]) / len(a_stats["a_conceded"]) if a_stats["a_conceded"] else 1.4
    
    # Moltiplicatore forma
    f_h = compute_form_weight(h_stats["form"])
    f_a = compute_form_weight(a_stats["form"])
    
    # Calcolo Lambda (Punti di forza incrociati)
    lam_h = max(avg_h_score * avg_a_conc * f_h / 1.35, 0.2)
    lam_a = max(avg_a_score * avg_h_conc * f_a / 1.35, 0.2)
    
    matrix = build_refined_matrix(lam_h, lam_a)
    
    # Mercati
    p1 = sum(v for (gh, ga), v in matrix.items() if gh > ga)
    px = sum(v for (gh, ga), v in matrix.items() if gh == ga)
    p2 = sum(v for (gh, ga), v in matrix.items() if gh < ga)
    pov = sum(v for (gh, ga), v in matrix.items() if gh + ga > 2.5)
    pgg = sum(v for (gh, ga), v in matrix.items() if gh > 0 and ga > 0)
    
    # Pick Logica
    best_label, best_pct = "X", px*100
    if p1 > px and p1 > p2: best_label, best_pct = "1", p1*100
    elif p2 > px and p2 > p1: best_label, best_pct = "2", p2*100
    
    if pov * 100 > 62: best_label, best_pct = "O2.5", pov*100
    
    return {
        "lam_h": lam_h, "lam_a": lam_a,
        "probs": {"1": p1*100, "X": px*100, "2": p2*100, "O2.5": pov*100, "GG": pgg*100},
        "best": {"label": best_label, "prob": round(best_pct, 1)},
        "matrix": matrix,
        "form": {"h": h_stats["form"][-5:], "a": a_stats["form"][-5:]}
    }

# ─────────────────────────────────────────────
#  UI COMPONENTS
# ─────────────────────────────────────────────
def draw_heatmap(matrix):
    z = [[0]*6 for _ in range(6)]
    for (gh, ga), v in matrix.items():
        if gh < 6 and ga < 6: z[ga][gh] = round(v * 100, 1)
    
    fig = go.Figure(data=go.Heatmap(
        z=z, x=[0,1,2,3,4,5], y=[0,1,2,3,4,5],
        colorscale='Blues', showscale=False,
        text=z, texttemplate="%{text}%", textfont={"size":10, "color":"white"}
    ))
    fig.update_layout(
        title="Probabilità Risultato Esatto",
        xaxis_title="Gol Casa", yaxis_title="Gol Ospiti",
        height=300, margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color="rgba(255,255,255,0.5)", size=10)
    )
    return fig

# ─────────────────────────────────────────────
#  APP MAIN
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="app-wordmark">donny</div><div class="app-tagline">Pro Analitica</div>', unsafe_allow_html=True)
    st.markdown("---")
    af_key = st.text_input("Football-Data Key", value=_env_af, type="password")
    sel_leagues = st.multiselect("Campionati", list(LEAGUES.keys()), default=list(LEAGUES.keys()))

if not af_key:
    st.info("Configura la chiave API nella sidebar per iniziare.")
    st.stop()

# Header
st.markdown('<div class="section-label">Dashboard Predittiva</div>', unsafe_allow_html=True)
col_btn, col_info = st.columns([1, 3])

if "data" not in st.session_state: st.session_state.data = {}

if col_btn.button("⚽ AGGIORNA PALINSESTO"):
    with st.spinner("Recupero partite in corso..."):
        all_fx = []
        for l_name in sel_leagues:
            l_id = FD_LEAGUE_MAP[LEAGUES[l_name]["id"]]
            res = _af_get(f"competitions/{l_id}/matches", af_key, {
                "dateFrom": datetime.now().strftime("%Y-%m-%d"),
                "dateTo": (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d")
            })
            for m in res.get("matches", []):
                all_fx.append({"league": l_name, "match": m})
        st.session_state.palinsesto = all_fx

if "palinsesto" in st.session_state:
    palinsesto = st.session_state.palinsesto
    
    # Tabella
    st.markdown("""
    <table class="match-table">
        <thead>
            <tr>
                <th>DATA</th><th>LEGA</th><th>MATCH</th><th>1</th><th>X</th><th>2</th><th>O2.5</th><th>PICK</th>
            </tr>
        </thead>
        <tbody>
    """, unsafe_allow_html=True)
    
    for item in palinsesto:
        m = item["match"]
        l_name = item["league"]
        mid = m["id"]
        
        # Analisi automatica al volo (o caricata da sessione)
        if mid not in st.session_state.data:
            with st.spinner(f"Analisi {m['homeTeam']['name']}..."):
                try:
                    st.session_state.data[mid] = analyze_match(af_key, "", {
                        "teams": {"home": {"id": m["homeTeam"]["id"]}, "away": {"id": m["awayTeam"]["id"]}}
                    }, l_name)
                except: continue
        
        res = st.session_state.data[mid]
        p = res["probs"]
        
        def color_pct(v): return "pct-green" if v > 50 else ("pct-yellow" if v > 35 else "")

        st.markdown(f"""
        <tr class="analyzed-row">
            <td style="font-family:JetBrains Mono; font-size:0.7rem;">{m['utcDate'][5:10]} {m['utcDate'][11:16]}</td>
            <td style="color:{LEAGUES[l_name]['color']}; font-weight:700;">{LEAGUES[l_name]['abbr']}</td>
            <td><strong>{m['homeTeam']['shortName']}</strong> vs {m['awayTeam']['shortName']}</td>
            <td class="{color_pct(p['1'])}">{p['1']:.0f}%</td>
            <td class="{color_pct(p['X'])}">{p['X']:.0f}%</td>
            <td class="{color_pct(p['2'])}">{p['2']:.0f}%</td>
            <td class="{color_pct(p['O2.5'])}">{p['O2.5']:.0f}%</td>
            <td><span class="badge-value">{res['best']['label']}</span></td>
        </tr>
        """, unsafe_allow_html=True)
    
    st.markdown("</tbody></table>", unsafe_allow_html=True)

    # Dettagli Espandibili
    st.markdown('<div class="section-label">Dettaglio Analisi Avanzata</div>', unsafe_allow_html=True)
    for item in palinsesto:
        m = item["match"]
        mid = m["id"]
        if mid in st.session_state.data:
            with st.expander(f"📊 {m['homeTeam']['name']} vs {m['awayTeam']['name']}"):
                res = st.session_state.data[mid]
                c1, c2, c3 = st.columns([2, 2, 3])
                
                with c1:
                    st.metric("Expected Goals Casa", f"{res['lam_h']:.2f}")
                    st.write(f"Forma Casa: {' '.join(res['form']['h'])}")
                with c2:
                    st.metric("Expected Goals Ospiti", f"{res['lam_a']:.2f}")
                    st.write(f"Forma Ospiti: {' '.join(res['form']['a'])}")
                with c3:
                    st.plotly_chart(draw_heatmap(res["matrix"]), use_container_width=True)

st.markdown('<div style="text-align:center; margin-top:50px; opacity:0.2; font-size:0.6rem;">DONNY ENGINE V2.1 • AGGIORNAMENTO DINAMICO</div>', unsafe_allow_html=True)