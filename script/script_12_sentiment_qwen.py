"""
SCRIPT 12 - Sentiment con Qwen: validazione e risultati

Usa la classificazione dei 128.002 testi 2023-2024 fatta da Qwen 2.5 7B e risponde a queste domande:
  A. Le risposte del modello sono utilizzabili? (leggibili, coerenti)
  B. Come si distribuiscono sentiment e tipi di testo?
  C. Regione: quante volte un testo cita una regione solo di passaggio?
  D. Validazione: quanto e' accurato Qwen sui testi annotati a mano? Come termini di
     paragone, sugli stessi testi, un metodo a dizionario (VADER adattato ai viaggi, calcolato nello script 6) e un
     modello transformer per il sentiment (RoBERTa, cardiffnlp/twitter-roberta-base-sentiment-latest).
  E. Tono nel corso dell'anno: il sentiment mensile segue gli arrivi stranieri?
  F. Che cosa peggiora d'estate: giudizi negativi per aspetto (folla, prezzi, trasporti, cibo, alloggio, luoghi)
  G. Temi e sentiment: il calo estivo dipende da cio' di cui si parla o da come se ne parla?
"""
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import accuracy_score, cohen_kappa_score, f1_score
from statsmodels.stats.contingency_tables import mcnemar
from statsmodels.stats.proportion import proportion_confint
import matplotlib.pyplot as plt

from script_0_comune import COL, LLM, NOMI, OUT, PROC, Registro

R = Registro("snt_risultati.txt")
MESI = list("GFMAMGLASOND")
NOME_Q = {"Piemonte": "ITC1", "Valle d'Aosta": "ITC2", "Liguria": "ITC3", "Lombardia": "ITC4",
          "Trentino-Alto Adige": "ITDA", "Veneto": "ITD3", "Friuli-Venezia Giulia": "ITD4", "Emilia-Romagna": "ITD5",
          "Toscana": "ITE1", "Umbria": "ITE2", "Marche": "ITE3", "Lazio": "ITE4", "Abruzzo": "ITF1", "Molise": "ITF2",
          "Campania": "ITF3", "Puglia": "ITF4", "Basilicata": "ITF5", "Calabria": "ITF6", "Sicilia": "ITG1",
          "Sardegna": "ITG2"}
ASPETTI = {"prices": "prezzi", "accommodation": "alloggio", "transport": "trasporti", "food": "cibo",
           "sights": "luoghi", "crowds": "folla"}

q = pd.read_csv(LLM / "qwen_completo.csv", dtype={"id": str}).drop(columns=["risposta_grezza"])
meta = pd.read_csv(LLM / "meta_testi.csv", dtype={"id": str})
d = q.merge(meta, on="id")
d["mese"] = d.TIME_PERIOD.str[5:].astype(int)
d["stagione"] = np.where(d.mese.between(6, 9), "estate", np.where(d.mese.isin([12, 1, 2, 3]), "inverno", "altro"))

# ================================================================ A. qualita'
R.titolo("A. QUALITA' DELLE RISPOSTE")
ok = ~d.errore.astype(str).eq("True")
segno = np.sign(d.score.astype(float))
coer = ((segno < 0) & (d.sentiment == "negative")) | ((segno == 0) & (d.sentiment == "neutral")) | \
       ((segno > 0) & (d.sentiment == "positive"))
R.say(f"Testi: {len(d):,} | risposte leggibili {ok.mean():.2%} | sentiment e punteggio coerenti {coer.mean():.1%}")

# ================================================================ B. distribuzioni
R.titolo("B. SENTIMENT E TIPI DI TESTO")
R.say(d.sentiment.value_counts(normalize=True).round(3).to_string())
R.say(d.text_type.value_counts(normalize=True).round(3).to_string())
R.say("\nPunteggio medio per tipo di testo:")
R.say(d.groupby("text_type").score.mean().round(3).to_string())

# ================================================================ C. regione
R.titolo("C. REGIONE DI CUI PARLA IL TESTO")
uno = d[d.n_regioni == 1]
rq = uno.main_region.map(NOME_Q)
R.say(f"Testi che citano una sola regione: {len(uno):,} | Qwen conferma la regione {(rq == uno.regioni).mean():.1%} | "
      f"solo citata di passaggio {(uno.main_region == 'none').mean():.1%}")
