"""
SCRIPT 14 - Indicatore di attenzione digitale (Digital Attention Index, DAI)

L'indicatore descrive l'attenzione online che ogni regione riceve da potenziali visitatori nel 2023-2024. Segue il
manuale OCSE-JRC sugli indicatori compositi (2008):
  1. quadro teorico: tre pilastri
       Visibilita'   quanto se ne parla          quota di visite Wikipedia, quota di menzioni su Reddit
       Reputazione   con che tono                sentiment di Qwen corretto, solo mercato estero
       Slancio       quanto e' cresciuta         crescita 2019-2024 di visite Wikipedia e ricerche Google
  2. normalizzazione con il punteggio di rango (0-100): per ogni indicatore le 20 regioni sono ordinate,
     100 = la migliore, 0 = la peggiore; 66 = meglio del 66% delle altre regioni. Guarda solo l'ordine, quindi
     non servono logaritmi e una regione molto grande (Lazio) non schiaccia le altre
  3. pesi uguali e media aritmetica
  4. validazione per pilastro: Visibilita' contro la quota di arrivi ISTAT, Slancio contro la crescita degli arrivi
     2019-2024. Il DAI nel suo complesso e' una sintesi descrittiva dell'attenzione online, non una stima dei flussi:
     somma livello, tono e crescita, che non hanno un unico equivalente ufficiale
  5. scarto tra attenzione e turisti:
       scarto di visibilita' = log(quota di attenzione digitale) - log(quota di arrivi)
           > 0: regione piu' cercata che visitata (potenziale non convertito); < 0: piu' visitata che cercata
       scarto di slancio = log(crescita digitale) - log(crescita degli arrivi), relative alla mediana nazionale
  6. analisi di incertezza: normalizzazione (ranghi, punteggi T, min-max) x pesi (uguali, componenti principali) x
     aggregazione (aritmetica, geometrica) x misura del tono (stima con shrinkage, media semplice, al netto del volume)
"""
import itertools

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

from script_0_comune import COL, NOMI, OUT, PROC, REG, Registro

R = Registro("ind_risultati.txt")
MERC_COL = {"estero": COL["arancio"], "domestico": COL["blu"]}
PIL_COL = {"Visibilita'": COL["blu"], "Reputazione": COL["giallo"], "Slancio": COL["verde"]}

istat, tr = pd.read_csv(PROC / "istat.csv"), pd.read_csv(PROC / "trends.csv")
wk, rd = pd.read_csv(PROC / "wiki.csv"), pd.read_csv(PROC / "reddit.csv")
for d in (istat, tr, wk, rd):
    d["anno"] = d.TIME_PERIOD.str[:4].astype(int)
rep = pd.read_csv(OUT / "rep_regioni.csv", index_col=0).reindex(REG)

# ================================================================ 1. indicatori elementari
R.titolo("1. INDICATORI ELEMENTARI")


def quota(df, col, filtro):
    a = df[filtro].groupby("REF_AREA")[col].sum().reindex(REG)
    return a / a.sum()


def crescita_wiki(mercato):
    a = wk[wk.market == mercato].groupby(["REF_AREA", "anno"]).views.sum().unstack()
    return (a[2024] / a[2019]).reindex(REG)


def crescita_trends(mercato):
    s = tr[(tr.market == mercato) & tr.usable & tr.anno.isin([2019, 2024])]
    a = s.groupby(["REF_AREA", "geo", "intent", "anno"]).value.mean().unstack()
    a = a[a[2019] > 0]
    return (a[2024] / a[2019]).groupby(level="REF_AREA").median().reindex(REG)


# misura del tono: stima con shrinkage (principale); le altre due entrano nell'analisi di incertezza
SENT = {"stima con shrinkage": rep.shrink, "media semplice": rep.media, "al netto del volume": rep.netto_volume}
PRINC = next(iter(SENT))


def elementari(mercato, sent=None):
    sent = sent or PRINC
    if mercato == "estero":
        return pd.DataFrame({
            "wiki_quota": quota(wk, "views", (wk.market == "estero") & wk.anno.isin([2023, 2024])),
            "reddit_quota": quota(rd, "n_testi", rd.anno.isin([2023, 2024])),
            "reddit_sentiment": SENT[sent],
            "wiki_crescita": crescita_wiki("estero"),
            "trends_crescita": crescita_trends("estero")})
    return pd.DataFrame({
        "wiki_quota": quota(wk, "views", (wk.market == "domestico") & wk.anno.isin([2023, 2024])),
        "wiki_crescita": crescita_wiki("domestico"),
        "trends_crescita": crescita_trends("domestico")})


