"""
SCRIPT 17 - Schemi del report

Schemi per il report PDF 
"""
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

from script_0_comune import COL, OUT

DIR = OUT / "schemi"
DIR.mkdir(exist_ok=True)
CHIARO = dict(blu="#dbe8f8", arancio="#fbe1d6", verde="#d4f1e5", giallo="#fbecc4", viola="#e4ddf7", grigio="#ecebe6")


def box(ax, x, y, w, h, testo, col="grigio", bordo=None, fs=9, peso="normal", ha="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.012",
                                fc=CHIARO.get(col, col), ec=bordo or COL.get(col, COL["grigio"]), lw=1.2))
    tx = x + w / 2 if ha == "center" else x + 0.01
    ax.text(tx, y + h / 2, testo, ha=ha, va="center", fontsize=fs, fontweight=peso, color=COL["nero"],
            linespacing=1.25)


def freccia(ax, a, b, col=None, stile="-|>", rad=0.0):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=stile, mutation_scale=12, lw=1.2,
                                 color=col or COL["grigio"], connectionstyle=f"arc3,rad={rad}"))


def tela(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    return fig, ax


def salva(fig, nome):
    fig.savefig(DIR / f"{nome}.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- s1 pipeline
def s1():
    fig, ax = tela(11, 6.6)
    colonne = [(0.01, "1. RACCOLTA"), (0.205, "2. PREPARAZIONE"), (0.40, "3. ESPLORAZIONE"), (0.595, "4. SENTIMENT"),
               (0.80, "5. MODELLI")]
    for x, t in colonne:
        ax.text(x + 0.09, 0.975, t, ha="center", fontsize=10, fontweight="bold", color=COL["testo"])
    W, H = 0.18, 0.13
    fonti = [("ISTAT\nIstatData", "blu"), ("Google Trends\nconsole del browser", "verde"),
             ("Wikipedia\nAPI Wikimedia", "viola"), ("Reddit r/ItalyTravel\nfile .jsonl", "arancio")]
    prep = [("script 1\npulizia e controlli", "blu"), ("script 2-3\ndownload e unione", "verde"),
            ("script 4\nvisite per regione e lingua", "viola"), ("script 5-6\ntesti, regioni citate", "arancio")]
    ys = [0.76, 0.56, 0.36, 0.16]
    for (t, c), (t2, c2), y in zip(fonti, prep, ys):
        box(ax, 0.01, y, W, H, t, c, fs=8.5)
        box(ax, 0.205, y, W, H, t2, c2, fs=8.2)
        freccia(ax, (0.01 + W, y + H / 2), (0.205, y + H / 2))
        freccia(ax, (0.205 + W, y + H / 2), (0.40, 0.66 if y > 0.2 else 0.24))
    box(ax, 0.40, 0.46, W, 0.40, "script 7  (EDA)\n\nfonti armonizzate su\nregione x mercato x mese\n\ndinamica, stagionalita',\nterritorio, variazioni annue", "grigio", fs=8.2)
    box(ax, 0.40, 0.16, W, 0.17, "script 8\ntopic model (NMF)\n6 temi", "arancio", fs=8.2)
    sent = [("script 9-10\nQwen 2.5 7B su Kaggle\n128.002 testi", 0.66), ("script 11\ntono per regione", 0.42),
            ("script 12-13\nvalidazione, stagioni,\naspetti, temi", 0.16)]
    for t, y in sent:
        box(ax, 0.595, y, W, 0.17, t, "arancio", fs=8.2)
    freccia(ax, (0.685, 0.66), (0.685, 0.59)); freccia(ax, (0.685, 0.42), (0.685, 0.33))
    freccia(ax, (0.40 + W, 0.245), (0.595, 0.245))
    mod = [("script 14\nindicatore di attenzione\ndigitale", 0.66), ("script 15\nclustering delle regioni", 0.42),
           ("script 16\nnowcasting degli arrivi", 0.16)]
    for t, y in mod:
        box(ax, 0.80, y, W, 0.17, t, "giallo", bordo=COL["nero"], fs=8.2)
        freccia(ax, (0.40 + W, 0.66), (0.80, y + 0.085))
    freccia(ax, (0.595 + W, 0.505), (0.80, 0.745), col=COL["nero"])
    ax.text(0.5, 0.03, "Script 17-18: schemi e report. Script 19: esegue tutto nell'ordine giusto.",
            ha="center", fontsize=8.5, color=COL["testo"], style="italic")
    salva(fig, "s1_pipeline")


# ---------------------------------------------------------------- s2 chiave comune
def s2():
    fig, ax = tela(10, 4.6)
    fonti = [("ISTAT\narrivi, presenze\n2011-2024", "blu", "domestico + estero"),
             ("Google Trends\nindice 0-100\n2011-2025", "verde", "IT = domestico\nDE GB US FR ES = estero"),
             ("Wikipedia\nvisite\n2015-07 / 2025", "viola", "it = domestico\nen de fr es = estero"),
             ("Reddit\nquota di testi\n2022-2025", "arancio", "solo estero\n(forum in inglese)")]
    for i, (t, c, m) in enumerate(fonti):
        x = 0.02 + i * 0.245
        box(ax, x, 0.66, 0.21, 0.27, t, c, fs=9, peso="bold")
        ax.text(x + 0.105, 0.58, m, ha="center", va="top", fontsize=7.8, color=COL["testo"])
        freccia(ax, (x + 0.105, 0.43), (0.5, 0.31))
    box(ax, 0.06, 0.06, 0.88, 0.24, "CHIAVE COMUNE\nREF_AREA (20 regioni NUTS-2)  x  market (domestico / estero)  x  TIME_PERIOD (mese)\n"
        "+ variazione annua  y = log(valore del mese) - log(stesso mese dell'anno prima)", "grigio",
        bordo=COL["nero"], fs=9)
    salva(fig, "s2_chiave")


# ---------------------------------------------------------------- s3 trends
def s3():
    fig, ax = tela(10.5, 4.2)
    box(ax, 0.01, 0.55, 0.2, 0.38, "1 regione\n(es. Toscana)\n\n5 mete:\nToscana, Firenze,\nPisa, Siena, Elba", "verde", fs=8.5)
    box(ax, 0.26, 0.55, 0.2, 0.38, "x 6 Paesi di chi cerca\nIT | DE GB US FR ES\n\nx 3 categorie Google\nhotel (179)\nvoli (203)\ndestinazioni (208)", "verde", fs=8.5)
    box(ax, 0.51, 0.55, 0.21, 0.38, "SOMMA delle 5 mete\n(stessa richiesta =\nstessa scala)\n\n37+33+2+15+2 = 89", "grigio", fs=8.5)
    box(ax, 0.77, 0.55, 0.22, 0.38, "SERIE UTILIZZABILE?\nquota di mesi a zero\n<= 20%\n\n265 su 360 serie", "giallo", fs=8.5)
    for a, b in [(0.21, 0.26), (0.46, 0.51), (0.72, 0.77)]:
        freccia(ax, (a, 0.74), (b, 0.74))
    box(ax, 0.12, 0.06, 0.76, 0.3, "VARIAZIONE ANNUA usata nei modelli\nyoy = log(1 + G del mese) - log(1 + G dello stesso mese dell'anno prima)\n\n"
        "L'indice 0-100 non e' confrontabile tra serie diverse, ma il rapporto dentro la stessa serie si':\n"
        "per questo Trends si confronta sempre con se stesso (nel tempo), mai tra regioni.", "grigio", bordo=COL["nero"], fs=8.6)
    freccia(ax, (0.88, 0.55), (0.75, 0.36))
    salva(fig, "s3_trends")


# ---------------------------------------------------------------- s4 DAI
def s4():
    fig, ax = tela(10.5, 4.8)
    box(ax, 0.33, 0.82, 0.34, 0.14, "DAI - Digital Attention Index\nmedia dei pilastri (punteggi di rango 0-100)", "grigio", bordo=COL["nero"], fs=9.5, peso="bold")
    pil = [("VISIBILITA'\nquanto se ne parla", "blu", 0.04, ["quota visite\nWikipedia\n2023-24", "quota menzioni\nReddit 2023-24\n(solo estero)"]),
           ("REPUTAZIONE\ncon che tono", "giallo", 0.37, ["sentiment di Qwen\n(destag. + shrinkage)\nsolo estero"]),
           ("SLANCIO\nquanto e' cresciuto", "verde", 0.70, ["crescita\nWikipedia\n2024 / 2019", "crescita\nTrends\n2024 / 2019"])]
    for t, c, x, elem in pil:
        box(ax, x, 0.52, 0.26, 0.16, t, c, fs=9, peso="bold")
        freccia(ax, (x + 0.13, 0.68), (0.5, 0.82))
        n = len(elem)
        for j, e in enumerate(elem):
            w = 0.26 / n - 0.01
            xe = x + j * (0.26 / n)
            box(ax, xe, 0.18, w, 0.2, e, c, fs=7.3)
            freccia(ax, (xe + w / 2, 0.38), (x + 0.13, 0.52))
    ax.text(0.5, 0.05, "Validazione: Visibilita' <-> quota di arrivi ISTAT;  Slancio <-> crescita degli arrivi 2019-2024;  "
            "Reputazione <-> nessun dato ISTAT (validata a mano sui testi)", ha="center", fontsize=8.3, color=COL["testo"], style="italic")
    salva(fig, "s4_dai")


# ---------------------------------------------------------------- s5 shrinkage
def s5():
    import pandas as pd
    rep = pd.read_csv(OUT / "rep_regioni.csv", index_col=0)
    mu = float((rep.shrink * 0 + rep.shrink).mean()) if "mu" not in rep else float(rep.mu.iloc[0])
    scelte = [("ITF2", COL["arancio"]), ("ITC2", COL["giallo"]), ("ITE3", COL["giallo"]), ("ITE4", COL["blu"])]
    fig, ax = plt.subplots(figsize=(9.5, 3.6))
    ax.axvline(mu, color=COL["nero"], ls="--", lw=1)
    ax.text(mu, 4.55, f"media delle regioni = {mu:.2f}", ha="center", fontsize=8.5)
    lo = min(rep.media.min(), rep.shrink.min())
    for i, (r, c) in enumerate(scelte):
        a, b = rep.media[r], rep.shrink[r]
        y = 3.6 - i
        ax.annotate("", xy=(b, y), xytext=(a, y), arrowprops=dict(arrowstyle="-|>", color=c, lw=2))
        ax.scatter([a], [y], color=COL["grigio"], marker="x", s=50, zorder=3)
        ax.scatter([b], [y], color=c, s=50, zorder=3)
        ax.text(lo - 0.12, y, f"{rep.regione[r]}\n{int(rep.n_thread[r]):,} thread".replace(",", "."), va="center", ha="left", fontsize=8.5)
    ax.set_xlim(lo - 0.13, rep.media.max() + 0.03); ax.set_ylim(0, 4.9); ax.set_yticks([])
    ax.set_xlabel("sentiment (x = media della regione, punto = stima con shrinkage)")
    ax.set_title("Shrinkage: piu' la media e' incerta, piu' viene avvicinata alla media delle regioni", fontsize=10.5)
    fig.savefig(DIR / "s5_shrinkage.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- s6 nowcast
def s6():
    fig, ax = plt.subplots(figsize=(10.5, 3.4))
    mesi = ["gen", "feb", "mar", "apr", "mag", "giu", "lug"]
    for i, m in enumerate(mesi):
        ax.axvline(i, color=COL["griglia"], lw=0.8, zorder=0)
        ax.text(i, -0.55, m, ha="center", fontsize=9)
    ax.barh(2, 3, left=-0.4, height=0.5, color=CHIARO["blu"], edgecolor=COL["blu"])
    ax.text(1.1, 2, "ISTAT gia' pubblicato (fino a t-3)", ha="center", va="center", fontsize=8.5)
    ax.barh(2, 3, left=2.6, height=0.5, color="white", edgecolor=COL["blu"], hatch="///")
    ax.text(4.1, 2, "ISTAT non ancora pubblicato", ha="center", va="center", fontsize=8.5,
            bbox=dict(fc="white", ec="none", pad=1.5))
    ax.barh(1, 6.8, left=-0.4, height=0.5, color=CHIARO["verde"], edgecolor=COL["verde"])
    ax.text(3, 1, "Google Trends e Wikipedia disponibili subito, fino al mese t", ha="center", va="center", fontsize=8.5)
    ax.scatter([5], [0.15], s=180, marker="v", color=COL["arancio"], zorder=4)
    ax.text(5.15, 0.15, "mese t da stimare (giugno)\ny_t = a + r1 y_(t-3) + r2 y_(t-4) + b x fonti digitali_t",
            va="center", fontsize=8.5)
    ax.annotate("", xy=(2, 2.55), xytext=(5, 2.55), arrowprops=dict(arrowstyle="<->", color=COL["nero"]))
    ax.text(3.5, 2.7, "ritardo di pubblicazione L = 3 mesi", ha="center", fontsize=8.5)
    ax.set_xlim(-0.6, 8.9); ax.set_ylim(-0.8, 3.0); ax.axis("off")
    ax.set_title("Pseudo tempo reale: ogni mese il modello si ristima usando solo cio' che era noto in quel mese",
                 fontsize=10.5, fontweight="bold")
    fig.savefig(DIR / "s6_nowcast.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ================================================================ figure didattiche (d01-d14)
# Piccole illustrazioni dei concetti usati nel progetto. Dove possibile usano i dati veri; quando servono solo a
# spiegare un'idea usano numeri inventati, e il titolo lo dice ("esempio illustrativo").
def _dati():
    import pandas as pd
    from script_0_comune import PROC
    return pd.read_csv(PROC / "istat.csv")


def d01_serie():
    """Che cos'e' una serie storica: arrivi stranieri in Toscana, mese per mese, e la sua variazione annua."""
    import pandas as pd
    ist = _dati()
    s = ist[(ist.REF_AREA == "ITE1") & (ist.market == "estero")].set_index("TIME_PERIOD").sort_index()
    x = pd.to_datetime(s.index)
    fig, axs = plt.subplots(2, 1, figsize=(9.5, 5.2), sharex=True, gridspec_kw=dict(height_ratios=[1.4, 1]))
    axs[0].plot(x, s.arrivi / 1e3, color=COL["arancio"], lw=1.6)
    axs[0].set_ylabel("migliaia di arrivi")
    axs[0].set_ylim(0, 1550)
    axs[0].set_title("Una serie storica: arrivi di turisti stranieri in Toscana, un valore per mese (ISTAT)", fontsize=10.5)
    picco = s.arrivi.idxmax()
    axs[0].annotate("ogni estate un picco:\nSTAGIONALITA'", xy=(pd.Timestamp("2016-08"), s.arrivi["2016-08"] / 1e3),
                    xytext=(pd.Timestamp("2012-03"), 1330), fontsize=8.5, arrowprops=dict(arrowstyle="->", color=COL["grigio"]))
    axs[0].annotate("2020: SHOCK\n(COVID)", xy=(pd.Timestamp("2020-05"), 20), xytext=(pd.Timestamp("2017-10"), 300),
                    fontsize=8.5, arrowprops=dict(arrowstyle="->", color=COL["grigio"]))
    axs[1].bar(x, s.yoy_arrivi.clip(-3, 3), width=25, color=np.where(s.yoy_arrivi >= 0, COL["verde"], COL["arancio"]))
    axs[1].axhline(0, color=COL["nero"], lw=0.8)
    axs[1].set_ylabel("variazione annua\n(log, tagliata a ±3)")
    axs[1].set_title("La stessa serie trasformata: ogni mese confrontato con lo stesso mese dell'anno prima", fontsize=10.5)
    fig.tight_layout()
    salva(fig, "d01_serie")


def d02_correlazione():
    """Correlazione: tre nuvole di punti con r diversi (esempio illustrativo)."""
    rng = np.random.default_rng(1)
    fig, axs = plt.subplots(1, 4, figsize=(11, 2.7))
    x = rng.normal(size=60)
    casi = [(x + rng.normal(scale=0.35, size=60), "r = +0,94\nforte positiva"),
            (rng.normal(size=60), "r ≈ 0\nnessun legame lineare"),
            (-x + rng.normal(scale=0.8, size=60), "r = -0,78\nnegativa"),
            (np.exp(1.2 * x) + rng.normal(scale=0.2, size=60), "Pearson 0,8 - Spearman 0,98\nmonotona ma non lineare")]
    for ax, (y, t) in zip(axs, casi):
        ax.scatter(x, y, s=12, color=COL["blu"])
        ax.set_title(t, fontsize=9.5)
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("Correlazione (esempio illustrativo): misura quanto due variabili salgono e scendono insieme", fontsize=10.5,
                 fontweight="bold", y=1.06)
    salva(fig, "d02_correlazione")


def d03_intervallo():
    """Errore standard e intervallo di confidenza: 20 campioni dalla stessa popolazione (esempio illustrativo)."""
    rng = np.random.default_rng(3)
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.3), gridspec_kw=dict(width_ratios=[1, 1.25]))
    for n, c, lab in [(20, COL["arancio"], "n = 20 testi"), (500, COL["blu"], "n = 500 testi")]:
        medie = rng.normal(0.36, 0.9, size=(4000, n)).mean(axis=1)
        axs[0].hist(medie, bins=60, density=True, alpha=0.6, color=c, label=f"{lab}: errore standard {medie.std():.2f}")
    axs[0].axvline(0.36, color=COL["nero"], lw=1)
    axs[0].legend(fontsize=8, loc="upper left")
    axs[0].set_title("Medie di tanti campioni: con piu' dati\nla media oscilla meno", fontsize=10)
    axs[0].set_yticks([])
    mancano = 0
    for i in range(20):
        c = rng.normal(0.36, 0.9, size=60)
        m, se = c.mean(), c.std(ddof=1) / np.sqrt(60)
        fuori = not (m - 1.96 * se <= 0.36 <= m + 1.96 * se)
        mancano += fuori
        axs[1].plot([m - 1.96 * se, m + 1.96 * se], [i, i], color=COL["arancio"] if fuori else COL["blu"], lw=2)
        axs[1].plot(m, i, "o", color=COL["nero"], ms=3)
    axs[1].axvline(0.36, color=COL["nero"], lw=1, ls="--")
    axs[1].set_yticks([])
    axs[1].set_title(f"20 intervalli al 95% da 20 campioni diversi:\n{20 - mancano} contengono il valore vero (linea)", fontsize=10)
    fig.suptitle("Esempio illustrativo con numeri simulati", fontsize=9, color=COL["grigio"], y=0.02)
    salva(fig, "d03_intervallo")


def d04_trends_scala():
    """Come Google Trends costruisce l'indice 0-100 dentro una richiesta (esempio illustrativo)."""
    mesi = np.arange(1, 13)
    a = np.array([30, 32, 40, 55, 70, 90, 120, 130, 80, 50, 35, 40.])        # ricerche (relative) di "Firenze"
    b = np.array([10, 11, 14, 20, 30, 45, 60, 58, 32, 18, 12, 14.])            # ricerche di "Siena"
    m = max(a.max(), b.max())
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.1))
    axs[0].plot(mesi, a, "o-", color=COL["blu"], label="meta A")
    axs[0].plot(mesi, b, "o-", color=COL["verde"], label="meta B")
    axs[0].set_title("1. Quota delle ricerche (invisibile all'utente)", fontsize=10)
    axs[0].legend(fontsize=8); axs[0].set_yticks([])
    axs[1].plot(mesi, np.round(100 * a / m), "o-", color=COL["blu"], label="meta A")
    axs[1].plot(mesi, np.round(100 * b / m), "o-", color=COL["verde"], label="meta B")
    axs[1].axhline(100, color=COL["grigio"], ls=":", lw=1)
    axs[1].set_title("2. Indice pubblicato: il massimo della richiesta = 100", fontsize=10)
    axs[1].set_ylim(0, 110); axs[1].legend(fontsize=8)
    for ax in axs:
        ax.set_xticks(mesi); ax.set_xticklabels(list("GFMAMGLASOND"))
    fig.suptitle("Google Trends (esempio illustrativo): A e B nella stessa richiesta condividono la scala e si possono sommare",
                 fontsize=10, fontweight="bold", y=1.04)
    salva(fig, "d04_trends_scala")


