import math
import html
from datetime import datetime, timezone
from itertools import product
from zoneinfo import ZoneInfo

# ═════════════════════════════════════════════════════════════
#  DONNY v5.0 — LOGICA (pura, senza Streamlit)
#
#  Modello: Poisson bivariato con correzione Dixon-Coles, rating
#  attacco/difesa per squadra stimati su tutta la stagione:
#    λ_casa = μ · γ · att_casa · dif_trasf
#    λ_trasf = μ · att_trasf · dif_casa
#  - peso temporale esponenziale (partite recenti valgono di più)
#  - correzione per la forza degli avversari (iterativa)
#  - shrinkage verso la media (K_PRIOR) per squadre con pochi dati
#  - vantaggio casalingo γ stimato dai dati del campionato
# ═════════════════════════════════════════════════════════════

XI = 0.0065          # decadimento per giorno (emivita ≈ 107 giorni)
K_PRIOR = 4.0        # "gol fittizi" di regressione verso la media
RHO = -0.13          # correzione Dixon-Coles sui punteggi bassi
MAX_G = 10           # gol massimi per squadra nella matrice
MIN_GAMES = 8        # partite minime per squadra, sotto → NO BET

MIN_LIFT = 0.25      # vantaggio minimo sul "caso medio" per consigliare
STRONG_LIFT = 0.45   # sopra questa soglia → pick FORTE

# chiave: (etichetta, probabilità minima assoluta)
MARKETS = {
    "1":   ("1",          0.55),
    "2":   ("2",          0.50),
    "1X":  ("1X",         0.78),
    "X2":  ("X2",         0.78),
    "O25": ("Over 2.5",   0.60),
    "U25": ("Under 2.5",  0.62),
    "GG":  ("Goal",       0.60),
    "NG":  ("No Goal",    0.62),
    "O15": ("Over 1.5",   0.82),
}
ALL_KEYS = list(MARKETS) + ["X"]


def outcome(key, gh, ga):
    """True se il mercato `key` è vinto col risultato gh-ga."""
    if key == "1":   return gh > ga
    if key == "X":   return gh == ga
    if key == "2":   return gh < ga
    if key == "1X":  return gh >= ga
    if key == "X2":  return gh <= ga
    if key == "O25": return gh + ga >= 3
    if key == "U25": return gh + ga <= 2
    if key == "O15": return gh + ga >= 2
    if key == "GG":  return gh > 0 and ga > 0
    if key == "NG":  return gh == 0 or ga == 0
    raise KeyError(key)


def fit_ratings(results, ref_date, iters=40):
    """
    results: lista di (home_id, away_id, gol_casa, gol_trasf, datetime_utc)
    Restituisce il modello (dict) oppure None se i dati sono troppo pochi.
    """
    if len(results) < 20:
        return None

    w = [math.exp(-XI * max((ref_date - r[4]).days, 0)) for r in results]
    teams = {t for r in results for t in (r[0], r[1])}
    tw = sum(w)
    mu = sum(wi * r[3] for wi, r in zip(w, results)) / tw   # media gol in trasferta
    gamma = 1.2
    att = dict.fromkeys(teams, 1.0)
    dfn = dict.fromkeys(teams, 1.0)

    for _ in range(iters):
        # ── attacco ──
        num = dict.fromkeys(teams, K_PRIOR)
        den = dict.fromkeys(teams, K_PRIOR)
        for wi, (h, a, gh, ga, _) in zip(w, results):
            num[h] += wi * gh
            den[h] += wi * mu * gamma * dfn[a]
            num[a] += wi * ga
            den[a] += wi * mu * dfn[h]
        att = {t: num[t] / den[t] for t in teams}

        # ── difesa (gol subiti attesi: più alto = difesa peggiore) ──
        num = dict.fromkeys(teams, K_PRIOR)
        den = dict.fromkeys(teams, K_PRIOR)
        for wi, (h, a, gh, ga, _) in zip(w, results):
            num[h] += wi * ga
            den[h] += wi * mu * att[a]
            num[a] += wi * gh
            den[a] += wi * mu * gamma * att[h]
        dfn = {t: num[t] / den[t] for t in teams}

        # ── vantaggio casalingo ──
        g_num = sum(wi * r[2] for wi, r in zip(w, results))
        g_den = sum(wi * mu * att[r[0]] * dfn[r[1]] for wi, r in zip(w, results))
        gamma = g_num / g_den

        # ── normalizzazione (λ resta invariato) ──
        ma = sum(att.values()) / len(att)
        md = sum(dfn.values()) / len(dfn)
        att = {t: v / ma for t, v in att.items()}
        dfn = {t: v / md for t, v in dfn.items()}
        mu *= ma * md

    games = {}
    for r in results:
        games[r[0]] = games.get(r[0], 0) + 1
        games[r[1]] = games.get(r[1], 0) + 1

    n = len(results)
    base = {k: sum(outcome(k, r[2], r[3]) for r in results) / n for k in ALL_KEYS}

    return {"att": att, "dfn": dfn, "mu": mu, "gamma": gamma,
            "games": games, "base": base}


