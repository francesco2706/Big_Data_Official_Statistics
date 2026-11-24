"""
SCRIPT 4 - Download e aggregazione delle visite Wikipedia

Visualizzazioni mensili delle pagine Wikipedia (Wikimedia REST API), 2015-07 -> 2025-12 considerando stesse mete di Trends.
cinque edizioni linguistiche: it = domestico; en, de, fr, es = estero (proxy linguistico dei mercati
Regno Unito/Stati Uniti, Germania, Francia, Spagna)
"""
import argparse
import json
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

#contatto per lo User-Agent.
CONTATTO = os.environ.get("WIKI_CONTATTO", "contatto non impostato")
UA = f"BDOS-student-project/2.0 ({CONTATTO})"

ap = argparse.ArgumentParser()
ap.add_argument("step", choices=["titoli", "download", "aggrega"])
ap.add_argument("--mock", action="store_true")
ap.add_argument("--sleep", type=float, default=0.3)
args = ap.parse_args()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
here = os.path.join(ROOT, "data", "raw", "wikipedia")
PROC = os.path.join(ROOT, "data", "processed")
TITOLI = os.path.join(here, "wiki_titoli.csv")
RAW = os.path.join(here, "wiki_grezzo_v2.csv")
START, END = "2015070100", "2025123100"

LANGS = {"it": "domestico", "en": "estero", "de": "estero", "fr": "estero", "es": "estero"}

PAGINE = {
    "ITC1": ["Piemonte", "Torino", "Lago Maggiore", "Langhe", "Sestriere"],
    "ITC2": ["Valle d'Aosta", "Courmayeur", "Breuil-Cervinia", "Monte Bianco", "Aosta"],
    "ITC3": ["Liguria", "Cinque Terre", "Genova", "Portofino", "Sanremo"],
    "ITC4": ["Lombardia", "Milano", "Lago di Como", "Sirmione", "Livigno"],
    "ITDA": ["Provincia autonoma di Bolzano", "Provincia autonoma di Trento", "Dolomiti", "Val Gardena", "Merano"],
    "ITD3": ["Veneto", "Venezia", "Lago di Garda", "Verona", "Jesolo"],
    "ITD4": ["Friuli-Venezia Giulia", "Trieste", "Lignano Sabbiadoro", "Grado (Italia)", "Udine"],
    "ITD5": ["Emilia-Romagna", "Rimini", "Bologna", "Riccione", "Ravenna"],
    "ITE1": ["Toscana", "Firenze", "Pisa", "Siena", "Isola d'Elba"],
    "ITE2": ["Umbria", "Perugia", "Assisi", "Orvieto", "Lago Trasimeno"],
    "ITE3": ["Marche", "Urbino", "Ancona", "San Benedetto del Tronto", "Senigallia"],
    "ITE4": ["Lazio", "Roma", "Città del Vaticano", "Colosseo"],
    "ITF1": ["Abruzzo", "Pescara", "L'Aquila", "Gran Sasso d'Italia", "Roccaraso"],
    "ITF2": ["Molise", "Campobasso", "Termoli", "Isernia"],
    "ITF3": ["Campania", "Napoli", "Costiera amalfitana", "Sorrento", "Isola d'Ischia"],
    "ITF4": ["Puglia", "Salento", "Bari", "Gargano", "Alberobello"],
    "ITF5": ["Basilicata", "Matera", "Maratea"],
    "ITF6": ["Calabria", "Tropea", "Reggio Calabria", "Scalea"],
    "ITG1": ["Sicilia", "Palermo", "Taormina", "Siracusa", "Isole Eolie"],
    "ITG2": ["Sardegna", "Costa Smeralda", "Cagliari", "Alghero", "Villasimius"],
}

# Correzioni manuali ei titoli
OVERRIDE_TITOLI = {
    ("Sicilia", "de"): "Sizilien",
    ("Sardegna", "de"): "Sardinien",
}


def get_json(url, tentativi=5):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for k in range(tentativi):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(10 * (k + 1))
        except Exception:
            time.sleep(10 * (k + 1))
    return None


# ---------------------------------------------------------------- 1) titoli in tutte le lingue via Wikidata
def step_titoli():
    rows = []
    sites = "|".join(f"{l}wiki" for l in LANGS)
    for area, titoli in PAGINE.items():
        for k, t in enumerate(titoli):
            if args.mock:
                ent = {"id": f"Q{abs(hash(t)) % 10**6}", "descriptions": {"it": {"value": "comune italiano"}},
                       "sitelinks": {f"{l}wiki": {"title": t} for l in LANGS if not (l == "es" and k == 4)}}
            else:
                url = ("https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&redirects=yes&normalize=1"
                       f"&sites=itwiki&titles={urllib.parse.quote(t)}&props=sitelinks|descriptions&languages=it"
                       f"&sitefilter={urllib.parse.quote(sites)}")
                js = get_json(url) or {}
                ent = next(iter(js.get("entities", {}).values()), {})
                time.sleep(0.2)
            if not ent or "missing" in ent:
                print(f"  {area} | {t}: NON TROVATO su it.wikipedia (correggi il titolo in PAGINE)")
                rows.append(dict(REF_AREA=area, ordine=k, titolo_it_input=t, qid="", descrizione="NON TROVATO"))
                continue
            desc = ent.get("descriptions", {}).get("it", {}).get("value", "")
            r = dict(REF_AREA=area, ordine=k, titolo_it_input=t, qid=ent.get("id", ""), descrizione=desc)
            for l in LANGS:
                r[f"titolo_{l}"] = OVERRIDE_TITOLI.get((t, l), ent.get("sitelinks", {}).get(f"{l}wiki", {}).get("title", ""))
            rows.append(r)
            flag = "  <-- DISAMBIGUA? controlla" if "disambigua" in desc.lower() else ""
            print(f"  {area} | {t:30s} {r['qid']:10s} {desc[:40]:40s} en={r['titolo_en']} | de={r['titolo_de']}{flag}")
    pd.DataFrame(rows).to_csv(TITOLI, index=False)
    print(f"\nSalvato {TITOLI}. Controlla la colonna 'descrizione' e i titoli: una cella vuota significa che la voce "
          f"non esiste in quella lingua (va bene, conta zero).")


