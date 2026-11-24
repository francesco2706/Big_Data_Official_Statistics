"""
SCRIPT 0 - Modulo comune

Raccoglie in un solo posto:
  * i percorsi delle cartelle del progetto (data/, output/, docs/), cosi' nessuno script dipende dalla cartella da cui
    viene lanciato
  * colori, nomi delle regioni, stile dei grafici
  * Registro: stampa a video e salva lo stesso testo in un file di risultati

Struttura del progetto:
  data/raw/        dati scaricati (ISTAT, Reddit .jsonl, Google Trends .zip, Wikipedia)
  data/processed/  dati puliti e file di lavoro prodotti da script 1-8
  data/llm/        dati della classificazione con Qwen (file per Kaggle, risultati grezzi, annotazioni a mano)
  output/          risultati: tabelle, grafici, file di testo (+ controlli/, llm/, schemi/, log/)
  docs/            report PDF, presentazione, guide
"""
from pathlib import Path

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt

SCRIPT = Path(__file__).resolve().parent 
PROGETTO = SCRIPT.parent                          
RAW = PROGETTO / "data" / "raw"
PROC = PROGETTO / "data" / "processed"
LLM = PROGETTO / "data" / "llm"
OUT = PROGETTO / "output"
DOCS = PROGETTO / "docs"
IN = OUT
for _c in (PROC, LLM, OUT, OUT / "llm", OUT / "controlli", OUT / "log", DOCS):
    _c.mkdir(parents=True, exist_ok=True)

COL = dict(nero="#0b0b0b", testo="#52514e", griglia="#e1e0d9", griglia2="#c3c2b7", grigio="#898781",
           blu="#2a78d6", arancio="#eb6834", verde="#1baf7a", giallo="#eda100", viola="#7a5bd6")
NOMI = {"ITC1": "Piemonte", "ITC2": "Valle d'Aosta", "ITC3": "Liguria", "ITC4": "Lombardia", "ITDA": "Trentino-AA",
        "ITD3": "Veneto", "ITD4": "Friuli-VG", "ITD5": "Emilia-Romagna", "ITE1": "Toscana", "ITE2": "Umbria",
        "ITE3": "Marche", "ITE4": "Lazio", "ITF1": "Abruzzo", "ITF2": "Molise", "ITF3": "Campania", "ITF4": "Puglia",
        "ITF5": "Basilicata", "ITF6": "Calabria", "ITG1": "Sicilia", "ITG2": "Sardegna"}
REG = list(NOMI)
MERC = {"domestico": ("Mercato domestico", COL["blu"]), "estero": ("Mercato estero", COL["arancio"])}

mpl.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
    "axes.edgecolor": COL["griglia2"], "axes.labelcolor": COL["testo"], "xtick.color": COL["testo"],
    "ytick.color": COL["testo"], "axes.grid": True, "grid.color": COL["griglia"], "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 11, "axes.titlesize": 12.5,
    "axes.titleweight": "bold", "axes.titlecolor": COL["nero"], "lines.linewidth": 2, "legend.frameon": False,
    "savefig.dpi": 200, "savefig.bbox": "tight"})


# ================================================================ versione inglese dei grafici per le slide
# I grafici del report restano in italiano; quelli usati nella presentazione (in inglese) vengono salvati una seconda
# volta in output/slide_en/ con tutte le scritte tradotte. La traduzione avviene sulla figura gia' disegnata.
import re as _re
import matplotlib.text as _mtext

GRAFICI_SLIDE = {"eda2_dinamica", "eda4_territorio", "nc_3_rmse_relativo", "nc_2_importanza_rf", "tm1_parole",
                 "snt1_mesi", "ind_1_pilastri", "ind_2_incertezza", "ind_3_scarti", "cl_3_profili_gruppi"}