def d05_nmf():
    """NMF: la matrice testi x parole scomposta in testi x temi per temi x parole (schema)."""
    rng = np.random.default_rng(4)
    W = rng.gamma(0.4, 1, size=(9, 3)); H = rng.gamma(0.4, 1, size=(3, 12))
    X = W @ H
    fig = plt.figure(figsize=(10, 3.2))
    gs = fig.add_gridspec(1, 5, width_ratios=[12, 1.2, 3, 0.8, 12])
    for k, (M, t, cm) in enumerate([(X, "X: testi x parole\n(pesi TF-IDF)", "Blues"), (None, "≈", None),
                                    (W, "W: testi x temi", "Oranges"), (None, "×", None),
                                    (H, "H: temi x parole", "Greens")]):
        ax = fig.add_subplot(gs[k])
        ax.axis("off")
        if M is None:
            ax.text(0.5, 0.5, t, fontsize=26, ha="center", va="center")
            continue
        ax.imshow(M, cmap=cm, aspect="equal")
        ax.set_title(t, fontsize=9.5)
    fig.suptitle("NMF: ogni testo e' una miscela di pochi temi, ogni tema e' un elenco pesato di parole", fontsize=10.5,
                 fontweight="bold", y=1.0)
    salva(fig, "d05_nmf")


