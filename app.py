import streamlit as st
import requests
import math
import os
import time
from itertools import product

# ─────────────────────────────────────────────
#  CONFIGURAZIONE INITIALE
# ─────────────────────────────────────────────
st.set_page_config(page_title="Donny v2.4", page_icon="⚽", layout="wide")

def get_api_key():
    # Cerca prima nei secrets di Streamlit, poi in env
    key = st.secrets.get("FOOTBALL_DATA_KEY", os.environ.get("FOOTBALL_DATA_KEY", ""))
    return key.strip()

AF_KEY = get_api_key()

# CSS per stabilità visiva
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    .stApp { background-color: #050505; color: #ffffff; }
    .card { background: #111; border: 1px solid #222; border-radius: 10px; padding: 20px; margin-bottom: 15px; }
    .pick { color: #0a84ff; font-weight: bold; font-family: 'JetBrains Mono'; border: 1px solid #0a84ff; padding: 2px 8px; border-radius: 4px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-top: 15px; }
    .stat-val { font-family: 'JetBrains Mono'; font-size: 0.85rem; }
    .disclaimer { font-size: 0.6rem; color: #444; text-align: center; margin-top: 50px; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  MOTORE DI CALCOLO (RESILIENTE)
# ─────────────────────────────────────────────
def poisson(lam, k):
    return (math.exp(-lam) * (lam**k) / math.factorial(k)) if lam > 0 else (1.0 if k==0 else 0.0)

@st.cache_data(ttl=3600) # Cache di 1 ora per risparmiare chiamate API
def get_team_data(team_id):
    if not AF_KEY: return {"att": 1.2, "def": 1.2}
    
    url = f"https://api.football-data.org/v4/teams/{team_id}/matches"
    headers = {"X-Auth-Token": AF_KEY}
    
    try:
        # Pausa forzata per rispettare il limite di 10 req/min
        time.sleep(2.0) 
        response = requests.get(url, headers=headers, params={"status": "FINISHED", "limit": 10}, timeout=15)
        
        if response.status_code == 429:
            st.warning("⏱️ Limite API raggiunto. Pausa di sicurezza...")
            time.sleep(15)
            return get_team_data(team_id)
            
        data = response.json()
        matches = data.get("matches", [])
        
        scored, conceded = [], []
        for m in matches:
            score = m.get("score", {}).get("fullTime", {})
            if score.get("home") is None: continue
            
            is_home = m["homeTeam"]["id"] == team_id
            s = score["home"] if is_home else score["away"]
            c = score["away"] if is_home else score["home"]
            scored.append(s); conceded.append(c)
            
        return {
            "att": sum(scored)/len(scored) if scored else 1.2,
            "def": sum(conceded)/len(conceded) if conceded else 1.2
        }
    except Exception:
        return {"att": 1.2, "def": 1.2} # Fallback neutro se l'API fallisce

def analyze_match(m):
    h_stats = get_team_data(m['homeTeam']['id'])
    a_stats = get_team_data(m['awayTeam']['id'])
    
    # Lambda calc
    lh = (h_stats['att'] * a_stats['def']) / 1.28
    la = (a_stats['att'] * h_stats['def']) / 1.28
    
    # Probabilità
    p1, px, p2, pov = 0, 0, 0, 0
    for gh, ga in product(range(7), range(7)):
        prob = poisson(lh, gh) * poisson(la, ga)
        if gh > ga: p1 += prob
        elif gh == ga: px += prob
        else: p2 += prob
        if gh + ga > 2.5: pov += prob
        
    res = {
        "1": p1*100, "X": px*100, "2": p2*100,
        "1X": (p1+px)*100, "X2": (px+p2)*100, "12": (p1+p2)*100,
        "U2.5": (1-pov)*100, "O2.5": pov*100
    }
    
    # Pick Logic
    best = "X"
    if p1 > px and p1 > p2: best = "1"
    elif p2 > px and p2 > p1: best = "2"
    if pov > 0.65: best = "O2.5"
    
    return res, best

# ─────────────────────────────────────────────
#  INTERFACCIA
# ─────────────────────────────────────────────
st.title("⚽ Donny Intelligence")

if not AF_KEY:
    st.error("Inserisci la chiave 'FOOTBALL_DATA_KEY' nei Secrets di Streamlit.")
    st.stop()

league_choice = st.selectbox("Scegli Campionato", ["Serie A", "Premier League", "La Liga", "Bundesliga", "Ligue 1"])
l_codes = {"Serie A": "SA", "Premier League": "PL", "La Liga": "PD", "Bundesliga": "BL1", "Ligue 1": "FL1"}

if st.button("ESEGUI ANALISI"):
    headers = {"X-Auth-Token": AF_KEY}
    try:
        url = f"https://api.football-data.org/v4/competitions/{l_codes[league_choice]}/matches"
        resp = requests.get(url, headers=headers, params={"status": "SCHEDULED"}, timeout=15)
        
        if resp.status_code != 200:
            st.error(f"Errore API: {resp.status_code}. Controlla la tua chiave.")
        else:
            matches = resp.json().get("matches", [])[:8] # Analizziamo solo i primi 8 per sicurezza
            
            if not matches:
                st.info("Nessun match in programma.")
            
            for m in matches:
                with st.spinner(f"Calcolo in corso: {m['homeTeam']['shortName']}..."):
                    probs, pick = analyze_match(m)
                    
                    st.markdown(f"""
                    <div class="card">
                        <div style="display:flex; justify-content:space-between;">
                            <span style="font-size:1.1rem; font-weight:700;">{m['homeTeam']['name']} vs {m['awayTeam']['name']}</span>
                            <span class="pick">{pick}</span>
                        </div>
                        <div class="grid">
                            <div><span style="color:#666; font-size:0.7rem;">1X2</span><br><span class="stat-val">{probs['1']:.0f}% | {probs['X']:.0f}% | {probs['2']:.0f}%</span></div>
                            <div><span style="color:#666; font-size:0.7rem;">DOPPIA CHANCE</span><br><span class="stat-val">{probs['1X']:.0f}% | {probs['X2']:.0f}%</span></div>
                            <div><span style="color:#666; font-size:0.7rem;">UNDER/OVER</span><br><span class="stat-val">U {probs['U2.5']:.0f}% | O {probs['O2.5']:.0f}%</span></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Si è verificato un errore: {e}")

st.markdown('<div class="disclaimer">Il gioco è vietato ai minori e può causare dipendenza patologica.</div>', unsafe_allow_html=True)