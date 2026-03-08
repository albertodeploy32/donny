import streamlit as st
import requests
import math
import os
import time
from itertools import product

# ─────────────────────────────────────────────
#  CONFIGURAZIONE
# ─────────────────────────────────────────────
st.set_page_config(page_title="Donny v3.0", page_icon="⚽", layout="wide")

def get_keys():
    return st.secrets.get("FOOTBALL_DATA_KEY", os.environ.get("FOOTBALL_DATA_KEY", "")).strip()

AF_KEY = get_keys()

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    .stApp { background-color: #050505; color: #ffffff; }
    .match-box { 
        background: #111; 
        border: 1px solid #222; 
        border-radius: 12px; 
        padding: 15px; 
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .btn-analyze { background: #0a84ff; color: white; border-radius: 5px; }
    .result-area { background: #1a1a1a; padding: 15px; border-radius: 8px; margin-top: 10px; border-left: 3px solid #0a84ff; }
    .disclaimer { font-size: 0.6rem; color: #444; text-align: center; margin-top: 40px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  LOGICA POISSON
# ─────────────────────────────────────────────
def poisson(lam, k):
    return (math.exp(-lam) * (lam**k) / math.factorial(k)) if lam > 0 else (1.0 if k==0 else 0.0)

def get_stats(team_id):
    url = f"https://api.football-data.org/v4/teams/{team_id}/matches"
    headers = {"X-Auth-Token": AF_KEY}
    try:
        r = requests.get(url, headers=headers, params={"status": "FINISHED", "limit": 10}, timeout=10)
        if r.status_code == 429: return None # Segnala superamento limite
        data = r.json().get("matches", [])
        gs, gc = [], []
        for m in data:
            is_h = m["homeTeam"]["id"] == team_id
            score = m["score"]["fullTime"]
            if score["home"] is None: continue
            gs.append(score["home"] if is_h else score["away"])
            gc.append(score["away"] if is_h else score["home"])
        return {"att": sum(gs)/len(gs) if gs else 1.2, "def": sum(gc)/len(gc) if gc else 1.2}
    except: return {"att": 1.2, "def": 1.2}

def run_analysis(m):
    h_s = get_stats(m['homeTeam']['id'])
    # Piccola pausa per non stressare l'API tra le due squadre
    time.sleep(1.2)
    a_s = get_stats(m['awayTeam']['id'])
    
    if h_s is None or a_s is None: return "LIMIT_ERROR"

    lh, la = (h_s['att'] * a_s['def']) / 1.3, (a_s['att'] * h_stats['def'] if 'h_stats' in locals() else a_s['att'] * h_s['def']) / 1.3
    p1, px, p2, pov = 0, 0, 0, 0
    for gh, ga in product(range(7), range(7)):
        prob = poisson(lh, gh) * poisson(la, ga)
        if gh > ga: p1 += prob
        elif gh == ga: px += prob
        else: p2 += prob
        if gh + ga > 2.5: pov += prob
    
    return {
        "1": p1*100, "X": px*100, "2": p2*100, "O2.5": pov*100, "U2.5": (1-pov)*100,
        "1X": (p1+px)*100, "X2": (px+p2)*100
    }

# ─────────────────────────────────────────────
#  APP PRINCIPALE
# ─────────────────────────────────────────────
st.title("⚽ Donny Smart Loader")
st.caption("Analisi singola per ottimizzare il limite API Free")

if not AF_KEY:
    st.error("Inserisci la chiave API nei Secrets.")
    st.stop()

league = st.selectbox("Seleziona Campionato", ["Serie A", "Premier League", "La Liga", "Bundesliga", "Ligue 1"])
l_codes = {"Serie A": "SA", "Premier League": "PL", "La Liga": "PD", "Bundesliga": "BL1", "Ligue 1": "FL1"}

# 1. Carichiamo solo la lista match (1 chiamata)
if 'matches' not in st.session_state or st.sidebar.button("Aggiorna Lista"):
    headers = {"X-Auth-Token": AF_KEY}
    r = requests.get(f"https://api.football-data.org/v4/competitions/{l_codes[league]}/matches", 
                     headers=headers, params={"status": "SCHEDULED"})
    if r.status_code == 200:
        st.session_state.matches = r.json().get("matches", [])[:15]
    else:
        st.error("Errore nel caricamento del palinsesto.")

# 2. Mostriamo i match
if 'matches' in st.session_state:
    for idx, m in enumerate(st.session_state.matches):
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"""
                <div style="padding:10px;">
                    <span style="color:#666; font-size:0.7rem;">{m['utcDate'][5:10]} {m['utcDate'][11:16]}</span><br>
                    <b style="font-size:1.1rem;">{m['homeTeam']['name']} vs {m['awayTeam']['name']}</b>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                if st.button(f"Analizza Match", key=f"btn_{m['id']}"):
                    with st.spinner("Calcolo Poisson..."):
                        res = run_analysis(m)
                        if res == "LIMIT_ERROR":
                            st.error("Limite API raggiunto. Aspetta 30 secondi.")
                        else:
                            st.session_state[f"res_{m['id']}"] = res

            # Se il risultato esiste per questo match, lo mostriamo sotto
            if f"res_{m['id']}" in st.session_state:
                r = st.session_state[f"res_{m['id']}"]
                st.markdown(f"""
                <div class="result-area">
                    <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:15px; font-family:'JetBrains Mono';">
                        <div><small>1X2</small><br><b>{r['1']:.0f}%|{r['X']:.0f}%|{r['2']:.0f}%</b></div>
                        <div><small>DOPPIE</small><br><b>{r['1X']:.0f}%|{r['X2']:.0f}%</b></div>
                        <div><small>U/O 2.5</small><br><b>U{r['U2.5']:.0f}%|O{r['O2.5']:.0f}%</b></div>
                        <div><small>PICK</small><br><b style="color:#0a84ff;">{"1X" if r['1X']>75 else "O2.5" if r['O2.5']>60 else "NO BET"}</b></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

st.markdown('<div class="disclaimer">IL GIOCO È VIETATO AI MINORI. | DONNY 3.0 LAZY-MODE</div>', unsafe_allow_html=True)