"""
SCRIPT 8 - Topic modeling dei testi di Reddit: di cosa si parla, e come cambiano i temi durante l'anno e negli anni?

  1. testi: post e commenti 2022-2025 (esclusi bot e moderatori, almeno 30 caratteri)
  2. rappresentazione TF-IDF: ogni testo e' un vettore di parole pesate (frequenti nel testo, rare nel corpus);
     i nomi di luoghi sono esclusi, cosi' i temi descrivono di cosa si parla (treni, cibo, alloggi...) e non dove
  3. NMF (Non-negative Matrix Factorization): X ~ W H, con H = temi (pesi delle parole) e W = peso di ogni tema in
     ogni testo. Il numero di temi k si sceglie con la coerenza UMass delle parole principali di ogni tema
  4. ogni testo riceve il tema con peso maggiore
Analisi
  * quota di ogni tema per mese dell'anno e correlazione con gli arrivi stranieri ISTAT (temi che salgono con il turismo)
  * quota di ogni tema per anno 2022-2025
  * temi per regione
"""
import argparse
import os
import re
import time
import warnings

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from script_0_comune import salva_inglese

warnings.filterwarnings("ignore")
ap = argparse.ArgumentParser()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap.add_argument("--input", default=os.path.join(ROOT, "data", "processed", "reddit_testi.csv.gz"))
ap.add_argument("--k", type=int, default=0, help="numero di temi (0 = scelta automatica)")
ap.add_argument("--campione", type=int, default=120_000, help="testi usati per stimare i temi")
args = ap.parse_args()
OUT = os.path.join(ROOT, "output")
PROC = os.path.join(ROOT, "data", "processed")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(0)

COL = dict(nero="#0b0b0b", testo="#52514e", griglia="#e1e0d9", griglia2="#c3c2b7", grigio="#898781",
           blu="#2a78d6", arancio="#eb6834", verde="#1baf7a", giallo="#eda100", viola="#7a5bd6")
NOMI = {"ITC1": "Piemonte", "ITC2": "Valle d'Aosta", "ITC3": "Liguria", "ITC4": "Lombardia", "ITDA": "Trentino-AA",
        "ITD3": "Veneto", "ITD4": "Friuli-VG", "ITD5": "Emilia-Romagna", "ITE1": "Toscana", "ITE2": "Umbria",
        "ITE3": "Marche", "ITE4": "Lazio", "ITF1": "Abruzzo", "ITF2": "Molise", "ITF3": "Campania", "ITF4": "Puglia",
        "ITF5": "Basilicata", "ITF6": "Calabria", "ITG1": "Sicilia", "ITG2": "Sardegna"}
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


# ================================================================ 1. testi
t0 = time.time()
say("=" * 70, "\n1. TESTI\n" + "=" * 70)
cols = ["id", "kind", "TIME_PERIOD", "bot", "mod", "n_char", "regioni", "text"]
d = pd.read_csv(args.input, usecols=cols, keep_default_na=False, dtype={"regioni": str, "text": str})
d = d[(d.bot.astype(str) != "True") & (d["mod"].astype(str) != "True") & (d.n_char.astype(int) >= 30)].reset_index(drop=True)
d["mese"] = d.TIME_PERIOD.str[5:].astype(int)
d["anno"] = d.TIME_PERIOD.str[:4].astype(int)
say(f"Testi analizzati: {len(d):,} (post {(d.kind == 'post').sum():,}, commenti {(d.kind == 'comment').sum():,}) "
    f"| lettura {time.time() - t0:.0f} s")

# ================================================================ 2. TF-IDF
# parole da ignorare: stop word inglesi + parole generiche del forum che compaiono in quasi tutti i temi
EXTRA = {"italy", "italian", "trip", "travel", "just", "like", "know", "want", "going", "thanks", "thank", "hi", "hello",
         "im", "don", "really", "would", "also", "get", "got", "day", "days", "time", "week", "weeks", "plan", "planning",
         "help", "visit", "visiting", "advice", "recommendations", "recommend", "does", "anyone", "good", "great", "best",
         "think", "lot", "way", "make", "need", "say", "said", "sure", "yes", "yeah", "people", "place", "places", "did",
         "didn", "doesn", "isn", "ve", "ll", "lol", "edit", "post", "question", "questions", "maybe", "probably", "actually",
         "definitely", "things", "thing", "pretty", "use", "used", "look", "looking", "go", "went", "come", "take", "took",
         "one", "two", "three", "first", "much", "many", "well", "still", "even", "could", "should", "will", "can", "us",
         "let", "see", "find", "found", "try", "ask", "asked", "able", "right", "bit", "little", "long", "years", "year"}
