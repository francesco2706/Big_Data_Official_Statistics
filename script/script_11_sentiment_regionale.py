"""
SCRIPT 11 - Sentiment regionale (pilastro Reputazione dell'indicatore)

Per ogni regione stima il tono con cui i turisti stranieri ne parlano su Reddit nel 2023-2024, a partire dal punteggio
di Qwen di ogni testo (da -2 a +2, script 10). La stima tiene conto di tre fatti:
  * stagionalita': il tono del forum cala d'estate; ogni testo e' confrontato con il tono medio del suo mese
    (destagionalizzazione), cosi' una regione discussa soprattutto d'estate non e' penalizzata dal calendario;
  * dipendenza dentro le discussioni: i commenti di uno stesso thread condividono il tono, quindi l'errore standard
    e' calcolato raggruppando per thread (cluster);
  * regioni con pochi testi: la media regionale e' combinata con la media nazionale in proporzione alla sua
    incertezza (shrinkage bayesiano empirico):
        media osservata y_r ~ N(theta_r, se_r^2),   theta_r ~ N(mu, tau^2)
        stima = mu + (1 - B_r) (y_r - mu),          B_r = se_r^2 / (se_r^2 + tau^2)
    con tau^2 (varianza vera tra regioni) stimata con il metodo dei momenti di DerSimonian-Laird.
La regione di un testo e' quella scelta da Qwen tra le regioni citate; un testo su piu' regioni conta per ognuna; un
testo che cita le regioni solo di passaggio e' escluso. Lo script misura anche il legame tra volume di discussione e
tono, e costruisce una variante "al netto del volume" usata nell'analisi di incertezza dell'indicatore.
"""
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt

from script_0_comune import COL, NOMI, LLM, OUT, PROC, REG, Registro

R = Registro("rep_risultati.txt")
ANNI = ("2023-01", "2024-12")
MIN_THREAD = 150                         # sotto questa soglia la regione e' segnalata come poco affidabile
NOME_Q = {"Piemonte": "ITC1", "Valle d'Aosta": "ITC2", "Liguria": "ITC3", "Lombardia": "ITC4",
          "Trentino-Alto Adige": "ITDA", "Veneto": "ITD3", "Friuli-Venezia Giulia": "ITD4", "Emilia-Romagna": "ITD5",
          "Toscana": "ITE1", "Umbria": "ITE2", "Marche": "ITE3", "Lazio": "ITE4", "Abruzzo": "ITF1", "Molise": "ITF2",
          "Campania": "ITF3", "Puglia": "ITF4", "Basilicata": "ITF5", "Calabria": "ITF6", "Sicilia": "ITG1",
          "Sardegna": "ITG2"}

# ================================================================ 1. testi e punteggi
R.titolo("1. TESTI 2023-2024 CLASSIFICATI DA QWEN")
parti = []
for c in pd.read_csv(PROC / "reddit_testi.csv.gz", usecols=["id", "link_id", "TIME_PERIOD", "regioni"],
                     chunksize=200_000, dtype={"id": str, "regioni": str, "link_id": str}):
    parti.append(c[c.TIME_PERIOD.between(*ANNI)])
T = pd.concat(parti, ignore_index=True)
Q = pd.read_csv(LLM / "qwen_completo.csv", dtype={"id": str}, usecols=["id", "score", "main_region"])
T = T.merge(Q, on="id")
T["score"] = T.score.astype(float)
# regione: quella scelta da Qwen; "several" -> tutte le regioni citate; "none" (solo citata di passaggio) -> esclusa
T["reg"] = np.where(T.main_region.isin(list(NOME_Q)), T.main_region.map(NOME_Q),
                    np.where(T.main_region == "several", T.regioni, None))
R.say(f"Testi: {len(T):,} | esclusi perche' le regioni sono solo citate: {(T.main_region == 'none').sum():,} | "
      f"su piu' regioni: {(T.main_region == 'several').sum():,}")

# ================================================================ 2. destagionalizzazione
R.titolo("2. DESTAGIONALIZZAZIONE")
T["dest"] = T.score - T.groupby("TIME_PERIOD").score.transform("mean") + T.score.mean()
R.say("Punteggio medio per mese dell'anno (tolto da ogni testo):")
R.say(T.groupby(T.TIME_PERIOD.str[5:]).score.mean().round(3).to_frame("media").T.to_string())
X = T.dropna(subset=["reg"]).assign(REF_AREA=lambda d: d.reg.str.split(";")).explode("REF_AREA")
X = X[X.REF_AREA.isin(REG)]


# ================================================================ 3. media ed errore standard per thread
def stima_regione(d, col):
    """Media dei testi ed errore standard robusto alla correlazione dentro i thread (cluster CR1)."""
    x = d[col].to_numpy()
    n, m = len(x), x.mean()
    s_g = (d[col] - m).groupby(d.link_id.values).sum().to_numpy()
    G = len(s_g)
    var = (G / max(G - 1, 1)) * (s_g @ s_g) / n ** 2
    return pd.Series(dict(n_testi=n, n_thread=G, media=m, se=np.sqrt(var), se_ingenuo=x.std(ddof=1) / np.sqrt(n)))


