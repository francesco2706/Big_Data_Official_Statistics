"""
SCRIPT 7 - analisi esplorativa e confronto tra le fonti digitali e il dato ufficiale ISTAT.

Sezioni
  1. caricamento e armonizzazione delle quattro fonti + qualita' di Google Trends
  2. dinamica annua 2016-2024 (indice 2019 = 100) e crescita di Reddit
  3. stagionalita': quanto ogni fonte riproduce il profilo mensile ISTAT, regione per regione
  4. distribuzione territoriale: le fonti ordinano le regioni come ISTAT?
  5. variazioni annue: correlazione con ISTAT per periodo (normale, COVID, ripresa)
  6. tabella riassuntiva sulla qualita' delle fonti
"""
import os
import warnings

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from script_0_comune import salva_inglese

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "processed")
OUT = os.path.join(ROOT, "output")
os.makedirs(OUT, exist_ok=True)

# ================================================================ stile e utilita'
COL = dict(nero="#0b0b0b", testo="#52514e", griglia="#e1e0d9", griglia2="#c3c2b7", grigio="#898781",
           blu="#2a78d6", arancio="#eb6834", verde="#1baf7a", giallo="#eda100", viola="#7a5bd6")
FONTI = {"ISTAT arrivi": COL["nero"], "Trends: hotel": COL["blu"], "Trends: voli": COL["arancio"],
         "Trends: destinazioni": COL["verde"], "Wikipedia": COL["viola"], "Reddit": COL["giallo"]}
NOMI = {"ITC1": "Piemonte", "ITC2": "Valle d'Aosta", "ITC3": "Liguria", "ITC4": "Lombardia", "ITDA": "Trentino-AA",
        "ITD3": "Veneto", "ITD4": "Friuli-VG", "ITD5": "Emilia-Romagna", "ITE1": "Toscana", "ITE2": "Umbria",
        "ITE3": "Marche", "ITE4": "Lazio", "ITF1": "Abruzzo", "ITF2": "Molise", "ITF3": "Campania", "ITF4": "Puglia",
        "ITF5": "Basilicata", "ITF6": "Calabria", "ITG1": "Sicilia", "ITG2": "Sardegna"}
INTENT = {"hotel": "Trends: hotel", "voli": "Trends: voli", "attrazioni": "Trends: destinazioni"}
MERCATI = [("domestico", "Mercato domestico"), ("estero", "Mercato estero")]
MESI = list("GFMAMGLASOND")
mpl.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
    "axes.edgecolor": COL["griglia2"], "axes.labelcolor": COL["testo"], "xtick.color": COL["testo"], "ytick.color": COL["testo"],
    "axes.grid": True, "grid.color": COL["griglia"], "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 11, "axes.titlesize": 12.5, "axes.titleweight": "bold", "axes.titlecolor": COL["nero"],
    "lines.linewidth": 2, "legend.frameon": False, "savefig.dpi": 200, "savefig.bbox": "tight"})
log = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    log.append(s)


def salva(fig, nome):
    fig.savefig(f"{OUT}/{nome}.png")
    salva_inglese(fig, nome)
    plt.close(fig)
    say(f"  grafico salvato: {OUT}/{nome}.png")


# ================================================================ 1. caricamento e armonizzazione
say("=" * 70, "\n1. DATI\n" + "=" * 70)

# ISTAT: gia' pulito dal passo 1 (Trentino-AA unito, 2025 escluso); dal 2011 come Google Trends
istat = pd.read_csv(f"{DATA}/istat_target.csv")
istat = istat[istat.TIME_PERIOD.between("2011-01", "2024-12")]

