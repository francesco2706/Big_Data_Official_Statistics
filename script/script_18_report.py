"""
SCRIPT 18 - Report PDF del progetto
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate, Paragraph,
                                Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents
from scipy import stats

import script_17_schemi as schemi
from script_0_comune import DOCS, LLM, OUT, PROC, RAW

# ================================================================ font e stili
F = Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont("Arial", str(F / "arial.ttf")))
pdfmetrics.registerFont(TTFont("Arial-Bold", str(F / "arialbd.ttf")))
pdfmetrics.registerFont(TTFont("Arial-Italic", str(F / "ariali.ttf")))
pdfmetrics.registerFont(TTFont("Arial-BoldItalic", str(F / "arialbi.ttf")))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial-Italic", boldItalic="Arial-BoldItalic")
pdfmetrics.registerFont(TTFont("Mono", str(F / "consola.ttf")))

BLU, ARANCIO, VERDE, GIALLO = colors.HexColor("#2a78d6"), colors.HexColor("#eb6834"), colors.HexColor("#1baf7a"), colors.HexColor("#eda100")
NERO, TESTO, GRIGIO, CHIARO = colors.HexColor("#0b0b0b"), colors.HexColor("#33322f"), colors.HexColor("#898781"), colors.HexColor("#f3f2ee")
BLU_CH, VERDE_CH, ARANCIO_CH, GIALLO_CH = (colors.HexColor(c) for c in ["#e8f1fb", "#e3f6ee", "#fdeee7", "#fdf3d9"])
VIOLA, VIOLA_CH = colors.HexColor("#7a5bd6"), colors.HexColor("#efebfb")
S = dict(
    titolo=ParagraphStyle("titolo", fontName="Arial-Bold", fontSize=26, leading=31, textColor=NERO, alignment=TA_CENTER),
    sottotitolo=ParagraphStyle("sottotitolo", fontName="Arial", fontSize=14, leading=19, textColor=TESTO, alignment=TA_CENTER),
    H1=ParagraphStyle("H1", fontName="Arial-Bold", fontSize=17, leading=21, textColor=BLU, spaceBefore=4, spaceAfter=10),
    H2=ParagraphStyle("H2", fontName="Arial-Bold", fontSize=12.5, leading=16, textColor=NERO, spaceBefore=10, spaceAfter=5),
    H3=ParagraphStyle("H3", fontName="Arial-Bold", fontSize=10.5, leading=14, textColor=TESTO, spaceBefore=6, spaceAfter=3),
    P=ParagraphStyle("P", fontName="Arial", fontSize=10, leading=14.2, textColor=TESTO, alignment=TA_JUSTIFY, spaceAfter=6),
    B=ParagraphStyle("B", fontName="Arial", fontSize=10, leading=14, textColor=TESTO, leftIndent=14, bulletIndent=3, spaceAfter=2.5),
    cella=ParagraphStyle("cella", fontName="Arial", fontSize=8.3, leading=10.5, textColor=TESTO),
    cellaB=ParagraphStyle("cellaB", fontName="Arial-Bold", fontSize=8.3, leading=10.5, textColor=colors.white),
    didascalia=ParagraphStyle("did", fontName="Arial-Italic", fontSize=8.5, leading=11, textColor=GRIGIO, alignment=TA_CENTER, spaceAfter=10),
    formula=ParagraphStyle("formula", fontName="Arial", fontSize=10, leading=15, textColor=NERO, alignment=TA_CENTER),
    box=ParagraphStyle("box", fontName="Arial", fontSize=9.6, leading=13.5, textColor=TESTO),
    mono=ParagraphStyle("mono", fontName="Mono", fontSize=7.8, leading=10, textColor=NERO),
    toc1=ParagraphStyle("toc1", fontName="Arial-Bold", fontSize=10.5, leading=16, leftIndent=0),
    toc2=ParagraphStyle("toc2", fontName="Arial", fontSize=9.5, leading=13, leftIndent=16, textColor=TESTO),
)
LARG = 17 * cm
story = []


def H1(t):
    story.append(PageBreak())
    story.append(Paragraph(t, S["H1"]))


def H2(t):
    story.append(Paragraph(t, S["H2"]))


def H3(t):
    story.append(Paragraph(t, S["H3"]))


def P(t):
    story.append(Paragraph(t, S["P"]))


def elenco(voci, numeri=False):
    for i, v in enumerate(voci, 1):
        story.append(Paragraph(v, S["B"], bulletText=f"{i}." if numeri else "•"))
    story.append(Spacer(1, 4))


def formula(t):
    tb = Table([[Paragraph(t, S["formula"])]], colWidths=[LARG])
    tb.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CHIARO), ("BOX", (0, 0), (-1, -1), 0.5, GRIGIO),
                            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.extend([tb, Spacer(1, 8)])


def riquadro(titolo, testo, sfondo=BLU_CH, bordo=BLU):
    tb = Table([[Paragraph(f"<b>{titolo}</b><br/>{testo}", S["box"])]], colWidths=[LARG])
    tb.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), sfondo), ("LINEBEFORE", (0, 0), (0, -1), 3, bordo),
                            ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                            ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    story.extend([Spacer(1, 3), tb, Spacer(1, 9)])


def teoria(titolo, testo):
    riquadro("Teoria - " + titolo, testo, VIOLA_CH, VIOLA)


def esempio(titolo, testo):
    riquadro("Esempio - " + titolo, testo, GIALLO_CH, GIALLO)


def inbreve(testo):
    riquadro("In breve", testo, VERDE_CH, VERDE)


def scheda(script, scopo, legge, scrive):
    """Carta d'identita' di uno script."""
    righe = [["Script", script], ["A cosa serve", scopo], ["Legge", legge], ["Scrive", scrive]]
    tb = Table([[Paragraph(f"<b>{a}</b>", S["cella"]), Paragraph(b, S["cella"])] for a, b in righe],
               colWidths=[2.6 * cm, LARG - 2.6 * cm])
    tb.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), BLU_CH), ("BOX", (0, 0), (-1, -1), 0.6, BLU),
                            ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#c9d9ef")),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 3),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story.extend([tb, Spacer(1, 9)])


def codice(testo):
    """Riquadro con testo a larghezza fissa (righe di un file, comandi)."""
    righe = testo.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(" ", "&nbsp;").split("\n")
    tb = Table([[Paragraph("<br/>".join(righe), S["mono"])]], colWidths=[LARG])
    tb.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f6f6f4")),
                            ("BOX", (0, 0), (-1, -1), 0.4, GRIGIO), ("LEFTPADDING", (0, 0), (-1, -1), 8),
                            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story.extend([tb, Spacer(1, 8)])


def tabella(righe, intest, larghezze=None, colore=BLU):
    dati = [[Paragraph(str(h), S["cellaB"]) for h in intest]] + [[Paragraph(str(c), S["cella"]) for c in r] for r in righe]
    larghezze = [LARG / len(intest)] * len(intest) if larghezze is None else [LARG * l / sum(larghezze) for l in larghezze]
    tb = Table(dati, colWidths=larghezze, repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), colore), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#d9d8d2")),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    st += [("BACKGROUND", (0, i), (-1, i), CHIARO) for i in range(2, len(dati), 2)]
    tb.setStyle(TableStyle(st))
    story.extend([tb, Spacer(1, 10)])


def _fmt(v):
    if isinstance(v, (bool, np.bool_)):
        return str(v)
    if isinstance(v, (int, np.integer)):
        return f"{v:,}".replace(",", ".")
    if isinstance(v, (float, np.floating)):
        if pd.isna(v):
            return ""
        if abs(v) >= 1000 and float(v).is_integer():
            return f"{v:,.0f}".replace(",", ".")
        return f"{v:.4g}".replace(".", ",")
    return str(v)


def mini(df, titolo=None, larghezze=None, colore=GRIGIO):
    """Piccola tabella con alcune righe vere di un dataset."""
    if titolo:
        story.append(Paragraph(f"<i>{titolo}</i>", ParagraphStyle("mt", parent=S["didascalia"], alignment=0, spaceAfter=3)))
    tabella([[_fmt(v) for v in r] for r in df.itertuples(index=False)], list(df.columns), larghezze, colore)


def figura(path, didascalia, max_alt=11.5 * cm):
    path = Path(path)
    if not path.exists():
        P(f"<i>[figura non trovata: {path.name}]</i>")
        return
    w, h = PILImage.open(path).size
    larg, alt = LARG, LARG * h / w
    if alt > max_alt:
        alt, larg = max_alt, max_alt * w / h
    story.append(KeepTogether([Image(str(path), width=larg, height=alt), Paragraph(didascalia, S["didascalia"])]))


def f(x, n=2):
    return f"{x:.{n}f}".replace(".", ",")


def pc(x, n=0):
    return f"{100 * x:.{n}f}%".replace(".", ",")


def mig(x):
    return f"{int(x):,}".replace(",", ".")


SCH = schemi.DIR

# ================================================================ risultati
O = OUT
STAG, YOY = pd.read_csv(O / "eda3_stagionalita.csv"), pd.read_csv(O / "eda5_correlazioni_yoy.csv")
TM = pd.read_csv(O / "tm_riepilogo.csv")
TMC = pd.read_csv(O / "tm_correlazione_arrivi.csv", index_col=0).iloc[:, 0]
TMK = pd.read_csv(O / "tm_scelta_k.csv", index_col=0).iloc[:, 0]
TMP = pd.read_csv(O / "tm_parole.csv")
REP = pd.read_csv(O / "rep_regioni.csv", index_col=0)
SV = pd.read_csv(O / "snt_validazione.csv", index_col=0)
SVR = pd.read_csv(O / "snt_validazione_regione.csv").iloc[0]
SMC = pd.read_csv(O / "snt_mcnemar.csv")
SCF = pd.read_csv(O / "snt_confusione.csv")
SRG = pd.read_csv(O / "snt_regione.csv").iloc[0]
SST = pd.read_csv(O / "snt_stagioni.csv").set_index("stagione")
SAS = pd.read_csv(O / "snt_aspetti.csv", index_col=0)
STE = pd.read_csv(O / "snt_temi.csv", index_col=0)
SDE = pd.read_csv(O / "snt_scomposizione.csv").iloc[0]
META = json.load(open(LLM / "qwen_completo_meta.json", encoding="utf-8"))
VAL = pd.read_csv(O / "ind_validazione.csv")
DAI_E = pd.read_csv(O / "ind_dai_estero.csv", index_col=0)
SC_E = pd.read_csv(O / "ind_scarto_estero.csv", index_col=0)
INC_E = pd.read_csv(O / "ind_incertezza_estero.csv", index_col=0)
SIN = pd.read_csv(O / "ind_sintesi_incertezza.csv").set_index("mercato")
EL = pd.read_csv(O / "ind_elementari_estero.csv", index_col=0)
K = pd.read_csv(O / "cl_scelta_k.csv")
ACC = pd.read_csv(O / "cl_accordo_k.csv")
MAN = pd.read_csv(O / "cl_mantel.csv")
GR4 = pd.read_csv(O / "cl_gruppi_k4.csv")
NC = pd.read_csv(O / "nc_rmse.csv")
IMP = pd.read_csv(O / "nc_importanza_rf.csv", index_col=0)


def nc(mk, per, mod, col="RMSE_rel_B1"):
    return NC[(NC.mercato == mk) & (NC.periodo == per) & (NC.modello == mod)][col].iloc[0]


def mantel(fonte, merc="entrambi i mercati"):
    r = MAN[(MAN.fonte == fonte) & (MAN.mercato == merc)].iloc[0]
    return r.mantel_r, r.p_value


r_w, _ = mantel("Wikipedia")
r_t, _ = mantel("Google Trends")
vis_e = VAL[(VAL.mercato == "estero") & (VAL.misura == "Visibilita'")].spearman.iloc[0]
QW, VD, RB = SV.loc["Qwen 2.5 7B"], SV.loc["VADER (dizionario)"], SV.loc["RoBERTa (transformer)"]
p_qv = SMC[SMC.confronto.str.contains("VADER")].p_value.iloc[0]
p_qr = SMC[SMC.confronto.str.contains("RoBERTa")].p_value.iloc[0]
neg_w, neg_s = SST.loc["inverno", "quota_negativi"], SST.loc["estate", "quota_negativi"]
r_mesi = SST.loc["inverno", "r_mesi_arrivi"]
SE_ = SIN.loc["estero"]
rho_v = stats.spearmanr(REP.n_testi, REP.shrink).correlation
ELc = EL.apply(lambda c: np.log(c) if c.name != "reddit_sentiment" else c).corr("spearman")
W_ = REP.peso_dati
MU = float(((REP.shrink - W_ * REP.media) / (1 - W_)).median())
TAU = float(np.sqrt((REP.se ** 2 * W_ / (1 - W_)).median()))
MOL = REP.loc["ITF2"]
LAZ = REP.loc["ITE4"]

# ---------------------------------------------------------------- esempi veri dai dataset
_ir = pd.read_csv(RAW / "istat" / "istat_movimento_clienti_mensile.csv", low_memory=False,
                  usecols=["REF_AREA", "DATA_TYPE", "TYPE_ACCOMMODATION", "COUNTRY_RES_GUESTS", "TIME_PERIOD", "OBS_VALUE"])
N_IST_RAW = len(_ir)
IST_RAW = _ir[(_ir.REF_AREA == "ITE1") & (_ir.TIME_PERIOD == "2024-07") & (_ir.DATA_TYPE == "AR")].sort_values(
    ["COUNTRY_RES_GUESTS", "TYPE_ACCOMMODATION"])
del _ir
IST = pd.read_csv(PROC / "istat_target.csv")
IST_T = IST[(IST.REF_AREA == "ITE1") & IST.TIME_PERIOD.isin(["2023-07", "2024-07"])][
    ["REF_AREA", "market", "TIME_PERIOD", "arrivi", "presenze", "permanenza_media", "yoy_arrivi"]].round(3)
_tr = pd.read_csv(PROC / "trends_rep1_all.csv")
TR_EX = _tr[(_tr.REF_AREA == "ITE1") & (_tr.geo == "DE") & (_tr.intent == "hotel")
            & _tr.TIME_PERIOD.isin(["2023-07", "2024-07"])][["REF_AREA", "geo", "cat", "intent", "nome", "TIME_PERIOD", "value"]]
del _tr
WT = pd.read_csv(RAW / "wikipedia" / "wiki_titoli.csv")
WT_EX = WT[WT.REF_AREA == "ITE1"][["titolo_it", "qid", "titolo_en", "titolo_de", "titolo_fr", "titolo_es"]]
N_TITOLI = len(WT)
WM = pd.read_csv(PROC / "wiki_mensile_v2.csv")
WM_EX = WM[(WM.REF_AREA == "ITE1") & (WM.TIME_PERIOD == "2024-07")][
    ["REF_AREA", "lang", "market", "TIME_PERIOD", "views_regione", "views_destinazioni", "views_totale"]]
RM = pd.read_csv(PROC / "reddit_mensile.csv")
RM_EX = RM[RM.REF_AREA.isin(["ITE1", "ITF2"]) & (RM.TIME_PERIOD == "2024-07")][
    ["REF_AREA", "TIME_PERIOD", "n_testi", "n_post", "n_testi_mese", "quota_testi"]].round(4)
QC = pd.read_csv(LLM / "qwen_completo.csv", dtype={"id": str}, nrows=4).drop(columns=["risposta_grezza", "errore"])

# ================================================================ copertina e indice
story += [Spacer(1, 4.2 * cm), Paragraph("From Clicks to Check-ins", S["titolo"]), Spacer(1, 0.4 * cm),
          Paragraph("Google Trends, Wikipedia e Reddit possono stimare in anticipo<br/>il turismo regionale italiano?", S["sottotitolo"]),
          Spacer(1, 1.2 * cm), Paragraph("Report del progetto: dati, teoria, metodi e risultati, script per script", S["sottotitolo"]),
          Spacer(1, 3.5 * cm),
          Paragraph("Francesco Pio Nardiello 2251083<br/>Big Data for Official Statistics - Sapienza Università di Roma<br/>A.A. 2026/2027",
                    ParagraphStyle("aut", parent=S["sottotitolo"], fontSize=11, leading=16)), Spacer(1, 2.0 * cm)]
riquadro("Come leggere questo report",
         "Il report segue il progetto nell'ordine in cui è stato costruito. Il <b>capitolo 3</b> spiega i concetti di base "
         "(serie storica, variazione annua, correlazione, intervallo di confidenza, p-value, regressione) che servono in "
         "tutto il resto. Dal capitolo 4 ogni capitolo corrisponde a uno o più <b>script</b> della cartella <i>script/</i> e "
         "si apre con una <b>scheda</b> (a cosa serve, che cosa legge, che cosa scrive). Dentro i capitoli si trovano quattro "
         "tipi di riquadri:<br/>"
         "• <font color='#7a5bd6'><b>Teoria</b></font>: il metodo statistico spiegato da zero;<br/>"
         "• <font color='#c98a00'><b>Esempio</b></font>: un calcolo fatto a mano con numeri veri o inventati;<br/>"
         "• <font color='#1baf7a'><b>In breve</b></font>: che cosa si porta a casa dal capitolo;<br/>"
         "• tabelle grigie: alcune righe vere dei dataset, per vedere com'è fatto il dato.")
story.append(PageBreak())
story.append(Paragraph("Indice", S["H1"]))
toc = TableOfContents()
toc.levelStyles = [S["toc1"], S["toc2"]]
story.append(toc)

# ================================================================ 1 sintesi
H1("1. Sintesi")
P("Il progetto si chiede se tre fonti digitali (<b>Google Trends</b>, <b>Wikipedia</b> e <b>Reddit</b>) permettano di "
  "conoscere in anticipo l'andamento del turismo nelle 20 regioni italiane, prima che l'ISTAT pubblichi il dato ufficiale "
  "sugli arrivi negli esercizi ricettivi. La domanda è divisa in tre parti:")
elenco(["<b>Rispecchiano?</b> Le fonti digitali riproducono la geografia e la stagionalità del turismo misurate da ISTAT?",
        "<b>Anticipano?</b> Aggiungono informazione utile a stimare gli arrivi del mese corrente (<i>nowcasting</i>)?",
        "<b>Spiegano?</b> I testi di Reddit aiutano a capire perché l'esperienza turistica cambia?"])
riquadro("Risposta in breve",
         f"<b>Rispecchiano: sì, nella struttura.</b> La quota di attenzione digitale riproduce la distribuzione degli arrivi "
         f"tra regioni (correlazione {f(vis_e)} per il mercato estero) e le regioni con stagionalità simile per ISTAT lo sono "
         f"anche per i dati digitali (test di Mantel: Wikipedia {f(r_w)}, Google Trends {f(r_t)}).<br/>"
         f"<b>Anticipano: solo nelle svolte.</b> Nel 2022, anno della ripresa, Google Trends riduce l'errore di stima del "
         f"{pc(1 - nc('domestico', '2022', 'B1+Trends'))} per il mercato domestico, con un intervallo di confidenza tutto "
         f"sotto 1. Negli anni normali 2023-2024 nessuna fonte digitale migliora la stima basata sui soli dati ufficiali.<br/>"
         f"<b>Spiegano: sì.</b> Un modello linguistico aperto (Qwen 2.5), validato su testi annotati a mano ({pc(QW.accuratezza)} "
         f"di accuratezza), mostra che il tono peggiora quando arrivano i turisti (testi negativi dal {pc(neg_w, 1)} in inverno "
         f"al {pc(neg_s, 1)} in estate), che il calo avviene dentro gli stessi argomenti e che peggiorano soprattutto i giudizi "
         f"su prezzi e alloggio.<br/><b>Messaggio:</b> i big data non sostituiscono ISTAT; lo affiancano come segnale precoce "
         f"nelle fasi di rottura e come fonte di spiegazione.", VERDE_CH, VERDE)

# ================================================================ 2 disegno
H1("2. Domanda di ricerca e disegno dello studio")
P("L'<b>unità di analisi</b> (il \"pezzo\" su cui si misura ogni cosa) è la combinazione <b>regione x mese x mercato</b>: "
  "20 regioni (classificazione europea NUTS-2, con Trento e Bolzano unite nel Trentino-Alto Adige), mesi dal 2011 al "
  "2024, mercato <b>domestico</b> (turisti residenti in Italia) ed <b>estero</b> (non residenti). Il riferimento ufficiale "
  "è il numero di <b>arrivi</b> negli esercizi ricettivi, cioè i clienti che hanno fatto check-in in alberghi o strutture "
  "extralberghiere (campeggi, B&amp;B, case vacanza...).")
P("Perché servono fonti digitali? Il dato ISTAT è completo e affidabile, ma arriva <b>con mesi di ritardo</b>. Le ricerche "
  "su Google, le visite alle pagine di Wikipedia e le discussioni su Reddit sono invece disponibili <b>subito</b>: se "
  "contenessero informazione sui viaggi, si potrebbe sapere prima come sta andando il turismo.")
figura(SCH / "s1_pipeline.png", "Figura 2.1 - Il percorso dei dati: dalla raccolta ai modelli (numeri = script).", max_alt=12 * cm)
tabella([["Analisi dei testi", "Modello linguistico (Qwen) e topic model", "Di cosa si parla, con che tono, e perché il tono cambia?", "8-13"],
         ["Indicatore composito", "Statistica descrittiva multivariata", "Quanta attenzione online riceve ogni regione, e quanto diverge dai turisti reali?", "14"],
         ["Clustering", "Apprendimento non supervisionato", "I dati digitali riconoscono gli stessi tipi di regioni turistiche visti da ISTAT?", "15"],
         ["Nowcasting", "Apprendimento supervisionato", "Le fonti digitali migliorano la stima degli arrivi del mese corrente?", "16"]],
        ["Analisi", "Metodo", "Domanda", "Script"], [2.3, 2.8, 5.6, 0.9])
P("<b>Supervisionato</b> vuol dire che il modello impara da esempi di cui si conosce la risposta giusta (gli arrivi ISTAT "
  "passati) e poi prova a indovinarla per i casi nuovi. <b>Non supervisionato</b> vuol dire che non c'è una risposta "
  "giusta da imparare: si cercano strutture nei dati (per esempio gruppi di regioni simili). <b>Descrittivo</b> vuol dire "
  "che si riassumono i dati in un numero leggibile, senza stimare nulla.")

# ================================================================ 3 concetti di base
H1("3. Concetti di base")
P("Questo capitolo raccoglie le idee statistiche che ritornano in tutto il progetto. Chi le conosce già può saltarlo; "
  "negli altri capitoli si rimanda qui quando servono.")
H2("3.1 Dataset, variabili, chiavi")
P("Un <b>dataset</b> è una tabella: ogni <b>riga</b> è un'osservazione, ogni <b>colonna</b> una <b>variabile</b>. Le "
  "colonne che dicono <i>a che cosa</i> si riferisce la riga si chiamano <b>chiavi</b> (o dimensioni): regione, mercato, "
  "mese. Le altre contengono le <b>misure</b>: arrivi, ricerche, visite, numero di testi. Due dataset si possono unire "
  "(\"fare il merge\") solo se hanno le stesse chiavi scritte nello stesso modo: per questo il progetto usa ovunque i "
  "codici europei delle regioni (ITE1 = Toscana, ITF2 = Molise...) e il mese nel formato AAAA-MM.")
esempio("una riga, tre chiavi e due misure",
        "<i>REF_AREA = ITE1, market = estero, TIME_PERIOD = 2024-07, arrivi = 1.181.400, presenze = 4.457.197</i>: a luglio "
        "2024 la Toscana ha accolto 1,18 milioni di turisti stranieri, che hanno trascorso in tutto 4,46 milioni di notti.")
H2("3.2 La serie storica")
P("Una <b>serie storica</b> è la sequenza dei valori di una misura <b>nel tempo</b>, tenendo fisse tutte le altre chiavi. "
  "\"Arrivi di stranieri in Toscana\" è una serie: un valore per ogni mese dal 2011 al 2024, cioè 168 valori. Quando nel "
  "report si dice che ISTAT ha \"40 serie\", si intende 20 regioni x 2 mercati = 40 sequenze mensili. Un insieme di "
  "serie con la stessa struttura (tante regioni osservate negli stessi mesi) si chiama <b>panel</b>.")
figura(SCH / "d01_serie.png", "Figura 3.1 - Una serie storica vera (sopra) e la sua variazione annua (sotto).", max_alt=9.5 * cm)
P("In una serie turistica si riconoscono tre componenti:")
elenco(["<b>stagionalità</b>: un andamento che si ripete ogni anno (il picco estivo, il minimo invernale);",
        "<b>tendenza</b> (trend): la crescita o il calo lento su più anni;",
        "<b>shock</b>: rotture improvvise, come il crollo del 2020 per il COVID e la ripresa del 2021-2022."])
P("Se si confrontano direttamente luglio e gennaio si vede soprattutto la stagionalità, che non dice nulla di nuovo "
  "(d'estate ci sono sempre più turisti). Per capire se il turismo <i>sta andando meglio o peggio</i> bisogna togliere "
  "la stagionalità: è il compito della variazione annua.")
H2("3.3 Logaritmo e variazione annua")
teoria("variazione annua logaritmica",
       "Si confronta ogni mese con <b>lo stesso mese dell'anno prima</b>: luglio 2024 con luglio 2023. Così la stagionalità "
       "si cancella da sola, perché luglio si confronta con luglio. Invece della differenza percentuale si usa la "
       "differenza dei logaritmi:<br/><br/>"
       "<b>y<sub>t</sub> = log(A<sub>t</sub>) - log(A<sub>t-12</sub>) = log(A<sub>t</sub> / A<sub>t-12</sub>)</b><br/><br/>"
       "Il logaritmo (naturale) trasforma i rapporti in differenze. Per variazioni piccole è quasi uguale alla variazione "
       "percentuale (+0,10 ≈ +10%), ma ha tre vantaggi: è <b>simmetrico</b> (raddoppiare = +0,69, dimezzare = -0,69, mentre "
       "in percentuale sarebbe +100% e -50%), si può <b>sommare</b> nel tempo, e rende confrontabili serie di grandezze "
       "molto diverse (la Lombardia e il Molise).")
tabella([["0", "uguale all'anno prima", "0%"], ["+0,10", "circa +10%", "+10,5%"], ["-0,10", "circa -10%", "-9,5%"],
         ["+0,69", "il doppio", "+100%"], ["-0,69", "la metà", "-50%"], ["-3", "crollo (COVID)", "-95%"]],
        ["Valore di y", "Lettura", "Variazione percentuale esatta"], [1.4, 2.5, 2.5])
_a = IST[(IST.REF_AREA == "ITE1") & (IST.market == "domestico")].set_index("TIME_PERIOD").arrivi
_a23, _a24 = _a["2023-07"], _a["2024-07"]
esempio("Toscana, turisti italiani",
        f"Luglio 2023: {mig(_a23)} arrivi; luglio 2024: {mig(_a24)}. y = log({mig(_a24)}) - log({mig(_a23)}) = "
        f"{f(np.log(_a24), 3)} - {f(np.log(_a23), 3)} = <b>{f(np.log(_a24 / _a23), 3)}</b>, cioè circa il "
        f"{abs(100 * np.log(_a24 / _a23)):.0f}% in meno (esattamente {f(100 * (_a24 / _a23 - 1), 1)}%).")
P("Per Google Trends, che può valere 0, si usa log(1 + G): il logaritmo di zero non esiste, aggiungere 1 lo evita senza "
  "cambiare molto i valori grandi.")
H2("3.4 Media, varianza, deviazione standard, z-score")
teoria("misure di posizione e di dispersione",
       "La <b>media</b> x&#772; = (x<sub>1</sub> + ... + x<sub>n</sub>) / n è il valore \"tipico\". La <b>varianza</b> misura "
       "quanto i valori si allontanano dalla media: s<super>2</super> = Σ (x<sub>i</sub> - x&#772;)<super>2</super> / (n - 1). "
       "La <b>deviazione standard</b> s è la radice della varianza ed è nella stessa unità dei dati. Lo <b>z-score</b> di un "
       "valore dice di quante deviazioni standard si trova sopra o sotto la media: z = (x - x&#772;) / s. Uno z-score di +1 "
       "vuol dire \"una deviazione standard sopra la media\"; serve a confrontare variabili con unità diverse (lo userà "
       "l'indicatore, capitolo 14). La <b>mediana</b> è il valore centrale dopo aver ordinato i dati: a differenza della "
       "media non si lascia spostare da pochi valori estremi.")
H2("3.5 Correlazione di Pearson e di Spearman")
teoria("correlazione",
       "La <b>correlazione di Pearson</b> r misura quanto due variabili si muovono insieme <i>in modo lineare</i>: "
       "r = Σ z<sub>x,i</sub> · z<sub>y,i</sub> / (n - 1), la media dei prodotti degli z-score. Vale tra -1 e +1: +1 = "
       "perfettamente insieme, 0 = nessun legame lineare, -1 = perfettamente opposte.<br/>"
       "La <b>correlazione di Spearman</b> ρ (rho) è la correlazione di Pearson calcolata sulle <b>posizioni in classifica</b> "
       "(ranghi) invece che sui valori. Risponde alla domanda \"le due variabili ordinano le unità nello stesso modo?\" ed è "
       "robusta ai valori estremi: la Toscana con il 13% delle visite non pesa più del Molise con lo 0,2%. Nel progetto si "
       "usa Spearman ogni volta che si confrontano <b>classifiche di regioni</b>.")
figura(SCH / "d02_correlazione.png", "Figura 3.2 - Esempi di correlazione (numeri inventati).", max_alt=5 * cm)
P("Attenzione: correlazione non vuol dire causa. Due serie possono essere correlate perché entrambe dipendono da una terza "
  "(per esempio la stagione).")
H2("3.6 Campione, errore standard, intervallo di confidenza")
teoria("incertezza di una stima",
       "Quasi sempre si osserva solo una parte dei casi possibili (un <b>campione</b>) e si vuole dire qualcosa di più "
       "generale. Una media calcolata su 20 testi cambierebbe se si prendessero altri 20 testi: l'<b>errore standard</b> "
       "misura di quanto oscilla la stima da un campione all'altro. Per una media vale se = s / √n: con più dati (n grande) "
       "la stima oscilla meno.<br/>"
       "L'<b>intervallo di confidenza al 95%</b> è circa stima ± 1,96 · se. Si legge così: se si ripetesse la raccolta dei "
       "dati tante volte, il 95% degli intervalli costruiti in questo modo conterrebbe il valore vero. Più l'intervallo è "
       "stretto, più la stima è precisa.")
figura(SCH / "d03_intervallo.png", "Figura 3.3 - A sinistra: più dati, meno oscillazione. A destra: circa 19 intervalli su 20 "
       "contengono il valore vero (numeri simulati).", max_alt=6 * cm)
H2("3.7 Test di ipotesi e p-value")
teoria("p-value",
       "Un test statistico parte da un'<b>ipotesi nulla</b> \"non c'è nessun effetto\" (per esempio: il tono del forum è "
       "uguale in estate e in inverno). Il <b>p-value</b> è la probabilità di osservare una differenza grande almeno quanto "
       "quella vista <i>se l'ipotesi nulla fosse vera</i>, cioè per puro caso. Un p-value piccolo (per convenzione sotto "
       "0,05) vuol dire che il caso spiega male quello che si vede: l'effetto si dice <b>statisticamente significativo</b>. "
       "Un p-value grande non prova che l'effetto non esista: dice solo che i dati non bastano a distinguerlo dal caso. "
       "Con moltissimi dati (128.000 testi) anche differenze minuscole diventano significative: per questo il report "
       "guarda sempre anche <b>quanto è grande</b> l'effetto, non solo il p-value.")
H2("3.8 Regressione")
teoria("regressione lineare",
       "Una <b>regressione</b> spiega una variabile y (per esempio la variazione annua degli arrivi) con una combinazione "
       "lineare di altre variabili x (le variazioni dei mesi precedenti, le ricerche Google):<br/>"
       "<b>y = a + b<sub>1</sub>x<sub>1</sub> + b<sub>2</sub>x<sub>2</sub> + ... + errore</b><br/>"
       "I coefficienti a, b si scelgono in modo che gli errori siano più piccoli possibile. Con i <b>minimi quadrati</b> si "
       "minimizza la somma degli errori al quadrato; con la <b>regressione di Huber</b> (capitolo 16) gli errori grandi "
       "pesano meno, così pochi mesi eccezionali non deformano la retta.")
H2("3.9 Dentro e fuori campione")
P("Un modello si valuta bene solo su dati che <b>non ha visto</b> durante la stima. Se si misura l'errore sugli stessi dati "
  "usati per stimarlo (\"dentro il campione\") si è troppo ottimisti: un modello molto flessibile può imparare a memoria "
  "anche il rumore (<b>overfitting</b>) e poi sbagliare sui casi nuovi. Per questo il nowcasting (capitolo 16) misura "
  "l'errore solo su mesi successivi a quelli usati per stimare il modello (\"fuori campione\").")
inbreve("Serie storica = una misura nel tempo. La variazione annua logaritmica toglie la stagionalità e porta tutte le fonti "
        "nella stessa unità. Spearman confronta classifiche. Errore standard e intervallo di confidenza misurano "
        "l'incertezza; il p-value dice se un effetto è distinguibile dal caso.")

# ================================================================ 4 organizzazione
H1("4. Organizzazione del progetto (script 0 e 19)")
P("Il progetto è organizzato in quattro cartelle. Gli script sono numerati nell'ordine in cui vanno eseguiti, così chi "
  "riprende il lavoro sa sempre da dove partire.")
codice("ZZ_TURISM/\n"
       "  data/raw/          dati scaricati, mai modificati (ISTAT, Reddit, Google Trends, Wikipedia)\n"
       "  data/processed/    dati puliti (script 1-6) e file di lavoro (script 7)\n"
       "  data/llm/          classificazione con Qwen: file per Kaggle, risultati, annotazioni a mano\n"
       "  script/            script_0 ... script_19\n"
       "  output/            tabelle (.csv), grafici (.png), riepiloghi (*_risultati.txt)\n"
       "  docs/              questo report, la presentazione, la guida per Kaggle")
scheda("script_0_comune.py",
       "Modulo condiviso, non si lancia da solo: lo importano gli altri script. Definisce i percorsi delle cartelle (così "
       "ogni script funziona da qualunque cartella venga lanciato), i colori dei grafici, i nomi brevi delle regioni e la "
       "classe <i>Registro</i>, che stampa a video i risultati e li salva anche in un file di testo.",
       "-", "crea le cartelle di output se mancano")
scheda("script_19_esegui_tutto.py",
       "Esegue gli script nell'ordine giusto e si ferma al primo errore. Con <i>--dati</i> riesegue anche la preparazione "
       "dei dati.", "-", "tutti gli output del progetto")
codice("python script_19_esegui_tutto.py           analisi e report: script 7-9 e 11-18 (circa 6 minuti)\n"
       "python script_19_esegui_tutto.py --dati    anche la preparazione dei dati: script 1, 3, 4, 6")
P("Non vengono eseguiti in automatico: lo script 2 (si incolla nella console del browser), lo script 4 nella fase di "
  "download (serve la rete) e lo script 10 (gira su una GPU di Kaggle; il suo risultato è già salvato in data/llm).")

# ================================================================ 5 ISTAT
H1("5. Il dato ufficiale: ISTAT (script 1)")
scheda("script_1_istat.py", "Controlla la coerenza del file ISTAT, tiene le serie che servono, unisce il Trentino-Alto Adige, "
       "calcola permanenza media e variazione annua degli arrivi (la grandezza da stimare in tutto il progetto).",
       "data/raw/istat/istat_movimento_clienti_mensile.csv",
       "data/processed/istat_target.csv, output/controlli/istat_controlli.txt")
H2("5.1 Com'è fatto il dataset")
P(f"Il file viene da IstatData, la banca dati dell'ISTAT, tavola <i>Movimento dei clienti negli esercizi ricettivi</i>, "
  f"frequenza mensile. Ha {mig(N_IST_RAW)} righe dal 2008 al 2025. È in formato <b>SDMX</b>, lo standard internazionale "
  f"per lo scambio di dati statistici: ogni riga contiene <b>un solo numero</b> (colonna OBS_VALUE) e tutte le colonne che "
  f"servono a capire che cosa sia. Le colonne utili sono:")
tabella([["REF_AREA", "territorio (codice NUTS)", "ITE1 = Toscana, ITD1 = Bolzano, ITD2 = Trento"],
         ["DATA_TYPE", "che cosa si conta", "AR = arrivi (clienti), NI = presenze (notti)"],
         ["TYPE_ACCOMMODATION", "tipo di struttura", "HOTELLIKE = alberghi, OTHER = extralberghiero, ALL = totale"],
         ["COUNTRY_RES_GUESTS", "residenza dei clienti", "IT = Italia, WRL_X_ITA = estero, WORLD = totale"],
         ["TIME_PERIOD", "mese", "2024-07"], ["OBS_VALUE", "il numero", "1181400"]],
        ["Colonna", "Significato", "Valori"], [2.4, 2.4, 5])
mini(IST_RAW, "Righe vere del file grezzo: arrivi in Toscana, luglio 2024, per struttura e residenza", [1, 1, 1.6, 1.6, 1.1, 1.2])
P("Si vede la logica a \"cubo\": per lo stesso mese e la stessa regione ci sono righe per ogni combinazione di struttura "
  "e residenza, compresi i totali.")
H2("5.2 Che cosa fa lo script, passo passo")
elenco(["<b>Lettura</b> delle sole colonne utili.",
        "<b>Controllo degli stati speciali</b>: una sola osservazione ha un segno di stato (un valore mancante per la Calabria "
        "nell'aprile 2020, extralberghiero, stranieri), che non tocca i totali usati.",
        "<b>Controllo di coerenza 1</b>: italiani + stranieri = totale. Si fa per 15.120 combinazioni (dal 2016, quando c'è "
        "anche il totale WORLD): <b>zero differenze</b>.",
        "<b>Controllo di coerenza 2</b>: alberghi + extralberghiero = totale, 23.184 combinazioni: <b>zero differenze</b>.",
        "<b>Selezione</b>: si tengono il totale delle strutture (ALL) e i due mercati (IT, WRL_X_ITA).",
        "<b>Trentino-Alto Adige</b>: ISTAT pubblica separatamente le province di Bolzano (ITD1) e Trento (ITD2); lo script le "
        "somma nel codice ITDA, così le regioni diventano 20 come nelle altre fonti.",
        "<b>Pivot</b>: arrivi e presenze diventano due colonne della stessa riga.",
        "<b>Controlli di plausibilità</b>: 40 serie complete, nessun valore mancante, nessun mese con zero arrivi, nessun "
        "mese con presenze inferiori agli arrivi (impossibile: chi arriva dorme almeno una notte).",
        "<b>Variabili derivate</b>: permanenza media = presenze / arrivi; variazione annua logaritmica di arrivi e presenze; "
        "etichetta del periodo (pre-COVID fino a febbraio 2020, COVID fino a marzo 2022, post-COVID dopo).",
        "<b>Esclusione del 2025</b>: i dati più recenti sono provvisori e verranno rivisti; si salva fino a dicembre 2024."], numeri=True)
H2("5.3 Il risultato")
mini(IST_T, "Righe vere di istat_target.csv (Toscana, luglio 2023 e 2024)", [1, 1.1, 1.1, 1.1, 1.1, 1.2, 1.1])
P("A luglio 2024 la Toscana ha accolto 774.620 turisti italiani, rimasti in media 4,5 notti: circa il 9% in meno di "
  "luglio 2023 (variazione annua -0,088). La colonna <i>yoy_arrivi</i> (year-over-year, \"anno su anno\") è il "
  "<b>target</b>, cioè la grandezza che il nowcasting cercherà di stimare.")
inbreve("Il dato ISTAT è internamente coerente al 100%. Dopo lo script 1 è un panel di 40 serie mensili (20 regioni x 2 "
        "mercati) con arrivi, presenze, permanenza media e variazione annua.")

# ================================================================ 6 Trends
H1("6. Google Trends (script 2 e 3)")
scheda("script_2_trends_download.js e script_3_trends_unione.py",
       "Lo script 2 (JavaScript) si incolla nella console del browser su trends.google.com e scarica le serie; lo script 3 "
       "(Python) unisce i 20 file scaricati in una sola tabella e controlla che non manchi nulla.",
       "trends.google.com (script 2); data/raw/trends/trends_rep1.zip (script 3)",
       "20 file trends_ITxx_rep1.csv; data/processed/trends_rep1_all.csv")
H2("6.1 Che cosa misura Google Trends")
teoria("l'indice di Google Trends",
       "Google non pubblica il <b>numero</b> di ricerche. Pubblica un <b>indice da 0 a 100</b> costruito così:<br/>"
       "1. prende un <b>campione</b> delle ricerche fatte in un Paese e in un periodo;<br/>"
       "2. per ogni mese calcola la <b>quota</b> delle ricerche che riguardano l'argomento richiesto sul totale delle ricerche "
       "di quel Paese (così un Paese grande non vince solo perché è grande);<br/>"
       "3. <b>riscala</b> tutto in modo che il valore massimo <i>dentro quella richiesta</i> valga 100.<br/>"
       "Conseguenze: (a) l'indice è <b>relativo</b>: 50 vuol dire \"metà del picco\", non 50 ricerche; (b) richieste diverse "
       "hanno <b>scale diverse</b> e non si possono confrontare tra loro; (c) argomenti chiesti <b>nella stessa richiesta</b> "
       "(fino a 5) condividono la scala e si possono sommare; (d) poiché si basa su un campione, scaricando la stessa serie "
       "in giorni diversi si ottengono valori un po' diversi; (e) quando le ricerche sono troppo poche Google scrive 0.")
figura(SCH / "d04_trends_scala.png", "Figura 6.1 - Come nasce l'indice 0-100 (numeri inventati).", max_alt=5.5 * cm)
H2("6.2 Che cosa si è scaricato")
elenco(["<b>Argomenti, non parole</b>: si usano gli <i>argomenti</i> di Google (codici come /m/02kx3 per Firenze), che "
        "raccolgono tutte le ricerche sulla stessa entità in qualunque lingua: \"Firenze\", \"Florenz\", \"Florence\" contano "
        "insieme. La funzione <i>risolvi()</i> dello script 2 trova il codice per ogni nome e permette di correggere a mano "
        "i casi sbagliati (per esempio Marche, che altrimenti verrebbe confuso con il marchio).",
        "<b>5 mete per regione</b>: la regione stessa e 4 destinazioni principali (per la Toscana: Toscana, Firenze, Pisa, "
        "Siena, Isola d'Elba), tutte nella stessa richiesta.",
        "<b>6 Paesi</b>: Italia per il mercato domestico; Germania, Regno Unito, Stati Uniti, Francia e Spagna per l'estero.",
        "<b>3 categorie</b> di Google: Hotel e alloggi (179), Viaggi aerei (203), Destinazioni turistiche (208). La categoria "
        "restringe le ricerche a quelle con intento di viaggio.",
        "<b>Periodo</b> 2011-2025, mensile; una pausa casuale di 7-13 secondi tra le richieste per non essere bloccati."])
figura(SCH / "s3_trends.png", "Figura 6.2 - Da 5 mete x 6 Paesi x 3 categorie alla serie usata nei modelli.", max_alt=8 * cm)
P("In totale: 20 regioni x 6 Paesi x 3 categorie = <b>360 serie</b>, ognuna fatta di 5 argomenti.")
H2("6.3 Il dataset e la serie usata")
mini(TR_EX, "Righe vere di trends_rep1_all.csv: Toscana, ricerche di hotel dalla Germania, luglio 2023 e 2024", [0.9, 0.6, 0.6, 0.8, 1.4, 1.1, 0.8])
P("Lo script 7 <b>somma i 5 argomenti</b> (stessa richiesta = stessa scala): per luglio 2024 37 + 33 + 2 + 15 + 2 = 89, "
  "per luglio 2023 83. Poi calcola la variazione annua log(1 + 89) - log(1 + 83) = <b>+0,069</b>, circa +7%. Si confronta "
  "sempre una serie con se stessa nel tempo, così la scala arbitraria si semplifica nel rapporto.")
P("<b>Serie utilizzabile</b>: una serie con molti zeri non contiene informazione (Google ha messo 0 perché le ricerche "
  "erano troppo poche). Si tiene una serie se ha <b>al massimo il 20% di mesi a zero</b>: risultano utilizzabili 265 serie "
  "su 360. Nel nowcasting questa scelta si rifà ogni mese usando solo i dati fino a quel mese (capitolo 16).")
inbreve("Google Trends è un indice relativo 0-100 calcolato su un campione: utile per confrontare una serie con se stessa nel "
        "tempo (variazione annua), non per confrontare regioni tra loro.")

# ================================================================ 7 Wikipedia
H1("7. Wikipedia (script 4)")
scheda("script_4_wikipedia.py",
       "Trova i titoli delle pagine nelle 5 lingue, scarica le visite mensili e le aggrega per regione e lingua. Ha tre fasi: "
       "<i>titoli</i>, <i>download</i> (servono la rete e un contatto nella variabile WIKI_CONTATTO, richiesto da Wikimedia "
       "per identificare chi scarica) e <i>aggrega</i>.",
       "API di Wikidata e di Wikimedia", "data/raw/wikipedia/wiki_titoli.csv, wiki_grezzo_v2.csv; data/processed/wiki_mensile_v2.csv")
H2("7.1 Dai titoli italiani alle altre lingue: Wikidata")
P("Le mete sono le stesse di Google Trends. Il titolo della pagina cambia da una lingua all'altra (Firenze, Florence, "
  "Florenz...) e scriverlo a mano porta errori. Lo script parte dal titolo italiano e interroga <b>Wikidata</b>, la banca "
  "dati che collega tra loro le pagine di tutte le Wikipedia: ogni concetto ha un codice (Q2044 = Firenze) e da lì si "
  "legge il titolo esatto in ogni lingua. Così si risolvono anche i <b>reindirizzamenti</b>: \"Alto Adige\" in italiano "
  "rimanda a \"Provincia autonoma di Bolzano\", e senza questa correzione le visite risulterebbero quasi nulle.")
mini(WT_EX, "Righe vere di wiki_titoli.csv per la Toscana", [1.3, 0.9, 1.2, 1.2, 1.2, 1.2])
H2("7.2 Le visite")
P(f"Le visite si scaricano dall'API Wikimedia <i>pageviews</i>, mese per mese da luglio 2015 (inizio della serie) a "
  f"dicembre 2025, per {N_TITOLI} mete x 5 lingue = {N_TITOLI * 5} pagine. Si contano solo le visite di <b>persone</b> "
  f"(agent = user), escludendo i robot dei motori di ricerca. La <b>lingua fa da proxy del mercato</b>: chi legge in "
  f"italiano è quasi sempre in Italia (mercato domestico); inglese, tedesco, francese e spagnolo rappresentano i "
  f"turisti stranieri. A differenza di Google Trends le visite sono <b>conteggi veri</b>, quindi si possono sommare tra "
  f"pagine e tra lingue.")
mini(WM_EX, "Righe vere di wiki_mensile_v2.csv: visite alle pagine della Toscana, luglio 2024", [0.9, 0.6, 1, 1, 1.2, 1.4, 1.2])
riquadro("Attenzione", "Wikipedia italiana è in <b>calo strutturale</b>: sempre più persone trovano le risposte direttamente "
         "su Google o con assistenti, senza aprire la pagina. La pagina della Toscana perde circa un terzo delle visite in "
         "un anno per motivi che non hanno a che fare con il turismo. Per questo, quando serve la crescita di Wikipedia, "
         "il progetto la confronta con la mediana delle altre regioni.", ARANCIO_CH, ARANCIO)
inbreve("Wikipedia dà conteggi veri di visite per regione e lingua; la lingua indica il mercato. È una misura di interesse "
        "generale, non solo turistico.")

# ================================================================ 8 Reddit
H1("8. Reddit r/ItalyTravel (script 5 e 6)")
scheda("script_6_reddit.py (con il modulo script_5_vader_turismo.py)",
       "Legge tutti i post e commenti del forum, li pulisce, segna bot e moderatori, trova le regioni citate e costruisce gli "
       "aggregati mensili per regione. Calcola anche un punteggio di sentiment a dizionario (VADER), usato nel progetto solo "
       "come termine di paragone per validare il modello linguistico.",
       "data/raw/reddit/r_ItalyTravel_posts.jsonl, r_ItalyTravel_comments.jsonl",
       "data/processed/reddit_testi.csv.gz (un testo per riga), reddit_mensile.csv, output/controlli/reddit_controlli.txt")
H2("8.1 Com'è fatto il dato grezzo: JSON Lines")
P("Reddit è un forum diviso in comunità (<i>subreddit</i>); r/ItalyTravel è quella dei viaggiatori in Italia, quasi tutta "
  "in inglese. Ci sono <b>post</b> (domande o racconti che aprono una discussione, detta <b>thread</b>) e <b>commenti</b> "
  "(le risposte). I file sono in formato <b>JSON Lines</b>: ogni riga è un oggetto JSON, cioè un insieme di coppie "
  "nome: valore. Un commento ha questa forma (testo inventato, campi veri):")
codice('{"id": "k3x9a1b", "author": "traveller_88", "created_utc": 1721044800,\n'
       ' "link_id": "t3_1e3f5gh", "score": 12, "distinguished": null,\n'
       ' "body": "We took the ferry from Positano to Amalfi, it was packed but the views were amazing."}')
P("<i>created_utc</i> è l'istante di pubblicazione in secondi dal 1° gennaio 1970 (1721044800 = 15 luglio 2024); "
  "<i>link_id</i> indica il thread a cui appartiene il commento (serve per gli errori standard del capitolo 13); "
  "<i>distinguished</i> = moderator segnala i messaggi ufficiali dei moderatori. Lo script legge i file <b>riga per riga</b>, "
  "senza caricarli tutti in memoria.")
H2("8.2 Pulizia, passo passo")
elenco(["<b>Testi rimossi o cancellati</b> ([removed], [deleted]): scartati (39.332). Di un post rimosso si tiene il titolo.",
        "<b>Pulizia del testo</b> con espressioni regolari: si tolgono i link (http...), i simboli di formattazione "
        "(asterischi, #, &gt;), si sostituiscono i codici HTML (&amp;amp; diventa &amp;), si riducono gli spazi.",
        "<b>Testi vuoti</b> (meno di 3 caratteri dopo la pulizia): scartati (1.284).",
        "<b>Data</b>: da created_utc si ricava il mese (AAAA-MM).",
        "<b>Bot</b>: autori come AutoModerator o con nome che finisce in \"bot\" (55.724 testi). <b>Moderatori</b>: messaggi "
        "distinti o fissati in alto (65.878). Restano nel file ma sono <b>esclusi</b> da tutti gli aggregati: non sono "
        "opinioni di viaggiatori."], numeri=True)
P("Risultato: 538.700 righe lette, <b>519.508 testi</b> tenuti (58.840 post e 460.668 commenti), da gennaio 2022 a "
  "dicembre 2025.")
H2("8.3 Quali regioni cita un testo: il dizionario")
P("Per ogni regione c'è un elenco di nomi in inglese e in italiano: la regione, le città, le mete (per la Campania: "
  "Campania, Naples, Napoli, Amalfi Coast, Positano, Sorrento, Capri, Pompeii...). Per ogni regione si costruisce "
  "un'<b>espressione regolare</b> che cerca uno qualunque di questi nomi come <b>parola intera</b> (il simbolo \\b indica "
  "il confine di parola: \"Como\" non viene trovato dentro \"comodo\"), senza distinguere maiuscole e minuscole. I nomi più "
  "lunghi si cercano per primi (\"Lake Como\" prima di \"Como\"). Un testo può citare più regioni. Il 39,7% dei testi cita "
  "almeno una regione (77,5% dei post, 34,9% dei commenti).")
esempio("il testo dell'esempio 8.1", "\"We took the ferry from <b>Positano</b> to <b>Amalfi</b>...\": trova Positano e Amalfi, "
        "entrambe nell'elenco della Campania, quindi regioni = ITF3.")
H2("8.4 Un primo punteggio di sentiment: VADER")
teoria("sentiment a dizionario (VADER)",
       "Il <b>sentiment</b> è l'atteggiamento espresso da un testo: positivo, neutro o negativo. Il metodo più semplice "
       "usa un <b>dizionario</b>: VADER (Valence Aware Dictionary and sEntiment Reasoner) contiene circa 7.500 parole con una "
       "<b>valenza</b> da -4 a +4 (amazing = +2,8, terrible = -2,5), più alcune regole: le negazioni invertono la valenza "
       "(\"not good\"), gli intensificatori la aumentano (\"very good\"), i punti esclamativi e le maiuscole la rafforzano. "
       "Le valenze del testo si sommano in x e si comprimono tra -1 e +1 con il punteggio <b>compound</b> = x / √(x<super>2</super> + 15). "
       "Lo script 5 adatta VADER ai testi di viaggio (parole come \"please\" o \"help\" diventano neutre; espressioni come "
       "\"tourist trap\" vengono aggiunte). Limite noto dei dizionari: sommano parole, quindi un testo lungo e gentile ma "
       "puramente informativo tende a risultare positivo. Per questo il sentiment del progetto è stimato con un modello "
       "linguistico (capitolo 11) e VADER resta solo un <b>termine di paragone</b> nella validazione.")
H2("8.5 Aggregati mensili per regione")
P("Per ogni regione e mese si contano i testi che la citano (esclusi bot e moderatori). Poiché la community è cresciuta "
  "enormemente (da 438 testi a gennaio 2022 a oltre 25.000 a luglio 2024, circa 58 volte), il numero di testi crescerebbe "
  "comunque. Si usa quindi la <b>quota</b>: testi che citano la regione / testi totali del mese.")
mini(RM_EX, "Righe vere di reddit_mensile.csv: Toscana e Molise, luglio 2024", [1, 1.1, 1, 1, 1.2, 1.1])
P("A luglio 2024 il 9,4% dei testi del forum cita la Toscana; il Molise compare in pochissimi testi.")
inbreve("Da 538.700 righe grezze a 519.508 testi puliti; il dizionario trova le regioni citate; gli aggregati mensili usano "
        "quote per neutralizzare la crescita del forum.")

# ================================================================ 9 EDA
H1("9. Analisi esplorativa (script 7)")
scheda("script_7_eda.py",
       "Armonizza le quattro fonti sulla chiave comune e verifica quanto ogni fonte digitale assomigli al dato ufficiale su "
       "quattro piani: andamento negli anni, stagionalità, distribuzione tra regioni, variazioni annue. Produce i file di "
       "lavoro usati da tutti i modelli.",
       "data/processed/istat_target.csv, trends_rep1_all.csv, wiki_mensile_v2.csv, reddit_mensile.csv",
       "data/processed/istat.csv, trends.csv, wiki.csv, reddit.csv; output/eda*.png e .csv")
H2("9.1 Armonizzazione: la chiave comune")
figura(SCH / "s2_chiave.png", "Figura 9.1 - Le quattro fonti sulla chiave comune regione x mercato x mese.", max_alt=7.5 * cm)
elenco(["<b>ISTAT</b>: dal 2011 al 2024, come Google Trends.",
        "<b>Google Trends</b>: somma dei 5 argomenti per regione, Paese, categoria e mese; quota di mesi a zero e flag "
        "<i>usable</i>; variazione annua log(1 + G<sub>t</sub>) - log(1 + G<sub>t-12</sub>).",
        "<b>Wikipedia</b>: visite sommate per regione e mercato (domestico = it; estero = en + de + fr + es); variazione annua.",
        "<b>Reddit</b>: quota di testi del mese che citano la regione; variazione annua (solo mercato estero)."])
H2("9.2 Copertura di Google Trends")
figura(O / "eda1_qualita_trends.png", "Figura 9.2 - Quota di serie Trends utilizzabili per Paese e categoria, e per regione.", max_alt=8 * cm)
P("Tutte le serie italiane sono utilizzabili; per i mercati esteri la copertura scende (Spagna 50-60%) e le regioni piccole "
  "(Molise, Marche, Abruzzo) hanno spesso volumi sotto la soglia di Google.")
H2("9.3 Dinamica 2016-2024: numeri indice")
teoria("numero indice",
       "Per confrontare l'andamento di grandezze con unità diverse (arrivi, indice Trends, visite) si dividono tutti i valori "
       "per quello di un anno di riferimento e si moltiplica per 100: <b>indice<sub>anno</sub> = 100 · valore<sub>anno</sub> / "
       "valore<sub>2019</sub></b>. 2019 = 100 è l'ultimo anno prima del COVID; 80 vuol dire \"20% sotto il 2019\". Per Trends, "
       "che non si può sommare tra regioni, ogni serie si indicizza al proprio 2019 e poi si prende la mediana tra le serie.")
figura(O / "eda2_dinamica.png", "Figura 9.3 - Indice annuo (2019 = 100) di arrivi ISTAT e fonti digitali, per mercato.", max_alt=7.5 * cm)
P("Google Trends segue il crollo del 2020 e la ripresa, soprattutto per il mercato estero (indice 114 sia per ISTAT sia per "
  "Trends nel 2024); Wikipedia italiana scende dal 2021 mentre gli arrivi risalgono.")
H2("9.4 Stagionalità: i profili mensili")
teoria("profilo stagionale",
       "Il <b>profilo stagionale</b> di una serie è la quota di ogni mese sul totale dell'anno (media 2023-2024): 12 numeri "
       "che sommano a 1. Per esempio, se agosto vale 0,15 vuol dire che il 15% degli arrivi dell'anno avviene in agosto. "
       "Esprimendo tutto in quote si possono confrontare fonti con unità diverse. Per ogni regione si calcola la correlazione "
       "di Pearson tra i 12 valori del profilo ISTAT e i 12 della fonte digitale: vicino a 1 = la fonte ha la stessa forma "
       "stagionale.")
s_ = STAG.groupby(["mercato", "fonte"]).r.agg(["median", "min", "max"]).reset_index()
tabella([[r.mercato, r.fonte, f(r["median"]), f(r["min"]), f(r["max"])] for _, r in s_.iterrows()],
        ["Mercato", "Fonte", "Mediana tra regioni", "Minimo", "Massimo"], [1.5, 3, 1.4, 1.2, 1.2])
figura(O / "eda3_stagionalita_esempi.png", "Figura 9.4 - Esempi di profili stagionali: ISTAT e fonti digitali.", max_alt=6 * cm)
P("Google Trends riproduce molto bene la stagionalità domestica (mediana fino a 0,94); per il mercato estero funzionano "
  "Trends, Wikipedia e Reddit. Wikipedia italiana non segue la stagionalità degli italiani.")
H2("9.5 Distribuzione tra regioni")
P("Si calcola la quota di ogni regione sul totale 2023-2024 (di arrivi, di visite, di menzioni) e si confrontano le "
  "classifiche con la correlazione di Spearman.")
figura(O / "eda4_territorio.png", "Figura 9.5 - Quote regionali 2023-2024: fonti digitali e arrivi ISTAT.", max_alt=6.5 * cm)
P("Le quote di attenzione ordinano le regioni quasi come gli arrivi (Spearman 0,91 per Wikipedia estera, 0,90 per Reddit, "
  "0,67 per Wikipedia italiana). Reddit parla soprattutto di città d'arte e coste, poco di montagna.")
H2("9.6 Variazioni annue: il test più difficile")
P("Qui si correlano, mese per mese e regione per regione, la variazione annua degli arrivi ISTAT e quella della fonte "
  "digitale, separando quattro periodi.")
y_ = YOY.pivot_table(index=["mercato", "fonte"], columns="periodo", values="r", sort=False)
y_ = y_[[c for c in ["2012-2019 (normale)", "2020-2021 (COVID)", "2022 (ripresa)", "2023-2024 (normale)"] if c in y_.columns]]
tabella([[i[0], i[1]] + ["-" if pd.isna(v) else f(v) for v in r] for i, r in y_.iterrows()],
        ["Mercato", "Fonte", "2012-2019", "2020-2021 COVID", "2022 ripresa", "2023-2024"], [1.4, 2.8, 1.3, 1.5, 1.4, 1.3])
inbreve("Le fonti digitali riproducono bene livelli, geografia e stagionalità. Le loro variazioni annue sono molto correlate "
        "con quelle ISTAT durante il COVID (fino a 0,85) e nella ripresa (fino a 0,78), ma solo intorno a 0,2 negli anni "
        "normali: seguono i grandi shock, poco le oscillazioni ordinarie.")

# ================================================================ 10 topic model
H1("10. Di cosa si parla: il topic model (script 8)")
scheda("script_8_topic_modeling.py",
       "Scopre in modo automatico i temi di discussione del forum (treni, cibo, biglietti...) e assegna a ogni testo il suo "
       "tema principale. I temi servono poi a capire se il tono cambia perché cambia l'argomento (capitolo 12).",
       "data/processed/reddit_testi.csv.gz", "output/tm_*.csv e tm*.png, output/tm_testi.csv.gz (tema di ogni testo)")
H2("10.1 Dal testo ai numeri: il modello \"bag of words\"")
P("Un computer non capisce le frasi: per analizzarle bisogna trasformarle in numeri. Il modo più semplice è il "
  "<b>sacco di parole</b> (bag of words): si ignora l'ordine e si conta quante volte compare ogni parola. Ogni testo "
  "diventa una riga di una grande tabella <b>testi x parole</b> (matrice documento-termine). Prima di contare:")
elenco(["<b>tokenizzazione</b>: il testo si spezza in parole (token); si tengono solo parole di almeno 3 lettere;",
        "<b>stop word</b>: si tolgono le parole che non portano significato (the, and, is...) e quelle generiche del forum "
        "(trip, travel, thanks, recommend...);",
        "<b>nomi di luogo</b>: si tolgono anche tutti i nomi di regioni, città e mete, così i temi descrivono <i>di cosa</i> si "
        "parla (treni, cibo) e non <i>dove</i>;",
        "<b>bigrammi</b>: oltre alle parole singole si contano le coppie di parole vicine (\"train station\", \"high speed\");",
        "<b>filtri di frequenza</b>: si ignorano le parole troppo rare (in meno di 60 testi) e quelle troppo comuni (in più "
        "del 25% dei testi); si tengono al massimo 15.000 termini."])
teoria("TF-IDF",
       "Contare non basta: una parola frequente in tutti i testi (\"day\") distingue poco, una parola frequente in un testo "
       "ma rara nel corpus (\"ferry\") dice molto di quel testo. Il peso <b>TF-IDF</b> combina le due cose:<br/>"
       "<b>tf-idf(t, d) = tf(t, d) · idf(t)</b><br/>"
       "• <b>tf</b> (term frequency) = quante volte la parola t compare nel testo d; si usa 1 + log(conteggio), così 10 "
       "ripetizioni non pesano 10 volte una;<br/>"
       "• <b>idf</b> (inverse document frequency) = log((1 + N) / (1 + n<sub>t</sub>)) + 1, dove N è il numero di testi e "
       "n<sub>t</sub> quelli che contengono t: alto per le parole rare;<br/>"
       "• infine ogni riga si divide per la sua lunghezza (norma euclidea), così testi lunghi e corti sono confrontabili.")
esempio("tre testi minuscoli",
        "A = \"train ticket train\", B = \"ticket museum\", C = \"museum pizza\". N = 3. \"train\" compare solo in A: "
        "idf = log(4/2) + 1 = 1,69; tf in A = 1 + log 2 = 1,69; peso grezzo 2,86. \"ticket\" compare in A e B: idf = "
        "log(4/3) + 1 = 1,29; in A pesa 1,29. Dopo la normalizzazione, in A \"train\" pesa 0,91 e \"ticket\" 0,41: il testo A "
        "parla soprattutto di treni.")
H2("10.2 Dai numeri ai temi: NMF")
teoria("Non-negative Matrix Factorization (NMF)",
       "La matrice X (testi x parole, pesi TF-IDF, tutti ≥ 0) si approssima con il prodotto di due matrici più piccole, "
       "anch'esse con soli valori ≥ 0:<br/><b>X ≈ W · H</b><br/>"
       "• <b>H</b> (temi x parole): ogni riga è un tema, cioè un elenco di parole con un peso; le parole con i pesi più alti "
       "descrivono il tema;<br/>"
       "• <b>W</b> (testi x temi): quanto ogni testo appartiene a ogni tema.<br/>"
       "W e H si trovano minimizzando la distanza ||X - WH||<super>2</super> (la somma dei quadrati delle differenze) con un "
       "algoritmo iterativo. Il vincolo \"niente valori negativi\" è ciò che rende i temi leggibili: un testo è una "
       "<i>somma</i> di temi, non può \"togliere\" parole. Il numero di temi k va scelto prima.")
figura(SCH / "d05_nmf.png", "Figura 10.1 - Schema della NMF (valori illustrativi).", max_alt=5.5 * cm)
H2("10.3 Quanti temi: la coerenza UMass")
teoria("coerenza UMass",
       "Un tema è buono se le sue parole principali compaiono davvero <b>negli stessi testi</b>. Per ogni coppia di parole "
       "(w<sub>i</sub>, w<sub>j</sub>) tra le 10 più importanti di un tema si calcola log((D(w<sub>i</sub>, w<sub>j</sub>) + 1) "
       "/ D(w<sub>j</sub>)), dove D(w<sub>i</sub>, w<sub>j</sub>) è il numero di testi che contengono entrambe e D(w<sub>j</sub>) "
       "quelli che contengono w<sub>j</sub>. Si fa la media su tutte le coppie e tutti i temi. Il valore è negativo: <b>meno "
       "negativo = temi più coerenti</b>. Lo script prova k = 6, 8, 10, 12, 14 su 30.000 testi e sceglie il migliore.")
tabella([[int(k), f(v, 3)] for k, v in TMK.items()], ["Numero di temi k", "Coerenza UMass"], [1, 1])
P(f"Vince k = {int(TMK.idxmax())}. Il modello finale è stimato su 120.000 testi estratti a caso e poi applicato a tutti; "
  f"ogni testo riceve il tema con il peso più alto in W (409.116 testi hanno almeno una parola del vocabolario).")
H2("10.4 I temi trovati")
tabella([[r.nome, r.parole] for r in TMP.itertuples()], ["Tema (nome dato leggendo le parole)", "Parole principali"], [2.2, 6])
tabella([[r.nome_tema, pc(r.quota, 1), f(TMC.get(r.nome_tema, float("nan")))] for _, r in TM.iterrows()],
        ["Tema", "Quota dei testi", "Correlazione con gli arrivi stranieri (mese)"], [3, 1.4, 2.4], colore=ARANCIO)
figura(O / "tm1_parole.png", "Figura 10.2 - Parole principali di ogni tema.", max_alt=7 * cm)
P("I nomi dei temi sono scelti da chi legge le parole: l'algoritmo trova solo gruppi di parole. Durante l'anno la quota di "
  "<i>Biglietti e prenotazioni</i> sale con gli arrivi stranieri, quella di <i>Itinerari e alloggio</i> scende: d'inverno si "
  "pianifica, d'estate si risolvono problemi pratici.")
inbreve("TF-IDF trasforma i testi in numeri, la NMF li scompone in 6 temi coerenti. Il tema di ogni testo viene usato nel "
        "capitolo 12 per capire se il tono cambia perché cambia l'argomento.")

# ================================================================ 11 LLM
H1("11. Leggere ogni testo con un modello linguistico (script 9 e 10)")
scheda("script_9_qwen_preparazione.py e script_10_qwen_kaggle.py",
       "Lo script 9 (sul PC) prepara i testi da classificare e il campione da annotare a mano. Lo script 10 (su Kaggle, con "
       "GPU) fa leggere ogni testo al modello Qwen 2.5 7B e salva la risposta in formato strutturato.",
       "data/processed/reddit_testi.csv.gz (script 9); data/llm/kaggle/ (script 10)",
       "data/llm/kaggle/completo.csv e gold_testi.csv, gold_da_annotare.csv, meta_testi.csv; data/llm/qwen_completo.csv e "
       "qwen_completo_meta.json")
H2("11.1 Che cos'è un modello linguistico")
teoria("Large Language Model (LLM)",
       "Un modello linguistico è una rete neurale addestrata su enormi quantità di testo a fare una cosa sola: <b>prevedere "
       "il pezzo di testo successivo</b>. Il testo viene spezzato in <b>token</b> (pezzi di parola: \"travelling\" può "
       "diventare \"travel\" + \"ling\"); dato l'inizio di un testo, il modello calcola la probabilità di ogni possibile token "
       "successivo, ne sceglie uno, lo aggiunge e ripete. Per prevedere bene deve aver imparato grammatica, significato, "
       "contesto, ironia.<br/>"
       "L'architettura si chiama <b>transformer</b>: il suo meccanismo centrale (<i>attention</i>) permette a ogni parola di "
       "\"guardare\" tutte le altre parole del testo, così \"not\" all'inizio di una frase può cambiare il senso di \"good\" "
       "alla fine. I modelli <b>Instruct</b> sono stati addestrati in più a seguire istruzioni scritte in linguaggio naturale. "
       "I <b>parametri</b> sono i numeri imparati durante l'addestramento: Qwen 2.5 7B ne ha 7 miliardi.")
P("Rispetto a un dizionario come VADER, un LLM legge il testo <b>intero</b> e ne capisce il senso: sa che una risposta "
  "lunga e gentile sugli orari dei treni è informativa (neutra), che \"no issues at all\" è positivo, che una frase "
  "ironica va letta al contrario. In più può rispondere a più domande insieme: tipo di testo, regione di cui si parla, "
  "giudizio su singoli aspetti.")
H2("11.2 Perché un modello open-weight, e come lo si fa girare")
elenco(["<b>Open-weight</b>: i parametri di Qwen 2.5 (Alibaba) sono pubblici, con licenza Apache 2.0. Chiunque può "
        "scaricare lo stesso modello e ottenere gli stessi risultati: è un requisito per la statistica ufficiale, che deve "
        "essere riproducibile. Con un modello a pagamento via API il modello può cambiare senza preavviso.",
        "<b>Quantizzazione AWQ a 4 bit</b>: ogni parametro normalmente occupa 16 bit; 7 miliardi x 2 byte = 14 GB, troppi "
        "per una GPU gratuita. La quantizzazione rappresenta i parametri con 4 bit (circa 5 GB in tutto) perdendo pochissima "
        "precisione; AWQ (Activation-aware Weight Quantization) protegge i parametri più importanti.",
        f"<b>GPU</b>: la scheda grafica fa in parallelo i miliardi di moltiplicazioni necessarie. Si è usato Kaggle (servizio "
        f"gratuito di Google) con 2 GPU {META.get('gpu', 'Tesla T4')} da 16 GB.",
        f"<b>vLLM</b> (versione {META.get('vllm', '')}): libreria che fa girare il modello in modo efficiente, elaborando "
        f"molti testi insieme. I 128.002 testi hanno richiesto circa 6 ore e mezza.",
        "<b>Temperatura 0 e seme fisso</b>: la temperatura regola quanto il modello \"azzarda\" token poco probabili; a 0 sceglie "
        "sempre il più probabile, quindi la stessa domanda dà sempre la stessa risposta."])
H2("11.3 Quali testi: lo script 9")
P(f"Si classificano tutti i testi del 2023-2024 che citano almeno una regione, esclusi bot e moderatori: <b>{mig(SRG.testi)}</b>. "
  f"I testi oltre 6.000 caratteri (111, lo 0,1%) vengono tagliati. Per ogni testo il file per Kaggle contiene solo l'id, "
  f"le regioni trovate dal dizionario e il testo.")
P("Lo script 9 estrae anche il <b>campione da annotare a mano</b>: 15 testi per regione tra quelli che citano una sola "
  "regione (così anche la regione si giudica facilmente), con probabilità doppia per i testi lunghi (sono i casi più "
  "difficili), in ordine casuale. Il file per l'annotazione non contiene nessun giudizio automatico: si annota "
  f"<b>alla cieca</b>. Ne sono stati annotati {int(QW.n)}. Lo script non sovrascrive mai questo file.")
H2("11.4 Che cosa si chiede al modello: prompt e schema")
P("Il <b>prompt</b> è l'istruzione scritta data al modello. Riassunto delle regole (il testo completo è in "
  "data/llm/qwen_completo_meta.json):")
elenco(["<b>sentiment</b>: l'atteggiamento di chi scrive verso il viaggio o i luoghi. I testi informativi (orari, logistica) "
        "sono neutri anche se lunghi e gentili; le formule di cortesia (\"thanks\", \"hope this helps\") non rendono un testo "
        "positivo; frustrazione, lamentele, avvertimenti sono negativi; si giudica il testo intero, con negazioni e ironia;",
        "<b>score</b>: da -2 (molto negativo) a +2 (molto positivo), coerente con il sentiment;",
        "<b>text_type</b>: domanda, consiglio, racconto di esperienza, altro;",
        "<b>aspects</b>: per folla, prezzi, trasporti, cibo, alloggio, luoghi: giudizio positivo, negativo o non espresso;",
        "<b>main_region</b>: la regione di cui il testo <i>parla davvero</i>, scelta tra le <b>regioni candidate</b> trovate dal "
        "dizionario; \"several\" se il testo parla di più regioni allo stesso modo (un itinerario); \"none\" se le regioni sono "
        "citate solo di passaggio (\"domani parto per Venezia\"). Il dizionario conosce la geografia (Matera è in Basilicata), "
        "il modello capisce il contenuto."])
teoria("decodifica guidata (output vincolato)",
       "Un LLM libero potrebbe rispondere con una frase, dimenticare un campo o inventare un valore (\"mixed\"). Con la "
       "<b>decodifica guidata</b> si fornisce uno <b>schema JSON</b> che elenca i campi obbligatori e i valori ammessi; a ogni "
       "passo vLLM esclude i token che porterebbero a una risposta non conforme. Così <b>ogni</b> risposta è un JSON valido e "
       "leggibile: su 128.002 testi, zero errori di lettura e coerenza totale tra sentiment e score.")
codice('{"text_type": "experience_report",\n'
       ' "aspects": {"crowds": "negative", "prices": "not_mentioned", "transport": "not_mentioned",\n'
       '             "food": "not_mentioned", "accommodation": "not_mentioned", "sights": "positive"},\n'
       ' "sentiment": "positive", "score": 1, "main_region": "Campania"}')
P("Questa è la risposta al testo inventato dell'esempio 8.1 (\"...it was packed but the views were amazing\"): folla "
  "negativa, luoghi positivi, giudizio complessivo positivo. Le risposte sono salvate in colonne:")
mini(QC, "Prime righe vere di qwen_completo.csv (senza il testo)", [1, 1.3, 0.9, 0.5, 1.1, 1, 1, 1, 1, 1.1, 1])
inbreve("Qwen 2.5 7B, open-weight e quantizzato, ha letto 128.002 testi su GPU gratuite. Il prompt fissa regole chiare e la "
        "decodifica guidata garantisce risposte sempre valide; il dizionario fornisce le regioni candidate.")

# ================================================================ 12 validazione e risultati
H1("12. Il sentiment: validazione e risultati (script 12 e 13)")
scheda("script_12_sentiment_qwen.py e script_13_testi_classificati.py",
       "Lo script 12 controlla la qualità delle risposte, misura l'accuratezza di Qwen sui testi annotati a mano (con due "
       "metodi di paragone), poi studia il tono durante l'anno, gli aspetti e i temi. Lo script 13 esporta i testi "
       "classificati in un Excel leggibile.",
       "data/llm/qwen_completo.csv, meta_testi.csv, gold_da_annotare.csv; data/processed/istat.csv; output/tm_testi.csv.gz",
       "output/snt_*.csv e snt*.png; output/llm/qwen_testi_classificati.xlsx")
H2("12.1 Come si misura l'accuratezza")
P(f"Sui {int(QW.n)} testi annotati a mano si confronta la risposta del modello con l'annotazione (la \"verità\"). Per avere "
  "un termine di paragone si applicano agli stessi testi due metodi standard: il dizionario <b>VADER</b> (capitolo 8.4) e "
  "<b>RoBERTa</b>, un modello transformer più piccolo addestrato apposta per classificare il sentiment di tweet.")
figura(SCH / "d06_confusione.png", "Figura 12.1 - Matrici di confusione: righe = annotazione a mano, colonne = metodo.", max_alt=6 * cm)
teoria("matrice di confusione, accuratezza, kappa di Cohen, F1",
       "La <b>matrice di confusione</b> incrocia la verità (righe) con la previsione (colonne): sulla diagonale i casi giusti, "
       "fuori diagonale gli errori e il loro tipo.<br/>"
       "• <b>Accuratezza</b> = casi giusti / totale.<br/>"
       "• <b>Kappa di Cohen</b> = (p<sub>o</sub> - p<sub>e</sub>) / (1 - p<sub>e</sub>): p<sub>o</sub> è l'accordo osservato "
       "(l'accuratezza), p<sub>e</sub> l'accordo che si otterrebbe <i>per caso</i> rispondendo a caso con le stesse frequenze. "
       "Kappa = 0 vuol dire \"non meglio del caso\", 1 accordo perfetto; sopra 0,6 si considera buono.<br/>"
       "• <b>F1</b> di una classe = media armonica di precisione (dei testi classificati \"negativi\", quanti lo sono davvero) "
       "e richiamo (dei testi davvero negativi, quanti sono stati trovati); l'<b>F1 macro</b> è la media sulle tre classi e "
       "punisce chi ignora le classi rare.")
cq = SCF[SCF.metodo == "Qwen 2.5 7B"].pivot_table(index="vero", columns="previsto", values="n", aggfunc="sum").fillna(0)
cq = cq.reindex(index=["negative", "neutral", "positive"], columns=["negative", "neutral", "positive"]).fillna(0)
_n = cq.values.sum()
_po = np.trace(cq.values) / _n
_pe = float((cq.sum(1).values * cq.sum(0).values).sum() / _n ** 2)
esempio("kappa di Qwen, a mano",
        f"Qwen indovina {int(np.trace(cq.values))} testi su {int(_n)}: p<sub>o</sub> = {f(_po, 3)}. Le annotazioni sono "
        f"{int(cq.sum(1)['negative'])} negative, {int(cq.sum(1)['neutral'])} neutre, {int(cq.sum(1)['positive'])} positive; "
        f"Qwen ne prevede {int(cq.sum(0)['negative'])}, {int(cq.sum(0)['neutral'])}, {int(cq.sum(0)['positive'])}. L'accordo "
        f"atteso per caso è p<sub>e</sub> = Σ (righe x colonne) / n<super>2</super> = {f(_pe, 3)}. Kappa = ({f(_po, 3)} - "
        f"{f(_pe, 3)}) / (1 - {f(_pe, 3)}) = <b>{f((_po - _pe) / (1 - _pe), 2)}</b>.")
teoria("intervallo di Wilson",
       "L'accuratezza su 43 testi è a sua volta una stima incerta. L'intervallo di <b>Wilson</b> è l'intervallo di confidenza "
       "consigliato per una proporzione p&#770; su campioni piccoli:<br/>"
       "<b>[ p&#770; + z<super>2</super>/2n ± z · √( p&#770;(1 - p&#770;)/n + z<super>2</super>/4n<super>2</super> ) ] / "
       "(1 + z<super>2</super>/n)</b>, con z = 1,96.<br/>"
       "A differenza della formula semplice p&#770; ± 1,96·√(p&#770;(1 - p&#770;)/n) non esce mai da [0, 1] e funziona anche "
       "quando p&#770; è vicino a 0 o 1.")
tabella([[n, f"{int(r.corretti)}/{int(r.n)}", pc(r.accuratezza, 1), f"{pc(r.ic_lo)} - {pc(r.ic_hi)}", f(r.kappa), f(r.F1_macro),
          pc(r.acc_testi_lunghi)] for n, r in SV.iterrows()],
        ["Metodo", "Corretti", "Accuratezza", "Intervallo 95% (Wilson)", "Kappa", "F1 macro", "Testi lunghi"],
        [2.4, 1, 1.2, 1.9, 0.9, 1, 1.1], colore=ARANCIO)
teoria("test di McNemar",
       "Per dire se Qwen è <i>davvero</i> migliore di un altro metodo non basta confrontare le accuratezze: sono misurate sugli "
       "<b>stessi</b> testi. Il test di McNemar guarda solo i testi su cui i due metodi <b>non sono d'accordo</b>: b = giusto "
       "solo per Qwen, c = giusto solo per l'altro. Se i metodi fossero equivalenti, b e c dovrebbero essere simili (come "
       "lanci di moneta). Con pochi casi si usa il test binomiale esatto: p-value = probabilità di uno squilibrio almeno "
       "così forte con una moneta equa.")
tabella([[r.confronto, int(r.giusto_solo_qwen), int(r.giusto_solo_altro), f(r.p_value, 4)] for r in SMC.itertuples()],
        ["Confronto", "Giusto solo Qwen (b)", "Giusto solo l'altro (c)", "p-value"], [3, 1.5, 1.5, 1], colore=ARANCIO)
vneu = SCF[(SCF.metodo == "VADER (dizionario)") & (SCF.vero == "neutral")]
P(f"Qwen è significativamente più accurato del dizionario (p = {f(p_qv, 3)}) ed è alla pari con RoBERTa (p = {f(p_qr, 2)}). "
  f"L'errore tipico del dizionario riguarda i testi informativi: dei {int(vneu.n.sum())} testi neutri ne classifica "
  f"{int(vneu[vneu.previsto == 'positive'].n.sum())} come positivi. A parità di accuratezza con RoBERTa, Qwen dà in più "
  f"tipo di testo, regione e aspetti, ed è questo che permette le analisi successive. La regione indicata da Qwen è "
  f"corretta nel {pc(SVR.qwen, 1)} dei casi (dizionario da solo: {pc(SVR.dizionario, 1)}).")
riquadro("Limite", f"{int(QW.n)} testi annotati da una sola persona: l'intervallo dell'accuratezza è largo circa ±12 punti. "
         "Bastano a distinguere differenze grandi (Qwen contro dizionario), non differenze piccole (Qwen contro RoBERTa).",
         ARANCIO_CH, ARANCIO)
H2("12.2 Che cosa dicono le risposte")
P(f"Su {mig(SRG.testi)} testi: 47,6% neutri, 37,5% positivi, 15,0% negativi. Tipi di testo: 38,7% consigli, 32,9% racconti "
  f"di esperienza, 24,8% domande. Sui {mig(SRG.una_regione)} testi che citano una sola regione il modello conferma la regione "
  f"del dizionario nel {pc(SRG.conferma, 1)} dei casi; in tutto {mig(SRG.solo_citata_tot)} testi citano le regioni solo di "
  f"passaggio e {mig(SRG.piu_regioni_tot)} parlano di più regioni.")
H2("12.3 Il tono nel corso dell'anno")
figura(O / "snt1_mesi.png", "Figura 12.2 - Sentiment medio mensile (linea) e arrivi stranieri ISTAT (barre), 2023-2024.", max_alt=7 * cm)
P(f"Per ogni mese dell'anno si calcola il punteggio medio dei testi e lo si confronta con gli arrivi stranieri medi dello "
  f"stesso mese. La correlazione di Pearson sui 12 mesi è <b>{f(r_mesi)}</b>: più turisti, tono più basso. Dall'inverno "
  f"(dicembre-marzo) all'estate (giugno-settembre) il punteggio medio passa da {f(SST.loc['inverno', 'punteggio'], 3)} a "
  f"{f(SST.loc['estate', 'punteggio'], 3)} e i testi negativi dal {pc(neg_w, 1)} al {pc(neg_s, 1)}. La differenza è "
  f"verificata con il <b>test t di Welch</b>, che confronta due medie senza supporre che i due gruppi abbiano la stessa "
  f"varianza: p &lt; 0,001.")
H2("12.4 Che cosa peggiora d'estate: gli aspetti")
teoria("test del chi-quadro su una tabella 2 x 2",
       "Per ogni aspetto si costruisce una tabella con due righe (inverno, estate) e due colonne (giudizi negativi, giudizi "
       "non negativi). Se la stagione non contasse, la quota di negativi sarebbe la stessa nelle due righe. Il <b>chi-quadro</b> "
       "somma, cella per cella, (osservato - atteso)<super>2</super> / atteso, dove \"atteso\" è il conteggio che ci si "
       "aspetterebbe con la stessa quota: più è grande, meno è plausibile che la differenza sia dovuta al caso.")
tabella([[i, pc(r.testi_che_lo_giudicano, 1), pc(r.negativi_inverno, 1), pc(r.negativi_estate, 1),
          f"{100 * r.differenza:+.1f}".replace(".", ","), "&lt; 0,001" if r.p_value < 0.001 else f(r.p_value, 2)] for i, r in SAS.iterrows()],
        ["Aspetto", "Testi che lo giudicano", "Negativi in inverno", "Negativi in estate", "Differenza (punti)", "p-value"],
        [1.6, 1.8, 1.6, 1.6, 1.6, 1.2], colore=ARANCIO)
figura(O / "snt2_aspetti.png", "Figura 12.3 - Giudizi negativi per aspetto, inverno contro estate.", max_alt=6.5 * cm)
P("Le quote sono calcolate solo sui testi che giudicano l'aspetto. Quando si parla di <b>folla</b> il giudizio è quasi "
  "sempre negativo in ogni stagione: d'estate se ne parla di più, non peggio. <b>Peggiorano davvero d'estate i giudizi su "
  "prezzi e alloggio</b>, poi trasporti e cibo.")
H2("12.5 Cambia l'argomento o il modo di parlarne? La scomposizione")
teoria("scomposizione composizione / interno (shift-share)",
       "Il punteggio medio di una stagione è la media dei punteggi dei temi pesata con la quota di ogni tema: "
       "m = Σ<sub>k</sub> q<sub>k</sub> · m<sub>k</sub>. La differenza estate - inverno si può scrivere esattamente come somma "
       "di due parti:<br/>"
       "<b>Δ = Σ<sub>k</sub> (q<sub>k</sub><super>E</super> - q<sub>k</sub><super>I</super>) · m<sub>k</sub><super>I</super> "
       "+ Σ<sub>k</sub> q<sub>k</sub><super>E</super> · (m<sub>k</sub><super>E</super> - m<sub>k</sub><super>I</super>)</b><br/>"
       "• <b>composizione</b> (prima somma): quanto cambierebbe il tono solo perché d'estate si parla di temi diversi, con il "
       "tono di ogni tema fermo all'inverno;<br/>"
       "• <b>effetto interno</b> (seconda somma): quanto cambia il tono <i>dentro</i> ogni tema.")
formula(f"differenza = composizione + interno:   {f(SDE.differenza, 3)} = {f(SDE.composizione, 3)} + ({f(SDE.interno, 3)})")
figura(O / "snt3_temi.png", "Figura 12.4 - Sentiment per tema in inverno e in estate.", max_alt=6.5 * cm)
P(f"L'effetto interno spiega il {pc(SDE.quota_interno)} del calo (più del 100% perché la composizione va leggermente nel "
  "verso opposto): il tono peggiora dentro ogni tema, mentre il cambio di argomenti quasi non conta.")
H2("12.6 Lo script 13: i testi in chiaro")
P("Lo script 13 produce <i>output/llm/qwen_testi_classificati.xlsx</i>: un foglio di istruzioni, un campione di testi con "
  "tutte le risposte del modello (tipo, sentiment, punteggio, regione, aspetti) e una selezione di esempi per ogni "
  "categoria. Serve a leggere con i propri occhi come il modello ha classificato i testi. Il file contiene testi di "
  "Reddit e non va pubblicato.")
inbreve(f"Qwen è accurato quanto il miglior metodo standard ({pc(QW.accuratezza)}) e molto più del dizionario. Il tono "
        f"peggiora quando arrivano i turisti (correlazione {f(r_mesi)}), dentro gli stessi temi, soprattutto su prezzi e "
        "alloggio.")

# ================================================================ 13 tono regionale
H1("13. Il tono di ogni regione (script 11)")
scheda("script_11_sentiment_regionale.py",
       "Stima con che tono i turisti stranieri parlano di ogni regione nel 2023-2024, tenendo conto della stagione, della "
       "dipendenza tra commenti dello stesso thread e del diverso numero di testi per regione. Il risultato è il pilastro "
       "Reputazione dell'indicatore (capitolo 14).",
       "data/processed/reddit_testi.csv.gz (thread di ogni testo), data/llm/qwen_completo.csv",
       "output/rep_regioni.csv, rep1_sentiment_regioni.png, rep2_volume.png, rep_risultati.txt")
P("L'idea più semplice sarebbe fare la media dei punteggi regione per regione. Questa media ha però tre problemi, che lo "
  "script risolve uno alla volta. Prima di tutto ogni testo va assegnato a una regione: quella scelta da Qwen; se il testo "
  "parla di più regioni conta per ciascuna; se le cita solo di passaggio è escluso.")
H2("13.1 Problema 1: la stagione")
P("Il tono cala d'estate (capitolo 12). Una regione di cui si parla soprattutto d'estate, come la Sardegna, sembrerebbe "
  "peggiore solo per il calendario. Si <b>destagionalizza</b>: a ogni testo si toglie il tono medio del suo mese e si "
  "rimette la media generale.")
formula("punteggio destagionalizzato = punteggio del testo - media del suo mese + media generale")
esempio("un testo di luglio", "Se a luglio 2024 la media del forum è 0,21, la media generale 0,29 e il testo vale +1, "
        "il punteggio destagionalizzato è 1 - 0,21 + 0,29 = 1,08: conta un po' di più, perché è positivo in un mese in cui "
        "il forum è meno positivo del solito.")
H2("13.2 Problema 2: i commenti dello stesso thread non sono indipendenti")
teoria("errore standard per cluster",
       "La formula se = s / √n (capitolo 3.6) vale se le osservazioni sono <b>indipendenti</b>. In un thread su un taxi "
       "truffaldino a Roma, 40 commenti saranno tutti negativi: non sono 40 opinioni indipendenti, ma quasi un unico "
       "episodio ripetuto. Trattarli come indipendenti rende l'errore standard troppo piccolo e la stima sembra più precisa "
       "di quanto sia.<br/>"
       "L'errore standard <b>per cluster</b> (qui: cluster = thread) somma prima gli scarti dentro ogni thread e poi tratta "
       "i thread come le unità indipendenti:<br/>"
       "<b>var = G/(G - 1) · Σ<sub>g</sub> ( Σ<sub>i∈g</sub> (x<sub>i</sub> - x&#772;) )<super>2</super> / n<super>2</super></b>, "
       "con G numero di thread (correzione CR1).<br/>"
       "L'<b>effetto del disegno</b> = (se per cluster / se ingenuo)<super>2</super> dice di quante volte la varianza sarebbe "
       "sottostimata ignorando i thread.")
tabella([[REP.loc[c, "regione"], mig(REP.loc[c, "n_testi"]), mig(REP.loc[c, "n_thread"]), f(REP.loc[c, "se_ingenuo"], 4),
          f(REP.loc[c, "se"], 4), f(REP.loc[c, "effetto_disegno"], 2)] for c in ["ITE4", "ITE1", "ITE2", "ITF2"]],
        ["Regione", "Testi", "Thread", "Errore standard ingenuo", "Errore standard per thread", "Effetto del disegno"],
        [1.5, 1, 1, 1.6, 1.6, 1.4], colore=ARANCIO)
P("Per le regioni molto discusse, con thread lunghi, la correzione conta molto; per il Molise quasi ogni thread ha un solo "
  "commento e la correzione è minima.")
H2("13.3 Problema 3: regioni con pochi testi - lo shrinkage bayesiano empirico")
P(f"Il Molise ha {mig(MOL.n_testi)} testi, il Lazio {mig(LAZ.n_testi)}. La media del Molise è molto più incerta: bastano pochi "
  "commenti entusiasti o arrabbiati per spostarla. Una classifica basata sulle medie semplici metterebbe spesso in cima o "
  "in fondo le regioni piccole, per puro caso. La soluzione è lo <b>shrinkage</b> (restringimento): avvicinare le stime "
  "incerte alla media generale, tanto più quanto sono incerte. Per capire da dove viene la formula serve un po' di "
  "statistica bayesiana.")
teoria("il ragionamento bayesiano",
       "Nella statistica <b>bayesiana</b> la probabilità misura quanto si è sicuri di qualcosa, e le conoscenze si aggiornano "
       "con i dati. Ci sono tre ingredienti:<br/>"
       "• la distribuzione <b>a priori</b>: che cosa si sa prima di guardare i dati della regione. Qui: \"le regioni hanno "
       "toni diversi, ma di solito intorno a una media μ, con una dispersione τ\";<br/>"
       "• la <b>verosimiglianza</b>: che cosa dicono i dati della regione. Qui: la media osservata y, con il suo errore "
       "standard se;<br/>"
       "• la distribuzione <b>a posteriori</b>: la sintesi delle due, cioè la stima finale.<br/>"
       "Quando sia l'a priori sia i dati hanno forma normale (a campana), la sintesi ha una forma semplicissima: la stima "
       "finale è una <b>media pesata</b> tra la media generale μ e la media della regione y, con pesi inversamente "
       "proporzionali alle rispettive varianze. Chi è più preciso pesa di più.")
formula("modello:  y<sub>r</sub> ~ N(θ<sub>r</sub>, se<sub>r</sub><super>2</super>),   θ<sub>r</sub> ~ N(μ, τ<super>2</super>)<br/>"
        "stima<sub>r</sub> = μ + (1 - B<sub>r</sub>) · (y<sub>r</sub> - μ),      B<sub>r</sub> = se<sub>r</sub><super>2</super> / "
        "(se<sub>r</sub><super>2</super> + τ<super>2</super>)")
P("θ<sub>r</sub> è il tono <i>vero</i> della regione r, che non si osserva; y<sub>r</sub> è la media dei suoi testi; "
  "1 - B<sub>r</sub> è il <b>peso dei dati</b>. Se se<sub>r</sub> è piccolo (tanti testi) B è quasi 0 e la stima resta y; se "
  "se<sub>r</sub> è grande (pochi testi) B cresce e la stima si avvicina a μ.")
teoria("perché \"empirico\": la stima di μ e τ",
       "In un'analisi bayesiana \"pura\" μ e τ andrebbero fissati in anticipo. Nel <b>Bayes empirico</b> si stimano <b>dai "
       "dati di tutte le regioni</b>: ogni regione \"prende in prestito\" informazione dalle altre. τ<super>2</super> è la "
       "varianza <i>vera</i> tra le regioni, al netto del rumore: si calcola con il metodo di <b>DerSimonian-Laird</b>, lo "
       "stesso delle meta-analisi mediche.<br/>"
       "1. si calcola la media pesata μ<sub>0</sub> = Σ w<sub>r</sub> y<sub>r</sub> / Σ w<sub>r</sub>, con w<sub>r</sub> = "
       "1/se<sub>r</sub><super>2</super>;<br/>"
       "2. si misura quanto le regioni si disperdono intorno a μ<sub>0</sub>: Q = Σ w<sub>r</sub> (y<sub>r</sub> - "
       "μ<sub>0</sub>)<super>2</super>. Se non ci fossero differenze vere, Q varrebbe in media R - 1 = 19 (solo rumore);<br/>"
       "3. l'eccesso di Q oltre 19 è la parte dovuta a differenze vere: τ<super>2</super> = max(0, (Q - 19) / (Σ w - "
       "Σ w<super>2</super>/Σ w));<br/>"
       "4. infine μ = media pesata con pesi 1/(se<sub>r</sub><super>2</super> + τ<super>2</super>).<br/>"
       "Un risultato classico (Stein, 1956) mostra che questa stima ha, in media, un errore complessivo più piccolo delle "
       "medie separate: è il motivo per cui si usa.")
esempio("il Molise, con i numeri veri",
        f"μ = {f(MU, 3)}, τ = {f(TAU, 3)}. Molise: y = {f(MOL.media, 3)}, se = {f(MOL.se, 3)}. "
        f"B = {f(MOL.se, 3)}<super>2</super> / ({f(MOL.se, 3)}<super>2</super> + {f(TAU, 3)}<super>2</super>) = "
        f"{f(1 - MOL.peso_dati, 3)}, peso dei dati = {f(MOL.peso_dati, 3)}. "
        f"Stima = {f(MU, 3)} + {f(MOL.peso_dati, 3)} x ({f(MOL.media, 3)} - {f(MU, 3)}) = <b>{f(MOL.shrink, 3)}</b>. "
        f"Il Lazio, con {mig(LAZ.n_thread)} thread, ha peso dei dati {f(LAZ.peso_dati, 3)}: la sua stima resta "
        f"praticamente la sua media ({f(LAZ.media, 3)} → {f(LAZ.shrink, 3)}).")
figura(SCH / "d07_bayes.png", "Figura 13.1 - Bayes empirico per il Molise: a priori (grigio), dati (arancio), stima finale (blu).", max_alt=6.5 * cm)
figura(SCH / "s5_shrinkage.png", "Figura 13.2 - Effetto dello shrinkage su quattro regioni: croce = media, punto = stima.", max_alt=6 * cm)
P(f"L'intervallo di confidenza della stima finale è stima ± 1,96 · √((1 - B) · se<super>2</super>). La quota della "
  f"variabilità tra regioni che è segnale vero (τ<super>2</super> rispetto a τ<super>2</super> + errore tipico) è circa il "
  f"97%: le differenze tra regioni sono quasi tutte reali e lo shrinkage sposta poco le stime, tranne per le regioni piccole.")
H2("13.4 Il risultato")
r_ = REP.sort_values("shrink", ascending=False)
tabella([[r.regione, mig(r.n_thread), f(r.media, 3), f(r.peso_dati, 2), f(r.shrink, 3), f"{f(r.ci_lo, 3)} - {f(r.ci_hi, 3)}"]
         for _, r in r_.iterrows()],
        ["Regione", "Thread", "Media destag.", "Peso dei dati", "Stima finale", "Intervallo 95%"], [2.4, 1, 1.2, 1.1, 1.2, 1.8], colore=ARANCIO)
n_sig = int(((REP.ci_lo > MU) | (REP.ci_hi < MU)).sum())
P(f"{n_sig} regioni su 20 hanno un tono significativamente diverso dalla media (il loro intervallo non contiene μ).")
figura(O / "rep2_volume.png", "Figura 13.3 - Tono e volume di discussione per regione.", max_alt=7 * cm)
P(f"<b>Tono e volume</b>: la correlazione di Spearman tra numero di testi e tono è {f(rho_v)}. Le regioni più discusse (Lazio, "
  "Lombardia, Campania, Toscana) hanno il tono più basso: le mete affollate raccolgono più lamentele su prezzi, code e "
  "logistica. Lo script costruisce anche una variante \"al netto del volume\" (il tono tolta la parte spiegata dal numero "
  "di testi), usata solo nell'analisi di incertezza dell'indicatore.")
inbreve("Tre correzioni: destagionalizzazione (la stagione), errori standard per thread (la dipendenza tra commenti), "
        "shrinkage bayesiano empirico (le regioni con pochi testi). In cima Umbria, Marche e Basilicata; in fondo Lazio e "
        "Lombardia.")

# ================================================================ 14 indicatore
H1("14. L'indicatore di attenzione digitale (script 14)")
scheda("script_14_indicatore.py",
       "Costruisce il Digital Attention Index (DAI): un numero per regione che riassume quanta attenzione online riceve nel "
       "2023-2024, con i suoi tre pilastri. Lo valida contro ISTAT, calcola lo scarto tra attenzione e turisti e misura "
       "quanto la classifica dipende dalle scelte di costruzione.",
       "data/processed/istat.csv, trends.csv, wiki.csv, reddit.csv; output/rep_regioni.csv",
       "output/ind_*.csv, ind_1_pilastri.png, ind_2_incertezza.png, ind_3_scarti.png")
teoria("indicatore composito",
       "Un <b>indicatore composito</b> riassume in un solo numero un fenomeno con più facce, combinando più <b>indicatori "
       "elementari</b>. Esempi noti: l'Indice di Sviluppo Umano dell'ONU, il BES dell'ISTAT. Il riferimento metodologico è "
       "il <i>Handbook on Constructing Composite Indicators</i> di OCSE e Centro Comune di Ricerca della Commissione europea "
       "(2008), che indica i passi: quadro teorico, scelta degli indicatori, normalizzazione, pesi, aggregazione, analisi di "
       "incertezza, validazione con dati esterni. Il progetto li segue tutti.")
H2("14.1 Quadro teorico: tre pilastri, cinque ingredienti")
figura(SCH / "s4_dai.png", "Figura 14.1 - Struttura del DAI: tre pilastri e cinque indicatori elementari.", max_alt=8 * cm)
tabella([["Visibilità", "Quanto se ne parla?", "quota di visite Wikipedia (en, de, fr, es) sul totale delle regioni; quota di testi Reddit che la citano (2023-24)"],
         ["Reputazione", "Con che tono?", "tono del capitolo 13 (Qwen, destagionalizzato, con shrinkage)"],
         ["Slancio", "Quanto è cresciuta l'attenzione?", "crescita 2024/2019 delle visite Wikipedia; crescita 2024/2019 delle ricerche Google (mediana delle serie utilizzabili)"]],
        ["Pilastro", "Domanda", "Indicatori elementari (mercato estero)"], [1.4, 2, 6])
P("Per il mercato domestico ci sono solo Visibilità (Wikipedia italiana) e Slancio: i testi Reddit sono in inglese e "
  "descrivono turisti stranieri. Si usano <b>quote</b> e <b>crescite</b>, non valori assoluti: Reddit è cresciuto di 58 volte "
  "e Wikipedia italiana è in calo, quindi conta la fetta di attenzione di ogni regione e come cambia rispetto a se stessa.")
H2("14.2 Normalizzazione: il punteggio di rango")
P("Gli ingredienti hanno unità diverse (una quota del 13%, un tono di 0,53, una crescita di 1,28) e non si possono sommare "
  "così come sono: sarebbe come sommare euro e chili. Si portano tutti sulla stessa scala con il metodo più semplice, il "
  "<b>punteggio di rango</b>:")
elenco(["per ogni ingrediente si ordinano le 20 regioni dalla peggiore alla migliore;",
        "<b>punteggio di rango</b> = (posizione - 1) / 19 · 100: 100 = la regione migliore, 0 = la peggiore;",
        "un punteggio di 66 vuol dire che la regione fa meglio del 66% delle altre 19 regioni."], numeri=True)
formula("punteggio di rango = (posizione dal basso - 1) / (numero di regioni - 1) x 100")
figura(SCH / "d13_ranghi.png", "Figura 14.2 - Dalla quota di visite Wikipedia al punteggio di rango (dati veri, mercato estero).", max_alt=5.5 * cm)
P("Il punteggio di rango guarda solo l'<b>ordine</b> delle regioni. Il vantaggio è che non servono trasformazioni (logaritmi, "
  "z-score) e che una regione molto grande non schiaccia le altre: il Lazio, con il 18% delle visite, vale 100, la Toscana "
  "(8%) vale 95. Il prezzo è che si perdono le distanze: tra Lazio e Toscana c'è un rapporto di più di due a uno, ma i "
  "punteggi sono vicini. Per un indice descrittivo è un compromesso accettabile, e il manuale OCSE-JRC lo prevede tra i "
  "metodi di normalizzazione (<i>ranking</i>). Le alternative (punteggi T = 50 + 10 · z-score, min-max) entrano "
  "nell'analisi di incertezza (14.6): la classifica resta quasi la stessa.")
H2("14.3 Pesi e aggregazione")
teoria("pesi e aggregazione",
       "<b>Pesi uguali</b>: dentro ogni pilastro si fa la media dei suoi indicatori, poi il DAI è la media dei tre pilastri. "
       "È la scelta più trasparente quando non c'è una ragione teorica per preferire un pilastro.<br/>"
       "In alternativa i pesi si possono ricavare dai dati con l'<b>analisi delle componenti principali</b> (PCA): la PCA "
       "cerca la combinazione dei due indicatori di un pilastro che riassume la maggior parte della loro variabilità; il "
       "peso di ciascun indicatore è il quadrato del suo coefficiente in quella combinazione.<br/>"
       "<b>Aggregazione aritmetica</b> (media semplice): un pilastro molto alto compensa uno molto basso. <b>Aggregazione "
       "geometrica</b> (media dei logaritmi): la compensazione è minore, una regione deve andare bene su tutti i pilastri. "
       "La versione principale usa pesi uguali e media aritmetica; le alternative entrano nell'analisi di incertezza.")
esempio("Friuli-Venezia Giulia, mercato estero",
        f"Visibilità {f(DAI_E.loc['Friuli-VG', 'Visibilita' + chr(39)], 1)}, Reputazione {f(DAI_E.loc['Friuli-VG', 'Reputazione'], 1)}, "
        f"Slancio {f(DAI_E.loc['Friuli-VG', 'Slancio'], 1)}: DAI = media = <b>{f(DAI_E.loc['Friuli-VG', 'DAI'], 1)}</b>. "
        "Il Friuli è tra le prime regioni non perché se ne parli molto (Visibilità nella parte bassa della classifica) ma perché se ne parla bene ed è la regione "
        "la cui attenzione è cresciuta di più. Per questo i pilastri vanno letti anche separati.")
H2("14.4 Validazione per pilastro")
P("Ogni pilastro si confronta, con la correlazione di Spearman tra le classifiche delle 20 regioni, con la grandezza "
  "ISTAT che dovrebbe rispecchiare.")
tabella([[r.mercato, r.misura, r.riferimento_ISTAT, f(r.spearman), f(r.p_value, 4)] for _, r in VAL.iterrows()],
        ["Mercato", "Misura", "Riferimento ISTAT", "Spearman", "p-value"], [1.5, 1.5, 2.5, 1.2, 1.2])
P(f"La Visibilità ordina le regioni quasi come la quota di arrivi ({f(vis_e)} per l'estero), lo Slancio come la crescita "
  f"degli arrivi. Il DAI nel suo complesso <b>non</b> segue gli arrivi, ed è giusto così: Visibilità e Reputazione vanno in "
  f"direzioni opposte (correlazione {f(ELc.loc['wiki_quota', 'reddit_sentiment'])}: le regioni più discusse hanno un tono "
  f"più basso) e lo Slancio è quasi indipendente dalle altre due. Il DAI è una <b>sintesi descrittiva</b> dell'attenzione "
  f"online, non una stima dei flussi.")
H2("14.5 Lo scarto tra attenzione e turisti")
formula("scarto di visibilità = log(quota di attenzione digitale) - log(quota di arrivi)<br/>"
        "scarto di slancio = log(crescita digitale / mediana) - log(crescita degli arrivi / mediana)")
P("La quota di attenzione è la media geometrica delle quote Wikipedia e Reddit. Uno scarto di visibilità positivo indica "
  "una regione <b>più cercata che visitata</b> (potenziale non convertito); negativo, una regione <b>più visitata che "
  "cercata</b> (turismo di prossimità, di ritorno, di montagna). +0,69 = il doppio, -0,69 = la metà. Lo scarto di slancio "
  "usa crescite relative alla mediana nazionale, perché Wikipedia cala per motivi suoi.")
se_ = SC_E.sort_values("scarto_visibilita", ascending=False)
tabella([[i, pc(r.quota_attenzione, 1), pc(r.quota_arrivi, 1), f(r.scarto_visibilita), f(r.scarto_slancio)] for i, r in se_.iterrows()],
        ["Regione (mercato estero)", "Quota attenzione", "Quota arrivi", "Scarto visibilità", "Scarto slancio"], [2.6, 1.5, 1.4, 1.5, 1.5])
figura(O / "ind_3_scarti.png", "Figura 14.3 - Scarto di visibilità e di slancio per regione.", max_alt=9 * cm)
P("Per le regioni con quote di arrivi minuscole (Molise, Basilicata, Abruzzo, Calabria per l'estero) lo scarto è un "
  "rapporto con un denominatore piccolissimo e va letto con cautela.")
H2("14.6 Analisi di incertezza")
teoria("analisi di incertezza",
       "Ogni scelta di costruzione è ragionevole ma non l'unica possibile. Si ricalcola l'indicatore con <b>tutte le "
       "combinazioni</b> di scelte alternative e si guarda quanto cambia la classifica: 3 normalizzazioni (ranghi, "
       "punteggi T, min-max) x 2 schemi di pesi (uguali, PCA) x 2 aggregazioni (aritmetica, geometrica) x 3 misure del tono "
       "(stima con shrinkage, media semplice, al netto del volume). Se una regione resta sempre in alto, la sua posizione è "
       "solida; se salta molto, dipende dalle scelte.")
P(f"Per l'estero si ottengono <b>{int(SE_.varianti)} varianti</b>. La correlazione minima tra due classifiche è "
  f"{f(SE_.spearman_min)}; ogni regione si sposta in media di {f(SE_.ampiezza_media, 1)} posizioni.")
tabella([[i, int(r.base), f(r.mediana, 1), f"{int(r['min'])} - {int(r['max'])}"] for i, r in INC_E.iterrows()],
        ["Regione (mercato estero)", "Posizione", "Posizione mediana", "Intervallo delle posizioni"], [2.6, 1.4, 1.6, 1.8])
figura(O / "ind_2_incertezza.png", "Figura 14.4 - Intervallo delle posizioni nelle varianti dell'indicatore.", max_alt=9 * cm)
H2("14.7 L'indicatore")
figura(O / "ind_1_pilastri.png", "Figura 14.5 - I tre pilastri e il DAI in punteggi di rango (100 = regione migliore, 0 = peggiore), regioni ordinate per DAI.", max_alt=10 * cm)
tabella([[i, f(r["Visibilita'"], 1), f(r.Reputazione, 1), f(r.Slancio, 1), f(r.DAI, 1)] for i, r in DAI_E.iterrows()],
        ["Regione (estero)", "Visibilità", "Reputazione", "Slancio", "DAI"], [2.6, 1.3, 1.3, 1.3, 1.3])
inbreve(f"Il DAI è una sintesi descrittiva dell'attenzione online; i pilastri Visibilità e Slancio sono validati dal dato "
        f"ISTAT. Nelle {int(SE_.varianti)} varianti restano sempre tra le prime 5 {SE_.sempre_prime5}, sempre tra le ultime 5 "
        f"{SE_.sempre_ultime5}. Il risultato più utile è lo scarto: Basilicata, Campania e Abruzzo attirano più attenzione "
        "che turisti stranieri; Trentino-AA, Friuli-VG e Veneto più turisti che attenzione.")

# ================================================================ 15 clustering
H1("15. Clustering delle regioni (script 15)")
scheda("script_15_clustering.py",
       "Raggruppa le regioni secondo la forma della loro stagionalità e verifica se i dati digitali riconoscono gli stessi "
       "gruppi visti da ISTAT.", "data/processed/istat.csv, trends.csv, wiki.csv",
       "output/cl_*.csv, cl_1_scelta_k.png, cl_2_accordo.png, cl_3_profili_gruppi.png")
H2("15.1 Ogni regione come un punto: il profilo stagionale")
P("Ogni regione è descritta dal suo <b>profilo stagionale</b> 2023-2024 (capitolo 9.4): 12 quote mensili degli arrivi per "
  "gli italiani e 12 per gli stranieri, in tutto <b>24 numeri</b>. Si può immaginare ogni regione come un punto in uno spazio "
  "a 24 dimensioni: regioni con stagionalità simile sono punti vicini. Lo stesso si fa con Google Trends (hotel e "
  "destinazioni) e Wikipedia.")
teoria("standardizzazione e distanza",
       "Prima di misurare le distanze ogni variabile si <b>standardizza</b> (media 0 e deviazione standard 1 tra le 20 "
       "regioni), così agosto, che varia molto, non conta più di novembre. La distanza tra due regioni è la <b>distanza "
       "euclidea</b>: la radice della somma dei quadrati delle differenze sulle 24 variabili, cioè la distanza \"in linea "
       "d'aria\" generalizzata a 24 dimensioni.")
H2("15.2 L'algoritmo k-means")
teoria("k-means",
       "Il <b>k-means</b> divide n punti in k gruppi in modo che ogni punto sia il più vicino possibile al centro del suo "
       "gruppo. Minimizza la <b>somma dei quadrati entro i gruppi</b>: Σ<sub>gruppi</sub> Σ<sub>punti</sub> distanza(punto, "
       "centro)<super>2</super>. L'algoritmo:<br/>"
       "1. sceglie k centri iniziali;<br/>2. assegna ogni punto al centro più vicino;<br/>3. sposta ogni centro nella media "
       "dei suoi punti;<br/>4. ripete 2-3 finché nessun punto cambia gruppo.<br/>"
       "Il risultato dipende dai centri iniziali, quindi lo script ripete l'algoritmo 10 volte e tiene la soluzione migliore. "
       "Il numero di gruppi k va scelto: è il punto più delicato.")
figura(SCH / "d08_kmeans.png", "Figura 15.1 - Il k-means passo per passo (esempio illustrativo in 2 dimensioni).", max_alt=5 * cm)
H2("15.3 Quanti gruppi? L'elbow method")
teoria("elbow method (metodo del gomito)",
       "Per ogni numero di gruppi k si stima il k-means e si misura l'<b>inerzia</b>: la somma delle distanze al quadrato di "
       "ogni regione dal centro del suo gruppo. Più è bassa, più i gruppi sono compatti. Aggiungendo gruppi l'inerzia scende "
       "sempre (con 20 gruppi ogni regione sarebbe da sola e l'inerzia varrebbe zero), quindi non si cerca il minimo ma il "
       "<b>gomito</b>: il punto dopo il quale un gruppo in più fa guadagnare poco. Per individuarlo in modo oggettivo si usa il "
       "metodo <b>Kneedle</b>: si traccia la retta che unisce il primo e l'ultimo punto della curva e si sceglie il k più "
       "lontano da questa retta.")
k_g = int(K.distanza_dalla_retta.idxmax()) if "k" not in K.columns else int(K.set_index("k").distanza_dalla_retta.idxmax())
KK = K.set_index("k") if "k" in K.columns else K
tabella([[int(k), f(r.inerzia, 1), pc(r.varianza_spiegata), "-" if pd.isna(r.calo) else f(r.calo, 1), f(r.distanza_dalla_retta, 3)]
         for k, r in KK.iterrows()],
        ["k", "Inerzia", "Varianza spiegata", "Calo rispetto a k-1", "Distanza dalla retta"], [0.6, 1.2, 1.4, 1.5, 1.5])
figura(O / "cl_1_scelta_k.png", "Figura 15.2 - Elbow method: inerzia del k-means per k da 1 a 10.", max_alt=7 * cm)
P(f"Fino a k = {k_g} ogni gruppo in più riduce molto l'inerzia, dopo i guadagni diventano piccoli: il gomito è a "
  f"<b>k = {k_g}</b>, che spiega il {pc(KK.varianza_spiegata[k_g])} della varianza. La solidità dei gruppi si verifica poi "
  "gruppo per gruppo.")
teoria("Rand index aggiustato (ARI) e indice di Jaccard",
       "Per confrontare due raggruppamenti delle stesse regioni si guardano tutte le coppie di regioni: il <b>Rand index</b> "
       "è la quota di coppie su cui i due raggruppamenti sono d'accordo (entrambi le mettono insieme, o entrambi le "
       "separano). L'<b>ARI</b> lo corregge per l'accordo che si avrebbe per caso: 0 = come due raggruppamenti casuali, "
       "1 = identici.<br/>"
       "L'<b>indice di Jaccard</b> confronta due insiemi A e B: |A ∩ B| / |A ∪ B|, la parte comune sulla parte totale. Per la "
       "stabilità di un gruppo (metodo di Hennig) si cerca, in ogni sottocampione, il gruppo più simile e si fa la media del "
       "Jaccard: sopra 0,75 il gruppo è solido, sotto 0,5 non va interpretato.")
H2("15.4 I quattro tipi di regioni")
tabella([[r.gruppo, r.regioni, f(r.jaccard), pc(r.quota_estiva), pc(r.quota_invernale), pc(r.quota_stranieri)] for _, r in GR4.iterrows()],
        ["Gruppo", "Regioni", "Jaccard", "Quota estiva", "Quota invernale", "Stranieri"], [2.4, 5.5, 1, 1.1, 1.2, 1.1])
figura(O / "cl_3_profili_gruppi.png", "Figura 15.3 - Profilo stagionale medio di ogni gruppo.", max_alt=6.5 * cm)
P("I nomi derivano dalle caratteristiche: il gruppo con più arrivi invernali è la montagna, quello con più arrivi estivi "
  "il mare, quello con meno estate le città. Città e affari, montagna e arte e mare sono solidi; il mare molto stagionale "
  "è il meno stabile.")
H2("15.5 I dati digitali vedono la stessa geografia stagionale?")
a_ = ACC.pivot(index="k", columns="fonte", values="ARI")
p_ = ACC.pivot(index="k", columns="fonte", values="p_value")
tabella([[int(k)] + [f"{f(a_.loc[k, c])} (p={f(p_.loc[k, c], 3)})" for c in a_.columns] for k in a_.index], ["k"] + list(a_.columns), [0.6, 2, 2, 2])
P("L'ARI tra gruppi ISTAT e gruppi digitali cambia molto con k (il p-value viene da 2.000 permutazioni casuali delle "
  "etichette). Serve una misura che non richieda di scegliere quanti gruppi esistono: il test di Mantel.")
teoria("test di Mantel",
       "Invece di confrontare gruppi si confrontano direttamente le <b>distanze</b>. Per tutte le 190 coppie di regioni (20 x "
       "19 / 2) si calcola la distanza secondo ISTAT e la distanza secondo i dati digitali, e si misura la correlazione di "
       "Spearman tra le due liste. Le 190 coppie però non sono indipendenti (ogni regione compare in 19 coppie), quindi il "
       "p-value non si può calcolare con la formula solita: si fa un <b>test di permutazione</b>. Si rimescolano a caso le "
       "etichette delle regioni in una delle due matrici (5.000 volte) e si ricalcola la correlazione: si ottiene la "
       "distribuzione delle correlazioni \"per caso\". Il p-value è la quota di permutazioni con correlazione almeno pari a "
       "quella osservata.")
figura(SCH / "d09_mantel.png", "Figura 15.4 - L'idea del test di Mantel (esempio illustrativo con 8 regioni).", max_alt=5.5 * cm)
tabella([[r.fonte, r.mercato, f(r.mantel_r), f(r.p_value, 4)] for _, r in MAN.iterrows()],
        ["Fonte", "Mercato", "Correlazione di Mantel", "p-value"], [2.5, 2.2, 2, 1.2])
figura(O / "cl_2_accordo.png", "Figura 15.5 - Accordo con ISTAT: ARI per k e test di Mantel.", max_alt=6.5 * cm)
inbreve(f"Le regioni si dividono in quattro tipi stagionali (città, montagna, arte e mare, mare). I dati digitali "
        f"riconoscono la stessa geografia stagionale: correlazione di Mantel {f(r_w)} per Wikipedia e {f(r_t)} per Google "
        f"Trends (p &lt; 0,01), fino a {f(mantel('Google Trends', 'solo domestico')[0])} per Trends sul mercato domestico.")

# ================================================================ 16 nowcasting
H1("16. Nowcasting degli arrivi (script 16)")
scheda("script_16_nowcasting.py",
       "Simula la situazione reale di uno statistico che deve stimare gli arrivi del mese corrente quando ISTAT non li ha "
       "ancora pubblicati, e misura se le fonti digitali migliorano la stima.",
       "data/processed/istat.csv, trends.csv, wiki.csv", "output/nc_rmse.csv, nc_previsioni.csv, nc_importanza_rf.csv, nc_1_rmse.png")
H2("16.1 L'esercizio")
P("<b>Nowcasting</b> (da <i>now</i> + <i>forecasting</i>) vuol dire stimare il <b>presente</b>: il valore del mese corrente, che "
  "esiste già ma non è ancora stato pubblicato. Si assume che ISTAT pubblichi con <b>L = 3 mesi di ritardo</b>: a fine "
  "giugno si conoscono gli arrivi fino a marzo. Google Trends e Wikipedia di giugno sono invece già disponibili. La "
  "grandezza da stimare è la variazione annua degli arrivi y<sub>t</sub> (capitolo 3.3).")
figura(SCH / "s6_nowcast.png", "Figura 16.1 - Che cosa è noto al momento della stima.", max_alt=6.5 * cm)
H2("16.2 I modelli")
tabella([["B0", "stagionale ingenuo: y = 0, cioè \"come lo stesso mese dell'anno prima\""],
         ["B1", "solo dati ufficiali: y<sub>t</sub> = a + r1 · y<sub>t-3</sub> + r2 · y<sub>t-4</sub> (le ultime due variazioni pubblicate)"],
         ["B1 + Trends", "+ variazioni annue di Trends (hotel, voli, destinazioni) del mese t"],
         ["B1 + Wiki", "+ variazione annua delle visite Wikipedia del mese t"], ["B1 + Trends + Wiki", "entrambe"]],
        ["Modello", "Specificazione"], [2, 8])
P("B1 è il termine di paragone: la domanda è se le fonti digitali aggiungono qualcosa a ciò che uno statistico sa già. "
  "Un modello per mercato, <b>comune alle 20 regioni</b> (un panel: stessi coefficienti per tutte, così ci sono abbastanza "
  "dati per stimarli). Le serie Trends di un mese possono mancare (serie non utilizzabile): in quel caso il valore si "
  "mette a 0 e una variabile indicatrice segnala il dato mancante.")
teoria("cambio di regime",
       "Durante il COVID le variazioni annue erano enormi (-3, +3) e il legame tra passato e presente era diverso da quello "
       "degli anni normali. Il modello include una variabile D = 1 quando l'ultima variazione pubblicata è grande "
       "(|y<sub>t-3</sub>| &gt; 0,5) e le interazioni di D con tutte le variabili: in pratica stima due insiemi di coefficienti, "
       "uno per i periodi \"normali\" e uno per i periodi \"di shock\".")
teoria("regressione di Huber",
       "I minimi quadrati penalizzano gli errori al quadrato: un errore di 3 pesa 9 volte uno di 1, e pochi mesi eccezionali "
       "possono trascinare tutta la retta. La <b>perdita di Huber</b> è quadratica per gli errori piccoli (sotto ε = 1,35 "
       "volte la scala degli errori) e solo lineare per quelli grandi: i mesi anomali contano, ma non dominano.")
figura(SCH / "d11_huber.png", "Figura 16.2 - Perdita quadratica e perdita di Huber.", max_alt=5.5 * cm)
H2("16.3 Pseudo tempo reale")
teoria("valutazione in pseudo tempo reale",
       "Per ogni mese da gennaio 2022 a dicembre 2024 (36 mesi) lo script:<br/>"
       "1. prende solo i dati che si sarebbero conosciuti in quel momento: ISTAT fino a t - 3, Trends e Wikipedia fino a t;<br/>"
       "2. sceglie le serie Trends utilizzabili (al massimo il 20% di zeri) guardando <b>solo i dati fino a t</b>;<br/>"
       "3. <b>ristima</b> tutti i modelli su tutti i mesi disponibili fino ad allora (la finestra si allarga ogni mese);<br/>"
       "4. stima gli arrivi del mese t per le 20 regioni e la confronta, a posteriori, con il valore vero.<br/>"
       "Così nessuna informazione \"dal futuro\" entra nella stima. Si dice <i>pseudo</i> tempo reale perché i dati Google "
       "Trends sono stati scaricati tutti dopo, e Google ricampiona le serie: i valori del 2022 non sono esattamente quelli "
       "che si sarebbero visti nel 2022.")
figura(SCH / "d10_finestra.png", "Figura 16.3 - La finestra di stima si allarga mese dopo mese.", max_alt=5.5 * cm)
H2("16.4 Come si valuta")
teoria("RMSE e RMSE relativo",
       "L'errore di ogni stima è stima - valore vero. L'<b>RMSE</b> (radice dell'errore quadratico medio) = √(media degli "
       "errori al quadrato) è l'errore tipico, nella stessa unità della variazione annua. L'<b>RMSE relativo</b> = RMSE del "
       "modello / RMSE di B1: sotto 1 le fonti digitali aiutano (0,71 = errore ridotto del 29%), sopra 1 peggiorano. Si "
       "calcola separatamente per il 2022 (anno di ripresa) e per il 2023-2024 (anni normali).")
teoria("test di Diebold-Mariano con correzione di Harvey-Leybourne-Newbold",
       "Due modelli hanno RMSE diversi: è una differenza vera o fortuna? Il test di <b>Diebold-Mariano</b> guarda la serie "
       "delle differenze di perdita mese per mese, d<sub>t</sub> = errore<super>2</super> del modello - errore<super>2</super> "
       "di B1 (media sulle 20 regioni). Se i modelli sono equivalenti, la media di d<sub>t</sub> è zero. La statistica è "
       "media(d) / errore standard(d); l'errore standard tiene conto che mesi vicini sono correlati (stima HAC di Newey-West "
       "con 3 ritardi). Con pochi mesi (12 nel 2022) il test originale rifiuta troppo spesso: la correzione di "
       "<b>Harvey, Leybourne e Newbold</b> moltiplica la statistica per un fattore minore di 1 e usa la distribuzione t di "
       "Student con n - 1 gradi di libertà.")
teoria("bootstrap a blocchi mobili",
       "Il <b>bootstrap</b> stima l'incertezza di una statistica ricampionando i dati: si estrae con ripetizione un nuovo "
       "campione della stessa dimensione, si ricalcola la statistica e si ripete migliaia di volte; la dispersione dei "
       "risultati misura l'incertezza. Con le serie storiche mesi vicini sono correlati, quindi non si pescano mesi singoli "
       "ma <b>blocchi di 3 mesi consecutivi</b>. Qui si ricampionano i mesi 2.000 volte, si ricalcola ogni volta il rapporto "
       "RMSE(modello) / RMSE(B1), e il 5° e il 95° percentile danno l'intervallo al 90%. Un miglioramento è solido solo se "
       "l'intervallo sta <b>tutto sotto 1</b>.")
figura(SCH / "d12_bootstrap.png", "Figura 16.4 - Bootstrap a blocchi di 3 mesi (schema).", max_alt=5 * cm)
H2("16.5 Risultati")
righe = []
for mk in ["domestico", "estero"]:
    for mod in ["B0", "B1+Trends", "B1+Wiki", "B1+Trends+Wiki"]:
        c_ = []
        for per in ["2022", "2023-2024"]:
            r = NC[(NC.mercato == mk) & (NC.periodo == per) & (NC.modello == mod)].iloc[0]
            c_.append(f"{f(r.RMSE_rel_B1)} [{f(r.ic90_lo)}-{f(r.ic90_hi)}] p={f(r.p_value, 3)}")
        righe.append([mk, mod] + c_)
tabella(righe, ["Mercato", "Modello", "2022 (ripresa)", "2023-2024 (anni normali)"], [1.4, 2.2, 3.5, 3.5], colore=GIALLO)
P("Ogni cella: RMSE relativo a B1 [intervallo bootstrap al 90%] e p-value del test DM-HLN.")
figura(O / "nc_1_rmse.png", "Figura 16.5 - RMSE relativo a B1 con intervallo bootstrap al 90%.", max_alt=8 * cm)
elenco([f"<b>2022, mercato domestico</b>: Google Trends riduce l'errore del {pc(1 - nc('domestico', '2022', 'B1+Trends'))} con "
        f"un intervallo tutto sotto 1: è il risultato più solido.",
        f"<b>2022, mercato estero</b>: miglioramento del {pc(1 - nc('estero', '2022', 'B1+Trends'))}, ma l'intervallo supera 1.",
        f"<b>2023-2024</b>: nessuna fonte digitale migliora B1; Trends + Wikipedia peggiora il mercato domestico "
        f"(RMSE relativo {f(nc('domestico', '2023-2024', 'B1+Trends+Wiki'))}).",
        "<b>Wikipedia</b> non aiuta in modo affidabile in nessun periodo."])
H2("16.6 Quali variabili contano: random forest e permutation importance")
teoria("random forest e permutation importance",
       "Un <b>albero di decisione</b> stima un valore con una serie di domande sì/no sulle variabili (\"la variazione ISTAT di "
       "tre mesi fa è sopra 0,2?\"). Un singolo albero è instabile; una <b>random forest</b> ne fa crescere 300, ognuno su un "
       "campione diverso dei dati e con una parte delle variabili scelta a caso, e fa la media delle loro stime. Coglie "
       "relazioni non lineari senza doverle specificare.<br/>"
       "La <b>permutation importance</b> misura quanto conta una variabile: si mescolano a caso i suoi valori (così non "
       "contiene più informazione) e si guarda di quanto peggiora l'errore. Qui la foresta è stimata sui dati fino al 2021 e "
       "l'importanza è misurata sul 2022-2024, cioè <b>fuori campione</b>: conta solo l'informazione utile su dati nuovi.")
figura(SCH / "d14_alberi.png", "Figura 16.6 - Un albero di decisione (numeri inventati).", max_alt=5.5 * cm)
eti = {"ar1": "ISTAT t-3", "ar2": "ISTAT t-4", "gt_hotel": "Trends hotel", "gt_voli": "Trends voli",
       "gt_attrazioni": "Trends destinazioni", "wiki": "Wikipedia", "mese": "mese dell'anno"}
tabella([[eti.get(i, i), f(r.domestico, 3), f(r.estero, 3)] for i, r in IMP.iterrows() if i in eti],
        ["Variabile", "Mercato domestico", "Mercato estero"], [3, 2, 2], colore=GIALLO)
P("Le ricerche di voli e destinazioni contano per entrambi i mercati; per l'estero la variabile più importante resta "
  "l'ultimo dato ISTAT pubblicato.")
inbreve("Le fonti digitali migliorano la stima degli arrivi solo nella fase di svolta del 2022, e in modo statisticamente "
        "solido solo per il mercato domestico con Google Trends. Negli anni normali il dato ufficiale con tre mesi di "
        "ritardo basta.")

# ================================================================ 17 conclusioni
H1("17. Risposta alla domanda di ricerca")
P("<b>From Clicks to Check-ins: Google Trends, Wikipedia e Reddit possono stimare in anticipo il turismo regionale "
  "italiano?</b> In parte: le tre fonti rispecchiano bene la <i>struttura</i> del turismo, ma anticipano il dato ufficiale "
  "solo nei momenti di svolta, e i testi aiutano a capire che cosa cambia nell'esperienza dei turisti.")
H2("17.1 Rispecchiano? Sì, nella struttura")
elenco([f"Geografia: la Visibilità digitale ordina le regioni come gli arrivi (Spearman {f(vis_e)} per l'estero).",
        "Stagionalità: i profili mensili di Trends coincidono con quelli ISTAT (mediana fino a 0,94).",
        f"Tipi di regioni: Mantel {f(r_w)} (Wikipedia) e {f(r_t)} (Trends), p &lt; 0,01.",
        "Limite: la corrispondenza è debole sulle variazioni annue negli anni normali (circa 0,2)."])
H2("17.2 Anticipano? Solo nei momenti di svolta")
elenco([f"Nel 2022 Trends riduce l'errore del {pc(1 - nc('domestico', '2022', 'B1+Trends'))} per il mercato domestico.",
        "Per il mercato estero il miglioramento non è statisticamente solido; negli anni normali nessuna fonte aiuta.",
        "L'evidenza poggia su un solo episodio di svolta ed è in pseudo tempo reale."])
H2("17.3 Spiegano? Sì")
elenco([f"Il tono peggiora quando arrivano i turisti: correlazione {f(r_mesi)} tra sentiment mensile e arrivi stranieri; "
        f"testi negativi dal {pc(neg_w, 1)} al {pc(neg_s, 1)}.",
        f"Il calo avviene dentro gli stessi temi ({pc(SDE.quota_interno)} effetto interno) e riguarda soprattutto prezzi "
        "e alloggio; la folla è giudicata male in ogni stagione.",
        f"Le regioni più discusse hanno il tono più basso (Spearman {f(rho_v)})."])
riquadro("Messaggio conclusivo", "I click riflettono fedelmente dove e quando avvengono i check-in, ma raramente li "
         "anticipano. Il valore dei big data per la statistica ufficiale sta nell'affiancarla: segnalare le svolte prima del "
         "dato ufficiale e spiegare con i testi ciò che i numeri non dicono.", VERDE_CH, VERDE)
H2("17.4 Limiti e sviluppi")
tabella([["Un solo download di Google Trends", "Il rumore di campionamento di Google non è mediato", "Riscaricare in più giorni e fare la media"],
         ["Pseudo tempo reale", "Le serie Trends del 2022 non sono quelle viste nel 2022", "Archiviare i dati mese per mese"],
         ["Un solo episodio di svolta", "La conclusione sulle svolte poggia sul 2022", "Ripetere l'analisi su shock futuri"],
         ["Reddit solo in inglese", "Copre solo una parte del mercato estero", "Aggiungere forum in altre lingue"],
         ["Wikipedia italiana in calo", "Proxy debole per il mercato domestico", "Usare quote relative invece dei livelli"],
         [f"Validazione su {int(QW.n)} testi, un annotatore", "Intervalli di confidenza larghi (circa ±12 punti)", "Annotare più testi, con un secondo annotatore"],
         ["Dati ISTAT 2025 provvisori", "Lo scarto di slancio non è verificabile", "Confronto con i dati definitivi"]],
        ["Limite", "Conseguenza", "Sviluppo"], [3, 4, 4])
P("Non si può dire che il DAI misuri i flussi turistici, che i tipi di regioni siano esattamente quattro, né che lo scarto "
  "di slancio anticipi la crescita futura.")

# ================================================================ appendici
H1("Appendice A. Gli script")
tabella([["0", "script_0_comune.py", "Percorsi, colori, nomi delle regioni, stile dei grafici (modulo)", "4"],
         ["1", "script_1_istat.py", "Pulizia e controlli dei dati ISTAT; variazione annua degli arrivi", "5"],
         ["2", "script_2_trends_download.js", "Download di Google Trends dalla console del browser", "6"],
         ["3", "script_3_trends_unione.py", "Unione dei 20 file di Google Trends", "6"],
         ["4", "script_4_wikipedia.py", "Titoli via Wikidata, visite mensili, aggregazione", "7"],
         ["5", "script_5_vader_turismo.py", "Dizionario di sentiment adattato ai viaggi (modulo, termine di paragone)", "8"],
         ["6", "script_6_reddit.py", "Pulizia dei testi di Reddit, regioni citate, aggregati mensili", "8"],
         ["7", "script_7_eda.py", "Analisi esplorativa e file di lavoro", "9"],
         ["8", "script_8_topic_modeling.py", "Topic model (TF-IDF + NMF)", "10"],
         ["9", "script_9_qwen_preparazione.py", "Testi per Kaggle e campione da annotare", "11"],
         ["10", "script_10_qwen_kaggle.py", "Classificazione con Qwen 2.5 7B su GPU (Kaggle)", "11"],
         ["11", "script_11_sentiment_regionale.py", "Tono per regione con shrinkage bayesiano empirico", "13"],
         ["12", "script_12_sentiment_qwen.py", "Validazione, tono nell'anno, aspetti, temi", "12"],
         ["13", "script_13_testi_classificati.py", "Excel e CSV leggibili dei testi classificati", "12"],
         ["14", "script_14_indicatore.py", "Indicatore di attenzione digitale", "14"],
         ["15", "script_15_clustering.py", "Clustering e test di Mantel", "15"],
         ["16", "script_16_nowcasting.py", "Nowcasting in pseudo tempo reale", "16"],
         ["17", "script_17_schemi.py", "Schemi e figure didattiche del report (modulo)", "-"],
         ["18", "script_18_report.py", "Questo report", "-"],
         ["19", "script_19_esegui_tutto.py", "Esegue gli script nell'ordine giusto", "4"]],
        ["#", "Script", "Cosa fa", "Capitolo"], [0.6, 4.2, 7.2, 1])
H1("Appendice B. Glossario")
tabella([["Arrivi / presenze", "Clienti che hanno fatto check-in / notti trascorse."],
         ["Serie storica, panel", "Valori di una misura nel tempo / insieme di serie con la stessa struttura (20 regioni)."],
         ["Variazione annua logaritmica", "log(valore del mese) - log(valore dello stesso mese dell'anno prima)."],
         ["Z-score", "Distanza dalla media in deviazioni standard."],
         ["Punteggio di rango", "(posizione - 1) / (n - 1) x 100: 100 = la migliore, 0 = la peggiore; usato per il DAI."],
         ["Correlazione di Pearson / Spearman", "Legame lineare tra due variabili / accordo tra le loro classifiche."],
         ["Errore standard", "Quanto oscillerebbe una stima cambiando campione."],
         ["Intervallo di confidenza", "Intervallo che, nel 95% delle ripetizioni, contiene il valore vero."],
         ["p-value", "Probabilità di un risultato così estremo se non ci fosse nessun effetto."],
         ["SDMX", "Standard internazionale per lo scambio di dati statistici (formato del file ISTAT)."],
         ["Argomento di Google (topic)", "Entità riconosciuta da Google, indipendente dalla lingua delle ricerche."],
         ["Wikidata", "Banca dati che collega le pagine di tutte le Wikipedia con un codice unico (Q...)."],
         ["JSON / JSON Lines", "Formato di dati a coppie nome: valore / un oggetto JSON per riga."],
         ["Espressione regolare", "Schema di ricerca nel testo (per esempio una parola intera tra un elenco di nomi)."],
         ["TF-IDF", "Peso di una parola: frequente nel testo e rara nel corpus."],
         ["NMF", "Scomposizione della matrice testi x parole in testi x temi e temi x parole, senza valori negativi."],
         ["Coerenza UMass", "Quanto le parole di un tema compaiono negli stessi testi."],
         ["LLM, token, transformer", "Modello linguistico / pezzo di parola / architettura basata sull'attention."],
         ["Open-weight", "Modello con parametri pubblici, eseguibile e riproducibile da chiunque."],
         ["Quantizzazione AWQ", "Rappresentazione dei parametri con 4 bit invece di 16, per occupare meno memoria."],
         ["Decodifica guidata", "Il modello può produrre solo testo conforme a uno schema JSON."],
         ["Matrice di confusione", "Tabella verità x previsione; sulla diagonale i casi giusti."],
         ["Kappa di Cohen", "Accordo corretto per quello che si avrebbe per caso."],
         ["Intervallo di Wilson", "Intervallo di confidenza per una proporzione, adatto a campioni piccoli."],
         ["Test di McNemar", "Confronta due classificatori sugli stessi casi guardando solo i disaccordi."],
         ["Test t di Welch, chi-quadro", "Confronto tra due medie / tra proporzioni in una tabella."],
         ["Errore standard per cluster", "Errore standard che tiene conto della dipendenza dentro i gruppi (thread)."],
         ["Bayes empirico, shrinkage", "Stima che combina i dati di un'unità con la distribuzione stimata da tutte le unità."],
         ["DerSimonian-Laird", "Metodo per stimare la varianza vera tra unità, al netto del rumore."],
         ["Indicatore composito", "Numero che sintetizza più indicatori elementari."],
         ["PCA", "Analisi delle componenti principali: la combinazione che riassume più variabilità."],
         ["k-means", "Divisione in k gruppi minimizzando le distanze dai centri."],
         ["Elbow method, inerzia", "Scelta di k dove la curva dell'inerzia (somma dei quadrati entro i gruppi) smette di scendere molto."],
         ["ARI, indice di Jaccard", "Accordo tra due classificazioni corretto per il caso / parte comune di due insiemi."],
         ["Test di Mantel", "Correlazione tra due matrici di distanze, con significatività per permutazione."],
         ["Nowcasting", "Stima del valore del mese corrente prima della pubblicazione ufficiale."],
         ["Pseudo tempo reale", "Simulazione in cui ogni stima usa solo i dati disponibili in quel momento."],
         ["Regressione di Huber", "Regressione robusta: gli errori grandi pesano in modo lineare, non quadratico."],
         ["RMSE", "Radice dell'errore quadratico medio: l'errore tipico di una stima."],
         ["Diebold-Mariano (HLN)", "Test che confronta l'accuratezza di due previsioni, corretto per campioni piccoli."],
         ["Bootstrap a blocchi", "Ricampionamento di blocchi di mesi consecutivi per stimare l'incertezza."],
         ["Random forest, permutation importance", "Media di molti alberi di decisione / aumento dell'errore mescolando una variabile."]],
        ["Termine", "Significato"], [3.4, 9])


class Documento(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(str(path), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm,
                         bottomMargin=2 * cm, title="From Clicks to Check-ins - Report del progetto", author="Francesco Pio Nardiello")
        self.addPageTemplates([PageTemplate(id="p", frames=[Frame(self.leftMargin, self.bottomMargin, self.width, self.height)],
                                            onPage=self.piede)])

    def piede(self, canv, doc):
        if doc.page == 1:
            return
        canv.saveState()
        canv.setFont("Arial", 8)
        canv.setFillColor(GRIGIO)
        canv.drawString(2 * cm, 1.2 * cm, "From Clicks to Check-ins - Report del progetto")
        canv.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"pagina {doc.page}")
        canv.setStrokeColor(colors.HexColor("#d9d8d2"))
        canv.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)
        canv.restoreState()

    def afterFlowable(self, fl):
        if isinstance(fl, Paragraph) and fl.style.name in ("H1", "H2") and fl.getPlainText() != "Indice":
            livello = 0 if fl.style.name == "H1" else 1
            chiave = f"h{id(fl)}"
            self.canv.bookmarkPage(chiave)
            self.canv.addOutlineEntry(fl.getPlainText(), chiave, level=livello, closed=livello > 0)
            self.notify("TOCEntry", (livello, fl.getPlainText(), self.page, chiave))


if __name__ == "__main__":
    schemi.tutti()
    dest = DOCS / "Report_progetto_turismo.pdf"
    Documento(dest).multiBuild(story)
    print(f"Report salvato: {dest}")