def d06_confusione():
    """Matrice di confusione di Qwen sui testi annotati a mano (dati veri)."""
    import pandas as pd
    cf = pd.read_csv(OUT / "snt_confusione.csv")
    lab = ["negative", "neutral", "positive"]
    nomi = ["negativo", "neutro", "positivo"]
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.3))
    for ax, met in zip(axs, ["Qwen 2.5 7B", "RoBERTa (transformer)", "VADER (dizionario)"]):
        c = cf[cf.metodo == met].pivot_table(index="vero", columns="previsto", values="n", aggfunc="sum").reindex(
            index=lab, columns=lab).fillna(0)
        ax.imshow(c.values, cmap="Blues", vmin=0, vmax=c.values.max() * 1.3)
        for i in range(3):
            for j in range(3):
                ax.text(j, i, int(c.values[i, j]), ha="center", va="center", fontsize=11,
                        fontweight="bold" if i == j else "normal")
        ax.set_xticks(range(3)); ax.set_xticklabels(nomi, fontsize=8.5)
        ax.set_yticks(range(3)); ax.set_yticklabels(nomi, fontsize=8.5)
        ax.set_xlabel("previsto dal metodo", fontsize=8.5)
        ax.set_title(met, fontsize=10); ax.grid(False)
    axs[0].set_ylabel("annotazione a mano", fontsize=8.5)
    fig.suptitle("Matrici di confusione sui testi annotati: sulla diagonale i casi giusti", fontsize=10.5, fontweight="bold", y=1.03)
    salva(fig, "d06_confusione")