LUOGHI = set("""abruzzo adige aeolian agrigento alba alberobello alghero alm alpe alta alto amalfi ampezzo anacapri ancona aosta apulia aquila aquileia arezzo ascoli assisi asti atrani bagnoregio bardolino bari barolo basilicata bassano bellagio benedetto bergamo bianco blanc bologna bolzano bormio bozen braies brescia breuil brindisi burano cagliari cala calabria camogli campania campiglio campobasso canazei capo capri caserta catania cefal cefalu cervinia cervo chianti cime cinque cividale civita coast colosseo colosseum como conero corniglia cortina cortona cosenza costa courmayeur cremona del della di dolomites dolomiti dtirol elba emilia ercolano erice etna europe favignana ferrara firenze fiumicino florence friuli funes gaeta gallipoli garda gardena gargano genoa genova gimignano giulio gonone grado gran gubbio herculaneum ischia iseo isernia isola italia italy itc itd itda ite itf itg jesolo la lago lake langhe lazio lazise le lecce lerici levanto lido lignano liguria lipari livigno livorno locorotondo lombardia lombardy loreto lucca maddalena madonna maggiore maiori malcesine manarola mantova mantua maranello maratea marche mare maremma margherita marsala matera menaggio merano messina milan milano minori modena modica molise monopoli mont montalcino monte montepulciano monterosso murano naples napoli noto nuoro olbia orcia orosei orta ortigia ortisei orvieto ostia ostuni otranto padova padua paestum palermo paradiso parma perugia pescara piacenza piedmont piemonte pienza pisa pizzo polignano pompei pompeii porto portofino portovenere positano praiano procida puglia ragusa ravello ravenna reggio region remo riccione rimini riomaggiore riva riviera roccaraso roma romagna rome salento salerno salina san sanremo santa sardegna sardinia sasso saturnia scalea scanno scilla seceda seiser senigallia sestriere sicilia sicily siena siracusa sirmione siusi smeralda sorrento south spello sperlonga spezia spoleto stresa stromboli sudtirol sulmona syracuse taormina termoli terre tivoli todi torino toscana trani trapani trasimeno trastevere tre trentino trento treviso trieste tronto tropea turin tuscany tyrol udine umbria urbino val valle valley varenna vatican vaticano venere veneto venezia venice vernazza verona vesuvius viareggio vicenza vieste villa villasimius viterbo vito volterra vulcano""".split())   # nomi di luoghi: la regione e' gia' nota dal dizionario, qui interessano i temi
STOP = list(ENGLISH_STOP_WORDS | EXTRA | LUOGHI)
N = len(d)
fit_idx = rng.choice(N, size=min(args.campione, N), replace=False)
vec = TfidfVectorizer(stop_words=STOP, min_df=max(5, int(0.0005 * len(fit_idx))), max_df=0.25, ngram_range=(1, 2),
                      max_features=15000, token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]{2,}\b", sublinear_tf=True)
X_fit = vec.fit_transform(d.text.values[fit_idx])
terms = np.array(vec.get_feature_names_out())
say(f"Vocabolario: {len(terms):,} termini | testi per la stima: {X_fit.shape[0]:,}")


# ================================================================ 3. scelta di k con la coerenza UMass
def umass(top_idx, B):
    """Coerenza UMass media delle parole principali: alta se le parole di un tema compaiono negli stessi testi."""
    df = np.asarray(B.sum(axis=0)).ravel()
    sc = []
    for idx in top_idx:
        s = []
        for i in range(1, len(idx)):
            for j in range(i):
                co = B[:, idx[i]].multiply(B[:, idx[j]]).sum()
                s.append(np.log((co + 1) / max(df[idx[j]], 1)))
        sc.append(np.mean(s))
    return float(np.mean(sc))


sub = X_fit[rng.choice(X_fit.shape[0], size=min(30_000, X_fit.shape[0]), replace=False)]
B = (sub > 0).astype(np.float32).tocsc()
if args.k:
    K = args.k