def _pmf(lam):
    return [math.exp(-lam + k * math.log(lam) - math.lgamma(k + 1)) for k in range(MAX_G + 1)]


def _tau(gh, ga, lh, la, rho=RHO):
    if gh == 0 and ga == 0: return 1.0 - lh * la * rho
    if gh == 1 and ga == 0: return 1.0 + la * rho
    if gh == 0 and ga == 1: return 1.0 + lh * rho
    if gh == 1 and ga == 1: return 1.0 - rho
    return 1.0


def predict(model, home_id, away_id):
    """Probabilità (0-1) di tutti i mercati + gol attesi."""
    lh = model["mu"] * model["gamma"] * model["att"].get(home_id, 1.0) * model["dfn"].get(away_id, 1.0)
    la = model["mu"] * model["att"].get(away_id, 1.0) * model["dfn"].get(home_id, 1.0)
    lh = min(max(lh, 0.30), 4.0)
    la = min(max(la, 0.20), 3.5)

    ph, pa = _pmf(lh), _pmf(la)
    p1 = px = p2 = o25 = o15 = gg = tot = 0.0
    for gh, ga in product(range(MAX_G + 1), repeat=2):
        p = max(ph[gh] * pa[ga] * _tau(gh, ga, lh, la), 0.0)
        tot += p
        if gh > ga:    p1 += p
        elif gh == ga: px += p
        else:          p2 += p
        if gh + ga >= 3: o25 += p
        if gh + ga >= 2: o15 += p
        if gh > 0 and ga > 0: gg += p

    m = {
        "1": p1 / tot, "X": px / tot, "2": p2 / tot,
        "1X": (p1 + px) / tot, "X2": (px + p2) / tot,
        "O25": o25 / tot, "U25": 1 - o25 / tot,
        "O15": o15 / tot,
        "GG": gg / tot, "NG": 1 - gg / tot,
    }
    return {"m": m, "lh": lh, "la": la}


def choose_pick(m, base):
    """
    Sceglie UN solo mercato: quello col maggior vantaggio rispetto alla
    frequenza media del campionato ("lift" 0-1), non quello con la
    probabilità grezza più alta (che favorirebbe sempre 1X / Over 1.5).
    """
    best = None
    for key, (label, min_p) in MARKETS.items():
        p = m[key]
        if p < min_p:
            continue
        b = base.get(key, 0.5)
        lift = (p - b) / (1 - b) if b < 0.999 else 0.0
        if lift < MIN_LIFT:
            continue
        if best is None or lift > best["lift"]:
            best = {"key": key, "label": label, "prob": p, "lift": lift,
                    "fair_odds": 1 / p, "strong": lift >= STRONG_LIFT}
    return best