# Google Trends: indice della regione = somma dei suoi argomenti (stessa richiesta, stessa scala)
raw = pd.read_csv(f"{DATA}/trends_rep1_all.csv")
tr = raw.groupby(["REF_AREA", "geo", "market", "intent", "TIME_PERIOD"], as_index=False).value.sum()
tr = tr.sort_values(["REF_AREA", "geo", "intent", "TIME_PERIOD"])
KEY = ["REF_AREA", "geo", "intent"]
tr["zero_share"] = tr.groupby(KEY).value.transform(lambda v: (v == 0).mean()) # quota di mesi a zero
tr["usable"] = tr.zero_share <= 0.20  # serie utilizzabile
tr["yoy"] = np.log1p(tr.value) - np.log1p(tr.groupby(KEY).value.shift(12)) # log(1+G_t) - log(1+G_t-12)

# Wikipedia: conteggi, quindi sommabili. Domestico = it, estero = en + de + fr + es
wk = pd.read_csv(f"{DATA}/wiki_mensile_v2.csv")
wk = (wk.groupby(["REF_AREA", "market", "TIME_PERIOD"], as_index=False).views_totale.sum()
        .rename(columns={"views_totale": "views"}).sort_values(["REF_AREA", "market", "TIME_PERIOD"]))
wk["yoy"] = np.log(wk.views) - np.log(wk.groupby(["REF_AREA", "market"]).views.shift(12))

# Reddit: quota di testi del mese che citano la regione
rd = pd.read_csv(f"{DATA}/reddit_mensile.csv").sort_values(["REF_AREA", "TIME_PERIOD"])
q = rd.quota_testi.where(rd.quota_testi > 0)
rd["yoy"] = np.log(q) - np.log(q.groupby(rd.REF_AREA).shift(12))

for nome, d in [("istat", istat), ("trends", tr), ("wiki", wk), ("reddit", rd)]:
    d.to_csv(f"{DATA}/{nome}.csv", index=False)
    d["anno"] = d.TIME_PERIOD.str[:4].astype(int)
    d["mese"] = d.TIME_PERIOD.str[5:].astype(int)

serie = tr.drop_duplicates(KEY)
say(pd.DataFrame([
    dict(fonte="ISTAT", periodo=f"{istat.TIME_PERIOD.min()} / {istat.TIME_PERIOD.max()}", serie=istat.groupby(["REF_AREA", "market"]).ngroups),
    dict(fonte="Google Trends", periodo=f"{tr.TIME_PERIOD.min()} / {tr.TIME_PERIOD.max()}", serie=len(serie)),
    dict(fonte="Wikipedia", periodo=f"{wk.TIME_PERIOD.min()} / {wk.TIME_PERIOD.max()}", serie=wk.groupby(["REF_AREA", "market"]).ngroups),
    dict(fonte="Reddit", periodo=f"{rd.TIME_PERIOD.min()} / {rd.TIME_PERIOD.max()}", serie=rd.REF_AREA.nunique())]).to_string(index=False))
say(f"\nTrends: serie utilizzabili {serie.usable.sum()} su {len(serie)} ({serie.usable.mean():.0%})")
qp = serie.pivot_table(index="geo", columns="intent", values="usable", aggfunc="mean")
say(qp.round(2).to_string())
qr = serie.groupby("REF_AREA").usable.sum().sort_values()

fig, axs = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw=dict(width_ratios=[1, 1.4], wspace=0.45))
im = axs[0].imshow(qp[["hotel", "voli", "attrazioni"]].values, cmap="Blues", vmin=0, vmax=1, aspect="auto")
axs[0].set_xticks(range(3)); axs[0].set_xticklabels(["hotel", "voli", "destinazioni"])
axs[0].set_yticks(range(len(qp))); axs[0].set_yticklabels(qp.index); axs[0].grid(False)
for i in range(len(qp)):
    for j, c in enumerate(["hotel", "voli", "attrazioni"]):
        v = qp[c].iloc[i]
        axs[0].text(j, i, f"{v:.0%}", ha="center", va="center", fontsize=10, color="white" if v > 0.6 else COL["nero"])
