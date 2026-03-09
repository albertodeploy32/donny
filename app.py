import streamlit as st
import requests
import math
import os
import time
from itertools import product
from datetime import datetime

# ─────────────────────────────────────────────
#  CONFIGURAZIONE
# ─────────────────────────────────────────────
st.set_page_config(page_title="Donny v3.5 PRO", page_icon="⚽", layout="wide")

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
    }
    .result-area { 
        background: #1a1a1a; 
        padding: 15px; 
        border-radius: 8px; 
        margin-top: 10px; 
        border-left: 4px solid #0a84ff;
    }
    .pick-badge {
        background: #0a84ff;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .disclaimer { font-size: 0.6rem; color: #444; text-align: center; margin-top: 40px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  LOGICA AVANZATA POISSON & TRENDS
# ─────────────────────────────────────────────
def poisson(lam, k):
    return (math.exp(-lam) * (lam**k) / math.factorial(k)) if lam > 0 else (1.0 if k==0 else 0.0)

def get_weighted_stats(team_id, venue_type="HOME"):
    """
    Calcola statistiche pesate:
    - Differenzia Casa/Trasferta
    - Decadimento temporale (partite recenti pesano di più)
    - Filtro Outlier (limita i risultati estremi)
    """
    url = f"https://api.football-data.org/v4/teams/{team_id}/matches"
    headers = {"X-Auth-Token": AF_KEY}
    try:
        r = requests.get(url, headers=headers, params={"status": "FINISHED", "limit": 12}, timeout=10)
        if r.status_code == 429: return "LIMIT"
        matches = r.json().get("matches", [])
        
        gs_weighted, gc_weighted = [], []
        weights = [1.5, 1.3, 1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3] # Decadimento
        
        for i, m in enumerate(matches):
            is_home = m["homeTeam"]["id"] == team_id
            # Pesa di più se la condizione Casa/Trasferta coincide con il match analizzato
            venue_multiplier = 1.2 if (is_home and venue_type == "HOME") or (not is_home and venue_type == "AWAY") else 0.8
            
            score = m["score"]["fullTime"]
            if score["home"] is None: continue
            
            # Filtro Outlier: i gol oltre i 4 vengono "calmati" per non falsare troppo la media
            raw_gs = score["home"] if is_home else score["away"]
            raw_gc = score["away"] if is_home else score["home"]
            
            clean_gs = raw_gs if raw_gs <= 4 else 4 + (raw_gs - 4) * 0.2
            clean_gc = raw_gc if raw_gc <= 4 else 4 + (raw_gc - 4) * 0.2
            
            final_weight = weights[i] * venue_multiplier
            gs_weighted.append(clean_gs * final_weight)
            gc_weighted.append(clean_gc * final_weight)
            
        if not gs_weighted: return {"att": 1.2, "def": 1.2}
        
        avg_weight = sum(weights[:len(gs_weighted)])
        return {
            "att": sum(gs_weighted) / avg_weight,
            "def": sum(gc_weighted) / avg_weight
        }
    except:
        return {"att": 1.1, "def": 1.3}

def run_advanced_analysis(m, league_avg_goals=2.6):
    """
    Analisi cross-market e calcolo dinamico basato su media campionato.
    """
    h_s = get_weighted_stats(m['homeTeam']['id'], "HOME")
    if h_s == "LIMIT": return "LIMIT_ERROR"
    time.sleep(1.0) # Protezione API
    
    a_s = get_weighted_stats(m['awayTeam']['id'], "AWAY")
    if a_s == "LIMIT": return "LIMIT_ERROR"

    # Calcolo Lambda basato sulla forza relativa rispetto alla media campionato
    # Formula: (Attacco_Casa * Difesa_Ospite) / Media_Campionato
    base_avg = league_avg_goals / 2
    lh = (h_s['att'] * a_s['def']) / base_avg
    la = (a_s['att'] * h_s['def']) / base_avg
    
    p1, px, p2, pov, pgg = 0, 0, 0, 0, 0
    for gh, ga in product(range(7), range(7)):
        prob = poisson(lh, gh) * poisson(la, ga)
        if gh > ga: p1 += prob
        elif gh == ga: px += prob
        else: p2 += prob
        if gh + ga > 2.5: pov += prob
        if gh > 0 and ga > 0: pgg += prob
    
    # Logica di raffinamento PICK (Incrocio mercati)
    res = {
        "1": p1*100, "X": px*100, "2": p2*100, "O2.5": pov*100, "U2.5": (1-pov)*100,
        "GG": pgg*100, "1X": (p1+px)*100, "X2": (px+p2)*100
    }
    
    # Algoritmo decisionale per il PICK
    pick = "NO BET"
    if res['1X'] > 82 and res['1'] > 45: pick = "1X + UNDER 4.5"
    elif res['X2'] > 82 and res['2'] > 45: pick = "X2"
    elif res['O2.5'] > 65 and res['GG'] > 55: pick = "OVER 2.5"
    elif res['U2.5'] > 65 and res['X'] > 30: pick = "UNDER 2.5"
    elif res['GG'] > 70: pick = "GOAL"
    
    return {**res, "PICK": pick}

# ─────────────────────────────────────────────
#  INTERFACCIA STREAMLIT
# ─────────────────────────────────────────────
st.title("⚽ Donny Smart Loader v3.5")
st.caption("Motore Statistico Avanzato: Ponderazione Temporale e Analisi Casa/Trasferta")

if not AF_KEY:
    st.error("Inserisci la chiave API nei Secrets.")
    st.stop()

col_l, col_r = st.columns([2, 1])
with col_l:
    league = st.selectbox("Seleziona Campionato", ["Serie A", "Premier League", "La Liga", "Bundesliga", "Ligue 1"])
with col_r:
    # Media gol stimata per campionato per affinare Poisson
    l_meta = {
        "Serie A": {"id": "SA", "avg": 2.62},
        "Premier League": {"id": "PL", "avg": 2.85},
        "La Liga": {"id": "PD", "avg": 2.55},
        "Bundesliga": {"id": "BL1", "avg": 3.10},
        "Ligue 1": {"id": "FL1", "avg": 2.70}
    }

if 'matches' not in st.session_state or st.sidebar.button("🔄 Aggiorna Palinsesto"):
    headers = {"X-Auth-Token": AF_KEY}
    r = requests.get(f"https://api.football-data.org/v4/competitions/{l_meta[league]['id']}/matches", 
                     headers=headers, params={"status": "SCHEDULED"})
    if r.status_code == 200:
        st.session_state.matches = r.json().get("matches", [])[:15]
    else:
        st.error("Errore API. Controlla il piano o la chiave.")

if 'matches' in st.session_state:
    for m in st.session_state.matches:
        with st.container():
            c1, c2 = st.columns([3, 1])
            with c1:
                date_str = m['utcDate'].replace("T", " ").replace("Z", "")
                st.markdown(f"""
                <div style="padding:10px; border-bottom: 1px solid #222;">
                    <span style="color:#888; font-size:0.75rem;">{date_str[5:16]}</span><br>
                    <b style="font-size:1.1rem; color:#0a84ff;">{m['homeTeam']['shortName']}</b> vs 
                    <b style="font-size:1.1rem; color:#0a84ff;">{m['awayTeam']['shortName']}</b>
                </div>
                """, unsafe_allow_html=True)
            
            with c2:
                if st.button(f"Analisi Pro", key=f"btn_{m['id']}", use_container_width=True):
                    with st.spinner("Analisi in corso..."):
                        res = run_advanced_analysis(m, l_meta[league]['avg'])
                        if res == "LIMIT_ERROR":
                            st.warning("⚠️ Limite API raggiunto. Attendi 1 minuto.")
                        else:
                            st.session_state[f"res_{m['id']}"] = res

            if f"res_{m['id']}" in st.session_state:
                r = st.session_state[f"res_{m['id']}"]
                st.markdown(f"""
                <div class="result-area">
                    <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:10px; font-family:'JetBrains Mono'; text-align:center;">
                        <div><small style="color:#888;">1 X 2</small><br><b>{r['1']:.0f}%|{r['X']:.0f}%|{r['2']:.0f}%</b></div>
                        <div><small style="color:#888;">GOAL/NO GOAL</small><br><b>GG {r['GG']:.0f}%</b></div>
                        <div><small style="color:#888;">U/O 2.5</small><br><b>U{r['U2.5']:.0f}%|O{r['O2.5']:.0f}%</b></div>
                        <div><small style="color:#888;">SUGGERIMENTO</small><br><span class="pick-badge">{r['PICK']}</span></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

st.markdown('<div class="disclaimer">DATI BASATI SU MODELLO MATEMATICO. IL GIOCO PUÒ CAUSARE DIPENDENZA. | V3.5 ENHANCED</div>', unsafe_allow_html=True)