PILASTRI = {"Visibilita'": ["wiki_quota", "reddit_quota"], "Reputazione": ["reddit_sentiment"],
            "Slancio": ["wiki_crescita", "trends_crescita"]}
LOG = ["wiki_quota", "reddit_quota", "wiki_crescita", "trends_crescita"]
IND = {mk: elementari(mk) for mk in ["estero", "domestico"]}
for mk, X in IND.items():
    X.rename(index=NOMI).round(4).to_csv(OUT / f"ind_elementari_{mk}.csv")

# correlazioni tra indicatori elementari: mostra perche' il composito non puo' imitare un solo dato ISTAT
C = IND["estero"].apply(lambda c: np.log(c) if c.name in LOG else c).corr("spearman")
R.say("Correlazioni di Spearman tra indicatori elementari (mercato estero):")
R.say(C.round(2).to_string())


# ================================================================ 2. normalizzazione, pesi, aggregazione
def normalizza(X, metodo):
    X = X.copy()
    for c in X.columns:
        if c in LOG:
            X[c] = np.log(X[c])
    z = (X - X.mean()) / X.std(ddof=0)
    if metodo == "punteggiT":
        return 50 + 10 * z
    if metodo == "minmax":
        return 100 * (X - X.min()) / (X.max() - X.min())
    return (X.rank() - 1) / (X.count() - 1) * 100                   # ranghi: 100 = migliore, 0 = peggiore


def pesi_pca(Xn, pil):
    w = {}
    for p, cols in pil.items():
        if len(cols) == 1:
            w[cols[0]] = 1.0
            continue
        z = ((Xn[cols] - Xn[cols].mean()) / Xn[cols].std(ddof=0)).fillna(0)
        load = PCA(1).fit(z).components_[0] ** 2
        w.update(dict(zip(cols, load / load.sum())))
    return w


def composito(X, norm="ranghi", pesi="uguali", aggr="aritmetica"):
    pil = {p: [c for c in cols if c in X.columns] for p, cols in PILASTRI.items()}
    pil = {p: c for p, c in pil.items() if c}
    Xn = normalizza(X, norm)
    w = pesi_pca(Xn, pil) if pesi == "pca" else {c: 1 / len(cols) for cols in pil.values() for c in cols}
    P = pd.DataFrame({p: (Xn[cols] * pd.Series({c: w[c] for c in cols})).sum(axis=1, min_count=1)
                      / Xn[cols].notna().mul(pd.Series({c: w[c] for c in cols})).sum(axis=1).replace(0, np.nan)
                      for p, cols in pil.items()})
    if aggr == "geometrica":
        idx = np.exp(np.log(P - P.min().min() + 1).mean(axis=1))      # traslazione comune: valori positivi
    else:
        idx = P.mean(axis=1)
    return idx, P


R.titolo("2. INDICATORE (punteggio di rango: 100 = regione migliore, 0 = peggiore, 50 = a meta' classifica)")
RIS = {}
for mk, X in IND.items():
    idx, P = composito(X)
    RIS[mk] = P.assign(DAI=idx).rename(index=NOMI).sort_values("DAI", ascending=False)
    RIS[mk].round(1).to_csv(OUT / f"ind_dai_{mk}.csv")
    R.say(f"\nMercato {mk}:")
    R.say(RIS[mk].round(1).to_string())
R.say(f"\nNota: il Molise ha {int(rep.n_thread['ITF2'])} thread; con lo shrinkage il suo tono e' avvicinato alla media "
      "invece di finire all'estremo della scala.")

# ================================================================ 3. validazione per pilastro
R.titolo("3. VALIDAZIONE PER PILASTRO (Spearman con ISTAT)")
ist = istat.groupby(["REF_AREA", "market", "anno"]).arrivi.sum()
VAL, righe = {}, []
for mk in ["estero", "domestico"]:
    q = ist.xs(mk, level="market").unstack()
    arr_q = ((q[2023] + q[2024]) / (q[2023] + q[2024]).sum()).reindex(REG).rename(index=NOMI)
    arr_c = (q[2024] / q[2019]).reindex(REG).rename(index=NOMI)
    VAL[mk] = (arr_q, arr_c)
    P = RIS[mk]
    for pil, rif, nome_rif in [("Visibilita'", arr_q, "quota arrivi 2023-24"),
                               ("Slancio", arr_c, "crescita arrivi 2019-24"),
                               ("DAI", arr_q, "quota arrivi 2023-24")]:
        r = stats.spearmanr(P[pil], rif.reindex(P.index))
        righe.append(dict(mercato=mk, misura=pil, riferimento_ISTAT=nome_rif, spearman=round(r.correlation, 2),
                          p_value=round(r.pvalue, 4)))