def d07_bayes():
    """Bayes empirico con i numeri veri del Molise: distribuzione a priori, dati e a posteriori."""
    import pandas as pd
    from scipy import stats as st
    rep = pd.read_csv(OUT / "rep_regioni.csv", index_col=0)
    r = rep.loc["ITF2"]
    y, se = r.media, r.se
    w = r.peso_dati                                     # 1 - B = tau^2 / (se^2 + tau^2)
    tau = float(np.sqrt(se ** 2 * w / (1 - w)))
    mu = float((r.shrink - w * y) / (1 - w))           # dalla formula stima = mu + w (y - mu)
    post, post_se = r.shrink, r.shrink_se
    x = np.linspace(0.0, 0.75, 400)
    fig, ax = plt.subplots(figsize=(9.5, 3.4))
    for m, s, c, lab in [(mu, tau, COL["grigio"], f"a priori: come sono le regioni in generale\n(media μ = {mu:.2f}, dev. std. τ = {tau:.2f})"),
                         (y, se, COL["arancio"], f"dati del Molise: media {y:.2f}, errore standard {se:.3f}"),
                         (post, post_se, COL["blu"], f"a posteriori (stima finale): {post:.2f} ± {1.96 * post_se:.2f}")]:
        ax.plot(x, st.norm.pdf(x, m, s), color=c, lw=2.2, label=lab)
        ax.fill_between(x, st.norm.pdf(x, m, s), color=c, alpha=0.12)
    ax.set_yticks([]); ax.set_xlabel("tono medio (scala di Qwen, da -2 a +2)")
    ax.legend(fontsize=8.3, loc="upper right")
    ax.set_title("Bayes empirico per il Molise: la stima finale combina i suoi dati con cio' che sappiamo di tutte le regioni",
                 fontsize=10)
    salva(fig, "d07_bayes")