else:
    say("\nScelta del numero di temi (coerenza UMass, meno negativa = temi piu' coerenti):")
    coer = {}
    for k in range(6, 15, 2):
        h = NMF(k, init="nndsvda", random_state=0, max_iter=300).fit(sub).components_
        coer[k] = umass([np.argsort(r)[::-1][:10] for r in h], B)
        say(f"  k = {k:2d}: coerenza {coer[k]:.3f}")
    K = max(coer, key=coer.get)
    pd.Series(coer, name="coerenza_umass").to_csv(f"{OUT}/tm_scelta_k.csv")
say(f"Numero di temi usato: k = {K}")

# ================================================================ 4. stima finale e assegnazione dei temi
nmf = NMF(K, init="nndsvda", random_state=0, max_iter=500).fit(X_fit)
H = nmf.components_
top = [terms[np.argsort(r)[::-1][:12]] for r in H]
#ETICHETTE = {}     # dopo aver letto le parole puoi dare un nome ai temi, es. {0: "Treni e trasporti", 1: "Cibo"}
ETICHETTE = {0: "Esperienze, citta' e cibo", 1: "Treni e trasporti", 2: "Auto e noleggio",
             3: "Biglietti e prenotazioni", 4: "Itinerari e alloggio", 5: "Tour e visite guidate"}
nome_tema = {k: ETICHETTE.get(k, f"T{k + 1}: " + ", ".join(top[k][:3])) for k in range(K)}
parole = pd.DataFrame({"tema": range(K), "nome": [nome_tema[k] for k in range(K)], "parole": [", ".join(t) for t in top]})
parole.to_csv(f"{OUT}/tm_parole.csv", index=False)
say("\nParole principali di ogni tema:")
for k in range(K):
    say(f"  T{k + 1:<2d} {', '.join(top[k])}")

temi, pesi = np.empty(N, dtype=int), np.empty(N)
for a in range(0, N, 50_000):                     # tutti i testi, a blocchi per non saturare la memoria
    W = nmf.transform(vec.transform(d.text.values[a:a + 50_000]))
    temi[a:a + 50_000], pesi[a:a + 50_000] = W.argmax(1), W.max(1)
d["tema"] = np.where(pesi > 0, temi, -1)           # -1 = nessuna parola del vocabolario
d = d[d.tema >= 0].copy()
d["nome_tema"] = d.tema.map(nome_tema)
d[["id", "kind", "TIME_PERIOD", "regioni", "tema", "nome_tema"]].to_csv(f"{OUT}/tm_testi.csv.gz", index=False, compression="gzip")
say(f"\nTesti con un tema assegnato: {len(d):,} | stima e assegnazione {time.time() - t0:.0f} s")

quota = d.nome_tema.value_counts(normalize=True).rename("quota")
riep = quota.to_frame().sort_values("quota", ascending=False)
riep.round(3).to_csv(f"{OUT}/tm_riepilogo.csv")
say("\nQuota dei testi per tema:")
say(riep.round(3).to_string())
ORD = list(riep.index)
COL_T = plt.cm.tab20(np.linspace(0, 1, 20))[:K]

fig, axs = plt.subplots(int(np.ceil(K / 4)), 4, figsize=(15, 3.1 * np.ceil(K / 4)))
for ax, k in zip(axs.flat, range(K)):
    idx = np.argsort(H[k])[::-1][:8][::-1]
    ax.barh(terms[idx], H[k][idx], color=COL["blu"], height=0.6)
    ax.set_title(f"T{k + 1} ({quota.get(nome_tema[k], 0):.0%} dei testi)", fontsize=10.5)
    ax.tick_params(axis="y", labelsize=9); ax.set_xticks([])
for ax in list(axs.flat)[K:]:
    ax.axis("off")
fig.suptitle("Parole principali di ogni tema (NMF)", fontweight="bold", y=1.01)
fig.tight_layout()
salva(fig, "tm1_parole")

