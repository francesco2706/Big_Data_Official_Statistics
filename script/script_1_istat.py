"""
SCRIPT 1 - Pulizia e controllo dei dati ISTAT (arrivi e presenze)

Dataset ISTAT di riferimento (Movimento dei clienti negli esercizi ricettivi, DCSC_TUR, mensile).csv
"""

# Questo file prende il file scaricato da IstatData, controlla la coerenza interna e 
# tiene solo le serie storiche che servono e prepara la variabile
# da stimare per tutto il progetto. inoltre unisce il Trentino Alto Adige (Bolzano e Trento)

# Variabili derivate: 
# - permanenza media: per ogni mese divide le presenze (notti trascorse) per gli arrivi (clienti arrivati)

# - variazione annua logaritmica: target del nowcasting --> per ogni mese, questo script prende gli arrivi del mese
# e dello stesso mese dell'anno precedente; calcola il logaritmo di entrambi i valori e successivamente fa la differenza
# y_t = log A_t - log A_(t-12)

# - Indicatore di periodo: assegna ad ogni mese un'etichetta in base alla data: pre-COVID, COVID e post-COVID

# Inoltre vengono scartati i dati 2025 perchè sono dati provvisori.

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # cartella ZZ_TURISM
RAW, PROC, OUT_DIR = (os.path.join(ROOT, "data", "raw"), os.path.join(ROOT, "data", "processed"),
                      os.path.join(ROOT, "output"))
src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAW, "istat", "istat_movimento_clienti_mensile.csv")
FINE = "2024-12" 
here = os.path.dirname(os.path.abspath(__file__))
log = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    log.append(s)


NOMI = {"ITC1": "Piemonte", "ITC2": "Valle d'Aosta", "ITC3": "Liguria", "ITC4": "Lombardia", "ITDA": "Trentino-Alto Adige",
        "ITD3": "Veneto", "ITD4": "Friuli-Venezia Giulia", "ITD5": "Emilia-Romagna", "ITE1": "Toscana", "ITE2": "Umbria",
        "ITE3": "Marche", "ITE4": "Lazio", "ITF1": "Abruzzo", "ITF2": "Molise", "ITF3": "Campania", "ITF4": "Puglia",
        "ITF5": "Basilicata", "ITF6": "Calabria", "ITG1": "Sicilia", "ITG2": "Sardegna"}
MERCATO = {"IT": "domestico", "WRL_X_ITA": "estero"}

d = pd.read_csv(src, low_memory=False,
                usecols=["REF_AREA", "DATA_TYPE", "TYPE_ACCOMMODATION", "COUNTRY_RES_GUESTS", "TIME_PERIOD", "OBS_VALUE", "OBS_STATUS"])
say(f"Righe lette: {len(d):,} | periodo {d.TIME_PERIOD.min()} - {d.TIME_PERIOD.max()}")

# ---------------------------------------------------------------- controllo 1: osservazioni con stato particolare
st = d[d.OBS_STATUS.notna()]
say(f"\n[1] Osservazioni con OBS_STATUS valorizzato: {len(st)}")
if len(st):
    say(st.to_string(index=False))

# ---------------------------------------------------------------- controllo 2: IT + WRL_X_ITA = WORLD
w = d.pivot_table(index=["REF_AREA", "DATA_TYPE", "TYPE_ACCOMMODATION", "TIME_PERIOD"], columns="COUNTRY_RES_GUESTS", values="OBS_VALUE")
w = w.dropna(subset=["WORLD"])
diff = (w.IT + w.WRL_X_ITA - w.WORLD).abs()
say(f"\n[2] IT + WRL_X_ITA = WORLD (dal 2016, {len(w):,} confronti): differenze non nulle = {(diff > 0).sum()}, "
    f"differenza massima = {diff.max():,.0f}")