def d08_kmeans():
    """k-means passo per passo (esempio illustrativo in 2 dimensioni)."""
    rng = np.random.default_rng(7)
    P = np.vstack([rng.normal(c, 0.45, size=(12, 2)) for c in [(0, 0), (3, 0.5), (1.5, 2.8)]])
    C = np.array([[0.5, 2.5], [0.2, 0.3], [2.0, 0.0]])
    fig, axs = plt.subplots(1, 4, figsize=(11.5, 2.9))
    cols = [COL["blu"], COL["arancio"], COL["verde"]]
    titoli = ["1. centri iniziali a caso", "2. ogni punto al centro\npiu' vicino", "3. ogni centro si sposta\nnella media del gruppo",
              "4. si ripete fino a quando\nnulla cambia"]
    for i, ax in enumerate(axs):
        lab = np.argmin(((P[:, None] - C[None]) ** 2).sum(-1), axis=1)
        ax.scatter(P[:, 0], P[:, 1], s=14, c=[COL["grigio"]] * len(P) if i == 0 else [cols[l] for l in lab])
        ax.scatter(C[:, 0], C[:, 1], marker="X", s=130, c=cols, edgecolor="k")
        ax.set_title(titoli[i], fontsize=9.5); ax.set_xticks([]); ax.set_yticks([])
        if i in (1, 2):
            C = np.array([P[lab == k].mean(0) for k in range(3)])
        if i == 2:
            for _ in range(5):
                lab = np.argmin(((P[:, None] - C[None]) ** 2).sum(-1), axis=1)
                C = np.array([P[lab == k].mean(0) for k in range(3)])
    fig.suptitle("k-means con k = 3 (esempio illustrativo; nel progetto ogni regione e' un punto in 24 dimensioni)",
                 fontsize=10.5, fontweight="bold", y=1.06)
    salva(fig, "d08_kmeans")