axs[0].set_title("Serie Trends utilizzabili per Paese")
axs[1].barh([NOMI[r] for r in qr.index], qr.values, color=COL["blu"], height=0.65)
axs[1].axvline(18, color=COL["grigio"], lw=1, ls=":")
axs[1].set_xlabel("serie utilizzabili su 18 (6 Paesi x 3 categorie)")
axs[1].set_xticks(range(0, 19, 3))
axs[1].set_title("Serie Trends utilizzabili per regione")
salva(fig, "eda1_qualita_trends")

# ================================================================ 2. dinamica annua 2016-2024
say("\n" + "=" * 70, "\n2. DINAMICA ANNUA 2016-2024 (indice 2019 = 100)\n" + "=" * 70)
ANNI = list(range(2016, 2025))


def indice_somma(df, col, mercato):
    a = df[df.market == mercato].groupby("anno")[col].sum()
    return 100 * a / a[2019]


def indice_trends(mercato, intent):
    # Trends non e' sommabile tra regioni: ogni serie si indicizza al proprio 2019, poi mediana tra le serie
    s = tr[(tr.market == mercato) & (tr.intent == intent) & tr.usable]
    a = s.groupby(["REF_AREA", "geo", "anno"]).value.mean().unstack()
    a = a[a[2019] > 0]
    return 100 * a.div(a[2019], axis=0).median()


righe = []
fig, axs = plt.subplots(1, 2, figsize=(13, 4.5), sharey=True)
for ax, (mercato, titolo) in zip(axs, MERCATI):
    ser = {"ISTAT arrivi": indice_somma(istat, "arrivi", mercato)}
    ser.update({INTENT[i]: indice_trends(mercato, i) for i in INTENT})
    ser["Wikipedia"] = indice_somma(wk, "views", mercato)
    for nome, s in ser.items():
        s = s.reindex(ANNI)
        ax.plot(ANNI, s.values, marker="o", ms=4, color=FONTI[nome], lw=2.8 if nome.startswith("ISTAT") else 1.8, label=nome)
        righe.append(pd.DataFrame({"mercato": mercato, "fonte": nome, "anno": ANNI, "indice": s.values}))
    ax.axhline(100, color=COL["griglia2"], lw=1)
    ax.axvline(2022, color=COL["grigio"], lw=0.8, ls=":")
    ax.text(2022.1, 22, "Google: cambio\nraccolta dati", fontsize=7.5, color=COL["grigio"])
    ax.set_title(titolo); ax.set_xticks(ANNI)
axs[0].set_ylabel("indice, 2019 = 100")
axs[1].legend(fontsize=9, loc="lower left", bbox_to_anchor=(0.0, 0.12))
salva(fig, "eda2_dinamica")
ind = pd.concat(righe)
ind.to_csv(f"{OUT}/eda2_indici.csv", index=False)
say(ind[ind.anno.isin([2016, 2020, 2021, 2022, 2024])].pivot_table(index=["mercato", "fonte"], columns="anno",
                                                                    values="indice", sort=False).round(0).to_string())

n = rd.drop_duplicates("TIME_PERIOD").set_index("TIME_PERIOD").n_testi_mese
fig, ax = plt.subplots(figsize=(11, 3.6))
ax.bar(pd.to_datetime(n.index), n.values / 1000, width=20, color=FONTI["Reddit"])
ax.set_ylabel("testi al mese (migliaia)")
ax.set_title("Reddit r/ItalyTravel: testi al mese (bot e moderatori esclusi)")
salva(fig, "eda2_reddit_volume")
say(f"Reddit: da {n.iloc[0]:,} testi (gen 2022) a {n.max():,} ({n.idxmax()}), fattore {n.max() / n.iloc[0]:.0f}")

# ================================================================ 3. stagionalita'
say("\n" + "=" * 70, "\n3. STAGIONALITA' (profili mensili 2023-2024)\n" + "=" * 70)