# ---------------------------------------------------------------- controllo 3: ALL = HOTELLIKE + OTHER
s = d.pivot_table(index=["REF_AREA", "DATA_TYPE", "COUNTRY_RES_GUESTS", "TIME_PERIOD"], columns="TYPE_ACCOMMODATION", values="OBS_VALUE")
diff = (s.HOTELLIKE + s.OTHER - s.ALL).abs()
say(f"[3] HOTELLIKE + OTHER = ALL ({len(s):,} confronti): differenze non nulle = {(diff > 0).sum()}, differenza massima = {diff.max():,.0f}")

# ---------------------------------------------------------------- selezione e unione Trentino-Alto Adige
x = d[(d.TYPE_ACCOMMODATION == "ALL") & d.COUNTRY_RES_GUESTS.isin(MERCATO)].copy()
x["REF_AREA"] = x.REF_AREA.replace({"ITD1": "ITDA", "ITD2": "ITDA"})
x["market"] = x.COUNTRY_RES_GUESTS.map(MERCATO)
x = x.groupby(["REF_AREA", "market", "TIME_PERIOD", "DATA_TYPE"], as_index=False).OBS_VALUE.sum()
t = x.pivot_table(index=["REF_AREA", "market", "TIME_PERIOD"], columns="DATA_TYPE", values="OBS_VALUE").reset_index()
t.columns.name = None
t = t.rename(columns={"AR": "arrivi", "NI": "presenze"})
t["regione"] = t.REF_AREA.map(NOMI)
t = t.sort_values(["REF_AREA", "market", "TIME_PERIOD"]).reset_index(drop=True)

# ---------------------------------------------------------------- controllo 4: completezza e valori anomali
n = t.groupby(["REF_AREA", "market"]).TIME_PERIOD.nunique()
say(f"\n[4] Serie regione x mercato: {len(n)} | mesi per serie: {n.min()}-{n.max()} | "
    f"valori mancanti: {t[['arrivi', 'presenze']].isna().sum().sum()} | mesi con zero arrivi: {(t.arrivi == 0).sum()}")
bad = t[t.presenze < t.arrivi]
say(f"    mesi con presenze < arrivi (impossibile: ogni arrivo genera almeno una notte): {len(bad)}")
if len(bad):
    say(bad.head(10).to_string(index=False))

# ---------------------------------------------------------------- trasformazioni
g = t.groupby(["REF_AREA", "market"])
t["permanenza_media"] = t.presenze / t.arrivi
for c in ("arrivi", "presenze"):
    lag = g[c].shift(12)
    t[f"yoy_{c}"] = np.log(t[c].where(t[c] > 0)) - np.log(lag.where(lag > 0))
t["periodo"] = np.select([t.TIME_PERIOD < "2020-03", t.TIME_PERIOD < "2022-04"], ["pre-COVID", "COVID"], "post-COVID")
# la variazione annua e' distorta anche nei 12 mesi dopo il COVID (confronto con mesi chiusi): flag separato
t["yoy_base_covid"] = t.TIME_PERIOD.between("2020-03", "2023-03")

# ---------------------------------------------------------------- riepilogo
say("\n[5] Variazione annua degli arrivi (mediana tra regioni) per anno e mercato:")
t["anno"] = t.TIME_PERIOD.str[:4]
say(t[t.anno >= "2011"].groupby(["anno", "market"]).yoy_arrivi.median().unstack().round(3).to_string())
say("\n[6] Arrivi annui (milioni) e quota estera:")
a = t.groupby(["anno", "market"]).arrivi.sum().unstack() / 1e6
a["quota_estero"] = a.estero / (a.estero + a.domestico)
say(a.loc["2011":].round(2).to_string())

t = t.drop(columns="anno")
t = t[t.TIME_PERIOD <= FINE]
say(f"\nPeriodo salvato: {t.TIME_PERIOD.min()} - {t.TIME_PERIOD.max()} (2025 escluso)")
t.to_csv(os.path.join(PROC, "istat_target.csv"), index=False)
open(os.path.join(OUT_DIR, "controlli", "istat_controlli.txt"), "w").write("\n".join(log))
say(f"\nSalvati istat_target.csv ({t.shape[0]:,} righe) e istat_controlli.txt")