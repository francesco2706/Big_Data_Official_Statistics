# From Clicks to Check-ins

**Google Trends, Wikipedia e Reddit possono stimare in anticipo il turismo regionale italiano?**
Progetto di Big Data for Official Statistics, Sapienza Università di Roma, A.A. 2026/2027.

Il progetto confronta tre fonti digitali (Google Trends, Wikipedia, Reddit r/ItalyTravel) con i dati ufficiali ISTAT
sugli arrivi negli esercizi ricettivi, per 20 regioni, mese per mese e per mercato (domestico/estero). Le domande sono
tre:

- **Mirror**: le fonti digitali riproducono dove e quando vanno i turisti?
- **Anticipate**: migliorano la stima degli arrivi del mese prima che ISTAT li pubblichi (nowcasting)?
- **Explain**: i testi di Reddit spiegano come cambia l'esperienza dei turisti?

A questo si aggiungono un indicatore composito di attenzione digitale (DAI) e un clustering delle regioni.

## Struttura delle cartelle

```
.
├── README.md               questo file
├── requirements.txt        pacchetti Python necessari
├── data/
│   ├── raw/                dati scaricati, non modificati
│   │   ├── istat/          movimento dei clienti negli esercizi ricettivi (IstatData)
│   │   ├── trends/         i 20 CSV scaricati dalla console di Google Trends (.zip)
│   │   └── wikipedia/      titoli delle pagine e visite mensili grezze
│   └── processed/          dati puliti (script 1-6) e file di lavoro (script 7)
├── script/                 tutti gli script, numerati nell'ordine di esecuzione
├── output/                 risultati: tabelle (.csv), grafici (.png), riepiloghi (_risultati.txt)
│   ├── controlli/          controlli di qualità sui dati
│   ├── schemi/             schemi e figure didattiche
│   └── slide_en/           versione inglese dei grafici usati nella presentazione
└── docs/                   guida per eseguire la classificazione su Kaggle
```

I testi di Reddit e i file che li contengono non sono inclusi (vedi sotto).

## Gli script, in ordine

| # | Script | Cosa fa | Legge | Scrive |
|---|---|---|---|---|
| 0 | `script_0_comune.py` | Modulo condiviso: percorsi, colori, nomi delle regioni, stile dei grafici (non si lancia) | – | – |
| 1 | `script_1_istat.py` | Controlla e pulisce i dati ISTAT; permanenza media e variazione annua degli arrivi | `raw/istat` | `processed/istat_target.csv` |
| 2 | `script_2_trends_download.js` | Scarica Google Trends dalla console del browser (si incolla in trends.google.com) | – | 20 CSV → `raw/trends` |
| 3 | `script_3_trends_unione.py` | Unisce i 20 CSV di Trends e controlla le 360 combinazioni | `raw/trends` | `processed/trends_rep1_all.csv` |
| 4 | `script_4_wikipedia.py` | Titoli via Wikidata, visite mensili, aggregazione per regione e lingua | API Wikimedia | `raw/wikipedia`, `processed/wiki_mensile_v2.csv` |
| 5 | `script_5_vader_turismo.py` | Sentiment a dizionario adattato ai viaggi, termine di paragone nella validazione (modulo) | – | – |
| 6 | `script_6_reddit.py` | Pulisce i testi di Reddit e trova le regioni citate | `raw/reddit` | `processed/reddit_testi.csv.gz`, `reddit_mensile.csv` |
| 7 | `script_7_eda.py` | Analisi esplorativa; armonizza le 4 fonti nei file di lavoro | `processed/` | `processed/istat.csv`, `trends.csv`, `wiki.csv`, `reddit.csv`; `output/eda*` |
| 8 | `script_8_topic_modeling.py` | Temi di discussione (TF-IDF + NMF) | `reddit_testi` | `output/tm_*` |
| 9 | `script_9_qwen_preparazione.py` | Prepara i testi per Kaggle e il campione da annotare a mano | `reddit_testi` | `data/llm/` |
| 10 | `script_10_qwen_kaggle.py` | Classifica i 128.002 testi con Qwen 2.5 7B (**su Kaggle, GPU**) | `data/llm/kaggle` | `data/llm/qwen_completo.csv` |
| 11 | `script_11_sentiment_regionale.py` | Tono per regione: destagionalizzazione, errori per thread, shrinkage | Qwen | `output/rep_*` |
| 12 | `script_12_sentiment_qwen.py` | Validazione sui testi annotati, tono nell'anno, aspetti, temi | `data/llm/`, `tm_testi` | `output/snt_*` |
| 13 | `script_13_testi_classificati.py` | Excel e CSV leggibili con testi e classificazioni | `data/llm/` | `output/llm/` |
| 14 | `script_14_indicatore.py` | Indicatore di attenzione digitale (punteggi di rango), validazione, scarto, robustezza | file di lavoro, `rep_*` | `output/ind_*` |
| 15 | `script_15_clustering.py` | Clustering: k con il metodo del gomito, stabilità, gruppi, test di Mantel | file di lavoro | `output/cl_*` |
| 16 | `script_16_nowcasting.py` | Nowcasting in pseudo tempo reale (regressione di Huber), random forest | file di lavoro | `output/nc_*` |
| 17 | `script_17_schemi.py` | Schemi e figure didattiche (modulo usato da 18) | – | `output/schemi/` |
| 18 | `script_18_report.py` | Report PDF con tutti i risultati | `output/`, `data/llm/` | `docs/` |
| 19 | `script_19_esegui_tutto.py` | Esegue la pipeline nell'ordine giusto | – | – |

## Come rieseguire

```bash
pip install -r requirements.txt
cd script
python script_19_esegui_tutto.py            # analisi e report (script 7-9, 11-18)
python script_19_esegui_tutto.py --dati     # anche la preparazione dei dati (script 1, 3, 4, 6)
```

- Lo script 2 (Google Trends) si esegue nel browser; lo script 4 in fase di download richiede la variabile d'ambiente
  `WIKI_CONTATTO` con un contatto da inviare a Wikimedia.
- Lo script 10 gira su Kaggle: istruzioni passo passo in [`docs/GUIDA_KAGGLE.md`](docs/GUIDA_KAGGLE.md).
- Gli script che leggono i testi di Reddit (6, 8, 9, 11-13) richiedono i dati di Reddit, che non sono inclusi.

## Dati

Dati ISTAT, Google Trends e Wikipedia sono pubblici e sono inclusi. Il modello Qwen ha pesi pubblici (Apache 2.0) ed è
stato eseguito con temperatura 0 e seme fisso. I testi di Reddit (post, commenti e relative classificazioni) **non sono
inclusi**, per i termini d'uso di Reddit e la privacy degli utenti: il repository contiene solo i dati aggregati per
regione e mese (`data/processed/reddit.csv`, `reddit_mensile.csv`) e i risultati delle analisi.