def analyze(model, home_id, away_id):
    """Analisi completa di una partita, pronta per la UI."""
    g = model["games"]
    pred = predict(model, home_id, away_id)
    pred["pick"] = None
    pred["note"] = ""
    if min(g.get(home_id, 0), g.get(away_id, 0)) < MIN_GAMES:
        pred["note"] = "dati insufficienti"
    else:
        pred["pick"] = choose_pick(pred["m"], model["base"])
    return pred


def run_backtest(results, n_test=60):
    """
    Walk-forward: per ogni giornata di test il modello viene stimato SOLO
    con le partite precedenti. Misura quanto i pick hanno beccato davvero.
    """
    results = sorted(results, key=lambda r: r[4])
    if len(results) < n_test + 60:
        return None
    test = results[-n_test:]
    dates = sorted({r[4].date() for r in test})

    picks = {}            # label -> [n, vinti, somma_prob]
    ll_model = ll_base = 0.0
    n_ll = n_top = hit_top = 0

    for d in dates:
        day_matches = [r for r in test if r[4].date() == d]
        cutoff = min(r[4] for r in day_matches)
        train = [r for r in results if r[4] < cutoff]
        model = fit_ratings(train, cutoff, iters=25)
        if model is None:
            continue
        for h, a, gh, ga, _ in day_matches:
            res = analyze(model, h, a)
            m = res["m"]
            real = "1" if gh > ga else ("X" if gh == ga else "2")
            ll_model += -math.log(max(m[real], 1e-6))
            ll_base += -math.log(max(model["base"][real], 1e-6))
            n_ll += 1
            top = max(("1", "X", "2"), key=lambda k: m[k])
            n_top += 1
            hit_top += (top == real)
            pk = res["pick"]
            if pk:
                row = picks.setdefault(pk["label"], [0, 0, 0.0])
                row[0] += 1
                row[1] += outcome(pk["key"], gh, ga)
                row[2] += pk["prob"]

    if n_ll == 0:
        return None
    tot_n = sum(v[0] for v in picks.values())
    tot_w = sum(v[1] for v in picks.values())
    tot_p = sum(v[2] for v in picks.values())
    return {
        "n_matches": n_ll,
        "logloss_model": ll_model / n_ll,
        "logloss_base": ll_base / n_ll,
        "acc_1x2": hit_top / n_top,
        "n_picks": tot_n,
        "hit_rate": (tot_w / tot_n) if tot_n else None,
        "avg_prob": (tot_p / tot_n) if tot_n else None,
        "by_market": [
            {"Mercato": k, "Pick": v[0], "Vinti": v[1],
             "Hit %": round(100 * v[1] / v[0], 1),
             "Prob. media %": round(100 * v[2] / v[0], 1)}
            for k, v in sorted(picks.items(), key=lambda kv: -kv[1][0])
        ],
    }


# ═════════════════════════════════════════════════════════════
#  INTERFACCIA STREAMLIT
# ═════════════════════════════════════════════════════════════
import os
import requests
import streamlit as st

st.set_page_config(page_title="Donny v5.0", page_icon="⚽", layout="wide")

API = "https://api.football-data.org/v4"
TZ = ZoneInfo("Europe/Rome")

LEAGUES = {
    "Serie A": "SA",
    "Premier League": "PL",
    "La Liga": "PD",
    "Bundesliga": "BL1",
    "Ligue 1": "FL1",
}


def get_key():
    try:
        k = st.secrets.get("FOOTBALL_DATA_KEY", "")
    except Exception:
        k = ""
    return (k or os.environ.get("FOOTBALL_DATA_KEY", "")).strip()