# ---------------------------------------------------------------- 2) visite mensili
def fetch(lang, title):
    if args.mock:
        t = pd.date_range("2015-07-01", "2025-12-01", freq="MS")
        rng = np.random.default_rng(abs(hash((lang, title))) % 2**32)
        v = 20000 * (1 + 0.4 * np.sin(2 * np.pi * (t.month.values - 5) / 12)) * rng.uniform(0.9, 1.1, len(t))
        return [dict(timestamp=ts.strftime("%Y%m%d00"), views=int(x)) for ts, x in zip(t, v)]
    url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
           f"{lang}.wikipedia/all-access/user/{urllib.parse.quote(title.replace(' ', '_'), safe='')}/monthly/{START}/{END}")
    js = get_json(url)
    return js.get("items") if js else None


def step_download():
    tit = pd.read_csv(TITOLI, dtype=str).fillna("")
    done = set()
    if os.path.exists(RAW):
        done = set(pd.read_csv(RAW, usecols=["REF_AREA", "lang", "article"], dtype=str).drop_duplicates().itertuples(index=False, name=None))
    jobs = [(r.REF_AREA, int(r.ordine), l, r[f"titolo_{l}"], r.qid) for _, r in tit.iterrows() if r.qid
            for l in LANGS if r[f"titolo_{l}"]]
    print(f"Pagine da scaricare: {len(jobs)} ({len([j for j in jobs if (j[0], j[2], j[3]) not in done])} mancanti)")
    missing = []
    for area, ordine, lang, title, qid in jobs:
        if (area, lang, title) in done:
            continue
        items = fetch(lang, title)
        if not items:
            print(f"   nessun dato: {lang}/{title}")
            missing.append(dict(REF_AREA=area, lang=lang, article=title, qid=qid))
            continue
        out = pd.DataFrame({"REF_AREA": area, "lang": lang, "market": LANGS[lang], "qid": qid, "ordine": ordine,
                            "tipo": "regione" if ordine == 0 else "destinazione", "article": title,
                            "TIME_PERIOD": [i["timestamp"][:4] + "-" + i["timestamp"][4:6] for i in items],
                            "views": [i["views"] for i in items]})
        out.to_csv(RAW, mode="a", header=not os.path.exists(RAW), index=False)
        print(f"  {area} | {lang} | {title}: {len(out)} mesi, media {out.views.mean():,.0f} visite/mese")
        if not args.mock:
            time.sleep(args.sleep + random.uniform(0, 0.2))
    pd.DataFrame(missing).to_csv(os.path.join(here, "wiki_senza_dati.csv"), index=False)
    print(f"Fine. Pagine senza dati: {len(missing)} (vedi wiki_senza_dati.csv)")


# ---------------------------------------------------------------- 3) aggregazione per regione e lingua
def step_aggrega():
    raw = pd.read_csv(RAW)
    # griglia completa: una pagina che manca in un mese (o non esiste ancora) conta zero
    mesi = sorted(raw.TIME_PERIOD.unique())
    key = ["REF_AREA", "lang", "market", "tipo", "article"]
    pag = raw[key].drop_duplicates()
    full = pag.merge(pd.DataFrame({"TIME_PERIOD": mesi}), how="cross").merge(raw[key + ["TIME_PERIOD", "views"]], how="left")
    full["views"] = full.views.fillna(0)
    piv = full.pivot_table(index=["REF_AREA", "lang", "market", "TIME_PERIOD"], columns="tipo", values="views", aggfunc="sum").reset_index()
    piv.columns.name = None
    for c in ("regione", "destinazione"):
        if c not in piv:
            piv[c] = 0.0
    piv = piv.rename(columns={"regione": "views_regione", "destinazione": "views_destinazioni"})
    piv["views_totale"] = piv.views_regione + piv.views_destinazioni
    piv["n_pagine"] = piv.merge(pag.groupby(["REF_AREA", "lang"]).size().rename("n").reset_index(), on=["REF_AREA", "lang"]).n.values
    piv = piv.sort_values(["REF_AREA", "lang", "TIME_PERIOD"]).reset_index(drop=True)
    g = piv.groupby(["REF_AREA", "lang"])
    for c in ("views_totale", "views_regione", "views_destinazioni"):
        piv[f"log_yoy_{c.replace('views_', '')}"] = np.log(piv[c].where(piv[c] > 0)) - np.log(g[c].shift(12).where(g[c].shift(12) > 0))
    piv.to_csv(os.path.join(PROC, "wiki_mensile_v2.csv"), index=False)
    print(f"Salvato wiki_mensile_v2.csv: {piv.shape}")
    print("\nVisite medie mensili (totale regione) per lingua, migliaia:")
    print((piv.groupby(["REF_AREA", "lang"]).views_totale.mean().unstack() / 1000).round(1).to_string())
    # controllo redirect / pagine poco viste
    chk = raw.groupby(["REF_AREA", "lang", "article"]).views.mean()
    low = chk[chk < 100]
    if len(low):
        print("\nPagine con meno di 100 visite al mese (normale per mete piccole in lingue straniere; controlla se sospette):")
        print(low.round(0).to_string())


{"titoli": step_titoli, "download": step_download, "aggrega": step_aggrega}[args.step]()