def d09_mantel():
    """Matrici delle distanze e test di permutazione (esempio illustrativo)."""
    rng = np.random.default_rng(2)
    n = 8
    A = rng.normal(size=(n, 2)); Bm = A + rng.normal(scale=0.5, size=(n, 2))
    from scipy.spatial.distance import pdist, squareform
    DA, DB = squareform(pdist(A)), squareform(pdist(Bm))
    iu = np.triu_indices(n, 1)
    r_oss = np.corrcoef(DA[iu], DB[iu])[0, 1]
    nulli = []
    for _ in range(3000):
        p = rng.permutation(n)
        nulli.append(np.corrcoef(DA[iu], DB[np.ix_(p, p)][iu])[0, 1])
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.1), gridspec_kw=dict(width_ratios=[1, 1, 1.5]))
    for ax, D, t in [(axs[0], DA, "distanze secondo ISTAT"), (axs[1], DB, "distanze secondo i dati digitali")]:
        ax.imshow(D, cmap="Purples"); ax.set_title(t, fontsize=9.5); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    axs[2].hist(nulli, bins=40, color=COL["griglia2"])
    axs[2].axvline(r_oss, color=COL["arancio"], lw=2.5)
    axs[2].text(r_oss, axs[2].get_ylim()[1] * 0.85, f"  correlazione osservata\n  {r_oss:.2f}", color=COL["arancio"], fontsize=9)
    axs[2].set_title("correlazioni ottenute rimescolando le regioni a caso", fontsize=9.5); axs[2].set_yticks([])
    fig.suptitle("Test di Mantel (esempio illustrativo con 8 regioni): l'accordo osservato e' piu' alto di quasi tutti quelli casuali?",
                 fontsize=10.5, fontweight="bold", y=1.05)
    salva(fig, "d09_mantel")


