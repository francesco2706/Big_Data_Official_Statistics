"""
SCRIPT 9 - Preparazione dei testi per Qwen (Kaggle) e del campione da annotare a mano

Produce i seguenti dataset:
  completo.csv              tutti i testi 2023-2024 che citano almeno una regione, esclusi bot e moderatori
                            (128.002), con le regioni trovate dal dizionario (colonna regioni_diz)
  gold_testi.csv            i 300 testi del campione annotato a mano, nello stesso formato
  script_10_qwen_kaggle.py  lo script da eseguire su Kaggle
  gold_da_annotare.csv      300 testi (15 per regione, ordine casuale) da etichettare a mano, senza nessun giudizio
                            automatico visibile ("alla cieca"): e' il riferimento per misurare l'accuratezza
  meta_testi.csv            mese, regioni del dizionario, punteggio VADER (usato come termine di paragone) e lunghezza

  * Qwen riceve le regioni trovate dal dizionario e sceglie tra queste quella di cui il testo parla davvero: il
    dizionario conosce bene la geografia (Matera -> Basilicata, Termoli -> Molise), il modello capisce il contenuto.
  * I testi oltre MAX_CAR caratteri vengono tagliati: la colonna troncato lo segnala.
"""
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from script_0_comune import LLM, PROC

KAG = LLM / "kaggle"
KAG.mkdir(parents=True, exist_ok=True)
MAX_CAR = 6000
N_GOLD_REG = 15
SEED = 0

cols = ["id", "kind", "TIME_PERIOD", "bot", "mod", "compound_tur", "regioni", "n_regioni", "n_char", "text"]
parti = []
for c in pd.read_csv(PROC / "reddit_testi.csv.gz", usecols=cols, chunksize=100_000,
                     dtype={"regioni": str, "id": str}):
    c = c[c.TIME_PERIOD.between("2023-01", "2024-12") & (c.bot.astype(str) != "True")
          & (c["mod"].astype(str) != "True") & c.regioni.notna() & c.text.notna()]
    parti.append(c.drop(columns=["bot", "mod"]))
T = pd.concat(parti, ignore_index=True)
T["troncato"] = T.text.str.len() > MAX_CAR
T["text"] = T.text.str.slice(0, MAX_CAR)
print(f"Testi 2023-2024 con almeno una regione: {len(T):,} | troncati a {MAX_CAR} caratteri: {T.troncato.sum()}")

NOME_LUNGO = {"ITC1": "Piemonte", "ITC2": "Valle d'Aosta", "ITC3": "Liguria", "ITC4": "Lombardia",
              "ITDA": "Trentino-Alto Adige", "ITD3": "Veneto", "ITD4": "Friuli-Venezia Giulia", "ITD5": "Emilia-Romagna",
              "ITE1": "Toscana", "ITE2": "Umbria", "ITE3": "Marche", "ITE4": "Lazio", "ITF1": "Abruzzo", "ITF2": "Molise",
              "ITF3": "Campania", "ITF4": "Puglia", "ITF5": "Basilicata", "ITF6": "Calabria", "ITG1": "Sicilia",
              "ITG2": "Sardegna"}
T["regioni_diz"] = T.regioni.str.split(";").map(lambda l: "; ".join(NOME_LUNGO[c] for c in l if c in NOME_LUNGO))
KAGGLE = ["id", "regioni_diz", "text"]        # su Kaggle serve solo questo
T[KAGGLE].to_csv(KAG / "completo.csv", index=False)

# ---------------------------------------------------------------- campione da annotare a mano
f_gold = LLM / "gold_da_annotare.csv"
if f_gold.exists():
    # contiene le annotazioni fatte a mano: non si rigenera, si riusano gli stessi testi nello stesso ordine
    ids = pd.read_csv(f_gold, dtype={"id": str}, usecols=["id"]).id
    G = T.set_index("id").loc[ids].reset_index()
    print(f"Campione annotato: {f_gold} esiste gia' ({len(G)} testi), non viene sovrascritto")
else:
    # 15 testi per regione tra quelli che citano una sola regione (cosi' anche la regione si giudica facilmente);
    # i testi lunghi pesano il doppio, per avere abbastanza casi difficili
    U = T[T.n_regioni == 1].assign(peso=lambda d: np.where(d.n_char > 600, 2.0, 1.0))
    G = (U.groupby("regioni", group_keys=False)[U.columns.tolist()]
          .apply(lambda d: d.sample(min(N_GOLD_REG, len(d)), weights="peso", random_state=SEED))
          .sample(frac=1, random_state=SEED))
    pd.DataFrame({"id": G.id, "testo": G.text, "sentiment_umano": "", "regione_umana": "", "note": ""}) \
      .to_csv(f_gold, index=False, encoding="utf-8-sig")              # utf-8-sig: si apre bene in Excel
    print(f"Campione da annotare: {len(G)} testi in data/llm/gold_da_annotare.csv")
G[KAGGLE].to_csv(KAG / "gold_testi.csv", index=False)

# metadati locali (non vanno su Kaggle), usati dagli script 11-13
T.drop(columns=["text"]).to_csv(LLM / "meta_testi.csv", index=False)
shutil.copy(Path(__file__).with_name("script_10_qwen_kaggle.py"), KAG / "script_10_qwen_kaggle.py")
for f in ["completo.csv", "gold_testi.csv", "script_10_qwen_kaggle.py"]:
    print(f"  kaggle/{f:26s} {(KAG / f).stat().st_size / 1e6:6.2f} MB")