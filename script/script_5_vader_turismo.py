"""
SCRIPT 5 - VADER adattato ai testi di viaggio (modulo)

VADER adattato ai testi di viaggio (r/ItalyTravel).

Due interventi sul dizionario originale:

A) PAROLE NEUTRALIZZATE (valenza -> 0). Selezionate con i dati: nel campione di validazione (500 testi classificati
   anche con RoBERTa) sono le parole presenti in almeno 8 testi per cui la valenza di VADER e' piu' lontana dal giudizio
   medio di RoBERTa sui testi che le contengono, e il cui uso nel forum e' funzionale o di cortesia, non valutativo:
   "like", "what kind of", "feel free / free time", "yes", "sure", "please", "help", "ok",
   "better to take the train", "bus stop", "avoid driving".

B) PAROLE AGGIUNTE. Termini frequenti nel corpus (>= 0.1% dei testi, oppure chiaramente valutativi) assenti dal dizionario.
   Per non inventare valenze, ogni termine riceve la valenza di una parola GIA' presente in VADER con significato
   simile (ancora). Le espressioni di piu' parole vengono unite in un solo token prima del calcolo
   ("tourist trap" -> "tourist_trap"), cosi' le regole di VADER continuano a valere:
   "not worth it" resta negativo.
"""
import re

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

NEUTRALIZZATE = ["like", "kind", "free", "yes", "sure", "please", "help", "ok", "better", "stop", "avoid"]

# termine -> parola ancora in VADER (la valenza viene copiata dal dizionario originale)
ANCORE = {
    # negativi
    "crowded": "uncomfortable", "overcrowded": "unpleasant", "touristy": "costly", "expensive": "costly",
    "pricey": "costly", "overpriced": "annoying", "hassle": "inconvenient", "nightmare": "horrible",
    "pickpocket": "thief", "pickpockets": "thief", "pickpocketed": "stolen", "robbed": "stolen", "theft": "stolen",
    "scammed": "scam", "ripoff": "scam", "unsafe": "dangerous", "sketchy": "suspicious", "fined": "penalty",
    "overrated": "disappointing", "underwhelming": "disappointing", "unbearable": "miserable", "sweltering": "uncomfortable",
    "tourist_trap": "annoying", "long_lines": "inconvenient", "long_line": "inconvenient", "long_queue": "inconvenient",
    "long_queues": "inconvenient", "long_wait": "inconvenient",
    # positivi
    "incredible": "amazing", "magical": "wonderful", "unforgettable": "wonderful", "memorable": "impressive",
    "tasty": "yummy", "underrated": "worthwhile", "gem": "treasure", "hidden_gem": "impressive",
    "worth_it": "worthwhile", "must_see": "worthwhile",
}
FRASI = {"tourist trap": "tourist_trap", "tourist traps": "tourist_trap", "hidden gem": "hidden_gem", "hidden gems": "hidden_gem",
         "worth it": "worth_it", "must see": "must_see", "must-see": "must_see", "long lines": "long_lines",
         "long line": "long_line", "long queue": "long_queue", "long queues": "long_queues", "long wait": "long_wait",
         "rip off": "ripoff", "rip-off": "ripoff", "over priced": "overpriced", "over-priced": "overpriced"}
_RX = re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(FRASI, key=len, reverse=True)) + r")\b", re.I)


class VaderTurismo:
    def __init__(self):
        self.an = SentimentIntensityAnalyzer()
        base = dict(self.an.lexicon)
        self.tabella = []
        for w in NEUTRALIZZATE:
            self.tabella.append(dict(termine=w, intervento="neutralizzata", ancora="", valenza_originale=base.get(w), valenza_nuova=0.0))
            self.an.lexicon[w] = 0.0
        for w, a in ANCORE.items():
            self.tabella.append(dict(termine=w.replace("_", " "), intervento="aggiunta", ancora=a,
                                     valenza_originale=base.get(w), valenza_nuova=base[a]))
            self.an.lexicon[w] = base[a]

    def polarity_scores(self, text):
        return self.an.polarity_scores(_RX.sub(lambda m: FRASI[m.group(0).lower()], text))


if __name__ == "__main__":
    import pandas as pd
    v, o = VaderTurismo(), SentimentIntensityAnalyzer()
    print(pd.DataFrame(v.tabella).to_string(index=False))
    for s in ["The Colosseum was crowded and overpriced.", "Beware of pickpockets near Termini", "Any help appreciated, thanks!",
              "Feel free to ask, I'd say better to take the train", "It's a tourist trap, not worth it", "Matera is a hidden gem, totally worth it"]:
        print(f"{o.polarity_scores(s)['compound']:+.3f} -> {v.polarity_scores(s)['compound']:+.3f}  {s}")