# ================================================================ 5. temi nell'anno: quali salgono con il turismo?
say("\n" + "=" * 70, "\n5. TEMI NELL'ANNO (2023-2025)\n" + "=" * 70)
ms = d[d.anno >= 2023] if d[d.anno >= 2023].mese.nunique() == 12 else d     # (campioni ridotti: tutti gli anni)
ms = ms.groupby(["mese", "nome_tema"]).size().unstack(fill_value=0)
ms = ms.div(ms.sum(1), axis=0)[ORD]
ms.round(4).to_csv(f"{OUT}/tm_quote_mese.csv")
corr = None
if os.path.exists(f"{PROC}/istat.csv"):
    ist = pd.read_csv(f"{PROC}/istat.csv")
    ist = ist[(ist.market == "estero") & ist.TIME_PERIOD.str[:4].isin(["2023", "2024"])]
    arr = ist.groupby("TIME_PERIOD").arrivi.sum()
    arr = arr.groupby(arr.index.str[5:].astype(int)).mean()
    corr = ms.apply(lambda c: np.corrcoef(c, arr.reindex(ms.index))[0, 1]).sort_values()
    corr.round(3).to_csv(f"{OUT}/tm_correlazione_arrivi.csv")
    say("Correlazione tra quota mensile del tema e arrivi stranieri ISTAT (>0: tema che cresce con il turismo):")
    say(corr.round(2).to_string())

fig, ax = plt.subplots(figsize=(11, 0.45 * K + 1.5))
rel = ms / ms.mean()                                   # 1 = quota media annua del tema
ordine = corr.index[::-1] if corr is not None else ORD
im = ax.imshow(rel[ordine].T.values, cmap="RdBu_r", vmin=0.5, vmax=1.5, aspect="auto")
ax.set_xticks(range(12)); ax.set_xticklabels(MESI)
ax.set_yticks(range(K)); ax.set_yticklabels([f"{t}  (r = {corr[t]:+.2f})" if corr is not None else t for t in ordine], fontsize=9)
ax.grid(False)
fig.colorbar(im, ax=ax, fraction=0.03, label="quota del mese / quota media")
ax.set_title("Quando si parla di cosa: quota di ogni tema per mese (r = correlazione con gli arrivi stranieri)")
salva(fig, "tm2_temi_mese")

# ================================================================ 6. temi negli anni
say("\n" + "=" * 70, "\n6. TEMI NEGLI ANNI\n" + "=" * 70)
an = d.groupby(["anno", "nome_tema"]).size().unstack(fill_value=0)
an = an.div(an.sum(1), axis=0)[ORD]
an.round(4).to_csv(f"{OUT}/tm_quote_anno.csv")
say(an.T.round(3).to_string())
fig, ax = plt.subplots(figsize=(11, 4.5))
for i, t in enumerate(ORD):
    ax.plot(an.index, an[t].values * 100, marker="o", color=COL_T[i], label=t)
ax.set_xticks(an.index); ax.set_ylabel("% dei testi dell'anno")
ax.legend(fontsize=7.5, loc="center left", bbox_to_anchor=(1.01, 0.5))
ax.set_title("Quota di ogni tema per anno (nel 2022 i testi sono pochi)")
salva(fig, "tm3_temi_anno")

# ================================================================ 7. temi per regione
say("\n" + "=" * 70, "\n7. TEMI PER REGIONE\n" + "=" * 70)
reg = d[d.regioni != ""].assign(REF_AREA=lambda x: x.regioni.str.split(";")).explode("REF_AREA")
tr = reg.groupby(["REF_AREA", "nome_tema"]).size().unstack(fill_value=0)
n_reg = tr.sum(1)
tr = tr[n_reg >= 300]                                   # solo regioni con abbastanza testi
tr = tr.div(tr.sum(1), axis=0)[ORD]
tr.index = tr.index.map(NOMI)
tr.round(4).to_csv(f"{OUT}/tm_temi_regione.csv")
say(f"Regioni con almeno 300 testi: {len(tr)}")
rel = tr / tr.mean()                                    # >1: tema piu' frequente della media delle regioni
fig, ax = plt.subplots(figsize=(1.0 * K + 3, 0.42 * len(tr) + 2))
im = ax.imshow(rel.values, cmap="RdBu_r", vmin=0.3, vmax=1.7, aspect="auto")
ax.set_xticks(range(K)); ax.set_xticklabels([t.split(":")[0] for t in ORD], fontsize=9)
ax.set_yticks(range(len(tr))); ax.set_yticklabels(tr.index, fontsize=9); ax.grid(False)
fig.colorbar(im, ax=ax, fraction=0.03, label="quota del tema / media delle regioni")
ax.set_title("Di cosa si parla quando si cita una regione")
salva(fig, "tm5_temi_regione")

open(f"{OUT}/tm_risultati.txt", "w", encoding="utf-8").write("\n".join(log))
print(f"\nFatto in {time.time() - t0:.0f} s. Risultati testuali in {OUT}/tm_risultati.txt")