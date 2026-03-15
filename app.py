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
st.set_page_config(page_title="Donny v4.0 AI-PRO", page_icon="⚽", layout="wide")

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
#  LOGICA PREDITTIVA v4.0
#  Modifiche rispetto a v3.6:
#    1. rho Dixon-Coles corretto a -0.13 (era +0.15, invertiva la correzione)
#    2. Normalizzazione lambda con split casa/trasferta 54/46
#    3. Form trend: moltiplicatore basato su ultimi 3 vs ultimi 4-10 match
#    4. Regression to mean 70/30: ancora le stime alla media campionato
#    5. Smart Pick conservativo con confidence score
# ─────────────────────────────────────────────

def poisson(lam, k):
    """Distribuzione di Poisson standard."""
    return (math.exp(-lam) * (lam**k) / math.factorial(k)) if lam > 0 else (1.0 if k == 0 else 0.0)


def dixon_coles_tau(gh, ga, lh, la, rho=-0.13):
    """
    Funzione τ di Dixon-Coles per la correzione dei punteggi bassi.

    rho NEGATIVO (valore originale del paper: -0.13):
      - aumenta la probabilità di 0-0 e 1-1  (Poisson le sottostima)
      - riduce  la probabilità di 1-0 e 0-1  (Poisson le sovrastima)

    Il codice precedente usava rho=+0.15 che invertiva entrambe le correzioni.
    """
    if gh == 0 and ga == 0:
        return 1.0 - lh * la * rho          # > 1  con rho neg → aumenta 0-0
    elif gh == 1 and ga == 0:
        return 1.0 + la * rho               # < 1  con rho neg → riduce 1-0
    elif gh == 0 and ga == 1:
        return 1.0 + lh * rho               # < 1  con rho neg → riduce 0-1
    elif gh == 1 and ga == 1:
        return 1.0 - rho                    # > 1  con rho neg → aumenta 1-1
    return 1.0


def get_advanced_stats(team_id, venue_type="HOME"):
    """
    Calcola statistiche di attacco/difesa con:
    - Pesi temporali esponenziali (match recenti valgono di più)
    - Venue weighting (partite nella stessa condizione campo valgono 1.4x)
    - Form trend: rapporto ultimi 3 vs precedenti
    - Clean Sheet Factor per la difesa
    """
    url = f"https://api.football-data.org/v4/teams/{team_id}/matches"
    headers = {"X-Auth-Token": AF_KEY}
    try:
        r = requests.get(url, headers=headers, params={"status": "FINISHED", "limit": 10}, timeout=10)
        if r.status_code == 429:
            return "LIMIT"
        matches = r.json().get("matches", [])

        gs_list, gc_list = [], []
        # Pesi esponenziali: il match più recente vale 3x l'ultimo
        weights = [1.8, 1.6, 1.4, 1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 0.6]

        for i, m in enumerate(matches[:10]):
            is_home = m["homeTeam"]["id"] == team_id
            score = m["score"]["fullTime"]
            if score["home"] is None:
                continue

            raw_gs = score["home"] if is_home else score["away"]
            raw_gc = score["away"] if is_home else score["home"]

            # Venue weight: partita nella stessa condizione casa/trasferta pesa 1.4x
            venue_mult = 1.4 if (is_home and venue_type == "HOME") or \
                                 (not is_home and venue_type == "AWAY") else 0.6

            # Cap outlier: oltre 4 gol cresce logaritmicamente
            clean_gs = raw_gs if raw_gs <= 4 else 4 + math.log(raw_gs - 3)
            clean_gc = raw_gc if raw_gc <= 4 else 4 + math.log(raw_gc - 3)

            w = weights[i] * venue_mult
            gs_list.append((clean_gs, w))
            gc_list.append((clean_gc, w))

        if not gs_list:
            return {"att": 1.2, "def": 1.1, "form_trend": 1.0}

        total_w  = sum(w for _, w in gs_list)
        att_avg  = sum(g * w for g, w in gs_list) / total_w
        def_avg  = sum(g * w for g, w in gc_list) / total_w

        # ── Form Trend ──────────────────────────────────────────
        # Rapporto media gol segnati ultimi 3 match vs match 4-10.
        # Se la squadra è in crescita (trend > 1) aumenta lievemente la lambda.
        if len(gs_list) >= 6:
            r3_w   = sum(w for _, w in gs_list[:3])
            r3_att = sum(g * w for g, w in gs_list[:3]) / r3_w

            old_w   = sum(w for _, w in gs_list[3:])
            old_att = sum(g * w for g, w in gs_list[3:]) / old_w if old_w > 0 else att_avg

            form_trend = r3_att / max(old_att, 0.30)
            # Clamp: max ±25% di variazione — evita amplificazioni eccessive
            form_trend = max(0.78, min(form_trend, 1.25))
        else:
            form_trend = 1.0

        # ── Clean Sheet Factor (difesa) ──────────────────────────
        cs_count  = sum(1 for g, _ in gc_list if g == 0)
        cs_factor = 1.0 - (cs_count / len(gc_list)) * 0.12

        return {
            "att":        att_avg,
            "def":        def_avg * cs_factor,
            "form_trend": form_trend,
        }

    except Exception:
        return {"att": 1.2, "def": 1.1, "form_trend": 1.0}


