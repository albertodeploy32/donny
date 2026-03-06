import streamlit as st
import requests
import math
import os
import time
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from itertools import product

# ─────────────────────────────────────────────
#  CONFIGURAZIONE E CHIAVI
# ─────────────────────────────────────────────
st.set_page_config(page_title="Donny | Intelligence", page_icon="⚽", layout="wide")

def _load_keys():
    af = st.secrets.get("FOOTBALL_DATA_KEY", os.environ.get("FOOTBALL_DATA_KEY", ""))
    odd = st.secrets.get("ODDS_API_KEY", os.environ.get("ODDS_API_KEY", ""))
    return af.strip(), odd.strip()

_env_af, _env_odds = _load_keys()

# ─────────────────────────────────────────────
#  STILE CSS (REFINED DARK MODE)
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
*, html, body, [class*="css"] { font-family: 'Figtree', sans-serif !important; }
.stApp { background: #050505 !important; color: #eee; }
.match-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px; margin-bottom: 15px; }
.badge { font-family: 'JetBrains Mono'; font-size: 0.7rem; padding: 4px 8px; border-radius: 4px; background: rgba(10, 132, 255, 0.2); color: #0a84ff; font-weight: 700; }
.metric-box { text-align: center; padding: 10px; background: rgba(255,255,255,0.02); border-radius: 8px; }
.disclaimer { font-size: 0.6rem; color: #555; text-align: center; margin-top: 50px; text-transform: uppercase; letter-spacing: 1px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  ENGINE DI CALCOLO
# ─────────────────────────────────────────────
def poisson_prob(lam, k):
    return (math.exp(-lam) * (lam**k) / math.factorial(k)) if lam > 0 else (1.0 if k==0 else 0.0)

@st.cache_data(ttl=3600)
def get_stats(key, team_id):
    headers = {"X-Auth-Token": key}
    url = f"https://api.football-data.org/v4/teams/{team_id}/matches"
    try:
        r = requests.get(url, headers=headers, params={"status": "FINISHED", "limit": 12}, timeout=10)
        if r.status_code == 429: 
            time.sleep(5)
            return get_stats(key, team_id)
        data = r.json().get("matches", [])
        h_s, h_c, a_s, a_c = [], [], [], []
        for m in data:
            is_home = m["homeTeam"]["id"] == team_id
            score = m["score"]["fullTime"]
            if score["home"] is None: continue
            if is_home: h_s.append(score["home"]); h_c.append(score["away"])
            else: a_s.append(score["away"]); a_c.append(score["home"])
        return {
            "h_att": sum(h_s)/len(h_s) if h_s else 1.3, "h_def": sum(h_c)/len(h_c) if h_c else 1.0,
            "a_att": sum(a_s)/len(a_s) if a_s else 1.0, "a_def": sum(a_c)/len(a_c) if a_c else 1.3
        }
    except: return {"h_att": 1.3, "h_def": 1.1, "a_att": 1.0, "a_def": 1.4}

def analyze_match(af_key, m):
    h_stats = get_stats(af_key, m["homeTeam"]["id"])
    a_stats = get_stats(af_key, m["awayTeam"]["id"])
    
    # Lambda calculation (Home/Away cross-impact)
    lam_h = max((h_stats["h_att"] * a_stats["a_def"]) / 1.25, 0.2)
    lam_a = max((a_stats["a_att"] * h_stats["h_def"]) / 1.25, 0.2)
    
    matrix = {(gh, ga): poisson_prob(lam_h, gh) * poisson_prob(lam_a, ga) for gh, ga in product(range(6), range(6))}
    
    p1 = sum(v for (gh, ga), v in matrix.items() if gh > ga)
    px = sum(v for (gh, ga), v in matrix.items() if gh == ga)
    p2 = sum(v for (gh, ga), v in matrix.items() if gh < ga)
    pov = sum(v for (gh, ga), v in matrix.items() if gh + ga > 2.5)
    
    probs = {
        "1": p1*100, "X": px*100, "2": p2*100, "1X": (p1+px)*100, 
        "X2": (px+p2)*100, "12": (p1+p2)*100, "U2.5": (1-pov)*100, "O2.5": pov*100
    }
    
    best_label = "1" if p1 > p2 and p1 > px else ("2" if p2 > p1 and p2 > px else "X")
    if pov > 0.65: best_label = "O2.5"
    
    return {"probs": probs, "best": best_label, "lam_h": lam_h, "lam_a": lam_a, "matrix": matrix}

# ─────────────────────────────────────────────
#  INTERFACCIA UTENTE
# ─────────────────────────────────────────────
st.markdown('<div style="font-size: 2rem; font-weight: 800; letter-spacing: -1px;">DONNY</div>', unsafe_allow_html=True)
st.markdown('<div style="font-family: JetBrains Mono; color: #555; font-size: 0.7rem; margin-bottom: 30px;">FOOTBALL INTELLIGENCE SYSTEM</div>', unsafe_allow_html=True)

if not _env_af:
    st.warning("⚠️ Configura FOOTBALL_DATA_KEY nei Secrets di Streamlit.")
    st.stop()

# Sidebar per selezione campionati
leagues = {"Serie A": "SA", "Premier League": "PL", "La Liga": "PD", "Bundesliga": "BL1", "Ligue 1": "FL1"}
sel_league = st.sidebar.selectbox("Seleziona Campionato", list(leagues.keys()))

if st.button("🚀 AVVIA ANALISI PALINSESTO"):
    with st.spinner(f"Analizzando {sel_league}..."):
        headers = {"X-Auth-Token": _env_af}
        url = f"https://api.football-data.org/v4/competitions/{leagues[sel_league]}/matches"
        res = requests.get(url, headers=headers, params={"status": "SCHEDULED"})
        
        if res.status_code != 200:
            st.error("Errore nel recupero dati. Controlla la tua API Key.")
        else:
            matches = res.json().get("matches", [])[:10] # Analizza i primi 10 match
            
            for m in matches:
                time.sleep(0.6) # Prevenzione rate limit
                data = analyze_match(_env_af, m)
                p = data["probs"]
                
                with st.container():
                    st.markdown(f"""
                    <div class="match-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <span class="badge">{sel_league.upper()}</span>
                                <div style="font-size: 1.1rem; font-weight: 700; margin-top: 5px;">
                                    {m['homeTeam']['name']} <span style="color: #555;">v</span> {m['awayTeam']['name']}
                                </div>
                                <div style="font-size: 0.7rem; color: #888; margin-top: 2px;">{m['utcDate'][:10]} • {m['utcDate'][11:16]} UTC</div>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-family: 'JetBrains Mono'; font-size: 1.2rem; font-weight: 700; color: #0a84ff;">{data['best']}</div>
                                <div style="font-size: 0.6rem; color: #555;">SUGGESTED PICK</div>
                            </div>
                        </div>
                        <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.05); margin: 15px 0;">
                        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;">
                            <div class="metric-box"><div style="font-size: 0.6rem; color: #888;">1X2</div><div style="font-weight:600;">{p['1']:.0f}% · {p['X']:.0f}% · {p['2']:.0f}%</div></div>
                            <div class="metric-box"><div style="font-size: 0.6rem; color: #888;">DOPPIA CHANCE</div><div style="font-weight:600;">{p['1X']:.0f}% · {p['X2']:.0f}%</div></div>
                            <div class="metric-box"><div style="font-size: 0.6rem; color: #888;">GOL TOTALI</div><div style="font-weight:600;">U {p['U2.5']:.0f}% · O {p['O2.5']:.0f}%</div></div>
                            <div class="metric-box"><div style="font-size: 0.6rem; color: #888;">EXP. GOL</div><div style="font-weight:600;">{data['lam_h']:.2f} - {data['lam_a']:.2f}</div></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

st.markdown("""
<div class="disclaimer">
    IL GIOCO È VIETATO AI MINORI DI 18 ANNI E PUÒ CAUSARE DIPENDENZA PATOLOGICA.<br>
    DONNY INTELLIGENCE SYSTEM • DATA PROVIDED BY FOOTBALL-DATA.ORG
</div>
""", unsafe_allow_html=True)