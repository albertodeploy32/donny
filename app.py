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
#  CARICAMENTO CHIAVI API
# ─────────────────────────────────────────────
def _load_keys() -> tuple[str, str]:
    try: from dotenv import load_dotenv; load_dotenv()
    except ImportError: pass
    def from_secrets(name):
        try: return st.secrets.get(name, "") or ""
        except Exception: return ""
    af = from_secrets("FOOTBALL_DATA_KEY") or os.environ.get("FOOTBALL_DATA_KEY", "")
    return af.strip(), ""

_env_af, _ = _load_keys()

# ─────────────────────────────────────────────
#  PAGE CONFIG & CSS (Allineato al Template)
# ─────────────────────────────────────────────
st.set_page_config(page_title="Donny | Intelligence System", page_icon="⚽", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
*, html, body, [class*="css"] { font-family: 'Figtree', sans-serif !important; }
.stApp { background: #050505 !important; color: #eee; }

/* Table Styling per Estrazione Dati */
.match-table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 0.8rem; }
.match-table th { background: rgba(255,255,255,0.05); color: #888; padding: 12px; text-align: center; border: 1px solid rgba(255,255,255,0.1); font-family: 'JetBrains Mono'; }
.match-table td { padding: 10px; border: 1px solid rgba(255,255,255,0.05); text-align: center; }
.match-table tr:hover { background: rgba(10, 132, 255, 0.05); }

/* Disclaimer conforme al template */
.disclaimer { font-size: 0.65rem; color: rgba(255,255,255,0.3); text-align: center; margin-top: 40px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 20px; line-height: 1.5; }
.badge-pick { background: #0a84ff; color: white; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-family: 'JetBrains Mono'; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  LOGICA DI CALCOLO (Poisson + Mercati Template)
# ─────────────────────────────────────────────
def poisson_prob(lam, k): return (math.exp(-lam) * (lam**k) / math.factorial(k)) if lam > 0 else (1.0 if k==0 else 0.0)

@st.cache_data(ttl=3600)
def get_stats(key, tid):
    url = f"https://api.football-data.org/v4/teams/{tid}/matches"
    r = requests.get(url, headers={"X-Auth-Token": key}, params={"status": "FINISHED", "limit": 10})
    if r.status_code == 429: time.sleep(10); return get_stats(key, tid)
    matches = r.json().get("matches", [])
    h_s, h_c, a_s, a_c = [], [], [], []
    for m in matches:
        is_h = m["homeTeam"]["id"] == tid
        gs, gc = (m["score"]["fullTime"]["home"], m["score"]["fullTime"]["away"]) if is_h else (m["score"]["fullTime"]["away"], m["score"]["fullTime"]["home"])
        if gs is not None:
            if is_h: h_s.append(gs); h_c.append(gc)
            else: a_s.append(gs); a_c.append(gc)
    return {"hs": sum(h_s)/len(h_s) if h_s else 1.3, "hc": sum(h_c)/len(h_c) if h_c else 1.1, "as": sum(a_s)/len(a_s) if a_s else 1.0, "ac": sum(a_c)/len(a_c) if a_c else 1.4}

def analyze(key, m):
    h, a = get_stats(key, m["homeTeam"]["id"]), get_stats(key, m["awayTeam"]["id"])
    lh, la = max(h["hs"] * a["ac"] / 1.3, 0.2), max(a["as"] * h["hc"] / 1.3, 0.2)
    matrix = {(gh, ga): poisson_prob(lh, gh) * poisson_prob(la, ga) for gh, ga in product(range(6), range(6))}
    
    p1 = sum(v for (gh, ga), v in matrix.items() if gh > ga)
    px = sum(v for (gh, ga), v in matrix.items() if gh == ga)
    p2 = sum(v for (gh, ga), v in matrix.items() if gh < ga)
    pov = sum(v for (gh, ga), v in matrix.items() if gh + ga > 2.5)
    
    # Nuovi Mercati dal Template
    p1x = p1 + px
    px2 = px + p2
    p12 = p1 + p2
    und = 1 - pov
    
    best = "1" if p1 > p2 and p1 > px else ("2" if p2 > p1 and p2 > px else "X")
    if pov > 0.65: best = "O2.5"
    
    return {"1": p1*100, "X": px*100, "2": p2*100, "1X": p1x*100, "12": p12*100, "X2": px2*100, "U2.5": und*100, "O2.5": pov*100, "best": best}

# ─────────────────────────────────────────────
#  INTERFACCIA
# ─────────────────────────────────────────────
st.title("⚽ Donny Prediction System")

if not _env_af:
    st.error("API Key mancante.")
    st.stop()

if st.button("🔄 Genera Estrazione Dati"):
    with st.spinner("Elaborazione dati in corso..."):
        # Esempio su Serie A (ID: SA)
        res = requests.get("https://api.football-data.org/v4/competitions/SA/matches", headers={"X-Auth-Token": _env_af}, params={"status": "SCHEDULED"}).json()
        matches = res.get("matches", [])[:8] # Primi 8 match
        
        html_table = """<table class="match-table"><thead><tr>
            <th>PARTITA</th><th>1</th><th>X</th><th>2</th><th>1X</th><th>12</th><th>X2</th><th>U2.5</th><th>O2.5</th><th>PICK</th>
        </tr></thead><tbody>"""
        
        for m in matches:
            data = analyze(_env_af, m)
            html_table += f"""<tr>
                <td><b>{m['homeTeam']['shortName']} - {m['awayTeam']['shortName']}</b></td>
                <td>{data['1']:.0f}%</td><td>{data['X']:.0f}%</td><td>{data['2']:.0f}%</td>
                <td>{data['1X']:.0f}%</td><td>{data['12']:.0f}%</td><td>{data['X2']:.0f}%</td>
                <td>{data['U2.5']:.0f}%</td><td>{data['O2.5']:.0f}%</td>
                <td><span class="badge-pick">{data['best']}</span></td>
            </tr>"""
        
        html_table += "</tbody></table>"
        st.markdown(html_table, unsafe_allow_html=True)

# Footer conforme al Template
st.markdown(f"""
<div class="disclaimer">
    IL GIOCO È VIETATO AI MINORI DI 18 ANNI E PUÒ CAUSARE DIPENDENZA PATOLOGICA.<br>
    PROBABILITÀ DI VINCITA SUL SITO ADM. | DONNY SYSTEM V2.2
</div>
""", unsafe_allow_html=True)