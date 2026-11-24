"""
SCRIPT 15 - Clustering delle regioni per profilo stagionale: i dati digitali riconoscono la stessa geografia 
stagionale del turismo misurata da ISTAT?
  1. ogni regione e' descritta dal profilo stagionale medio 2023-2024: 12 quote mensili per gli italiani e 12 per gli
     stranieri (24 variabili standardizzate), per ISTAT, Google Trends (hotel e destinazioni) e Wikipedia
  2. numero di gruppi k scelto con l'elbow method: inerzia del k-means (somma dei quadrati entro i gruppi) per k = 1..10;
     il gomito e' il k piu' lontano dalla retta che unisce il primo e l'ultimo punto della curva (metodo Kneedle)
  3. stabilita' di ogni gruppo (indice di Jaccard di Hennig) e profili medi dei gruppi con k = 4
  4. accordo tra gruppi ISTAT e gruppi digitali per k = 2..5 (ARI, p-value di permutazione, intervallo per
     sottocampionamento)
  5. test di Mantel: correlazione tra le distanze di tutte le 190 coppie di regioni secondo ISTAT e secondo i dati
     digitali, con significativita' per permutazione delle regioni. Non richiede di scegliere k ed e' la misura
     principale dell'accordo
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")   # su 20 punti i thread paralleli rallentano soltanto

import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist, squareform
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt

from script_0_comune import COL, NOMI, OUT, PROC, REG, Registro

R = Registro("cl_risultati.txt")
rng = np.random.default_rng(0)
B_SUB, N_TOLTE, N_PERM, K_RANGE = 200, 4, 2000, range(1, 11)


# ================================================================ 1. profili stagionali
def profili(df, col, chiavi):
    d = df[df.TIME_PERIOD.str[:4].isin(["2023", "2024"])].copy()
    d["mese"] = d.TIME_PERIOD.str[5:].astype(int)
    p = d.groupby(chiavi + ["mese"])[col].mean()
    return p / p.groupby(level=chiavi).transform("sum")


def matrice(p):
    m = p.unstack(["market", "mese"])
    m = m.reindex(columns=pd.MultiIndex.from_product([["domestico", "estero"], range(1, 13)]))
    return m.reindex(REG)


def standardizza(X):
    A = X.to_numpy(dtype=float)
    A = np.where(np.isnan(A), np.nanmean(A, axis=0), A)
    return StandardScaler().fit_transform(A)


istat = pd.read_csv(PROC / "istat.csv")
tr = pd.read_csv(PROC / "trends.csv")
tr = tr[tr.intent.isin(["hotel", "attrazioni"])]
ok = tr.groupby(["REF_AREA", "market"]).usable.transform("any")
tr = tr[tr.usable | ~ok]
pt = profili(tr, "value", ["REF_AREA", "market", "geo", "intent"]).groupby(level=["REF_AREA", "market", "mese"]).mean()
pt = pt / pt.groupby(level=["REF_AREA", "market"]).transform("sum")
wk = pd.read_csv(PROC / "wiki.csv")
X_wiki, X_trends = matrice(profili(wk, "views", ["REF_AREA", "market"])), matrice(pt)
Z = {"ISTAT": standardizza(matrice(profili(istat, "arrivi", ["REF_AREA", "market"]))),
     "Google Trends": standardizza(X_trends), "Wikipedia": standardizza(X_wiki),
     "Trends + Wikipedia": standardizza(pd.concat([X_trends, X_wiki], axis=1))}
DIGITALI = [f for f in Z if f != "ISTAT"]


def km(Zm, k, seed=0):
    return KMeans(k, n_init=10, random_state=seed).fit_predict(Zm)


# ================================================================ 2. scelta di k: elbow method
R.titolo("2. SCELTA DI k SUI DATI ISTAT: ELBOW METHOD")
inerzia = pd.Series({k: KMeans(k, n_init=10, random_state=0).fit(Z["ISTAT"]).inertia_ for k in K_RANGE}, name="inerzia")
x = (inerzia.index - inerzia.index[0]) / (inerzia.index[-1] - inerzia.index[0])
y = (inerzia - inerzia.iloc[-1]) / (inerzia.iloc[0] - inerzia.iloc[-1])
distanza = (y - (1 - x)).abs()                       # distanza dalla retta che unisce il primo e l'ultimo punto
K_GOMITO = int(distanza.idxmax())
K = pd.DataFrame({"inerzia": inerzia, "varianza_spiegata": 1 - inerzia / inerzia.iloc[0],
                  "calo": -inerzia.diff(), "distanza_dalla_retta": distanza})
K.index.name = "k"
K.round(3).to_csv(OUT / "cl_scelta_k.csv")
R.say("inerzia = somma dei quadrati delle distanze di ogni regione dal centro del suo gruppo (piu' bassa = gruppi piu' compatti)")
R.say(K.round(3).to_string())
R.say(f"\nGomito: k = {K_GOMITO} (varianza spiegata {K.varianza_spiegata[K_GOMITO]:.0%}). Dopo il gomito ogni gruppo in piu'\n"
      "riduce poco l'inerzia. L'accordo con i dati digitali si misura con il test di Mantel (sezione 5), che non dipende da k.")

# ================================================================ 3. stabilita' di ogni gruppo (Jaccard di Hennig)
R.titolo("3. STABILITA' DI OGNI GRUPPO (Jaccard medio sui sottocampioni: > 0.75 solido, < 0.5 da non interpretare)")


def jaccard_gruppi(Zm, k):
    lab = km(Zm, k)
    J = {g: [] for g in range(k)}
    for b in range(B_SUB):
        tieni = np.sort(rng.choice(20, 20 - N_TOLTE, replace=False))
        lb = km(Zm[tieni], k, seed=b)
        for g in range(k):
            A = set(np.where(lab[tieni] == g)[0])
            if not A:
                continue
            J[g].append(max(len(A & set(np.where(lb == h)[0])) / len(A | set(np.where(lb == h)[0]))
                            for h in range(k)))
    return lab, {g: np.mean(v) for g, v in J.items()}


SOL, JAC = {}, {}
for k in (2, 4):
    lab, J = jaccard_gruppi(Z["ISTAT"], k)
    SOL[k], JAC[k] = lab, J
    R.say(f"\nk = {k}:")
    for g in range(k):
        membri = [NOMI[r] for r, l in zip(REG, lab) if l == g]
        giudizio = "solido" if J[g] > 0.75 else ("incerto" if J[g] >= 0.5 else "NON stabile")
        R.say(f"  gruppo {g} (Jaccard {J[g]:.2f}, {giudizio}): {', '.join(membri)}")
pd.DataFrame({"regione": [NOMI[r] for r in REG], "gruppo_k2": SOL[2], "gruppo_k4": SOL[4]}).to_csv(
    OUT / "cl_gruppi.csv", index=False)

# profili dei gruppi con k = 4 e nomi dati dalle loro caratteristiche (quote estiva, invernale e di stranieri)
X_istat = matrice(profili(istat, "arrivi", ["REF_AREA", "market"]))
arr = istat[istat.TIME_PERIOD.str[:4].isin(["2023", "2024"])].copy()
arr["mese"] = arr.TIME_PERIOD.str[5:].astype(int)
tot = arr.groupby("REF_AREA").arrivi.sum()
estate = (arr[arr.mese.between(6, 9)].groupby("REF_AREA").arrivi.sum() / tot).reindex(REG).values
inverno = (arr[arr.mese.isin([12, 1, 2, 3])].groupby("REF_AREA").arrivi.sum() / tot).reindex(REG).values
stranieri = (arr[arr.market == "estero"].groupby("REF_AREA").arrivi.sum() / tot).reindex(REG).values
lab4 = SOL[4]
c_inv = pd.Series(inverno).groupby(lab4).mean()
c_est = pd.Series(estate).groupby(lab4).mean()
montagna = c_inv.idxmax()
resto = c_est.drop(montagna)
mare, citta = resto.idxmax(), resto.idxmin()
NOME_G = {citta: "Citta' e affari", montagna: "Montagna (due stagioni)", mare: "Mare (molto stagionale)"}
for g in range(4):
    NOME_G.setdefault(g, "Arte e mare (stagionalita' intermedia)")
ORD_G = [citta, montagna] + [g for g in range(4) if g not in (citta, montagna, mare)] + [mare]
GR = pd.DataFrame([dict(gruppo=NOME_G[g], regioni=", ".join(NOMI[r] for r, l in zip(REG, lab4) if l == g),
                        n=int((lab4 == g).sum()), jaccard=JAC[4][g], quota_estiva=estate[lab4 == g].mean(),
                        quota_invernale=inverno[lab4 == g].mean(), quota_stranieri=stranieri[lab4 == g].mean())
                   for g in ORD_G])
GR.round(3).to_csv(OUT / "cl_gruppi_k4.csv", index=False)
R.say("\nGruppi con k = 4:")
R.say(GR.round(2).to_string(index=False))
COL_G = [COL["viola"], COL["blu"], COL["verde"], COL["arancio"]]
fig, axs = plt.subplots(1, 2, figsize=(13, 4), sharey=True)
for ax, mk, tit in [(axs[0], "domestico", "Clienti italiani"), (axs[1], "estero", "Clienti stranieri")]:
    for c_, g in zip(COL_G, ORD_G):
        ax.plot(range(1, 13), X_istat[mk].values[lab4 == g].mean(axis=0), color=c_, marker="o", ms=4, label=NOME_G[g])
    ax.set_xticks(range(1, 13)); ax.set_xticklabels(list("GFMAMGLASOND")); ax.set_title(tit)
axs[0].set_ylabel("quota del totale annuo"); axs[1].legend(fontsize=8.5)
fig.suptitle("Profilo stagionale medio di ogni gruppo di regioni (ISTAT, 2023-2024)", y=1.02, fontweight="bold")
R.salva_grafico(fig, "cl_3_profili_gruppi")

# ================================================================ 4. accordo ISTAT-digitale per ogni k
R.titolo("4. ACCORDO ISTAT-DIGITALE PER k = 2..5 (ARI, p di permutazione, intervallo per sottocampionamento)")
righe = []
for k in range(2, 6):
    li = km(Z["ISTAT"], k)
    for f in DIGITALI:
        ld = km(Z[f], k)
        ari = adjusted_rand_score(li, ld)
        perm = np.array([adjusted_rand_score(li, rng.permutation(ld)) for _ in range(N_PERM)])
        sub = []
        for b in range(50):
            t = np.sort(rng.choice(20, 20 - N_TOLTE, replace=False))
            sub.append(adjusted_rand_score(km(Z["ISTAT"][t], k, b), km(Z[f][t], k, b)))
        righe.append(dict(k=k, fonte=f, ARI=ari, p_value=(np.sum(perm >= ari) + 1) / (N_PERM + 1),
                          ARI_p10=np.percentile(sub, 10), ARI_p90=np.percentile(sub, 90)))
A = pd.DataFrame(righe)
A.round(3).to_csv(OUT / "cl_accordo_k.csv", index=False)
R.say(A.pivot(index="k", columns="fonte", values="ARI").round(2).to_string())
R.say("\np-value di permutazione:")
R.say(A.pivot(index="k", columns="fonte", values="p_value").round(3).to_string())
R.say("\nintervallo 10-90% dell'ARI togliendo 4 regioni a caso:")
R.say(A.assign(int_=A.ARI_p10.round(2).astype(str) + " - " + A.ARI_p90.round(2).astype(str))
      .pivot(index="k", columns="fonte", values="int_").to_string())

# ================================================================ 5. test di Mantel (non dipende da k)
R.titolo("5. TEST DI MANTEL: le distanze tra regioni sono simili nelle due fonti?")


def mantel(Da, Db, nperm=10000):
    iu = np.triu_indices_from(Da, 1)
    ra = stats.rankdata(Da[iu])
    r = np.corrcoef(ra, stats.rankdata(Db[iu]))[0, 1]          # Spearman = Pearson sui ranghi
    cnt = 0
    for _ in range(nperm):
        p = rng.permutation(len(Da))                             # si permutano le REGIONI, non le coppie
        cnt += np.corrcoef(ra, stats.rankdata(Db[np.ix_(p, p)][iu]))[0, 1] >= r
    return r, (cnt + 1) / (nperm + 1)


D = {f: squareform(pdist(z)) for f, z in Z.items()}
righe = []
for f in DIGITALI:
    for nome, cols in [("entrambi i mercati", slice(None)), ("solo domestico", slice(0, 12)),
                       ("solo estero", slice(12, 24))]:
        if f == "Trends + Wikipedia" and nome != "entrambi i mercati":
            continue
        if nome == "entrambi i mercati":
            Di, Dd = D["ISTAT"], D[f]
        else:
            Di = squareform(pdist(Z["ISTAT"][:, cols]))
            Dd = squareform(pdist(Z[f][:, cols]))
        r, p = mantel(Di, Dd, 5000)
        righe.append(dict(fonte=f, mercato=nome, mantel_r=r, p_value=p))
M = pd.DataFrame(righe)
M.round(4).to_csv(OUT / "cl_mantel.csv", index=False)
R.say(M.round(3).to_string(index=False))
R.say("\nLettura: mantel_r e' la correlazione di Spearman tra le distanze di 190 coppie di regioni. E' la misura\n"
      "principale da riportare: risponde alla domanda senza dover scegliere quanti gruppi esistono.")

# ================================================================ grafici
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(K.index, K.inerzia, marker="o", color=COL["blu"], lw=2.5)
ax.plot([K.index[0], K.index[-1]], [K.inerzia.iloc[0], K.inerzia.iloc[-1]], ls=":", color=COL["grigio"], lw=1.2)
ax.plot(K_GOMITO, K.inerzia[K_GOMITO], "o", ms=16, mfc="none", mec=COL["arancio"], mew=2.5)
ax.annotate(f"gomito: k = {K_GOMITO}\n({K.varianza_spiegata[K_GOMITO]:.0%} della varianza spiegata)",
            xy=(K_GOMITO, K.inerzia[K_GOMITO]), xytext=(K_GOMITO + 1.3, K.inerzia.iloc[0] * 0.55), color=COL["arancio"],
            arrowprops=dict(arrowstyle="->", color=COL["arancio"]))
for k_, v_ in K.inerzia.items():
    ax.text(k_, v_ + K.inerzia.iloc[0] * 0.025, f"{v_:.0f}", ha="center", fontsize=8, color=COL["testo"])
ax.set_xticks(list(K.index)); ax.set_xlabel("numero di gruppi k")
ax.set_ylabel("inerzia (somma dei quadrati entro i gruppi)")
ax.set_title("Elbow method: k-means sui profili stagionali ISTAT 2023-2024")
R.salva_grafico(fig, "cl_1_scelta_k")

fig, axs = plt.subplots(1, 2, figsize=(13, 4.2))
for f, c in zip(DIGITALI, [COL["blu"], COL["viola"], COL["verde"]]):
    a = A[A.fonte == f]
    axs[0].plot(a.k, a.ARI, marker="o", color=c, label=f)
    axs[0].fill_between(a.k, a.ARI_p10, a.ARI_p90, color=c, alpha=0.12)
axs[0].axhline(0, color=COL["griglia2"]); axs[0].set_xticks(range(2, 6)); axs[0].set_xlabel("k")
axs[0].set_ylabel("ARI con ISTAT"); axs[0].set_title("L'accordo dipende da k"); axs[0].legend(fontsize=8.5)
Mm = M[M.mercato == "entrambi i mercati"]
axs[1].barh(Mm.fonte, Mm.mantel_r, color=[COL["blu"], COL["viola"], COL["verde"]][:len(Mm)])
for i, (r, p) in enumerate(zip(Mm.mantel_r, Mm.p_value)):
    axs[1].text(r + 0.01, i, f"r = {r:.2f}, p = {p:.4f}", va="center", fontsize=9)
axs[1].set_xlim(0, 1); axs[1].set_xlabel("correlazione di Mantel con le distanze ISTAT")
axs[1].set_title("Confronto che non dipende da k")
R.salva_grafico(fig, "cl_2_accordo")

R.chiudi()