"""
SCRIPT 6 - Testi di Reddit: pulizia, regioni citate, aggregati mensili

Reddit r/ItalyTravel (post e commenti, 2022-2025). Legge i file .jsonl riga per riga:
  1. pulizia: scarta testi rimossi/cancellati e vuoti, toglie link e formattazione, segna bot (AutoModerator, ...) e
     messaggi dei moderatori (esclusi da tutti gli aggregati)
  2. regioni citate: dizionario di nomi di regioni, citta' e mete in inglese e italiano, coerente con le mete usate per
     Google Trends e Wikipedia (ricerca per parola intera, senza distinguere maiuscole e minuscole)
  3. punteggio di sentiment a dizionario (VADER adattato ai viaggi, script_5_vader_turismo.py): nel progetto e' usato
     solo come termine di paragone nella validazione del modello linguistico (script 12). Le colonne compound /
     sentiment_orig contengono il VADER standard, per completezza
  4. aggregati mensili per regione: numero di testi che la citano e quota sul totale del mese (la community cresce)
"""
# pip install pandas vaderSentiment
import argparse
import gzip
import json
import os
import re
import time

import numpy as np
import pandas as pd

ap = argparse.ArgumentParser()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap.add_argument("--posts", default=os.path.join(ROOT, "data", "raw", "reddit", "r_ItalyTravel_posts.jsonl"))
ap.add_argument("--comments", default=os.path.join(ROOT, "data", "raw", "reddit", "r_ItalyTravel_comments.jsonl"))
ap.add_argument("--start", default="2022-01")
ap.add_argument("--end", default="2025-12")
args = ap.parse_args()
here = os.path.join(ROOT, "data", "processed")
CONTROLLI = os.path.join(ROOT, "output", "controlli")
OUT_TXT = os.path.join(here, "reddit_testi.csv.gz")
log = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    log.append(s)


# ---------------------------------------------------------------- dizionario regioni
GAZ = {
    "ITC1": ["Piedmont", "Piemonte", "Turin", "Torino", "Langhe", "Barolo", "Alba", "Stresa", "Lake Maggiore", "Lago Maggiore", "Lake Orta",
             "Orta San Giulio", "Asti", "Sestriere"],
    "ITC2": ["Aosta", "Aosta Valley", "Valle d'Aosta", "Courmayeur", "Cervinia", "Breuil-Cervinia", "Gran Paradiso", "Mont Blanc", "Monte Bianco"],
    "ITC3": ["Liguria", "Cinque Terre", "Genoa", "Genova", "Portofino", "Riomaggiore", "Vernazza", "Monterosso", "Manarola", "Corniglia",
             "La Spezia", "Sanremo", "San Remo", "Santa Margherita", "Camogli", "Levanto", "Portovenere", "Porto Venere", "Lerici"],
    "ITC4": ["Lombardy", "Lombardia", "Milan", "Milano", "Lake Como", "Lago di Como", "Como", "Bellagio", "Varenna", "Menaggio", "Bergamo",
             "Brescia", "Mantua", "Mantova", "Sirmione", "Lake Iseo", "Cremona", "Livigno", "Bormio"],
    "ITDA": ["Dolomites", "Dolomiti", "South Tyrol", "Sudtirol", "Südtirol", "Alto Adige", "Trentino", "Trento", "Bolzano", "Bozen", "Ortisei",
             "Val Gardena", "Merano", "Alpe di Siusi", "Seiser Alm", "Seceda", "Braies", "Tre Cime", "Val di Funes", "Riva del Garda",
             "Madonna di Campiglio", "Canazei"],
    "ITD3": ["Veneto", "Venice", "Venezia", "Verona", "Padua", "Padova", "Vicenza", "Burano", "Murano", "Treviso", "Cortina",
             "Cortina d'Ampezzo", "Lake Garda", "Lago di Garda", "Bardolino", "Lazise", "Malcesine", "Jesolo", "Bassano"],
    "ITD4": ["Friuli", "Trieste", "Udine", "Aquileia", "Grado", "Cividale", "Lignano"],
    "ITD5": ["Emilia-Romagna", "Emilia Romagna", "Bologna", "Parma", "Modena", "Ravenna", "Rimini", "Ferrara", "Reggio Emilia",
             "Maranello", "Piacenza", "Riccione"],
    "ITE1": ["Tuscany", "Toscana", "Florence", "Firenze", "Pisa", "Siena", "Lucca", "San Gimignano", "Chianti", "Val d'Orcia",
             "Montepulciano", "Cortona", "Elba", "Arezzo", "Volterra", "Pienza", "Montalcino", "Viareggio", "Saturnia", "Livorno", "Maremma"],
    "ITE2": ["Umbria", "Perugia", "Assisi", "Orvieto", "Spoleto", "Gubbio", "Todi", "Spello", "Trasimeno"],
    "ITE3": ["Marche", "Le Marche", "Urbino", "Ancona", "Ascoli", "Conero", "Loreto", "Senigallia", "San Benedetto del Tronto"],
    "ITE4": ["Rome", "Roma", "Lazio", "Vatican", "Tivoli", "Ostia", "Civita di Bagnoregio", "Bagnoregio", "Fiumicino", "Trastevere",
             "Colosseum", "Colosseo", "Gaeta", "Sperlonga", "Viterbo"],
    "ITF1": ["Abruzzo", "Pescara", "L'Aquila", "Sulmona", "Gran Sasso", "Scanno", "Roccaraso"],
    "ITF2": ["Molise", "Campobasso", "Termoli", "Isernia"],
    "ITF3": ["Campania", "Naples", "Napoli", "Amalfi", "Amalfi Coast", "Positano", "Sorrento", "Capri", "Pompeii", "Pompei", "Ravello",
             "Ischia", "Salerno", "Herculaneum", "Ercolano", "Procida", "Vesuvius", "Paestum", "Praiano", "Anacapri", "Caserta", "Minori",
             "Maiori", "Atrani"],
    "ITF4": ["Puglia", "Apulia", "Bari", "Lecce", "Alberobello", "Polignano", "Polignano a Mare", "Ostuni", "Monopoli", "Salento", "Gallipoli",
             "Otranto", "Brindisi", "Locorotondo", "Gargano", "Vieste", "Trani"],
    "ITF5": ["Basilicata", "Matera", "Maratea"],
    "ITF6": ["Calabria", "Tropea", "Reggio Calabria", "Scilla", "Pizzo", "Cosenza", "Capo Vaticano", "Scalea"],
    "ITG1": ["Sicily", "Sicilia", "Palermo", "Taormina", "Catania", "Syracuse", "Siracusa", "Ortigia", "Etna", "Agrigento", "Cefalu", "Cefalù",
             "Noto", "Trapani", "Favignana", "Aeolian", "Lipari", "Stromboli", "Vulcano", "Salina", "Ragusa", "Modica", "Marsala", "Erice",
             "San Vito Lo Capo", "Messina"],
    "ITG2": ["Sardinia", "Sardegna", "Cagliari", "Alghero", "Olbia", "Costa Smeralda", "Cala Gonone", "La Maddalena", "Maddalena",
             "Porto Cervo", "Villasimius", "Nuoro", "Orosei"],
}
REGIONI = list(GAZ)
RX = {r: re.compile(r"\b(?:" + "|".join(re.escape(n) for n in sorted(ns, key=len, reverse=True)) + r")\b", re.I) for r, ns in GAZ.items()}
URL = re.compile(r"https?://\S+|www\.\S+")
MD = re.compile(r"[*_>#~`]|\[(.*?)\]\(.*?\)")
BOT = re.compile(r"(?:^automoderator$|bot$|^[a-z0-9_-]*-bot$)", re.I)