R.titolo("3. MEDIA PER REGIONE CON ERRORE STANDARD PER THREAD")
reg = X.groupby("REF_AREA")[["dest", "link_id"]].apply(lambda d: stima_regione(d, "dest")).reindex(REG)
reg["grezzo"] = X.groupby("REF_AREA").score.mean().reindex(REG)
reg["effetto_disegno"] = (reg.se / reg.se_ingenuo) ** 2
R.say("effetto_disegno = di quante volte la varianza sarebbe sottostimata trattando i testi come indipendenti")
R.say(reg.rename(index=NOMI)[["n_testi", "n_thread", "grezzo", "media", "se", "effetto_disegno"]].round(4).to_string())

# ================================================================ 4. shrinkage bayesiano empirico
R.titolo("4. SHRINKAGE BAYESIANO EMPIRICO")
y, v = reg.media.to_numpy(), reg.se.to_numpy() ** 2
w = 1 / v
mu0 = np.sum(w * y) / np.sum(w)
Qs = np.sum(w * (y - mu0) ** 2)
tau2 = max(0.0, (Qs - (len(y) - 1)) / (np.sum(w) - np.sum(w ** 2) / np.sum(w)))
mu = np.sum(y / (v + tau2)) / np.sum(1 / (v + tau2))
B = v / (v + tau2)
reg["peso_dati"] = 1 - B
reg["shrink"] = mu + (1 - B) * (y - mu)
reg["shrink_se"] = np.sqrt((1 - B) * v)
reg["ci_lo"], reg["ci_hi"] = reg.shrink - 1.96 * reg.shrink_se, reg.shrink + 1.96 * reg.shrink_se
reg["affidabile"] = reg.n_thread >= MIN_THREAD
R.say(f"media nazionale mu = {mu:.4f} | dev. std. vera tra regioni tau = {np.sqrt(tau2):.4f}")
R.say(f"quota della variabilita' tra regioni che e' segnale (regione tipica) = {tau2 / (tau2 + np.median(v)):.0%}")
tab = reg.rename(index=NOMI).sort_values("shrink", ascending=False)
R.say(tab[["n_thread", "media", "peso_dati", "shrink", "ci_lo", "ci_hi", "affidabile"]].round(3).to_string())
dist = tab[(tab.ci_lo > mu) | (tab.ci_hi < mu)]
R.say(f"\nRegioni con tono significativamente diverso dalla media: {len(dist)} su 20 ({', '.join(dist.index)})")
R.say(f"Regioni poco affidabili (< {MIN_THREAD} thread): {', '.join(tab.index[~tab.affidabile]) or 'nessuna'}")

# ================================================================ 5. tono e volume di discussione
R.titolo("5. TONO E VOLUME DI DISCUSSIONE")
lx = np.log(reg.n_testi)
rho = stats.spearmanr(lx, reg.shrink)
R.say(f"Spearman(log numero di testi, sentiment) = {rho.correlation:.2f} (p = {rho.pvalue:.3f})")
b = np.polyfit(lx, reg.shrink, 1)
reg["netto_volume"] = reg.shrink - np.polyval(b, lx) + reg.shrink.mean()
R.say(f"Raddoppiare i testi sposta il sentiment di {b[0] * np.log(2):+.4f}. La variante 'al netto del volume' toglie\n"
      "questa relazione: non e' la misura principale (l'affollamento fa parte dell'esperienza), ma entra nell'analisi\n"
      "di incertezza dell'indicatore.")
reg.assign(regione=reg.index.map(NOMI)).round(5).to_csv(OUT / "rep_regioni.csv")

# ================================================================ grafici
o = tab.iloc[::-1]
yy = np.arange(len(o))
fig, ax = plt.subplots(figsize=(9, 7))
ax.hlines(yy, o.ci_lo, o.ci_hi, color=COL["griglia2"], lw=5, label="intervallo al 95%")
ax.scatter(o.media, yy, color=COL["grigio"], marker="x", s=40, zorder=3, label="media della regione")
ax.scatter(o.shrink, yy, color=[COL["giallo"] if a else COL["arancio"] for a in o.affidabile], s=45, zorder=4,
           label="stima (shrinkage)")
ax.axvline(mu, color=COL["nero"], ls="--", lw=1)
ax.set_yticks(yy); ax.set_yticklabels(o.index)
ax.set_xlabel("sentiment (Qwen, da -2 a +2), destagionalizzato")
ax.set_title("Tono con cui si parla di ogni regione su Reddit (2023-2024)")
ax.legend(fontsize=8.5, loc="lower right")
R.salva_grafico(fig, "rep1_sentiment_regioni")

fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(reg.n_testi, reg.shrink, color=COL["giallo"], s=45, zorder=3)
xs = np.linspace(lx.min(), lx.max(), 50)
ax.plot(np.exp(xs), np.polyval(b, xs), color=COL["grigio"], ls="--")
for r_ in REG:
    ax.annotate(NOMI[r_], (reg.n_testi[r_], reg.shrink[r_]), xytext=(4, 2), textcoords="offset points", fontsize=8)
ax.set_xscale("log"); ax.set_xlabel("testi sulla regione, 2023-2024 (scala log)")
ax.set_ylabel("sentiment (stima)")
ax.set_title(f"Si parla peggio delle regioni piu' discusse? (Spearman {rho.correlation:.2f})")
R.salva_grafico(fig, "rep2_volume")
R.chiudi()