val = pd.DataFrame(righe)
val.to_csv(OUT / "ind_validazione.csv", index=False)
R.say(val.to_string(index=False))
R.say("\nLettura: i pilastri Visibilita' e Slancio sono validati dal dato ufficiale; il DAI no, e non deve esserlo:\n"
      "mescola livello, tono e crescita. Va presentato come sintesi descrittiva dell'attenzione online, accompagnato\n"
      "dai pilastri e dall'intervallo di incertezza, non come stima dei flussi turistici.")

# ================================================================ 4. scarto tra attenzione digitale e turisti
R.titolo("4. SCARTO TRA ATTENZIONE DIGITALE E TURISTI")
scarti = {}
for mk in ["estero", "domestico"]:
    X = IND[mk].rename(index=NOMI)
    arr_q, arr_c = VAL[mk]
    att = np.exp(np.log(X[["wiki_quota", "reddit_quota"]] if mk == "estero" else X[["wiki_quota"]]).mean(axis=1))
    att = att / att.sum()                                               # quota di attenzione (media geometrica)
    cresc_dig = np.exp(np.log(X[["wiki_crescita", "trends_crescita"]]).mean(axis=1))   # NaN Trends: solo Wiki
    S = pd.DataFrame({"quota_attenzione": att, "quota_arrivi": arr_q,
                      "scarto_visibilita": np.log(att) - np.log(arr_q),
                      "crescita_digitale": cresc_dig, "crescita_arrivi": arr_c,
                      # crescite relative alla mediana nazionale: Wikipedia italiana cala per motivi suoi (meno uso
                      # di Wikipedia in generale), quindi conta la crescita di una regione RISPETTO alle altre
                      "scarto_slancio": np.log(cresc_dig / cresc_dig.median()) - np.log(arr_c / arr_c.median())})
    scarti[mk] = S
    S.round(4).to_csv(OUT / f"ind_scarto_{mk}.csv")
    R.say(f"\nMercato {mk} (log-rapporti: +0.69 = il doppio, -0.69 = la meta'; slancio relativo alla mediana):")
    piccole = S.index[S.quota_arrivi < 0.005]
    if len(piccole):
        R.say(f"Attenzione: quota di arrivi sotto lo 0.5% per {', '.join(piccole)}: lo scarto e' un rapporto con un "
              "denominatore piccolissimo e va letto con cautela.")
    R.say(S.sort_values("scarto_visibilita", ascending=False)
          [["quota_attenzione", "quota_arrivi", "scarto_visibilita", "scarto_slancio"]].round(3).to_string())

# ================================================================ 5. analisi di incertezza allargata
R.titolo("5. ANALISI DI INCERTEZZA")
NORM, PESI, AGGR = ["ranghi", "punteggiT", "minmax"], ["uguali", "pca"], ["aritmetica", "geometrica"]
INC, SINTESI = {}, []
for mk in ["estero", "domestico"]:
    versioni = list(SENT) if mk == "estero" else [PRINC]               # il domestico non usa il sentiment
    ranks = {}
    for n, w, a, s in itertools.product(NORM, PESI, AGGR, versioni):
        ranks[f"{n}/{w}/{a}/{s}"] = composito(elementari(mk, s), n, w, a)[0].rename(index=NOMI).rank(ascending=False)
    ranks = pd.DataFrame(ranks)
    base = RIS[mk].DAI.rank(ascending=False)
    rr = pd.DataFrame({"base": base, "mediana": ranks.median(1), "min": ranks.min(1), "max": ranks.max(1),
                       "p10": ranks.quantile(0.1, axis=1), "p90": ranks.quantile(0.9, axis=1)}).sort_values("mediana")
    rr.to_csv(OUT / f"ind_incertezza_{mk}.csv")
    INC[mk] = rr
    rho = ranks.corr("spearman").to_numpy()
    R.say(f"Mercato {mk}: {ranks.shape[1]} combinazioni | Spearman minima tra classifiche = {rho.min():.2f} | "
          f"ampiezza media dell'intervallo di posizioni = {(rr['max'] - rr['min']).mean():.1f}")
    if mk == "estero":
        for s in versioni[1:]:
            a_ = composito(elementari(mk, s))[0]
            b_ = composito(elementari(mk, PRINC))[0]
            R.say(f"   sentiment '{s}' invece di '{PRINC}': Spearman classifica DAI = "
                  f"{stats.spearmanr(a_, b_).correlation:.2f}")
    # posizioni "sicure": regioni sempre nel primo o nell'ultimo quarto
    prime, ultime = ", ".join(rr.index[rr["max"] <= 5]) or "nessuna", ", ".join(rr.index[rr["min"] >= 16]) or "nessuna"
    R.say(f"   sempre tra le prime 5: {prime} | sempre tra le ultime 5: {ultime}")
    SINTESI.append(dict(mercato=mk, varianti=ranks.shape[1], spearman_min=round(rho.min(), 2),
                        ampiezza_media=round((rr["max"] - rr["min"]).mean(), 1), sempre_prime5=prime,
                        sempre_ultime5=ultime, sentiment_principale=PRINC, versioni_sentiment=len(versioni)))