SLIDE_EN = OUT / "slide_en"
EN_ESATTE = {
    # mesi (assi a lettere) e mercati
    "G": "J", "L": "J",
    "Mercato domestico": "Domestic market", "Mercato estero": "Foreign market",
    "Clienti italiani": "Italian guests", "Clienti stranieri": "Foreign guests",
    # eda2
    "ISTAT arrivi": "ISTAT arrivals", "Trends: hotel": "Trends: hotels", "Trends: voli": "Trends: flights",
    "Trends: destinazioni": "Trends: destinations", "indice, 2019 = 100": "index, 2019 = 100",
    "Google: cambio\nraccolta dati": "Google: new\ndata collection",
    # eda4
    "quota arrivi ISTAT 2023-24": "share of ISTAT arrivals 2023-24", "quota della fonte digitale": "share of the digital source",
    # nowcasting
    "Nowcasting: errore (RMSE) rispetto al modello con soli dati ufficiali":
        "Nowcasting: error (RMSE) relative to the model with official data only",
    "RMSE relativo a B1 (sotto 1 = meglio)": "RMSE relative to B1 (below 1 = better)",
    "ISTAT t-3": "ISTAT t−3", "ISTAT t-4": "ISTAT t−4", "Trends hotel": "Trends hotels", "Trends voli": "Trends flights",
    "Trends destinazioni": "Trends destinations", "mese dell'anno": "month of the year",
    "Random forest stimato fino al 2021: importanza delle variabili fuori campione":
        "Random forest trained up to 2021: out-of-sample variable importance",
    "aumento dell'RMSE sul 2022-2024 quando la variabile viene rimescolata":
        "increase of the 2022-2024 RMSE when the variable is shuffled",
    # topic modeling
    "Parole principali di ogni tema (NMF)": "Top words of each topic (NMF)",
    # sentiment
    "sentiment medio (Qwen, da -2 a +2)": "average sentiment (Qwen, from −2 to +2)",
    "arrivi stranieri ISTAT (milioni, media 2023-24)": "ISTAT foreign arrivals (millions, 2023-24 average)",
    # indicatore
    "Visibilita'": "Visibility", "Reputazione": "Reputation", "Slancio": "Momentum",
    "I tre pilastri e il DAI (punteggi di rango; regioni ordinate per DAI)":
        "The three pillars and the DAI (rank scores; regions sorted by DAI)",
    "punteggio di rango (100 = migliore, 0 = peggiore)": "rank score (100 = best, 0 = worst)",
    "min-max": "full range", "10-90%": "10-90%", "scelta principale": "version used",
    "posizione (1 = massima attenzione)": "rank (1 = most attention)",
    "Incertezza della classifica DAI (normalizzazione x pesi x aggregazione x sentiment)":
        "Robustness of the DAI ranking across 36 versions of the index",
    "Dove l'attenzione online e i flussi turistici divergono (2019-2024)":
        "Where online attention and tourist flows diverge (2019-2024)",
    "scarto di visibilita' (> 0: piu' attenzione che turisti)": "visibility gap (> 0: more attention than tourists)",
    "scarto di slancio (> 0: interesse cresciuto piu' dei turisti)": "momentum gap (> 0: interest grew faster than tourists)",
    # clustering
    "Citta' e affari": "Cities & business", "Montagna (due stagioni)": "Mountains (two seasons)",
    "Arte e mare (stagionalita' intermedia)": "Art & sea (intermediate seasonality)",
    "Mare (molto stagionale)": "Seaside (very seasonal)", "quota del totale annuo": "share of the yearly total",
    "Profilo stagionale medio di ogni gruppo di regioni (ISTAT, 2023-2024)":
        "Average seasonal profile of each group of regions (ISTAT, 2023-2024)",
}
EN_REGEX = [
    (r"^Domestico: Wikipedia it \(Spearman (.+)\)$", r"Domestic: Italian Wikipedia (Spearman \1)"),
    (r"^Estero: Wikipedia en/de/fr/es \(Spearman (.+)\)$", r"Foreign: Wikipedia en/de/fr/es (Spearman \1)"),
    (r"^Estero: menzioni Reddit \(Spearman (.+)\)$", r"Foreign: Reddit mentions (Spearman \1)"),
    (r"^T(\d) \((\d+)% dei testi\)$", r"T\1 (\2% of texts)"),
    (r"^Il tono cala quando arrivano i turisti \(correlazione (.+)\)$",
     r"The tone drops when tourists arrive (correlation \1)"),
]


def _en(s):
    if s in EN_ESATTE:
        return EN_ESATTE[s]
    for p, r in EN_REGEX:
        if _re.match(p, s):
            return _re.sub(p, r, s)
    return s


def salva_inglese(fig, nome):
    """Per i grafici delle slide: traduce le scritte della figura e la salva in output/slide_en/."""
    if nome not in GRAFICI_SLIDE:
        return
    SLIDE_EN.mkdir(exist_ok=True)
    fig.canvas.draw()
    for ax in fig.axes:                       # etichette degli assi scritte a mano (mesi, nomi delle variabili)
        for asse in (ax.xaxis, ax.yaxis):
            testi = [t.get_text() for t in asse.get_ticklabels()]
            tradotti = [_en(s) for s in testi]
            if tradotti != testi:
                asse.set_ticks(asse.get_ticklocs())
                asse.set_ticklabels(tradotti)
    rimasti = set()
    import os
    for t in fig.findobj(_mtext.Text):
        s = t.get_text()
        if s and os.environ.get("EN_DEBUG"):
            print(f"  [{nome}] {s!r} -> {_en(s)!r}")
        if s:
            nuovo = _en(s)
            t.set_text(nuovo)
            if nuovo == s and _re.search(r"[a-z]{3}", s) and _re.search(
                    r"\b(di|del|della|dei|delle|che|piu|quota|mercato|arrivi|anno|mese|tema|regioni|e)\b", s.lower()):
                rimasti.add(s)
    fig.savefig(SLIDE_EN / f"{nome}.png")
    if rimasti:
        print(f"  ATTENZIONE {nome}: scritte non tradotte: {sorted(rimasti)}")


class Registro:
    """say() stampa e memorizza; salva_grafico() salva una figura; chiudi() scrive il file di testo dei risultati."""

    def __init__(self, nome_file):
        self.nome_file, self.righe = nome_file, []

    def say(self, *a):
        s = " ".join(str(x) for x in a)
        print(s)
        self.righe.append(s)

    def titolo(self, testo):
        self.say("\n" + "=" * 70 + "\n" + testo + "\n" + "=" * 70)

    def salva_grafico(self, fig, nome):
        fig.savefig(OUT / f"{nome}.png")
        salva_inglese(fig, nome)
        plt.close(fig)
        self.say(f"  grafico salvato: output/{nome}.png")

    def chiudi(self):
        (OUT / self.nome_file).write_text("\n".join(self.righe), encoding="utf-8")
        print(f"\nFatto. Risultati testuali in output/{self.nome_file}")
