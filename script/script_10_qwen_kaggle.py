"""
SCRIPT 10 - Classificazione dei testi con Qwen (modello open weight servito da vLLM) su Kaggle

Per ogni testo il modello restituisce un JSON:
  text_type     question / advice / experience_report / other
  aspects       per ognuno di crowds, prices, transport, food, accommodation, sights:
                positive / negative / not_mentioned
  sentiment     negative / neutral / positive
  score         -2 (molto negativo) ... +2 (molto positivo)
  main_region   la regione di cui il testo parla DAVVERO 

"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import shutil
import sys
import time

import pandas as pd

# ================================================================ configurazione
MODELLO = "Qwen/Qwen2.5-7B-Instruct-AWQ"   # 7 miliardi di parametri, quantizzato a 4 bit: entra in una T4 (16 GB)
# Alternativa piu' recente: "Qwen/Qwen3-8B-AWQ" (lo script disattiva da solo la modalita' "thinking" di Qwen3)
MAX_LEN_MODELLO = 4096        # token per prompt + risposta (i testi sono tagliati a 6.000 caratteri dallo script 9)
BLOCCO = 2000                 # testi elaborati e salvati per volta
SEME = 0

REGIONI = ["Piemonte", "Valle d'Aosta", "Liguria", "Lombardia", "Trentino-Alto Adige", "Veneto", "Friuli-Venezia Giulia",
           "Emilia-Romagna", "Toscana", "Umbria", "Marche", "Lazio", "Abruzzo", "Molise", "Campania", "Puglia",
           "Basilicata", "Calabria", "Sicilia", "Sardegna"]
ASPETTI = ["crowds", "prices", "transport", "food", "accommodation", "sights"]
VAL_ASP = ["positive", "negative", "not_mentioned"]

SCHEMA = {
    "type": "object",
    "properties": {
        "text_type": {"type": "string", "enum": ["question", "advice", "experience_report", "other"]},
        "aspects": {"type": "object",
                    "properties": {a: {"type": "string", "enum": VAL_ASP} for a in ASPETTI},
                    "required": ASPETTI, "additionalProperties": False},
        "sentiment": {"type": "string", "enum": ["negative", "neutral", "positive"]},
        "score": {"type": "integer", "enum": [-2, -1, 0, 1, 2]},
        "main_region": {"type": "string", "enum": REGIONI + ["none", "several"]},
    },
    "required": ["text_type", "aspects", "sentiment", "score", "main_region"],
    "additionalProperties": False,
}

SISTEMA = f"""You annotate posts and comments from r/ItalyTravel, a forum where travellers discuss trips to Italy.
For each text return a JSON object with these fields.

