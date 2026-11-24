"""
SCRIPT 16 - Nowcasting: le fonti digitali migliorano la stima degli arrivi del mese corrente?

Esercizio in pseudo tempo reale (2022-2024):
  * target: y = log A(t) - log A(t-12), variazione annua logaritmica degli arrivi ISTAT per regione e mercato
  * ISTAT pubblica con L = 3 mesi di ritardo; Google Trends e Wikipedia sono disponibili subito
  * ogni mese di valutazione i modelli si stimano di nuovo su una finestra che si allarga, usando solo i dati noti in
    quel momento, e producono la stima per le 20 regioni. Anche la scelta delle serie Trends utilizzabili (al massimo
    il 20% di mesi a zero) si fa mese per mese, usando solo i dati Trends fino a quel mese
  * modelli (uno per mercato, comuni alle regioni), stimati con la regressione di Huber con cambio di regime:
        B0  stagionale ingenuo (y = 0)
        B1  solo dati ufficiali: ultime due variazioni ISTAT pubblicate (t-3, t-4)
        B1 + Trends, B1 + Wiki, B1 + Trends + Wiki: aggiungono le variazioni annue delle fonti digitali del mese t
  * valutazione: RMSE relativo a B1 per 2022 (ripresa post-COVID) e 2023-2024 (anni normali), con intervallo al 90%
    da bootstrap a blocchi mobili sui mesi e test di Diebold-Mariano con la correzione di Harvey-Leybourne-Newbold
    per campioni piccoli
  * importanza delle variabili: random forest stimato fino al 2021, permutation importance misurata sul 2022-2024

Limite: i dati Google Trends sono stati scaricati a posteriori e Google ricampiona le serie, quindi l'esercizio e' in
pseudo tempo reale, non in tempo reale vero.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import HuberRegressor
import matplotlib.pyplot as plt

from script_0_comune import COL, OUT, MERC, PROC, Registro

warnings.filterwarnings("ignore")
R = Registro("nc_risultati.txt")
rng = np.random.default_rng(0)
L, SOGLIA_REGIME, SOGLIA_ZERI = 3, 0.5, 0.20
GT = ["gt_hotel", "gt_voli", "gt_attrazioni"]
FEATS = {"B1": [], "B1+Trends": GT, "B1+Wiki": ["wiki"], "B1+Trends+Wiki": GT + ["wiki"]}
MODELLI = ["B0"] + list(FEATS)
VAL = {"2022-2024": ("2022-01", "2024-12"), "2022": ("2022-01", "2022-12"), "2023-2024": ("2023-01", "2024-12")}

# ================================================================ dati
istat = pd.read_csv(PROC / "istat.csv", usecols=["REF_AREA", "market", "TIME_PERIOD", "yoy_arrivi"])
istat = istat[istat.TIME_PERIOD >= "2012-01"]
tr = pd.read_csv(PROC / "trends.csv")
tr["zero"] = tr.value == 0
KEY = ["REF_AREA", "geo", "intent"]
wk = pd.read_csv(PROC / "wiki.csv").set_index(["REF_AREA", "market", "TIME_PERIOD"]).yoy.rename("wiki")


def regressori_trends(fino_a):
    """Variazioni annue Trends per regione x mercato x mese, con le serie utilizzabili secondo i dati fino a fino_a."""
    zeri = tr[tr.TIME_PERIOD <= fino_a].groupby(KEY).zero.mean()      # la scelta delle serie usa solo il passato
    ok = zeri[zeri <= SOGLIA_ZERI].index
    s = tr.set_index(KEY).loc[lambda d: d.index.isin(ok)].reset_index()
    gt = s.groupby(["REF_AREA", "market", "TIME_PERIOD", "intent"]).yoy.mean().unstack()
    gt = gt.reindex(columns=["hotel", "voli", "attrazioni"])
    gt.columns = [f"gt_{c}" for c in gt.columns]
    return gt, len(ok)


def pannello(gt):
    P = istat.set_index(["REF_AREA", "market", "TIME_PERIOD"]).join(gt, how="left").join(wk, how="left").reset_index()
    P = P.sort_values(["REF_AREA", "market", "TIME_PERIOD"])
    g = P.groupby(["REF_AREA", "market"]).yoy_arrivi
    P["ar1"], P["ar2"] = g.shift(L), g.shift(L + 1)
    P["mese"] = P.TIME_PERIOD.str[5:].astype(int)
    return P.dropna(subset=["yoy_arrivi", "ar1", "ar2"])


def design(df, feats, regime=SOGLIA_REGIME):
    X = df[["ar1", "ar2"] + feats].copy()
    for f in feats:
        X[f"manca_{f}"] = X[f].isna().astype(float)
        X[f] = X[f].fillna(0.0)
    if regime is not None:
        D = (df.ar1.abs() > regime).astype(float)
        X["D"] = D
        for f in ["ar1", "ar2"] + feats:
            X[f"{f}_xD"] = X[f] * D
    return X


def huber(X, y):
    return HuberRegressor(epsilon=1.35, alpha=1e-4, max_iter=1000).fit(X, y)


# ================================================================ 1. serie Trends utilizzabili, mese per mese
R.titolo("1. SERIE TRENDS UTILIZZABILI (scelte ogni mese con i soli dati disponibili)")
mesi_test = pd.period_range("2022-01", "2024-12", freq="M").strftime("%Y-%m")
GT_RT, n_rt = {}, {}
for m in mesi_test:
    GT_RT[m], n_rt[m] = regressori_trends(m)
R.say(f"Serie utilizzabili (su 360): gen 2022 {n_rt['2022-01']}, dic 2022 {n_rt['2022-12']}, dic 2024 {n_rt['2024-12']}")


# ================================================================ 2. esercizio di nowcasting
def nowcast(mercato):
    out = []
    for m in mesi_test:
        d = pannello(GT_RT[m])
        d = d[d.market == mercato]
        cutoff = (pd.Period(m, "M") - L).strftime("%Y-%m")
        tr_, te = d[d.TIME_PERIOD <= cutoff], d[d.TIME_PERIOD == m]
        row = te[["REF_AREA", "TIME_PERIOD", "yoy_arrivi"]].rename(columns={"yoy_arrivi": "y"}).copy()
        row["B0"] = 0.0
        for nome, f in FEATS.items():
            trn = tr_.dropna(subset=["wiki"]) if "wiki" in f else tr_
            row[nome] = huber(design(trn, f), trn.yoy_arrivi).predict(design(te, f))
        out.append(row)
    return pd.concat(out, ignore_index=True).assign(market=mercato)


def perdite_mensili(r, mod):
    return ((r[mod] - r.y) ** 2).groupby(r.TIME_PERIOD).mean()


def dm_hln(r, m1, m2="B1", h=1):
    """Diebold-Mariano con correzione di Harvey-Leybourne-Newbold, varianza HAC di Bartlett (lag 3), t con n-1 g.d.l."""
    d = (perdite_mensili(r, m1) - perdite_mensili(r, m2)).to_numpy()
    n, dc, lag = len(d), d - d.mean(), 3
    v = dc @ dc / n + 2 * sum((1 - k / (lag + 1)) * (dc[k:] @ dc[:-k]) / n for k in range(1, lag + 1))
    s = d.mean() / np.sqrt(v / n)
    s *= np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    return s, 2 * stats.t.sf(abs(s), n - 1)


def bootstrap_rapporto(r, m1, m2="B1", B=2000, blocco=3):
    """Intervallo al 90% del rapporto RMSE(m1)/RMSE(m2) con bootstrap a blocchi mobili sui mesi."""
    a, b = perdite_mensili(r, m1).to_numpy(), perdite_mensili(r, m2).to_numpy()
    n = len(a)
    nb = int(np.ceil(n / blocco))
    rr = []
    for _ in range(B):
        idx = np.concatenate([np.arange(s, s + blocco) for s in rng.integers(0, n - blocco + 1, nb)])[:n]
        rr.append(np.sqrt(a[idx].mean() / b[idx].mean()))
    return np.percentile(rr, [5, 95])


R.titolo("2. RISULTATI")
RES = {mk: nowcast(mk) for mk in MERC}
pd.concat(RES.values()).to_csv(OUT / "nc_previsioni.csv", index=False)
righe = []
for mk, r in RES.items():
    for per, (a, b) in VAL.items():
        rr = r[r.TIME_PERIOD.between(a, b)]
        e = {m: np.sqrt(((rr[m] - rr.y) ** 2).mean()) for m in MODELLI}
        for mod in MODELLI:
            if mod == "B1":
                s, p, lo, hi = np.nan, np.nan, 1.0, 1.0
            else:
                s, p = dm_hln(rr, mod)
                lo, hi = bootstrap_rapporto(rr, mod)
            righe.append(dict(mercato=mk, periodo=per, modello=mod, RMSE=e[mod], RMSE_rel_B1=e[mod] / e["B1"],
                              ic90_lo=lo, ic90_hi=hi, DM_HLN=s, p_value=p))
T = pd.DataFrame(righe)
T.round(4).to_csv(OUT / "nc_rmse.csv", index=False)
R.say("RMSE relativo a B1 [intervallo bootstrap 90%] e p-value DM-HLN (sotto 1 = le fonti digitali aiutano):")
q = T[T.modello != "B1"].copy()
q["cella"] = (q.RMSE_rel_B1.round(2).astype(str) + " [" + q.ic90_lo.round(2).astype(str) + ", "
              + q.ic90_hi.round(2).astype(str) + "] p=" + q.p_value.round(3).astype(str))
R.say(q.pivot_table(index=["mercato", "modello"], columns="periodo", values="cella", aggfunc="first",
                    sort=False).to_string())
R.say("\nUn miglioramento e' solido solo se l'intervallo sta tutto sotto 1.")

# ================================================================ 3. importanza delle variabili fuori campione
R.titolo("3. IMPORTANZA DELLE VARIABILI (random forest stimato fino al 2021, misurata sul 2022-2024)")
imp = []
for mk in MERC:
    P = pannello(regressori_trends("2021-12")[0])
    d = P[(P.market == mk)].dropna(subset=["wiki"])
    X = design(d, GT + ["wiki"], None).assign(mese=d.mese.values)
    X = X[[c for c in X.columns if not c.startswith("manca_")]]
    trm, tem = (d.TIME_PERIOD <= "2021-12").to_numpy(), (d.TIME_PERIOD >= "2022-01").to_numpy()
    rf = RandomForestRegressor(n_estimators=300, min_samples_leaf=5, max_features=0.6, random_state=0, n_jobs=-1)
    rf.fit(X[trm], d.yoy_arrivi[trm])
    pi = permutation_importance(rf, X[tem], d.yoy_arrivi[tem], n_repeats=10, random_state=0,
                                scoring="neg_root_mean_squared_error")
    imp.append(pd.Series(pi.importances_mean, index=X.columns, name=mk))
imp = pd.concat(imp, axis=1)
imp.round(4).to_csv(OUT / "nc_importanza_rf.csv")
R.say("Aumento dell'RMSE quando la variabile viene permutata (piu' alto = piu' importante):")
R.say(imp.round(4).to_string())

# ================================================================ grafico
fig, axs = plt.subplots(1, 2, figsize=(13, 4.6), sharey=True)
mods = [m for m in MODELLI if m != "B1"]
for ax, mk in zip(axs, MERC):
    for k, (per, c) in enumerate([("2022", COL["blu"]), ("2023-2024", COL["giallo"])]):
        s = T[(T.mercato == mk) & (T.periodo == per)].set_index("modello").loc[mods]
        x = np.arange(len(mods)) + (k - 0.5) * 0.36
        ax.bar(x, s.RMSE_rel_B1, 0.34, color=c, label=per)
        ax.errorbar(x, s.RMSE_rel_B1, yerr=[s.RMSE_rel_B1 - s.ic90_lo, s.ic90_hi - s.RMSE_rel_B1],
                    fmt="none", ecolor=COL["nero"], lw=1, capsize=3)
    ax.axhline(1, color=COL["nero"], ls="--", lw=1)
    ax.set_xticks(range(len(mods))); ax.set_xticklabels([m.replace("+", "\n+ ") for m in mods], fontsize=9)
    ax.set_title(MERC[mk][0])
axs[0].set_ylabel("RMSE relativo a B1 (intervallo bootstrap 90%)")
axs[1].legend(fontsize=8.5)
fig.suptitle("Nowcasting in pseudo tempo reale: errore rispetto al modello con soli dati ufficiali", fontweight="bold", y=1.02)
R.salva_grafico(fig, "nc_1_rmse")

# per la presentazione: RMSE relativo dei due modelli digitali rispetto a B1 (senza intervalli)
mods_p = ["B1+Trends", "B1+Wiki"]
fig, axs = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
for ax, mk in zip(axs, MERC):
    for k, (per, c) in enumerate([("2022", COL["blu"]), ("2023-2024", COL["giallo"])]):
        s = T[(T.mercato == mk) & (T.periodo == per)].set_index("modello").loc[mods_p]
        x = np.arange(len(mods_p)) + (k - 0.5) * 0.36
        ax.bar(x, s.RMSE_rel_B1, 0.34, color=c, label=per)
        for xi, v in zip(x, s.RMSE_rel_B1):
            ax.text(xi, v + 0.03, f"{v:.2f}", ha="center", fontsize=8.5)
    ax.axhline(1, color=COL["nero"], ls="--", lw=1)
    ax.set_xticks(range(len(mods_p))); ax.set_xticklabels([m.replace("+", " + ") for m in mods_p], fontsize=10)
    ax.set_title(MERC[mk][0])
axs[0].set_ylabel("RMSE relativo a B1 (sotto 1 = meglio)")
axs[1].legend(fontsize=8.5)
fig.suptitle("Nowcasting: errore (RMSE) rispetto al modello con soli dati ufficiali", fontweight="bold", y=1.02)
R.salva_grafico(fig, "nc_3_rmse_relativo")

# importanza delle variabili (random forest, fuori campione)
ETI = {"ar1": "ISTAT t-3", "ar2": "ISTAT t-4", "gt_hotel": "Trends hotel", "gt_voli": "Trends voli",
       "gt_attrazioni": "Trends destinazioni", "wiki": "Wikipedia", "mese": "mese dell'anno"}
iv = imp.loc[[c for c in ETI if c in imp.index]]
fig, ax = plt.subplots(figsize=(9, 5.2))
y = np.arange(len(iv))
for k, mk in enumerate(MERC):
    ax.barh(y + (k - 0.5) * 0.38, iv[mk], 0.36, color=MERC[mk][1], label=MERC[mk][0])
ax.axvline(0, color=COL["nero"], lw=0.8)
ax.set_yticks(y); ax.set_yticklabels([ETI[c] for c in iv.index]); ax.invert_yaxis()
ax.set_xlabel("aumento dell'RMSE sul 2022-2024 quando la variabile viene rimescolata")
ax.legend(fontsize=9)
ax.set_title("Random forest stimato fino al 2021: importanza delle variabili fuori campione")
R.salva_grafico(fig, "nc_2_importanza_rf")
R.chiudi()