def d10_finestra():
    """Pseudo tempo reale con finestra che si allarga: ogni mese si ristima il modello."""
    fig, ax = plt.subplots(figsize=(10, 3.2))
    anni = np.arange(2012, 2025.01, 1 / 12)
    for i, (t, lab) in enumerate([(2022.0, "stima per gen 2022"), (2022.5, "stima per lug 2022"), (2023.75, "stima per ott 2023"),
                                  (2024.92, "stima per dic 2024")]):
        y = 3 - i
        ax.barh(y, t - 0.25 - 2012, left=2012, height=0.5, color=CHIARO["blu"], edgecolor=COL["blu"])
        ax.barh(y, 0.25, left=t - 0.25, height=0.5, color="white", edgecolor=COL["blu"], hatch="///")
        ax.plot(t, y, "v", color=COL["arancio"], ms=10)
        ax.text(2012.1, y, "dati usati per stimare il modello", va="center", fontsize=8)
        ax.text(t + 0.3, y, lab, va="center", fontsize=8.5, color=COL["arancio"])
    ax.set_yticks([]); ax.set_xlim(2012, 2026.6)
    ax.set_title("Finestra che si allarga: ogni mese il modello si ristima con tutto cio' che era pubblicato fino ad allora\n"
                 "(tratteggio = ultimi 3 mesi ISTAT non ancora pubblicati)", fontsize=10)
    salva(fig, "d10_finestra")


def d11_huber():
    """Perdita quadratica e perdita di Huber."""
    e = np.linspace(-4, 4, 400)
    k = 1.35
    hub = np.where(np.abs(e) <= k, e ** 2 / 2, k * np.abs(e) - k ** 2 / 2)
    fig, ax = plt.subplots(figsize=(7.5, 3.0))
    ax.plot(e, e ** 2 / 2, color=COL["grigio"], lw=2, label="quadratica (minimi quadrati)")
    ax.plot(e, hub, color=COL["blu"], lw=2.5, label="Huber (ε = 1,35)")
    ax.axvspan(-k, k, color=CHIARO["blu"], alpha=0.5)
    ax.text(0, 6.3, "errori piccoli:\nstessa penalita'", ha="center", fontsize=8.5)
    ax.text(3.0, 2.0, "errori grandi (COVID):\npenalita' solo lineare", ha="center", fontsize=8.5)
    ax.set_xlabel("errore della stima"); ax.set_ylabel("penalita'"); ax.legend(fontsize=8.5, loc="upper left")
    ax.set_ylim(0, 8)
    ax.set_title("Regressione di Huber: un mese anomalo non puo' trascinare tutta la retta", fontsize=10)
    salva(fig, "d11_huber")