def smart_pick(res):
    """
    Algoritmo decisionale conservativo con confidence score.

    Logica:
    - Genera tutti i pick candidati con il loro livello di fiducia stimato.
    - Seleziona il pick con confidence massima.
    - Restituisce "NO BET" se nessun pick supera la soglia minima del 62%.

    Differenze rispetto a v3.6:
    - Doppia chance (1X/X2): threshold abbassato a 80% ma corretto con P(UN4.5) ≈ 91%
    - Segno singolo: 1 a ≥67%, 2 a ≥63%
    - Mercati gol: solo se ≥65% (era 64% e 68%)
    - GG/NG: threshold 68% e 65%
    - NO BET se confidence < 62%
    """
    candidates = []

    p1x = res["1"] + res["X"]
    px2 = res["2"] + res["X"]

    # Doppia chance + Under 4.5 (UN4.5 si verifica in ~91% delle partite europee)
    if p1x >= 80:
        candidates.append(("1X + UNDER 4.5", round(p1x * 0.91, 1)))
    if px2 >= 80:
        candidates.append(("X2 + UNDER 4.5", round(px2 * 0.91, 1)))

    # Segno singolo forte
    if res["1"] >= 67:
        candidates.append(("1 FISSO", round(res["1"], 1)))
    if res["2"] >= 63:
        candidates.append(("2 FISSO", round(res["2"], 1)))

    # Mercato gol
    if res["O2.5"] >= 65:
        candidates.append(("OVER 2.5", round(res["O2.5"], 1)))
    if res["U2.5"] >= 65:
        candidates.append(("UNDER 2.5", round(res["U2.5"], 1)))

    # Goal / No Goal
    if res["GG"] >= 68:
        candidates.append(("GOAL", round(res["GG"], 1)))
    ng = 100 - res["GG"]
    if ng >= 65:
        candidates.append(("NO GOAL", round(ng, 1)))

    # Under 1.5 (partite molto chiuse)
    if res["U1.5"] >= 48:
        candidates.append(("UNDER 1.5", round(res["U1.5"], 1)))

    if not candidates:
        return "NO BET", 0

    best_label, best_conf = max(candidates, key=lambda x: x[1])

    # Soglia minima: sotto il 62% non raccomandiamo nulla
    if best_conf < 62:
        return "NO BET", round(best_conf, 1)

    return best_label, round(best_conf, 1)


