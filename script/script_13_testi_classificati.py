"""
SCRIPT 13 - Testi classificati in formato leggibile
Produce qwen_testi_classificati.xlsx qwen_testi_classificati.csv    
"""
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from script_0_comune import LLM, NOMI, OUT

ASP = {"crowds": "folla", "prices": "prezzi", "transport": "trasporti", "food": "cibo",
       "accommodation": "alloggio", "sights": "luoghi"}
TIPO = {"question": "domanda", "advice": "consiglio", "experience_report": "esperienza", "other": "altro"}
SENT = {"positive": "positivo", "neutral": "neutro", "negative": "negativo"}
REG_QWEN = {"Trentino-Alto Adige": "Trentino-AA", "Friuli-Venezia Giulia": "Friuli-VG",
            "several": "piu' regioni", "none": "nessuna (solo citata)"}

q = pd.read_csv(LLM / "qwen_completo.csv", dtype={"id": str}).drop(columns=["risposta_grezza", "errore"])
m = pd.read_csv(LLM / "meta_testi.csv", dtype={"id": str})
t = pd.read_csv(LLM / "kaggle" / "completo.csv", dtype={"id": str}, usecols=["id", "text"])
d = q.merge(m, on="id").merge(t, on="id")


def elenco(r, valore):
    return ", ".join(ASP[a] for a in ASP if r[f"asp_{a}"] == valore)


X = pd.DataFrame({
    "id": d.id,
    "mese": d.TIME_PERIOD,
    "post/commento": d.kind.map({"post": "post", "comment": "commento"}),
    "testo": d.text,
    "tipo": d.text_type.map(TIPO),
    "sentiment": d.sentiment.map(SENT),
    "punteggio (-2..+2)": d.score,
    "aspetti positivi": d.apply(lambda r: elenco(r, "positive"), axis=1),
    "aspetti negativi": d.apply(lambda r: elenco(r, "negative"), axis=1),
    "regione": d.main_region.replace(REG_QWEN),
    "regioni citate": d.regioni.str.split(";").map(lambda l: ", ".join(NOMI.get(c, c) for c in l)),
    "caratteri": d.n_char,
})
X.to_csv(OUT / "llm" / "qwen_testi_classificati.csv", index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------- campione annotato a mano
gold = pd.read_csv(LLM / "gold_da_annotare.csv", dtype=str, keep_default_na=False)[["id", "sentiment_umano", "regione_umana"]]
C = gold.merge(X, on="id", how="left")
C = C[["id", "mese", "testo", "sentiment_umano", "sentiment", "regione_umana", "regione", "tipo", "punteggio (-2..+2)",
       "aspetti positivi", "aspetti negativi"]].rename(columns={"sentiment_umano": "sentiment (a mano)",
                                                                "sentiment": "sentiment (Qwen)", "regione_umana": "regione (a mano)",
                                                                "regione": "regione (Qwen)"})

# ---------------------------------------------------------------- esempi
parti = []
for (tp, se), g in d.groupby(["text_type", "sentiment"]):
    sel = g.sample(min(8, len(g)), random_state=0)
    parti.append(X.loc[sel.index].assign(gruppo=f"{TIPO[tp]} / {SENT[se]}", testi_nel_gruppo=len(g)))
sel = d[(d.main_region == "none") & (d.n_regioni == 1)].sample(20, random_state=0)
parti.append(X.loc[sel.index].assign(gruppo="regione citata solo di passaggio", testi_nel_gruppo=int((d.main_region == "none").sum())))
ES = pd.concat(parti)[["gruppo", "testi_nel_gruppo"] + list(X.columns)]

LEGGI = pd.DataFrame([
    ["Campione", "i 300 testi del campione annotato a mano (compilati: le righe con il sentiment a mano)"],
    ["Esempi", "8 esempi per ogni combinazione tipo di testo / sentiment, e 20 testi che citano una regione solo di passaggio"],
    ["qwen_testi_classificati.csv", "tutti i 128.002 testi con le stesse colonne"],
    ["", ""],
    ["tipo", "domanda / consiglio / esperienza / altro"],
    ["sentiment", "atteggiamento complessivo di chi scrive: positivo / neutro / negativo"],
    ["punteggio", "-2 molto negativo, -1 negativo, 0 neutro, +1 positivo, +2 molto positivo"],
    ["aspetti", "aspetti su cui il testo esprime un giudizio positivo o negativo (folla, prezzi, trasporti, cibo, alloggio, luoghi)"],
    ["regione", "regione di cui il testo parla davvero, scelta tra le regioni citate; 'nessuna' = citata solo di passaggio"],
    ["regioni citate", "regioni trovate cercando nomi di luoghi nel testo (script 6)"],
], columns=["voce", "significato"])

f = OUT / "llm" / "qwen_testi_classificati.xlsx"
with pd.ExcelWriter(f, engine="openpyxl") as w:
    LEGGI.to_excel(w, sheet_name="Leggimi", index=False)
    C.to_excel(w, sheet_name="Campione", index=False)
    ES.to_excel(w, sheet_name="Esempi", index=False)

wb = load_workbook(f)
LARG = {"testo": 90, "gruppo": 30, "significato": 110, "voce": 28}
for ws in wb.worksheets:
    for j, h in enumerate([c.value for c in ws[1]], start=1):
        ws.column_dimensions[get_column_letter(j)].width = LARG.get(h, 16 if len(str(h)) < 16 else min(len(str(h)) + 2, 24))
    for row in ws.iter_rows():
        for c in row:
            c.font = Font(name="Arial", size=9, bold=c.row == 1, color="FFFFFF" if c.row == 1 else "000000")
            c.alignment = Alignment(wrap_text=True, vertical="top")
            if c.row == 1:
                c.fill = PatternFill("solid", fgColor="2A78D6")
    if ws.title != "Leggimi":
        ws.freeze_panes = "D2"
        ws.auto_filter.ref = ws.dimensions
        for r in range(2, ws.max_row + 1):
            ws.row_dimensions[r].height = 60
wb.save(f)
print(f"Salvati: {f} (Campione {len(C)} righe, Esempi {len(ES)} righe) e qwen_testi_classificati.csv ({len(X):,} righe)")