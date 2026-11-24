"""
SCRIPT 3 - Unisce i 20 CSV scaricati dalla console (trends_ITxx_rep1.csv) in data/processed/trends_rep1_all.csv.
"""
import glob
import os
import re
import sys
import zipfile

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cartella = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "raw", "trends", "trends_rep1.zip")
if cartella.endswith(".zip"):
    z = zipfile.ZipFile(cartella)
    file = sorted(n for n in z.namelist() if re.match(r"trends_IT\w+_rep1\.csv$", os.path.basename(n)))
    tabelle = [pd.read_csv(z.open(n)) for n in file]
else:
    file = sorted(glob.glob(os.path.join(cartella, "trends_IT*_rep1.csv")))
    tabelle = [pd.read_csv(f) for f in file]
print(f"File trovati: {len(file)}")
if len(file) != 20:
    print("Warning: expected 20 files, one for region.")

df = pd.concat(tabelle, ignore_index=True)
df["hasData"] = df.hasData.astype(str).str.lower() == "true"
df = df.sort_values(["REF_AREA", "geo", "cat", "ordine", "TIME_PERIOD"]).reset_index(drop=True)

# controlli: una riga per regione x Paese x categoria x argomento x mese
dup = df.duplicated(["REF_AREA", "geo", "cat", "ordine", "TIME_PERIOD"]).sum()
print(f"Righe: {len(df):,} | regioni: {df.REF_AREA.nunique()} | Paesi: {df.geo.nunique()} | "
      f"categorie: {df.cat.nunique()} | mesi: {df.TIME_PERIOD.min()} - {df.TIME_PERIOD.max()} | duplicati: {dup}")
print("Combinazioni regione x Paese x categoria:", df.groupby(["REF_AREA", "geo", "cat"]).ngroups, "(attese 360)")

dest = os.path.join(ROOT, "data", "processed", "trends_rep1_all.csv")
os.makedirs(os.path.dirname(dest), exist_ok=True)
df.to_csv(dest, index=False)
print(f"Salvato: {dest}")
