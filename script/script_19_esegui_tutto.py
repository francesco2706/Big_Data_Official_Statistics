"""
SCRIPT 19 - Esegue la pipeline nell'ordine giusto.

    python script_19_esegui_tutto.py           analisi e report: script 7-9 e 11-18
    python script_19_esegui_tutto.py --dati    anche la preparazione dei dati: script 1, 3, 4 (aggrega), 6

Non vengono eseguiti:
  * il download di Google Trends (nella console del browser)
  * Wikipedia
  * Qwen: gira su una GPU di Kaggle.
"""
import subprocess
import sys
import time
from pathlib import Path

QUI = Path(__file__).resolve().parent
DATI = [["script_1_istat.py"], ["script_3_trends_unione.py"], ["script_4_wikipedia.py", "aggrega"], ["script_6_reddit.py"]]
ANALISI = [["script_7_eda.py"], ["script_8_topic_modeling.py"], ["script_9_qwen_preparazione.py"],
           ["script_11_sentiment_regionale.py"], ["script_12_sentiment_qwen.py"], ["script_13_testi_classificati.py"],
           ["script_14_indicatore.py"], ["script_15_clustering.py"], ["script_16_nowcasting.py"], ["script_18_report.py"]]

ordine = (DATI if "--dati" in sys.argv else []) + ANALISI
for cmd in ordine:
    print(f"\n{'#' * 70}\n# {' '.join(cmd)}\n{'#' * 70}", flush=True)
    t0 = time.time()
    if subprocess.run([sys.executable, *cmd], cwd=QUI).returncode != 0:
        sys.exit(f"Errore in {cmd[0]}: mi fermo.")
    print(f"# {cmd[0]}: {time.time() - t0:.0f} s")
print("\nTutto fatto. Risultati in output/, report in docs/.")
