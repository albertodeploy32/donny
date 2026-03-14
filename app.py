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
st.set_page_config(page_title="Donny v3.6 AI-PRO", page_icon="⚽", layout="wide")

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
        border-left: 4px solid #00d1ff;
    }
    .pick-badge {
        background: #00d1ff;
        color: black;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 0.9rem;
    }
    .disclaimer { font-size: 0.6rem; color: #444; text-align: center; margin-top: 40px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  LOGICA PREDITTIVA AVANZATA
# ─────────────────────────────────────────────

def poisson(lam, k):
    """Calcola la distribuzione di Poisson standard."""
    return (math.exp(-lam) * (lam**k) / math.factorial(k)) if lam > 0 else (1.0 if k==0 else 0.0)

def dixon_coles_adjustment(gh, ga, lh, la, rho=0.15):
    """
    Applica l'aggiustamento di Dixon-Coles per correggere la correlazione 
    sui punteggi bassi (0-0, 1-0, 0-1, 1-1) tipica della Poisson indipendente.
    """
    if gh == 0 and ga == 0:
        return 1 - (lh * la * rho)
    elif gh == 1 and ga == 0:
        return 1 + (la * rho)
    elif gh == 0 and ga == 1:
        return 1 + (lh * rho)
    elif gh == 1 and ga == 1:
        return 1 - rho
    return 1.0

def get_advanced_stats(team_id, venue_type="HOME"):
    """
    Calcola statistiche con Clean Sheet Factor e Peso Temporale.
    """
    url = f"https://api.football-data.org/v4/teams/{team_id}/matches"
    headers = {"X-Auth-Token": AF_KEY}
    try:
        r = requests.get(url, headers=headers, params={"status": "FINISHED", "limit": 10}, timeout=10)
        if r.status_code == 429: return "LIMIT"
        matches = r.json().get("matches", [])
        
        gs_weighted, gc_weighted = [], []
        clean_sheets = 0
        weights = [1.5, 1.4, 1.3, 1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 0.6]
        
        for i, m in enumerate(matches):
            is_home = m["homeTeam"]["id"] == team_id
            score = m["score"]["fullTime"]
            if score["home"] is None: continue
            
            raw_gs = score["home"] if is_home else score["away"]
            raw_gc = score["away"] if is_home else score["home"]
            
            # Clean Sheet Detection
            if raw_gc == 0: clean_sheets += 1
            
            # Outlier damping (Cap a 4 gol con crescita logaritmica oltre)
            clean_gs = raw_gs if raw_gs <= 4 else 4 + math.log(raw_gs - 3)
            clean_gc = raw_gc if raw_gc <= 4 else 4 + math.log(raw_gc - 3)
            
            # Venue Weighting: Pesa di più i match giocati nella stessa condizione (Casa/Trasferta)
            venue_mult = 1.25 if (is_home and venue_type == "HOME") or (not is_home and venue_type == "AWAY") else 0.75
            
            final_w = weights[i] * venue_mult
            gs_weighted.append(clean_gs * final_w)
            gc_weighted.append(clean_gc * final_w)
            
        if not gs_weighted: return {"att": 1.1, "def": 1.2, "cs_factor": 1.0}
        
        avg_w = sum(weights[:len(gs_weighted)])
        cs_bonus = 1.0 - (clean_sheets / len(gs_weighted)) * 0.15 # Riduce la Lambda subita se fa molti Clean Sheets
        
        return {
            "att": sum(gs_weighted) / avg_w,
            "def": (sum(gc_weighted) / avg_w) * cs_bonus,
            "cs_factor": cs_bonus
        }
    except:
        return {"att": 1.0, "def": 1.3, "cs_factor": 1.0}

def run_pro_analysis(m, league_avg):
    """
    Analisi Bivariante Dixon-Coles con Home Advantage Dinamico.
    """
    h_s = get_advanced_stats(m['homeTeam']['id'], "HOME")
    if h_s == "LIMIT": return "LIMIT_ERROR"
    time.sleep(0.6) # Anti-throttle
    
    a_s = get_advanced_stats(m['awayTeam']['id'], "AWAY")
    if a_s == "LIMIT": return "LIMIT_ERROR"

    # 1. Calcolo Home Advantage Dinamico (approssimato sul campionato selezionato)
    # Nelle versioni future lo calcoleremo sui dati storici totali, ora usiamo un delta basato su medie
    base_lam = league_avg / 2
    
    # 2. Definizione Lambda Attesa
    lh = (h_s['att'] * a_s['def']) / base_lam
    la = (a_s['att'] * h_s['def']) / base_lam
    
    # Correzione empirica per il vantaggio campo basata sulla media campionato
    lh *= 1.10 
    la *= 0.90

    # 3. Matrice delle Probabilità (Bivariate Adjustment)
    p1, px, p2, pov25, pgg, p_under15 = 0, 0, 0, 0, 0, 0
    
    for gh, ga in product(range(7), range(7)):
        # Probabilità Poisson indipendente
        prob = poisson(lh, gh) * poisson(la, ga)
        
        # Applicazione Dixon-Coles per migliorare l'accuratezza dei pareggi
        adj = dixon_coles_adjustment(gh, ga, lh, la)
        prob *= adj
        
        if gh > ga: p1 += prob
        elif gh == ga: px += prob
        else: p2 += prob
        
        if gh + ga > 2.5: pov25 += prob
        if gh + ga < 1.5: p_under15 += prob
        if gh > 0 and ga > 0: pgg += prob
    
    # Normalizzazione (per sicurezza dopo aggiustamenti)
    total_p = p1 + px + p2
    res = {
        "1": (p1/total_p)*100, "X": (px/total_p)*100, "2": (p2/total_p)*100,
        "O2.5": pov25*100, "U2.5": (1-pov25)*100, "GG": pgg*100,
        "U1.5": p_under15*100
    }
    
    # 4. ALGORITMO DECISIONALE "SMART PICK"
    pick = "NO BET"
    # Priorità 1: Alta affidabilità 1X / X2
    if res['1'] + res['X'] > 84: pick = "1X + UNDER 4.5"
    elif res['2'] + res['X'] > 84: pick = "X2 + UNDER 4.5"
    # Priorità 2: Trend Gol/NoGol
    elif res['GG'] > 68 and res['O2.5'] > 60: pick = "GOAL + OVER 2.5"
    elif res['U2.5'] > 64 and res['U1.5'] < 35: pick = "UNDER 3.5"
    elif res['GG'] > 72: pick = "GOAL"
    # Priorità 3: Value Bet su Segno
    elif res['1'] > 65: pick = "1 FISSO"
    elif res['2'] > 60: pick = "2 FISSO"
    
    return {**res, "PICK": pick}

# ─────────────────────────────────────────────
#  INTERFACCIA STREAMLIT
# ─────────────────────────────────────────────
st.title("⚽ Donny Smart Loader v3.6 AI-PRO")
st.caption("Modello Dixon-Coles Bivariante | Clean Sheet Factor | Analisi Pesata")

if not AF_KEY:
    st.error("Inserisci la chiave API nei Secrets.")
    st.stop()

# Layout Campionato
l_meta = {
    "Serie A": {"id": "SA", "avg": 2.62},
    "Premier League": {"id": "PL", "avg": 2.85},
    "La Liga": {"id": "PD", "avg": 2.55},
    "Bundesliga": {"id": "BL1", "avg": 3.10},
    "Ligue 1": {"id": "FL1", "avg": 2.70}
}

league_name = st.selectbox("Seleziona Campionato", list(l_meta.keys()))

if 'matches' not in st.session_state or st.sidebar.button("🔄 Carica Nuovi Match"):
    headers = {"X-Auth-Token": AF_KEY}
    try:
        r = requests.get(f"https://api.football-data.org/v4/competitions/{l_meta[league_name]['id']}/matches", 
                         headers=headers, params={"status": "SCHEDULED"})
        if r.status_code == 200:
            st.session_state.matches = r.json().get("matches", [])[:12]
        else:
            st.error(f"Errore API {r.status_code}. Controlla il piano.")
    except Exception as e:
        st.error(f"Connessione fallita: {e}")

if 'matches' in st.session_state:
    for m in st.session_state.matches:
        with st.container():
            c1, c2 = st.columns([3, 1])
            with c1:
                date_obj = datetime.strptime(m['utcDate'], "%Y-%m-%dT%H:%M:%SZ")
                st.markdown(f"""
                <div style="padding:10px; border-bottom: 1px solid #222;">
                    <span style="color:#666; font-size:0.8rem;">{date_obj.strftime('%d %b - %H:%M')}</span><br>
                    <b style="font-size:1.1rem; color:#fff;">{m['homeTeam']['shortName']}</b> vs 
                    <b style="font-size:1.1rem; color:#fff;">{m['awayTeam']['shortName']}</b>
                </div>
                """, unsafe_allow_html=True)
            
            with c2:
                if st.button(f"Analisi AI", key=f"btn_{m['id']}", use_container_width=True):
                    with st.spinner("Elaborazione Dixon-Coles..."):
                        res = run_pro_analysis(m, l_meta[league_name]['avg'])
                        if res == "LIMIT_ERROR":
                            st.warning("⚠️ Limite API raggiunto. Attendi.")
                        else:
                            st.session_state[f"res_{m['id']}"] = res

            if f"res_{m['id']}" in st.session_state:
                r = st.session_state[f"res_{m['id']}"]
                st.markdown(f"""
                <div class="result-area">
                    <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:10px; font-family:'JetBrains Mono'; text-align:center;">
                        <div><small style="color:#00d1ff;">1 X 2</small><br><b>{r['1']:.0f}%|{r['X']:.0f}%|{r['2']:.0f}%</b></div>
                        <div><small style="color:#00d1ff;">G/NG</small><br><b>GG {r['GG']:.0f}%</b></div>
                        <div><small style="color:#00d1ff;">U/O 2.5</small><br><b>U{r['U2.5']:.0f}%|O{r['O2.5']:.0f}%</b></div>
                        <div><small style="color:#00d1ff;">SUGGERIMENTO AI</small><br><span class="pick-badge">{r['PICK']}</span></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

st.markdown('<div class="disclaimer">MODELLO PRO STATISTICO AVANZATO. I DATI NON GARANTISCONO VINCITE. | V3.6 AI-PRO</div>', unsafe_allow_html=True)