def run_pro_analysis(m, league_avg):
    """
    Analisi bivariante Dixon-Coles v4.0.

    Schema di calcolo:
      1. Scarica ultime 10 partite per ciascuna squadra (2 chiamate API).
      2. Normalizza att/def rispetto alle medie campionato splittate 54/46 casa-trasferta.
      3. Applica regression to mean 70/30 per evitare lambda estreme.
      4. Moltiplica per form_trend (+/- fino al 25%) per catturare il momento.
      5. Calcola la matrice di probabilità 8x8 con correzione τ Dixon-Coles.
      6. Chiama smart_pick() per il suggerimento finale.
    """
    h_s = get_advanced_stats(m["homeTeam"]["id"], "HOME")
    if h_s == "LIMIT":
        return "LIMIT_ERROR"
    time.sleep(0.6)  # anti-throttle invariato

    a_s = get_advanced_stats(m["awayTeam"]["id"], "AWAY")
    if a_s == "LIMIT":
        return "LIMIT_ERROR"

    # ── Media gol per squadra, split casa/trasferta ──────────────
    # In media nei top 5 campionati europei:
    #   54% dei gol totali è segnato dalla squadra di casa
    #   46% è segnato dalla squadra in trasferta
    mu_h = league_avg * 0.535   # gol attesi per la squadra di casa
    mu_a = league_avg * 0.465   # gol attesi per la squadra in trasferta

    # ── Parametri di forza normalizzati ─────────────────────────
    # attack_strength > 1 → squadra sopra la media in attacco
    # defense_weakness > 1 → squadra sopra la media nel subire gol
    att_h = max(h_s["att"] / mu_h, 0.25)
    def_h = max(h_s["def"] / mu_h, 0.25)
    att_a = max(a_s["att"] / mu_a, 0.25)
    def_a = max(a_s["def"] / mu_a, 0.25)

    # ── Regression to mean (70% squad stats / 30% league mean) ──
    # Un parametro di 1.0 equivale alla media campionato.
    # Blend: riduce l'impatto di outlier statistici (es. squadra con 2 match utili).
    α = 0.70
    att_h = att_h * α + 1.0 * (1 - α)
    def_h = def_h * α + 1.0 * (1 - α)
    att_a = att_a * α + 1.0 * (1 - α)
    def_a = def_a * α + 1.0 * (1 - α)

    # ── Lambda expected goals (schema Dixon-Coles standard) ─────
    # λH = attacco casa × debolezza difensiva avversaria × media campionato
    lh = att_h * def_a * mu_h * h_s["form_trend"]
    la = att_a * def_h * mu_a * a_s["form_trend"]

    # Clamp: range fisicamente plausibile
    lh = max(0.40, min(lh, 3.80))
    la = max(0.25, min(la, 3.20))

    # ── Matrice di probabilità 8×8 con correzione Dixon-Coles ────
    p1, px, p2 = 0.0, 0.0, 0.0
    pov25, pgg, p_under15 = 0.0, 0.0, 0.0

    for gh, ga in product(range(8), range(8)):
        p_raw = poisson(lh, gh) * poisson(la, ga)
        tau   = dixon_coles_tau(gh, ga, lh, la, rho=-0.13)
        p_adj = max(p_raw * tau, 0.0)   # garantisce non-negatività

        if   gh > ga: p1 += p_adj
        elif gh == ga: px += p_adj
        else:          p2 += p_adj

        if gh + ga > 2.5:          pov25    += p_adj
        if gh + ga < 1.5:          p_under15 += p_adj
        if gh > 0 and ga > 0:      pgg      += p_adj

    # Normalizzazione finale (per sicurezza dopo aggiustamenti)
    total_p = p1 + px + p2
    if total_p < 0.001:
        total_p = 1.0

    res = {
        "1":    (p1    / total_p) * 100,
        "X":    (px    / total_p) * 100,
        "2":    (p2    / total_p) * 100,
        "O2.5": pov25  * 100,
        "U2.5": (1 - pov25) * 100,
        "GG":   pgg    * 100,
        "U1.5": p_under15 * 100,
        "xG_H": round(lh, 2),
        "xG_A": round(la, 2),
    }

    pick, confidence = smart_pick(res)

    # Confidence visibile nel badge (es. "OVER 2.5 · 68%")
    if pick != "NO BET" and confidence > 0:
        res["PICK"] = f"{pick} · {confidence}%"
    else:
        res["PICK"] = pick

    return res