def profilo(df, col, keys):
    """Profilo medio 2023-2024: ogni mese come quota del totale annuo."""
    d = df[df.anno.isin([2023, 2024])]
    p = d.groupby(keys + ["mese"])[col].mean()
    return p / p.groupby(level=keys).transform("sum")


p_ist = profilo(istat, "arrivi", ["REF_AREA", "market"])
p_tr = profilo(tr[tr.usable], "value", ["REF_AREA", "geo", "intent"])
p_wk = profilo(wk, "views", ["REF_AREA", "market"])
p_rd = profilo(rd, "n_testi", ["REF_AREA"])
righe = []
for reg in NOMI:
    for mercato, _ in MERCATI:
        y = p_ist.loc[(reg, mercato)].values
        for i, lab in INTENT.items():
            geos = tr[(tr.REF_AREA == reg) & (tr.market == mercato) & (tr.intent == i) & tr.usable].geo.unique()
            if len(geos):
                r = [np.corrcoef(y, p_tr.loc[(reg, g, i)].reindex(range(1, 13)).values)[0, 1] for g in geos]
                righe.append(dict(REF_AREA=reg, mercato=mercato, fonte=lab, r=np.nanmedian(r)))
        righe.append(dict(REF_AREA=reg, mercato=mercato, fonte="Wikipedia", r=np.corrcoef(y, p_wk.loc[(reg, mercato)].values)[0, 1]))
        if mercato == "estero" and rd[rd.REF_AREA == reg].n_testi.sum() >= 240:     # almeno ~10 testi al mese
            righe.append(dict(REF_AREA=reg, mercato=mercato, fonte="Reddit", r=np.corrcoef(y, p_rd.loc[reg].values)[0, 1]))
sea = pd.DataFrame(righe)
sea.to_csv(f"{OUT}/eda3_stagionalita.csv", index=False)
say("Correlazione tra profilo mensile della fonte e profilo ISTAT (statistiche sulle regioni):")
say(sea.groupby(["mercato", "fonte"]).r.agg(["median", "min", "max", "count"]).round(2).to_string())

ORDINE = list(INTENT.values()) + ["Wikipedia", "Reddit"]
fig, axs = plt.subplots(1, 2, figsize=(13, 4.4), sharey=True)
for ax, (mercato, titolo) in zip(axs, MERCATI):
    s = sea[sea.mercato == mercato]
    labs = [o for o in ORDINE if o in s.fonte.unique()]
    for j, lab in enumerate(labs):
        v = s[s.fonte == lab].r.values
        ax.scatter(j + np.random.default_rng(j).uniform(-0.12, 0.12, len(v)), v, s=22, color=FONTI[lab], alpha=0.75)
        ax.hlines(np.median(v), j - 0.3, j + 0.3, color=COL["nero"], lw=2)
    ax.set_xticks(range(len(labs))); ax.set_xticklabels([l.replace("Trends: ", "Trends\n") for l in labs], fontsize=9.5)
    ax.axhline(0, color=COL["griglia2"], lw=1); ax.set_title(titolo)
axs[0].set_ylabel("correlazione con il profilo ISTAT")
fig.suptitle("Profili stagionali 2023-2024: un punto per regione, linea = mediana", y=1.02, fontweight="bold")
salva(fig, "eda3_stagionalita")

fig, axs = plt.subplots(1, 3, figsize=(14, 3.9), sharey=True)
for ax, (reg, mercato, geo) in zip(axs, [("ITG2", "domestico", "IT"), ("ITDA", "estero", "DE"), ("ITE4", "estero", "US")]):
    ax.plot(range(1, 13), p_ist.loc[(reg, mercato)].values, color=COL["nero"], lw=2.8, label="ISTAT arrivi")
    ax.plot(range(1, 13), p_tr.loc[(reg, geo, "hotel")].values, color=COL["blu"], label=f"Trends hotel ({geo})")
    ax.plot(range(1, 13), p_wk.loc[(reg, mercato)].values, color=COL["viola"], label="Wikipedia")
    if mercato == "estero":
        ax.plot(range(1, 13), p_rd.loc[reg].values, color=COL["giallo"], label="Reddit")
    ax.set_xticks(range(1, 13)); ax.set_xticklabels(MESI)
    ax.set_title(f"{NOMI[reg]}, {mercato}", fontsize=11); ax.legend(fontsize=8.5)