text_type: "question" (asks for information or advice), "advice" (gives information, tips, itineraries or
logistics to someone else), "experience_report" (tells about the writer's own trip), "other".

aspects: for each aspect say whether the text expresses a positive or negative opinion about it, or
"not_mentioned" if the text gives no opinion on it. Neutral facts (timetables, prices quoted without judgement)
are "not_mentioned".
  crowds = crowding, queues, number of tourists; prices = costs, value for money; transport = trains, buses,
  driving, ferries, flights; food = food and restaurants; accommodation = hotels and rentals;
  sights = places, views, museums, beaches, landscapes.
  The polarity is the writer's judgement: "it is quiet, few tourists, no crowds" is crowds = "positive";
  "packed, long queues, overrun" is crowds = "negative".

sentiment: the overall attitude of the writer towards the travel experience or the places discussed.
  - Informational texts (timetables, logistics, how-to answers) are "neutral" even if they are friendly or long.
    Practical remarks inside them ("buses are reliable", "take bus 400") do not make them positive: a practical
    answer is positive only if the writer clearly expresses enthusiasm or praise for the place or experience.
  - Politeness ("thanks", "hope this helps", "have a great trip") does not make a text positive.
  - Frustration, complaints, warnings, disappointment are "negative"; enthusiasm and praise are "positive".
  - Judge the whole text, not single words; take negation and irony into account ("no issues" is not negative).
score: -2 very negative, -1 negative, 0 neutral, +1 positive, +2 very positive. It must agree with sentiment.

main_region: the Italian region the text is mainly ABOUT. Before the text you receive the list of regions whose
places were found in it by keyword matching ("Candidate regions"); the place-to-region assignment in that list is
reliable, so do not reassign places to other regions (Matera is in Basilicata, Termoli in Molise, Sorrento in Campania).
  - If the text is mainly about one of the candidate regions, answer that region.
  - If it is about two or more candidate regions equally (an itinerary), answer "several".
  - Answer "none" only if every candidate is mentioned just in passing ("tomorrow I leave for Venice") and the text is
    not about any of them. A text about a small town, a mountain, a lake or a hut in a candidate region IS about it.
  - Answer a region outside the candidates only if the text clearly discusses a place the keyword matching missed.
Allowed values: {", ".join(REGIONI)}, "several", "none".

Answer with the JSON object only."""

# ================================================================ argomenti e percorsi
ap = argparse.ArgumentParser()
ap.add_argument("--file", default="tutti", choices=["tutti", "gold", "completo"],
                help="tutti (predefinito): un'unica esecuzione su tutti i testi, campione annotato per primo")
ap.add_argument("--mock", action="store_true", help="risposte casuali, senza GPU: solo per provare la catena")
ap.add_argument("--limite", type=int, default=None, help="classifica solo i primi N testi (prove)")
ap.add_argument("--modello", default=MODELLO)
ap.add_argument("--gpu", type=int, default=1, help="GPU da usare in parallelo (tensor parallel), es. 2 con T4 x2")
args = ap.parse_args()

SU_KAGGLE = os.path.isdir("/kaggle/input")
QUI = os.path.dirname(os.path.abspath(__file__))
LLM_LOCALE = os.path.join(os.path.dirname(QUI), "data", "llm")        # in locale: ZZ_TURISM/data/llm
DIR_OUT = "/kaggle/working" if SU_KAGGLE else LLM_LOCALE


def trova(nome):
    g = (glob.glob(f"/kaggle/input/**/{nome}", recursive=True) if SU_KAGGLE
         else glob.glob(os.path.join(LLM_LOCALE, "kaggle", nome)))
    return g[0] if g else None


def leggi_input(nome):
    f = trova(nome)
    if f is None:
        sys.exit(f"File {nome} non trovato (su Kaggle: aggiungi il Dataset con Add Input).")
    d = pd.read_csv(f, dtype={"id": str})
    if "regioni_diz" not in d.columns:
        sys.exit(f"{nome} non ha la colonna 'regioni_diz': e' la versione vecchia dei dati. Rilancia "
                 "script_9_qwen_preparazione.py sul PC e carica su Kaggle la nuova versione del Dataset (New Version).")
    return d, f


if args.file == "tutti":
    # il campione annotato e' un sottoinsieme di completo: basta classificare completo, mettendo per primi i suoi testi.
    # Cosi' dopo pochi minuti i testi necessari alla valutazione sono gia' pronti, anche se poi la sessione si ferma.
    T, f_in = leggi_input("completo.csv")
    prio = {}
    for k, nome in enumerate(["gold_testi.csv"]):
        if trova(nome):
            for i in pd.read_csv(trova(nome), dtype={"id": str}, usecols=["id"]).id:
                prio.setdefault(i, k)
    T = T.assign(_p=T.id.map(prio).fillna(2)).sort_values("_p", kind="stable").drop(columns="_p")
    print(f"Ordine: {len(prio)} testi del campione annotato, poi tutti gli altri")
    nome_out = "completo"
else:
    T, f_in = leggi_input({"gold": "gold_testi.csv", "completo": "completo.csv"}[args.file])
    nome_out = args.file
F_OUT = os.path.join(DIR_OUT, f"qwen_{nome_out}{'_mock' if args.mock else ''}.csv")

# ripresa: su Kaggle l'output di un'esecuzione precedente (salvata con Save Version) si aggiunge come Input
if SU_KAGGLE and not os.path.exists(F_OUT):
    prec = glob.glob(f"/kaggle/input/**/{os.path.basename(F_OUT)}", recursive=True)
    if prec:
        shutil.copy(prec[0], F_OUT)
        print(f"Trovato un output precedente ({prec[0]}): riprendo da li'")

if args.limite:
    T = T.head(args.limite)
fatti = set(pd.read_csv(F_OUT, dtype={"id": str}, usecols=["id"]).id) if os.path.exists(F_OUT) else set()
T = T[~T.id.isin(fatti)].reset_index(drop=True)
print(f"Input {f_in} | da classificare: {len(T):,} | gia' fatti: {len(fatti):,} | output: {F_OUT}")
if T.empty:
    print("Niente da fare: tutti i testi sono gia' classificati.")
    sys.exit(0)


# ================================================================ lettura della risposta
def leggi(testo):
    """JSON della risposta -> dizionario piatto. Con la decodifica guidata e' sempre valido; il ripiego con la
    regex serve solo se la versione di vLLM non supporta la decodifica guidata."""
    try:
        d = json.loads(testo)
    except (json.JSONDecodeError, TypeError):
        m = re.search(r"\{.*\}", testo or "", re.S)
        try:
            d = json.loads(m.group(0)) if m else None
        except json.JSONDecodeError:
            d = None
    if not isinstance(d, dict):
        return {"errore": True}
    r = {"errore": False, "text_type": d.get("text_type"), "sentiment": d.get("sentiment"),
         "score": d.get("score"), "main_region": d.get("main_region")}
    asp = d.get("aspects") or {}
    for a in ASPETTI:
        r[f"asp_{a}"] = asp.get(a)
    return r


# ================================================================ modello
if args.mock:
    import random
    random.seed(SEME)

    def genera(testi, candidati):
        out = []
        for _ in testi:
            s = random.choice([-2, -1, 0, 1, 2])
            out.append(json.dumps({"text_type": random.choice(["question", "advice", "experience_report", "other"]),
                                   "aspects": {a: random.choice(VAL_ASP) for a in ASPETTI},
                                   "sentiment": "negative" if s < 0 else ("positive" if s > 0 else "neutral"),
                                   "score": s, "main_region": random.choice(REGIONI + ["none"])}))
        return out
    info = {"vllm": "mock", "gpu": "nessuna"}
else:
    import torch
    import vllm
    from vllm import LLM, SamplingParams

    llm = LLM(model=args.modello, dtype="half", max_model_len=MAX_LEN_MODELLO, gpu_memory_utilization=0.90,
              tensor_parallel_size=args.gpu, seed=SEME)
    tok = llm.get_tokenizer()
    # decodifica guidata dallo schema JSON: il nome dell'API e' cambiato tra le versioni di vLLM
    try:
        from vllm.sampling_params import StructuredOutputsParams
        sp = SamplingParams(temperature=0, max_tokens=256, seed=SEME,
                            structured_outputs=StructuredOutputsParams(json=SCHEMA))
        guida = "structured_outputs"
    except (ImportError, TypeError):
        try:
            from vllm.sampling_params import GuidedDecodingParams
            sp = SamplingParams(temperature=0, max_tokens=256, seed=SEME,
                                guided_decoding=GuidedDecodingParams(json=SCHEMA))
            guida = "guided_decoding"
        except (ImportError, TypeError):
            sp = SamplingParams(temperature=0, max_tokens=256, seed=SEME)
            guida = "nessuna (solo istruzioni nel prompt)"
    print(f"Decodifica guidata: {guida}")

    def prompt(testo, cand):
        msg = [{"role": "system", "content": SISTEMA},
               {"role": "user", "content": f"Candidate regions: {cand}\n\nText:\n\"\"\"\n{testo}\n\"\"\""}]
        # enable_thinking=False serve a Qwen3; i modelli Qwen2.5 ignorano il parametro
        return tok.apply_chat_template(msg, tokenize=False, add_generation_prompt=True, enable_thinking=False)

    def genera(testi, candidati):
        res = llm.generate([prompt(t, c) for t, c in zip(testi, candidati)], sp, use_tqdm=True)
        return [r.outputs[0].text for r in res]
    info = {"vllm": vllm.__version__, "gpu": torch.cuda.get_device_name(0), "decodifica_guidata": guida}

json.dump({"modello": args.modello, "data": dt.datetime.now().isoformat(timespec="seconds"), "temperatura": 0,
           "seme": SEME, "max_len": MAX_LEN_MODELLO, "prompt_sistema": SISTEMA, "schema": SCHEMA, **info},
          open(F_OUT.replace(".csv", "_meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ================================================================ classificazione a blocchi
t0 = time.time()
for i in range(0, len(T), BLOCCO):
    b = T.iloc[i:i + BLOCCO]
    risposte = genera(b.text.tolist(), b.regioni_diz.tolist())
    R = pd.DataFrame([leggi(x) for x in risposte])
    R.insert(0, "id", b.id.values)
    R["risposta_grezza"] = risposte
    R.to_csv(F_OUT, mode="a", header=not os.path.exists(F_OUT), index=False)
    fatto = i + len(b)
    v = fatto / (time.time() - t0)
    print(f"  {fatto:,}/{len(T):,} testi | {v:.1f} testi/s | mancano circa {(len(T) - fatto) / v / 60:.0f} min | "
          f"errori di lettura nel blocco: {int(R.errore.sum())}", flush=True)
print(f"Fatto in {(time.time() - t0) / 60:.1f} minuti. File: {F_OUT}")