def d12_bootstrap():
    """Bootstrap a blocchi mobili (schema)."""
    rng = np.random.default_rng(5)
    fig, ax = plt.subplots(figsize=(10, 2.8))
    n, bl = 12, 3
    cm = plt.get_cmap("tab20")
    for i in range(n):
        ax.add_patch(plt.Rectangle((i, 3), 0.9, 0.8, color=cm(i % 20)))
        ax.text(i + 0.45, 3.4, f"m{i + 1}", ha="center", va="center", fontsize=8)
    ax.text(-0.3, 3.4, "mesi osservati", ha="right", va="center", fontsize=9)
    for r in range(2):
        start = rng.integers(0, n - bl + 1, n // bl)
        pos = 0
        for s in start:
            for j in range(bl):
                ax.add_patch(plt.Rectangle((pos, 1.6 - r * 1.3), 0.9, 0.8, color=cm((s + j) % 20)))
                ax.text(pos + 0.45, 2.0 - r * 1.3, f"m{s + j + 1}", ha="center", va="center", fontsize=8)
                pos += 1
            ax.plot([pos - 0.05, pos - 0.05], [1.5 - r * 1.3, 2.5 - r * 1.3], color=COL["nero"], lw=1.5)
        ax.text(-0.3, 2.0 - r * 1.3, f"campione bootstrap {r + 1}", ha="right", va="center", fontsize=9)
    ax.set_xlim(-4, n); ax.set_ylim(0, 4); ax.axis("off")
    ax.set_title("Bootstrap a blocchi di 3 mesi: si pescano a caso blocchi di mesi consecutivi (con ripetizione) e si "
                 "ricalcola il rapporto degli errori;\nripetuto 2.000 volte, il 5° e il 95° percentile danno l'intervallo al 90%",
                 fontsize=9.5)
    salva(fig, "d12_bootstrap")


def d13_ranghi():
    """Dal valore grezzo al punteggio di rango (0-100): quota di visite Wikipedia (mercato estero), dati veri."""
    import pandas as pd
    el = pd.read_csv(OUT / "ind_elementari_estero.csv", index_col=0)
    v = el.wiki_quota
    rg = (v.rank() - 1) / (v.count() - 1) * 100
    fig, axs = plt.subplots(2, 1, figsize=(10, 2.8))
    for ax, s, t in [(axs[0], 100 * v, "1. quota di visite Wikipedia (%): il Lazio e' lontanissimo dalle altre"),
                     (axs[1], rg, "2. punteggio di rango = (posizione - 1) / 19 x 100: conta solo l'ordine")]:
        ax.scatter(s, np.zeros(len(s)), s=30, color=COL["blu"], zorder=3)
        for nome in ["Lazio", "Toscana", "Molise", "Umbria"]:
            ax.annotate(nome, (s[nome], 0), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=7.5)
        ax.set_yticks([]); ax.set_title(t, fontsize=9.5, loc="left"); ax.spines["left"].set_visible(False)
        ax.grid(axis="y", visible=False)
    axs[1].set_xlim(-5, 105)
    fig.tight_layout()
    salva(fig, "d13_ranghi")


def d14_alberi():
    """Albero di decisione e random forest (schema)."""
    fig, ax = tela(10, 3.4)
    box(ax, 0.36, 0.78, 0.28, 0.16, "variazione ISTAT t-3 > 0,2 ?", "giallo", fs=9)
    box(ax, 0.08, 0.42, 0.3, 0.16, "Trends voli > 0,1 ?", "giallo", fs=9)
    box(ax, 0.62, 0.42, 0.3, 0.16, "stima = +0,25", "verde", fs=9)
    box(ax, 0.0, 0.06, 0.2, 0.16, "stima = +0,08", "verde", fs=9)
    box(ax, 0.26, 0.06, 0.2, 0.16, "stima = -0,05", "verde", fs=9)
    for a, b, t in [((0.5, 0.78), (0.23, 0.58), "no"), ((0.5, 0.78), (0.77, 0.58), "si'"),
                    ((0.23, 0.42), (0.1, 0.22), "si'"), ((0.23, 0.42), (0.36, 0.22), "no")]:
        freccia(ax, a, b)
        ax.text((a[0] + b[0]) / 2 + 0.01, (a[1] + b[1]) / 2, t, fontsize=8.5, color=COL["testo"])
    box(ax, 0.55, 0.04, 0.44, 0.28, "Random forest = 300 alberi come questo, ognuno stimato su un\n"
        "campione diverso dei dati e con variabili scelte a caso.\nLa stima finale e' la media dei 300 alberi.", "grigio", fs=8.5)
    ax.text(0.5, 0.99, "Un albero di decisione (esempio illustrativo con numeri inventati)", ha="center", fontsize=10.5,
            fontweight="bold")
    salva(fig, "d14_alberi")


DIDATTICHE = (d01_serie, d02_correlazione, d03_intervallo, d04_trends_scala, d05_nmf, d06_confusione, d07_bayes,
              d08_kmeans, d09_mantel, d10_finestra, d11_huber, d12_bootstrap, d13_ranghi, d14_alberi)


def tutti():
    for f in (s1, s2, s3, s4, s5, s6) + DIDATTICHE:
        f()
    print(f"Schemi salvati in {DIR}")


if __name__ == "__main__":
    tutti()