axs[0].set_ylabel("quota del totale annuo")
salva(fig, "eda3_stagionalita_esempi")

# ================================================================ 4. distribuzione territoriale
say("\n" + "=" * 70, "\n4. DISTRIBUZIONE TERRITORIALE (quote 2023-2024)\n" + "=" * 70)


def quote(df, col, mercato=None):
    d = df[df.anno.isin([2023, 2024])]
    if mercato:
        d = d[d.market == mercato]
    a = d.groupby("REF_AREA")[col].sum()
    return a / a.sum()


sh = pd.DataFrame({"istat_dom": quote(istat, "arrivi", "domestico"), "istat_est": quote(istat, "arrivi", "estero"),
                   "wiki_dom": quote(wk, "views", "domestico"), "wiki_est": quote(wk, "views", "estero"),
                   "reddit": quote(rd, "n_testi")})
sh["reddit_su_istat"] = sh.reddit / sh.istat_est
sh.assign(regione=sh.index.map(NOMI)).round(4).to_csv(f"{OUT}/eda4_quote_regionali.csv")
CONFR = [("istat_dom", "wiki_dom", "Domestico: Wikipedia it"), ("istat_est", "wiki_est", "Estero: Wikipedia en/de/fr/es"),
         ("istat_est", "reddit", "Estero: menzioni Reddit")]
rho = {b: stats.spearmanr(sh[a], sh[b]) for a, b, _ in CONFR}
for a, b, t in CONFR:
    say(f"{t:32s} Spearman = {rho[b].correlation:.2f} (p = {rho[b].pvalue:.4f})")
say("\nReddit: quota di menzioni / quota di arrivi stranieri ISTAT (>1 sovrarappresentata):")
say(sh.reddit_su_istat.rename(NOMI).sort_values(ascending=False).round(2).to_string())

fig, axs = plt.subplots(1, 3, figsize=(15, 4.8))
for ax, (a, b, t) in zip(axs, CONFR):
    ax.scatter(sh[a], sh[b], s=40, color=FONTI["Reddit" if b == "reddit" else "Wikipedia"], zorder=3)
    lim = [min(sh[a].min(), sh[b].min()) * 0.7, max(sh[a].max(), sh[b].max()) * 1.4]
    ax.plot(lim, lim, color=COL["nero"], lw=1, ls="--")
    for reg, r in sh.iterrows():
        ax.annotate(NOMI[reg], (r[a], r[b]), xytext=(3, 2), textcoords="offset points", fontsize=7.5, color=COL["testo"])
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("quota arrivi ISTAT 2023-24"); ax.set_ylabel("quota della fonte digitale")
    ax.set_title(f"{t} (Spearman {rho[b].correlation:.2f})", fontsize=11)
salva(fig, "eda4_territorio")

# ================================================================ 5. variazioni annue per periodo
say("\n" + "=" * 70, "\n5. VARIAZIONI ANNUE: correlazione con ISTAT per periodo\n" + "=" * 70)
X = [tr[(tr.intent == i) & tr.usable].groupby(["REF_AREA", "market", "TIME_PERIOD"]).yoy.mean().rename(lab)
     for i, lab in INTENT.items()]                              # estero: media sui Paesi utilizzabili
X.append(wk.set_index(["REF_AREA", "market", "TIME_PERIOD"]).yoy.rename("Wikipedia"))
X.append(rd.assign(market="estero").set_index(["REF_AREA", "market", "TIME_PERIOD"]).yoy.rename("Reddit"))
P = (istat[["REF_AREA", "market", "TIME_PERIOD", "yoy_arrivi"]].set_index(["REF_AREA", "market", "TIME_PERIOD"])
     .join(pd.concat(X, axis=1), how="left").reset_index())