AF_KEY = get_key()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
.stApp { background-color:#050505; color:#fff; }
.card { background:#111; border:1px solid #222; border-radius:12px; padding:14px 16px; margin-bottom:10px; }
.date { color:#666; font-size:.8rem; }
.teams { font-size:1.15rem; font-weight:700; margin:2px 0 8px 0; }
.pick { display:inline-block; padding:5px 12px; border-radius:7px; font-weight:700; font-size:1rem; color:#000; }
.strong { background:#00e676; } .normal { background:#00d1ff; } .nobet { background:#333; color:#999; }
.meta { font-family:'JetBrains Mono',monospace; font-size:.78rem; color:#9aa; margin-top:8px; }
.odds { color:#bbb; font-size:.85rem; margin-left:10px; }
.disclaimer { font-size:.6rem; color:#444; text-align:center; margin-top:40px; }
</style>
""", unsafe_allow_html=True)


class ApiError(Exception):
    pass


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def api_get(path, params, key):
    """Le eccezioni NON vengono messe in cache: un 429 non resta "incollato" 6 ore."""
    r = requests.get(f"{API}{path}", headers={"X-Auth-Token": key},
                     params=dict(params), timeout=20)
    if r.status_code != 200:
        raise ApiError(r.status_code)
    return r.json()


def parse_dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def parse_results(matches):
    out = []
    for m in matches:
        ft = m.get("score", {}).get("fullTime", {})
        if ft.get("home") is None or ft.get("away") is None:
            continue
        out.append((m["homeTeam"]["id"], m["awayTeam"]["id"],
                    ft["home"], ft["away"], parse_dt(m["utcDate"])))
    return out


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def load_league(code, key):
    now = datetime.now(timezone.utc)
    season = now.year if now.month >= 7 else now.year - 1

    cur = api_get(f"/competitions/{code}/matches",
                  (("status", "FINISHED"), ("season", season)), key)
    results = parse_results(cur.get("matches", []))

    prev_ok = True
    try:   # stagione precedente: se il piano non la concede, si va avanti senza
        prev = api_get(f"/competitions/{code}/matches",
                       (("status", "FINISHED"), ("season", season - 1)), key)
        results += parse_results(prev.get("matches", []))
    except ApiError:
        prev_ok = False

    # SCHEDULED + TIMED: la v4.1 perdeva le partite con orario già confermato
    fx = api_get(f"/competitions/{code}/matches",
                 (("status", "SCHEDULED,TIMED"),), key).get("matches", [])
    fixtures = sorted(
        [{"id": m["id"], "dt": parse_dt(m["utcDate"]),
          "hid": m["homeTeam"]["id"], "aid": m["awayTeam"]["id"],
          "home": m["homeTeam"].get("shortName") or m["homeTeam"]["name"],
          "away": m["awayTeam"].get("shortName") or m["awayTeam"]["name"]}
         for m in fx if m["homeTeam"].get("id") and m["awayTeam"].get("id")],
        key=lambda x: x["dt"])
    return results, fixtures, prev_ok


# ─────────────────────────── UI ───────────────────────────
st.title("⚽ Donny v5.0")
st.caption("Rating attacco/difesa stagionali · Dixon-Coles · pick singolo basato sul vantaggio reale")

if not AF_KEY:
    st.error("Inserisci FOOTBALL_DATA_KEY nei Secrets (o come variabile d'ambiente).")
    st.stop()

league_name = st.selectbox("Campionato", list(LEAGUES))
code = LEAGUES[league_name]

if st.sidebar.button("🔄 Aggiorna dati"):
    st.cache_data.clear()

try:
    with st.spinner("Carico i dati del campionato..."):
        results, fixtures, prev_ok = load_league(code, AF_KEY)
except ApiError as e:
    msg = {429: "Limite di richieste raggiunto, riprova tra un minuto.",
           403: "La tua chiave non ha accesso a questo campionato.",
           401: "Chiave API non valida."}.get(e.args[0], "Errore API.")
    st.error(f"{msg} (codice {e.args[0]})")
    st.stop()
except Exception as e:
    st.error(f"Connessione fallita: {e}")
    st.stop()

model = fit_ratings(results, datetime.now(timezone.utc))
if model is None:
    st.warning("Troppe poche partite giocate per stimare il modello.")
    st.stop()

if not prev_ok:
    st.info("Stagione precedente non disponibile col tuo piano: uso solo quella in corso.")

# ── Backtest ──
with st.sidebar:
    st.markdown("### 🧪 Backtest")
    st.caption("Rigioca le ultime 60 partite usando solo i dati precedenti a ciascuna.")
    if st.button("Esegui backtest"):
        with st.spinner("Walk-forward in corso..."):
            bt = run_backtest(results, 60)
        if bt is None:
            st.warning("Dati insufficienti per il backtest.")
        else:
            st.metric("Log-loss 1X2 (modello)", f"{bt['logloss_model']:.3f}",
                      f"{bt['logloss_model'] - bt['logloss_base']:+.3f} vs media campionato",
                      delta_color="inverse")
            st.metric("1X2: esito più probabile azzeccato", f"{bt['acc_1x2']*100:.0f}%")
            if bt["n_picks"]:
                st.metric(f"Pick vinti ({bt['n_picks']} pick)", f"{bt['hit_rate']*100:.0f}%",
                          f"prob. media stimata {bt['avg_prob']*100:.0f}%", delta_color="off")
                st.dataframe(bt["by_market"], hide_index=True)
                st.caption("Se 'Hit %' è molto sotto 'Prob. media %' il modello è "
                           "troppo ottimista: alza MIN_LIFT.")
            else:
                st.info("Nessun pick generato nel periodo di test.")

# ── Partite ──
if not fixtures:
    st.info("Nessuna partita in programma trovata.")

for f in fixtures[:12]:
    res = analyze(model, f["hid"], f["aid"])
    m, pk = res["m"], res["pick"]

    if pk:
        css = "strong" if pk["strong"] else "normal"
        tag = "🔥 " if pk["strong"] else ""
        badge = f'<span class="pick {css}">{tag}{html.escape(pk["label"])} · {pk["prob"]*100:.0f}%</span>' \
                f'<span class="odds">quota minima {pk["fair_odds"]:.2f}</span>'
    else:
        why = f" ({res['note']})" if res["note"] else ""
        badge = f'<span class="pick nobet">NO BET{why}</span>'

    dt = f["dt"].astimezone(TZ)
    st.markdown(
        '<div class="card">'
        f'<div class="date">{dt.strftime("%d/%m · %H:%M")}</div>'
        f'<div class="teams">{html.escape(f["home"])} vs {html.escape(f["away"])}</div>'
        f'{badge}'
        f'<div class="meta">1X2 {m["1"]*100:.0f}|{m["X"]*100:.0f}|{m["2"]*100:.0f}'
        f' &nbsp;·&nbsp; O2.5 {m["O25"]*100:.0f}% &nbsp;·&nbsp; GG {m["GG"]*100:.0f}%'
        f' &nbsp;·&nbsp; xG {res["lh"]:.2f}–{res["la"]:.2f}</div>'
        '</div>',
        unsafe_allow_html=True,
    )

with st.expander("Come leggere il suggerimento"):
    st.markdown(
        "- **Percentuale**: probabilità stimata dal modello per quel mercato.\n"
        "- **Quota minima**: 100 / probabilità. Se il bookmaker offre di più c'è valore, se offre meno lascia stare.\n"
        "- **🔥 Forte**: il mercato supera nettamente la frequenza media del campionato.\n"
        "- **NO BET**: nessun mercato ha un vantaggio sufficiente (o ci sono pochi dati sulle squadre)."
    )

st.markdown('<div class="disclaimer">MODELLO STATISTICO. NESSUNA GARANZIA DI VINCITA. | V5.0</div>',
            unsafe_allow_html=True)