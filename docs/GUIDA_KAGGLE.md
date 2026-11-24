# Sentiment con Qwen su Kaggle – guida passo passo

Obiettivo: classificare i testi di Reddit con un modello linguistico **open-weight** (Qwen 2.5, 7 miliardi di
parametri), usando una GPU gratuita di Kaggle, e validarlo su testi annotati a mano.

```
script_9_qwen_preparazione.py     (sul tuo PC)  ->  data/llm/kaggle/            da caricare su Kaggle
                                                    data/llm/gold_da_annotare.csv  da compilare a mano
script_10_qwen_kaggle.py          (su Kaggle)   ->  qwen_completo.csv + qwen_completo_meta.json  da scaricare
script_11_sentiment_regionale.py  (sul tuo PC)  ->  output/rep_*   tono per regione
script_12_sentiment_qwen.py       (sul tuo PC)  ->  output/snt_*   validazione, stagioni, aspetti, temi
script_13_testi_classificati.py   (sul tuo PC)  ->  output/llm/qwen_testi_classificati.xlsx
```

---

## Passo 0 – Preparare i file

```bash
python script_9_qwen_preparazione.py
```

Crea la cartella `data/llm/kaggle/` con tre file:

| File | Contenuto | Dimensione |
|---|---|---|
| `gold_testi.csv` | i testi del campione da annotare (15 per regione) | 0,1 MB |
| `completo.csv` | tutti i 128.002 testi 2023-2024 che citano una regione | 54 MB |
| `script_10_qwen_kaggle.py` | lo script da eseguire | – |

Ogni testo arriva a Qwen con le **regioni trovate dal dizionario** (colonna `regioni_diz`): Qwen sceglie tra queste
quella di cui il testo parla davvero. Il dizionario conosce i luoghi, Qwen capisce di cosa parla il testo.

## Passo 1 – Account Kaggle

1. Registrati su kaggle.com.
2. **Verifica il numero di telefono** (Settings → Phone verification). Senza verifica Kaggle non attiva né la GPU né
   l'accesso a Internet nei notebook, e Internet serve per installare vLLM e scaricare il modello.

## Passo 2 – Caricare i dati come Dataset

1. kaggle.com → **Datasets** → **New Dataset**.
2. Trascina i 3 file della cartella `data/llm/kaggle/`.
3. Titolo, ad esempio `reddit-italytravel-qwen`; lascialo **Private**. → **Create**.

## Passo 3 – Creare il notebook

1. **Code** → **New Notebook**.
2. Nel pannello a destra, **Session options**:
   - **Accelerator**: `GPU T4 x2`;
   - **Internet**: `On`.
3. **Add Input** → cerca il tuo dataset → **Add**.

## Passo 4 – Eseguire

Il notebook ha **tre celle**, una per comando:

```python
!pip install -q vllm
```
```python
!cp $(find /kaggle/input -name script_10_qwen_kaggle.py | head -1) .
```
```python
!python script_10_qwen_kaggle.py --gpu 2
```

Un'unica esecuzione classifica **tutti i 128.002 testi** (prima quelli del campione da annotare) e salva tutto in
`qwen_completo.csv`. Con 2 GPU T4 servono circa 6 ore e mezza.

**In background.** Clicca **Save Version** → **Save & Run All (Commit)** → **Save**. Kaggle esegue il notebook fino
alla fine anche se chiudi il browser (massimo 12 ore) e conserva i file nella scheda **Output** di quella versione.

- `--gpu 2` usa tutte e due le T4. Se dà errore, toglilo.
- Se l'esecuzione si interrompe, aggiungi l'Output della versione come **Input** e rilancia: lo script riparte dai
  testi mancanti.
- La quota gratuita di GPU è di circa 30 ore a settimana.

| Problema | Soluzione |
|---|---|
| `pip install vllm` dà conflitti di versione | riavvia la sessione (Run → Restart) e rilancia l'installazione |
| errore di memoria della GPU (CUDA out of memory) | nello script abbassa `MAX_LEN_MODELLO` a 3072 |

## Passo 5 – Scaricare i risultati

Dal pannello **Output** scarica `qwen_completo.csv` e `qwen_completo_meta.json` (modello, versione di vLLM, GPU,
data, prompt e schema: è la documentazione per la riproducibilità) e mettili in `data/llm/`.

## Passo 6 – Annotare il campione (a mano)

Apri `data/llm/gold_da_annotare.csv` e compila per ogni testo:

- **sentiment_umano**: `positivo`, `neutro` oppure `negativo`;
- **regione_umana**: la regione di cui il testo parla davvero, oppure `nessuna`;
- **note** (facoltativo).

Le regole sono le stesse date a Qwen:

- si giudica l'atteggiamento di chi scrive verso il viaggio o i luoghi, non le singole parole;
- testi informativi (orari, logistica, risposte pratiche) = **neutro**, anche se lunghi e gentili;
- le formule di cortesia non rendono un testo positivo;
- frustrazione, lamentele, avvertimenti, delusione = **negativo**; entusiasmo e lodi = **positivo**;
- un luogo citato di passaggio non conta per la regione.

Si annota **alla cieca**, prima di guardare i risultati del modello; i testi sono in ordine casuale. Lo script 9 non
sovrascrive mai questo file.

## Passo 7 – Analisi

```bash
python script_11_sentiment_regionale.py
python script_12_sentiment_qwen.py
python script_13_testi_classificati.py
```

`script_12_sentiment_qwen.py` scrive `output/snt_risultati.txt` con: qualità dell'output, scelta della regione,
**validazione** sui testi annotati (Qwen, con VADER e RoBERTa come termini di paragone: accuratezza, intervallo di
Wilson, kappa, test di McNemar), tono nel corso dell'anno, aspetti che peggiorano d'estate, scomposizione per temi.

## Riproducibilità

- Modello: `Qwen/Qwen2.5-7B-Instruct-AWQ` (pesi pubblici, licenza Apache 2.0), quantizzazione AWQ a 4 bit.
- Inferenza: vLLM (versione nel file `_meta.json`), 2 GPU NVIDIA T4, temperatura 0, seme 0.
- Output vincolato a uno schema JSON (decodifica guidata); prompt e schema nel file `_meta.json`.
- Testi oltre 6.000 caratteri tagliati: 111 su 128.002.
- Validazione: 43 testi annotati alla cieca, con le stesse regole date al modello.