PERIODI = {"2012-2019\n(normale)": ("2012-01", "2019-12"), "2020-2021\n(COVID)": ("2020-01", "2021-12"),
           "2022\n(ripresa)": ("2022-01", "2022-12"), "2023-2024\n(normale)": ("2023-01", "2024-12")}
righe = []
for per, (a, b) in PERIODI.items():
    for mercato, _ in MERCATI:
        d = P[(P.market == mercato) & P.TIME_PERIOD.between(a, b)]
        for f in ORDINE:
            ok = d[["yoy_arrivi", f]].replace([np.inf, -np.inf], np.nan).dropna()
            if len(ok) >= 30:
                righe.append(dict(periodo=per.replace("\n", " "), mercato=mercato, fonte=f, r=ok.yoy_arrivi.corr(ok[f]), n=len(ok)))
cr = pd.DataFrame(righe)
cr.to_csv(f"{OUT}/eda5_correlazioni_yoy.csv", index=False)
say(cr.pivot_table(index=["mercato", "fonte"], columns="periodo", values="r", sort=False)
      .reindex(columns=[p.replace("\n", " ") for p in PERIODI]).round(2).to_string())

fig, axs = plt.subplots(1, 2, figsize=(14, 4.4), sharey=True)
for ax, (mercato, titolo) in zip(axs, MERCATI):
    d = cr[cr.mercato == mercato]
    fonti = [o for o in ORDINE if o in d.fonte.unique()]
    w = 0.8 / len(fonti)
    for j, f in enumerate(fonti):
        v = d[d.fonte == f].set_index("periodo").r.reindex([p.replace("\n", " ") for p in PERIODI])
        ax.bar(np.arange(len(PERIODI)) + (j - (len(fonti) - 1) / 2) * w, v.values, w * 0.92, color=FONTI[f], label=f)
    ax.axhline(0, color=COL["griglia2"], lw=1)
    ax.set_xticks(range(len(PERIODI))); ax.set_xticklabels(list(PERIODI), fontsize=9.5); ax.set_title(titolo)
axs[0].set_ylabel("correlazione con la variazione annua ISTAT")
axs[1].legend(fontsize=8.5, loc="upper right")
salva(fig, "eda5_correlazioni_yoy")

# ================================================================ 6. qualita' delle fonti
say("\n" + "=" * 70, "\n6. QUALITA' DELLE FONTI\n" + "=" * 70)
qual = pd.DataFrame([
    dict(fonte="ISTAT", unita="arrivi (conteggi)", periodo="2011-2024", serie=40,
         note="2025 escluso: versione scaricata incoerente con i dati provvisori ISTAT"),
    dict(fonte="Google Trends", unita="indice 0-100 per richiesta", periodo="2011-2025", serie=len(serie),
         note=f"{serie.usable.mean():.0%} utilizzabili; non confrontabile tra regioni; cambio raccolta dati gen 2022"),
    dict(fonte="Wikipedia", unita="visite (conteggi)", periodo="2015-07 / 2025-12", serie=40,
         note="lingua come proxy del mercato; Wikipedia italiana in calo dal 2022"),
    dict(fonte="Reddit", unita="quota di testi che citano la regione", periodo="2022-2025", serie=20,
         note=f"solo anglofoni; community x{n.max() / n.iloc[0]:.0f}; regioni piccole con pochi testi"),
])
qual.to_csv(f"{OUT}/eda7_qualita_fonti.csv", index=False)
say(qual.to_string(index=False))

open(f"{OUT}/eda_risultati.txt", "w", encoding="utf-8").write("\n".join(log))
print(f"\nFatto. Risultati testuali in {OUT}/eda_risultati.txt")