def pulisci(t):
    t = URL.sub(" ", t)
    t = MD.sub(lambda m: m.group(1) or " ", t)
    t = t.replace("&amp;", "&").replace("&gt;", ">").replace("&lt;", "<").replace("&#x200B;", " ")
    return re.sub(r"\s+", " ", t).strip()


# ---------------------------------------------------------------- 1-3: lettura, pulizia, sentiment, regioni
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from script_5_vader_turismo import VaderTurismo

vader = SentimentIntensityAnalyzer()
vader_tur = VaderTurismo()
SOGLIA = 0.4


def etichetta(c, thr):
    return "positivo" if c >= thr else ("negativo" if c <= -thr else "neutro")
cols = ["id", "kind", "TIME_PERIOD", "date", "author", "score", "link_id", "flair", "bot", "mod", "n_char",
        "compound", "pos", "neu", "neg", "sentiment_orig", "compound_tur", "sentiment", "regioni", "n_regioni", "text"]
conta = dict(lette=0, rimosse=0, vuote=0, fuori_periodo=0, tenute=0)


def leggi(path, kind):
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            conta["lette"] += 1
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if kind == "post":
                corpo = o.get("selftext") or ""
                rimosso = corpo in ("[removed]", "[deleted]") or o.get("removed_by_category")
                raw = (o.get("title") or "") + ". " + ("" if corpo in ("[removed]", "[deleted]") else corpo)
            else:
                raw = o.get("body") or ""
                rimosso = raw in ("[removed]", "[deleted]")
                if rimosso:
                    conta["rimosse"] += 1
                    continue
            if kind == "post" and rimosso:
                conta["rimosse"] += 1
            t = pulisci(raw)
            if len(t) < 3:
                conta["vuote"] += 1
                continue
            ts = pd.Timestamp(int(float(o["created_utc"])), unit="s")
            tp = ts.strftime("%Y-%m")
            if not (args.start <= tp <= args.end):
                conta["fuori_periodo"] += 1
                continue
            conta["tenute"] += 1
            yield o, kind, t, ts, tp


t0 = time.time()
if os.path.exists(OUT_TXT):
    os.remove(OUT_TXT)