R.say(f"Su tutti i testi: solo citata di passaggio {(d.main_region == 'none').sum():,} | "
      f"su piu' regioni {(d.main_region == 'several').sum():,}")
pd.DataFrame([dict(testi=len(d), una_regione=len(uno), conferma=(rq == uno.regioni).mean(),
                   solo_citata_una=(uno.main_region == "none").mean(), solo_citata_tot=int((d.main_region == "none").sum()),
                   piu_regioni_tot=int((d.main_region == "several").sum()))]).round(4).to_csv(OUT / "snt_regione.csv", index=False)

# ================================================================ D. validazione sul campione annotato a mano
R.titolo("D. VALIDAZIONE SUL CAMPIONE ANNOTATO A MANO")
gold = pd.read_csv(LLM / "gold_da_annotare.csv", dtype=str, keep_default_na=False)
gold["vero"] = gold.sentiment_umano.str.strip().str.lower().map(
    {"positivo": "positive", "neutro": "neutral", "negativo": "negative"})
A = gold.dropna(subset=["vero"]).merge(d[["id", "sentiment", "main_region", "compound_tur", "regioni", "n_char"]], on="id")
R.say(f"Testi annotati: {len(A)} (annotazione alla cieca, con le stesse regole date al modello)")
if len(A) >= 30:
    A["vader"] = np.where(A.compound_tur >= 0.4, "positive", np.where(A.compound_tur <= -0.4, "negative", "neutral"))
    f_rg = LLM / "roberta_gold.csv"
    if not f_rg.exists():
        from transformers import pipeline
        clf = pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                       truncation=True, max_length=512)
        testi = gold.set_index("id").loc[A.id, "testo"].tolist()
        pd.DataFrame({"id": A.id, "roberta_lab": [o["label"].lower() for o in clf(testi, batch_size=16)]}).to_csv(f_rg, index=False)
    A = A.merge(pd.read_csv(f_rg, dtype={"id": str}), on="id", how="left")
    metodi = {"Qwen 2.5 7B": "sentiment", "RoBERTa (transformer)": "roberta_lab", "VADER (dizionario)": "vader"}
    righe = []
    for nome, c in metodi.items():
        giusto = A[c] == A.vero
        lo, hi = proportion_confint(giusto.sum(), len(giusto), method="wilson")
        righe.append(dict(metodo=nome, corretti=int(giusto.sum()), n=len(giusto), accuratezza=giusto.mean(), ic_lo=lo,
                          ic_hi=hi, F1_macro=f1_score(A.vero, A[c], average="macro"), kappa=cohen_kappa_score(A.vero, A[c]),
                          acc_testi_lunghi=giusto[A.n_char > A.n_char.median()].mean()))
    V = pd.DataFrame(righe).set_index("metodo")
    V.round(4).to_csv(OUT / "snt_validazione.csv")
    R.say(V.round(3).to_string())
    mc = []
    for nome, c in list(metodi.items())[1:]:
        a, b = A.sentiment == A.vero, A[c] == A.vero
        t = [[int((a & b).sum()), int((a & ~b).sum())], [int((~a & b).sum()), int((~a & ~b).sum())]]
        pv = mcnemar(t, exact=True).pvalue
        mc.append(dict(confronto=f"Qwen contro {nome}", giusto_solo_qwen=t[0][1], giusto_solo_altro=t[1][0], p_value=pv))
        R.say(f"McNemar Qwen vs {nome}: giusto solo Qwen {t[0][1]}, solo l'altro {t[1][0]}, p = {pv:.4f}")
    pd.DataFrame(mc).round(4).to_csv(OUT / "snt_mcnemar.csv", index=False)
    pd.concat([pd.crosstab(A.vero, A[c]).stack().rename("n").reset_index().rename(columns={c: "previsto"}).assign(metodo=nome)
               for nome, c in metodi.items()]).to_csv(OUT / "snt_confusione.csv", index=False)
    R.say("\nMatrice di confusione di Qwen (righe = annotazione a mano):")
    R.say(pd.crosstab(A.vero, A.sentiment).to_string())
    inv = {v.lower(): k for k, v in NOMI.items()} | {k.lower(): v for k, v in NOME_Q.items()} | \
          {"nessuna": "none", "piu' regioni": "several"}
    A["reg_vera"] = A.regione_umana.str.strip().str.lower().map(inv)
    A["reg_q"] = A.main_region.map(lambda r: NOME_Q.get(r, r))
    Rg = A.dropna(subset=["reg_vera"])
    R.say(f"\nRegione corretta (n = {len(Rg)}): Qwen {(Rg.reg_q == Rg.reg_vera).mean():.1%} | "
          f"solo dizionario {(Rg.regioni == Rg.reg_vera).mean():.1%}")
    pd.DataFrame({"n": [len(Rg)], "qwen": [(Rg.reg_q == Rg.reg_vera).mean()],
                  "dizionario": [(Rg.regioni == Rg.reg_vera).mean()]}).round(4).to_csv(OUT / "snt_validazione_regione.csv", index=False)