pd.DataFrame(SINTESI).to_csv(OUT / "ind_sintesi_incertezza.csv", index=False)   # letto da script_18_report.py

# ================================================================ grafici
fig, axs = plt.subplots(1, 2, figsize=(13, 6.5), gridspec_kw=dict(width_ratios=[4, 3], wspace=0.45))
for ax, mk in zip(axs, ["estero", "domestico"]):
    P = RIS[mk]                                                   # pilastri + DAI, regioni gia' ordinate per DAI
    im = ax.imshow(P.to_numpy(), cmap="RdBu", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(P.shape[1])); ax.set_xticklabels(P.columns); ax.grid(False)
    ax.set_yticks(range(len(P))); ax.set_yticklabels(P.index, fontsize=9)
    ax.axvline(P.shape[1] - 1.5, color="white", lw=4)              # separa i pilastri dal DAI
    for i in range(P.shape[0]):
        for j in range(P.shape[1]):
            ax.text(j, i, f"{P.iat[i, j]:.0f}", ha="center", va="center", fontsize=8,
                    fontweight="bold" if P.columns[j] == "DAI" else "normal")
    ax.set_title(f"Mercato {mk}")
fig.colorbar(im, ax=axs, shrink=0.6, label="punteggio di rango (100 = migliore, 0 = peggiore)")
fig.suptitle("I tre pilastri e il DAI (punteggi di rango; regioni ordinate per DAI)", fontweight="bold")
R.salva_grafico(fig, "ind_1_pilastri")

fig, axs = plt.subplots(1, 2, figsize=(14, 6.5))
for ax, mk in zip(axs, ["estero", "domestico"]):
    rr = INC[mk]
    y = np.arange(len(rr))
    ax.hlines(y, rr["min"], rr["max"], color=COL["griglia"], lw=6, label="min-max")
    ax.hlines(y, rr.p10, rr.p90, color=COL["griglia2"], lw=6, label="10-90%")
    ax.scatter(rr.base, y, color=COL["nero"], s=35, zorder=3, label="scelta principale")
    ax.set_yticks(y); ax.set_yticklabels(rr.index); ax.invert_yaxis()
    ax.set_xlabel("posizione (1 = massima attenzione)"); ax.set_title(f"Mercato {mk}")
    ax.legend(fontsize=8.5, loc="lower right")
fig.suptitle("Incertezza della classifica DAI (normalizzazione x pesi x aggregazione x sentiment)",
             fontweight="bold", y=1.01)
R.salva_grafico(fig, "ind_2_incertezza")

fig, axs = plt.subplots(1, 2, figsize=(14, 6))
for ax, mk in zip(axs, ["estero", "domestico"]):
    S = scarti[mk]
    ax.axhline(0, color=COL["griglia2"]); ax.axvline(0, color=COL["griglia2"])
    ax.scatter(S.scarto_visibilita, S.scarto_slancio, color=MERC_COL[mk], s=45, zorder=3)
    for reg in S.index:
        ax.annotate(reg, (S.scarto_visibilita[reg], S.scarto_slancio[reg]), xytext=(4, 2),
                    textcoords="offset points", fontsize=8)
    ax.set_xlabel("scarto di visibilita' (> 0: piu' attenzione che turisti)")
    ax.set_ylabel("scarto di slancio (> 0: interesse cresciuto piu' dei turisti)")
    ax.set_title(f"Mercato {mk}")
fig.suptitle("Dove l'attenzione online e i flussi turistici divergono (2019-2024)", fontweight="bold", y=1.01)
R.salva_grafico(fig, "ind_3_scarti")

R.chiudi()