buf, first, n = [], True, 0
for path, kind in ((args.posts, "post"), (args.comments, "comment")):
    for o, k, t, ts, tp in leggi(path, kind):
        s = vader.polarity_scores(t[:5000])
        ct = vader_tur.polarity_scores(t[:5000])["compound"]
        regs = [r for r in REGIONI if RX[r].search(t)]
        author = o.get("author") or ""
        buf.append(dict(
            id=o.get("id"), kind=k, TIME_PERIOD=tp, date=ts.strftime("%Y-%m-%d"), author=author, score=o.get("score"),
            link_id=(o.get("link_id") or "").replace("t3_", "") if k == "comment" else o.get("id"),
            flair=(o.get("link_flair_text") or "") if k == "post" else "",
            bot=bool(BOT.search(author)), mod=o.get("distinguished") == "moderator" or bool(o.get("stickied")),
            n_char=len(t), compound=s["compound"], pos=s["pos"], neu=s["neu"], neg=s["neg"],
            sentiment_orig=etichetta(s["compound"], 0.05), compound_tur=ct, sentiment=etichetta(ct, SOGLIA),
            regioni=";".join(regs), n_regioni=len(regs), text=t))
        n += 1
        if len(buf) >= 50000:
            pd.DataFrame(buf, columns=cols).to_csv(OUT_TXT, mode="a", header=first, index=False, compression="gzip")
            first, buf = False, []
            print(f"  {n:,} testi elaborati ({time.time() - t0:.0f} s)")
if buf:
    pd.DataFrame(buf, columns=cols).to_csv(OUT_TXT, mode="a", header=first, index=False, compression="gzip")
say(f"Lettura completata in {time.time() - t0:.0f} s: {conta}")

# ---------------------------------------------------------------- controlli
d = pd.read_csv(OUT_TXT, usecols=[c for c in cols if c != "text"], dtype={"regioni": str}, keep_default_na=False)
d["compound"] = d.compound.astype(float)
d["compound_tur"] = d.compound_tur.astype(float)
say(f"\nTesti tenuti: {len(d):,} (post {(d.kind == 'post').sum():,}, commenti {(d.kind == 'comment').sum():,}) | "
    f"periodo {d.TIME_PERIOD.min()} - {d.TIME_PERIOD.max()}")
say(f"Bot: {d.bot.sum():,} | messaggi dei moderatori/fissati: {d['mod'].sum():,} (esclusi dagli aggregati)")
say(f"Testi che citano almeno una regione: {(d.n_regioni > 0).mean():.1%} (post {(d[d.kind == 'post'].n_regioni > 0).mean():.1%}, "
    f"commenti {(d[d.kind == 'comment'].n_regioni > 0).mean():.1%})")
say("\nDistribuzione del sentiment per tipo di testo, VADER adattato (soglia 0.4):")
say(pd.crosstab(d.kind, d.sentiment, normalize="index").round(3).to_string())
say("VADER originale (soglia 0.05):")
say(pd.crosstab(d.kind, d.sentiment_orig, normalize="index").round(3).to_string())
say("\nTesti per anno:")
say(d.groupby([d.TIME_PERIOD.str[:4], "kind"]).size().unstack().to_string())

# ---------------------------------------------------------------- 4: aggregati mensili per regione
u = d[~d.bot & ~d["mod"]].copy()
tot = u.groupby("TIME_PERIOD").agg(n_testi_mese=("id", "size"), sent_medio_mese=("compound_tur", "mean"),
                                    sent_medio_mese_orig=("compound", "mean"))
long = u[u.n_regioni > 0].assign(REF_AREA=lambda x: x.regioni.str.split(";")).explode("REF_AREA")
m = long.groupby(["REF_AREA", "TIME_PERIOD"]).agg(
    n_testi=("id", "size"), n_post=("kind", lambda k: (k == "post").sum()),
    sent_medio=("compound_tur", "mean"), sent_medio_orig=("compound", "mean"),
    quota_pos=("sentiment", lambda s: (s == "positivo").mean()),
    quota_neg=("sentiment", lambda s: (s == "negativo").mean())).reset_index()
grid = pd.MultiIndex.from_product([REGIONI, sorted(u.TIME_PERIOD.unique())], names=["REF_AREA", "TIME_PERIOD"]).to_frame(index=False)
m = grid.merge(m, how="left").merge(tot.reset_index(), on="TIME_PERIOD")
m[["n_testi", "n_post"]] = m[["n_testi", "n_post"]].fillna(0).astype(int)
m["quota_testi"] = m.n_testi / m.n_testi_mese          # normalizzazione: la community cresce nel tempo
m.to_csv(os.path.join(here, "reddit_mensile.csv"), index=False)
say("\nTesti per regione (totale periodo) e sentiment medio:")
w = m.assign(sw=m.sent_medio.fillna(0) * m.n_testi, sw_o=m.sent_medio_orig.fillna(0) * m.n_testi)
r = w.groupby("REF_AREA")[["n_testi", "sw", "sw_o"]].sum()
r["sent_medio"], r["sent_medio_orig"] = r.sw / r.n_testi, r.sw_o / r.n_testi
say(r[["n_testi", "sent_medio", "sent_medio_orig"]].sort_values("n_testi", ascending=False).round(3).to_string())

open(os.path.join(CONTROLLI, "reddit_controlli.txt"), "w", encoding="utf-8").write("\n".join(log))
say("\nSalvati: reddit_testi.csv.gz, reddit_mensile.csv, reddit_controlli.txt")