# ================================================================ E. tono nel corso dell'anno
R.titolo("E. TONO NEL CORSO DELL'ANNO")
ist = pd.read_csv(PROC / "istat.csv")
ist = ist[(ist.market == "estero") & ist.TIME_PERIOD.str[:4].isin(["2023", "2024"])]
arr = ist.groupby("TIME_PERIOD").arrivi.sum()
arr = arr.groupby(arr.index.str[5:].astype(int)).mean() / 1e6
M = pd.DataFrame({"punteggio": d.groupby("mese").score.mean(),
                  "quota_negativi": d.groupby("mese").sentiment.apply(lambda s: (s == "negative").mean()),
                  "arrivi_stranieri_mln": arr})
M.round(4).to_csv(OUT / "snt_mesi.csv")
r_m = stats.pearsonr(M.punteggio, M.arrivi_stranieri_mln)
w, s_ = d[d.stagione == "inverno"], d[d.stagione == "estate"]
p_t = stats.ttest_ind(s_.score, w.score, equal_var=False).pvalue
R.say(M.round(3).to_string())
R.say(f"\nCorrelazione tra punteggio mensile e arrivi stranieri: {r_m[0]:.2f} (p = {r_m[1]:.4f})")
R.say(f"Inverno (dic-mar) vs estate (giu-set): punteggio {w.score.mean():.3f} -> {s_.score.mean():.3f} (p = {p_t:.1e}); "
      f"testi negativi {(w.sentiment == 'negative').mean():.1%} -> {(s_.sentiment == 'negative').mean():.1%}")
pd.DataFrame({"stagione": ["inverno", "estate"], "punteggio": [w.score.mean(), s_.score.mean()],
              "quota_negativi": [(w.sentiment == "negative").mean(), (s_.sentiment == "negative").mean()],
              "p_value": [p_t, p_t], "r_mesi_arrivi": [r_m[0], r_m[0]]}).round(5).to_csv(OUT / "snt_stagioni.csv", index=False)

fig, ax = plt.subplots(figsize=(10, 4.2))
ax2 = ax.twinx()
ax2.bar(range(1, 13), M.arrivi_stranieri_mln, color=COL["griglia"], width=0.6, zorder=0)
ax2.set_ylabel("arrivi stranieri ISTAT (milioni, media 2023-24)", color=COL["grigio"]); ax2.grid(False)
ax.plot(range(1, 13), M.punteggio, color=COL["arancio"], marker="o", lw=2.5, zorder=3)
ax.set_zorder(ax2.get_zorder() + 1); ax.patch.set_visible(False)
ax.set_xticks(range(1, 13)); ax.set_xticklabels(MESI); ax.set_ylabel("sentiment medio (Qwen, da -2 a +2)")
ax.set_title(f"Il tono cala quando arrivano i turisti (correlazione {r_m[0]:.2f})")
R.salva_grafico(fig, "snt1_mesi")

# ================================================================ F. aspetti
R.titolo("F. CHE COSA PEGGIORA D'ESTATE")
righe = []
for a, nome in ASPETTI.items():
    c = d[d[f"asp_{a}"] != "not_mentioned"]
    cw, cs = c[c.stagione == "inverno"], c[c.stagione == "estate"]
    nw, ns = cw[f"asp_{a}"] == "negative", cs[f"asp_{a}"] == "negative"
    p = stats.chi2_contingency([[nw.sum(), (~nw).sum()], [ns.sum(), (~ns).sum()]])[1]
    righe.append(dict(aspetto=nome, testi_che_lo_giudicano=(d[f"asp_{a}"] != "not_mentioned").mean(),
                      negativi_inverno=nw.mean(), negativi_estate=ns.mean(), differenza=ns.mean() - nw.mean(),
                      menzioni_inverno=(w[f"asp_{a}"] != "not_mentioned").mean(),
                      menzioni_estate=(s_[f"asp_{a}"] != "not_mentioned").mean(), p_value=p))