# ─────────────────────────────────────────────
#  INTERFACCIA STREAMLIT  (invariata)
# ─────────────────────────────────────────────
st.title("⚽ Donny Smart Loader v4.0 AI-PRO")
st.caption("Dixon-Coles τ corretto | Form Trend | Regression to Mean | xG normalizzati")

if not AF_KEY:
    st.error("Inserisci la chiave API nei Secrets.")
    st.stop()

l_meta = {
    "Serie A":       {"id": "SA",  "avg": 2.62},
    "Premier League":{"id": "PL",  "avg": 2.85},
    "La Liga":       {"id": "PD",  "avg": 2.55},
    "Bundesliga":    {"id": "BL1", "avg": 3.10},
    "Ligue 1":       {"id": "FL1", "avg": 2.70},
}

league_name = st.selectbox("Seleziona Campionato", list(l_meta.keys()))

if "matches" not in st.session_state or st.sidebar.button("🔄 Carica Nuovi Match"):
    headers = {"X-Auth-Token": AF_KEY}
    try:
        r = requests.get(
            f"https://api.football-data.org/v4/competitions/{l_meta[league_name]['id']}/matches",
            headers=headers,
            params={"status": "SCHEDULED"},
        )
        if r.status_code == 200:
            st.session_state.matches = r.json().get("matches", [])[:12]
        else:
            st.error(f"Errore API {r.status_code}. Controlla il piano.")
    except Exception as e:
        st.error(f"Connessione fallita: {e}")

if "matches" in st.session_state:
    for m in st.session_state.matches:
        with st.container():
            c1, c2 = st.columns([3, 1])
            with c1:
                date_obj = datetime.strptime(m["utcDate"], "%Y-%m-%dT%H:%M:%SZ")
                st.markdown(f"""
                <div style="padding:10px; border-bottom: 1px solid #222;">
                    <span style="color:#666; font-size:0.8rem;">{date_obj.strftime('%d %b - %H:%M')}</span><br>
                    <b style="font-size:1.1rem; color:#fff;">{m['homeTeam']['shortName']}</b> vs 
                    <b style="font-size:1.1rem; color:#fff;">{m['awayTeam']['shortName']}</b>
                </div>
                """, unsafe_allow_html=True)

            with c2:
                if st.button("Analisi AI", key=f"btn_{m['id']}", use_container_width=True):
                    with st.spinner("Elaborazione Dixon-Coles..."):
                        res = run_pro_analysis(m, l_meta[league_name]["avg"])
                        if res == "LIMIT_ERROR":
                            st.warning("⚠️ Limite API raggiunto. Attendi.")
                        else:
                            st.session_state[f"res_{m['id']}"] = res

            if f"res_{m['id']}" in st.session_state:
                r = st.session_state[f"res_{m['id']}"]
                st.markdown(f"""
                <div class="result-area">
                    <div style="display:grid; grid-template-columns: repeat(5, 1fr); gap:10px; font-family:'JetBrains Mono'; text-align:center;">
                        <div><small style="color:#00d1ff;">1 X 2</small><br><b>{r['1']:.0f}%|{r['X']:.0f}%|{r['2']:.0f}%</b></div>
                        <div><small style="color:#00d1ff;">G/NG</small><br><b>GG {r['GG']:.0f}%</b></div>
                        <div><small style="color:#00d1ff;">U/O 2.5</small><br><b>U{r['U2.5']:.0f}%|O{r['O2.5']:.0f}%</b></div>
                        <div><small style="color:#00d1ff;">xG</small><br><b>{r['xG_H']} — {r['xG_A']}</b></div>
                        <div><small style="color:#00d1ff;">SUGGERIMENTO AI</small><br><span class="pick-badge">{r['PICK']}</span></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

st.markdown('<div class="disclaimer">MODELLO PRO STATISTICO AVANZATO. I DATI NON GARANTISCONO VINCITE. | V4.0 AI-PRO</div>', unsafe_allow_html=True)