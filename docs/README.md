# Taccuino su GitHub Pages

In Settings → Pages selezionare Deploy from a branch, ramo main, cartella /docs e salvare.

URL previsto: https://floffy17.github.io/app-gestione-spesa/

Su iPhone aprire in Safari e scegliere Condividi → Aggiungi alla schermata Home. Su Android aprire in Chrome e scegliere Installa app o Aggiungi alla schermata Home.

I file di questa cartella sono il sito completo precompilato: non servono npm, backend o variabili segrete per pubblicarlo. Per aggiornarlo sostituire i file del sito mantenendo lo stesso indirizzo.

Le spese e i budget sono salvati sul dispositivo, non su GitHub. Il sito funziona offline dopo il primo caricamento. Le notifiche richiedono consenso e, per il sito installabile su iPhone, iOS 16.4 o successivo. Gli avvisi vengono controllati durante l’utilizzo e alla riapertura; non c’è un servizio di controllo continuo in background.

## Versione 1.3: macrocategorie personalizzabili

In Costi → Budget → Gestisci macrocategorie è possibile aggiungere categorie e modificare nome, colore del grafico e limite mensile. Il campo limite è facoltativo: vuoto o 0 significa nessun limite. I limiti sono disponibili anche in Limiti per categoria. La categoria dei costi fissi mantiene il comportamento ricorrente anche quando viene rinominata.

Le categorie nuove si selezionano nel modulo di inserimento spesa; le scelte vengono apprese per le descrizioni successive. Rinominare una categoria non cambia le associazioni delle spese precedenti. Nome, colore, limiti e categorie sono personali, salvati sul dispositivo come le spese.

L’aggiornamento mantiene la chiave di salvataggio e gli identificativi originali. È stata verificata una migrazione dalla versione 1.2 sulla stessa origine, con conservazione di transazioni, costi fissi, diario, attività, categorie apprese e limiti. Non cancellare i dati del sito o cambiare origine per aggiornare.

Per verificare il sito, con un server HTTP che serve la radice del repository:

```sh
python3 -m pip install -r tests/requirements.txt
TACCUINO_TEST_URL=http://127.0.0.1:8005/docs/ python3 tests/smoke.py
python3 tests/categories.py
```

Il test della migrazione usa il commit precedente ab907b5502d51e315d81d8422671ac065bf40d5e, che deve essere disponibile nella cronologia Git locale. Richiede Playwright Python e Chromium (il percorso predefinito del test è /usr/bin/chromium).