AS = pd.DataFrame(righe).set_index("aspetto")
AS.round(5).to_csv(OUT / "snt_aspetti.csv")
R.say("Quota di giudizi negativi tra i testi che giudicano l'aspetto:")
R.say(AS.round(3).to_string())
fig, ax = plt.subplots(figsize=(10, 4.3))
x = np.arange(len(AS))
ax.bar(x - 0.2, AS.negativi_inverno * 100, 0.38, color=COL["blu"], label="inverno (dic-mar)")
ax.bar(x + 0.2, AS.negativi_estate * 100, 0.38, color=COL["arancio"], label="estate (giu-set)")
for i, (a, b) in enumerate(zip(AS.negativi_inverno, AS.negativi_estate)):
    ax.text(i + 0.2, b * 100 + 1, f"{100 * (b - a):+.1f}", ha="center", fontsize=9, color=COL["testo"])
ax.set_xticks(x); ax.set_xticklabels(AS.index); ax.set_ylabel("% di giudizi negativi")
ax.legend(); ax.set_title("Giudizi negativi per aspetto: inverno contro estate (sopra le barre: differenza in punti)")
R.salva_grafico(fig, "snt2_aspetti")

# ================================================================ G. temi e sentiment
R.titolo("G. TEMI E SENTIMENT: COSA CAMBIA D'ESTATE?")
tm = pd.read_csv(OUT / "tm_testi.csv.gz", dtype={"id": str}, usecols=["id", "nome_tema"])
g = d.merge(tm, on="id")
R.say(f"Testi con tema e sentiment: {len(g):,}")
s2 = g[g.stagione.isin(["inverno", "estate"])]
pi = s2.groupby(["stagione", "nome_tema"]).size().unstack(fill_value=0)
pi = pi.div(pi.sum(1), axis=0)
st_ = s2.groupby(["stagione", "nome_tema"]).score.mean().unstack()
diff = s2[s2.stagione == "estate"].score.mean() - s2[s2.stagione == "inverno"].score.mean()
comp = ((pi.loc["estate"] - pi.loc["inverno"]) * st_.loc["inverno"]).sum()
inter = (pi.loc["estate"] * (st_.loc["estate"] - st_.loc["inverno"])).sum()
T_ = pd.DataFrame({"quota": g.nome_tema.value_counts(normalize=True), "punteggio": g.groupby("nome_tema").score.mean(),
                   "quota_inverno": pi.loc["inverno"], "quota_estate": pi.loc["estate"],
                   "punteggio_inverno": st_.loc["inverno"], "punteggio_estate": st_.loc["estate"]}).sort_values("quota", ascending=False)
T_.round(4).to_csv(OUT / "snt_temi.csv")
pd.DataFrame({"differenza": [diff], "composizione": [comp], "interno": [inter],
              "quota_interno": [inter / diff]}).round(5).to_csv(OUT / "snt_scomposizione.csv", index=False)
R.say(T_.round(3).to_string())
R.say(f"\nDifferenza estate - inverno: {diff:+.3f} = composizione {comp:+.3f} ({comp / diff:.0%}) "
      f"+ interno {inter:+.3f} ({inter / diff:.0%})")
fig, ax = plt.subplots(figsize=(10, 0.5 * len(T_) + 1.5))
y = np.arange(len(T_))
ax.scatter(T_.punteggio_inverno, y, color=COL["blu"], s=50, label="inverno (dic-mar)", zorder=3)
ax.scatter(T_.punteggio_estate, y, color=COL["arancio"], s=50, label="estate (giu-set)", zorder=3)
for i in range(len(T_)):
    ax.plot([T_.punteggio_inverno.iloc[i], T_.punteggio_estate.iloc[i]], [i, i], color=COL["griglia2"], lw=1.5, zorder=1)
ax.set_yticks(y); ax.set_yticklabels(T_.index); ax.invert_yaxis()
ax.set_xlabel("sentiment medio (Qwen)"); ax.legend(fontsize=9)
ax.set_title(f"Stesso tema, inverno contro estate: il {inter / diff:.0%} del calo avviene dentro i temi")
R.salva_grafico(fig, "snt3_temi")
R.chiudi()