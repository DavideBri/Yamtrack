# Camantra — Draft Assistant (Fantacalcio Mantra Euroleghe)

Strumento per **vincere la lega Camantra**: dallo studio del listone alla
**dashboard live** che ti dice *chi chiamare* durante l'asta.

> ⚠️ **Non è un tool a budget.** Il regolamento Camantra prevede un'**asta
> DRAFT a crediti infiniti**: si chiama a turno, senza rilanci. La risorsa
> scarsa sono le **chiamate**, non i crediti. Per questo il ranking non usa
> "prezzi" ma il **VOR** (value over replacement) con il **FVM** come prior di
> mercato — la stessa metrica che, nel regolamento, pilota anche l'ordine di
> chiamata dai round ≥2.

---

## Cosa fa (Fase 1 — ASTA)

- **Big Board**: listone Euroleghe ordinato per VOR, con tier per ruolo,
  fantapunti proiettati, filtri per ruolo/campionato/squadra.
- **Draft Room live**: registri le chiamate di tutti gli 8 fantallenatori;
  l'app calcola **chi è di turno**, ricostruisce l'**ordine dei round** (round
  1 sorteggiato, round ≥2 dal FVM di rosa più basso), e ti dà le **migliori
  chiamate per la tua squadra** con **probabilità di sopravvivenza** del target
  fino al tuo prossimo turno.
- **Rosa & Moduli**: quali degli 11 moduli ammessi riesci a schierare
  (matching ruoli↔slot), dove hai buchi tattici, e un *miglior XI* indicativo.

Regolamento codificato in [`config/league.yaml`](config/league.yaml) (unica
fonte di verità: 37 squadre / 5 campionati, rosa 3P+27, ruoli Mantra, 11
moduli, bonus/malus, modificatore difesa, fattore capitano, penalità).

---

## ⚠️ Nota sui dati (importante)

Questo progetto è nato in un ambiente cloud in cui **`fantacalcio.it` è
bloccato dalla policy di rete** (egress proxy → 403): da lì non è possibile
scaricare il listone. Di conseguenza:

1. Il **percorso affidabile** è l'**import del file ufficiale**: scarichi a
   mano il listone/quotazioni Euroleghe (xlsx/csv) e lo carichi nell'app.
2. Lo **scraper** ([`camantra/ingest/scraper.py`](camantra/ingest/scraper.py))
   è **opzionale e da lanciare sulla TUA macchina**, dove il sito è
   raggiungibile.
3. Senza file reale l'app parte con un **dataset SAMPLE sintetico** (etichettato
   `is_sample`), solo per far girare tutto end-to-end. **Non usarlo per
   decisioni vere** — sostituiscilo appena hai il listone.

---

## Setup

```bash
cd camantra
uv venv .venv                       # oppure: python -m venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
# oppure: .venv/bin/pip install -r requirements.txt   (con venv classico)
```

## Avvio dashboard

```bash
.venv/bin/streamlit run dashboard/app.py
```

Pagine (menu a sinistra): **Big Board**, **🎯 Draft Room**, **🧩 Rosa & Moduli**.

## Inserire il listone reale

Due modi:

- **Dalla dashboard**: sidebar → *Carica listone Euroleghe (xlsx/csv)*. Il file
  viene salvato in `data/listone.xlsx` e usato al posto del sample.
- **A mano**: metti il file in `camantra/data/listone.xlsx` (o `.csv`).

Il parser riconosce le colonne in modo *fuzzy* (Nome, Squadra, Ruolo/RM, FVM,
Fantamedia, Presenze, …), salta la riga "banner" dei file quotazioni, e
riconcilia i nomi squadra con le 37 squadre del regolamento. Se una colonna ha
un nome inatteso, l'errore te lo segnala.

### (Opzionale) scraper sul tuo PC

```bash
.venv/bin/pip install requests
python -m camantra.ingest.scraper --url "<URL_EXPORT_XLSX>" --out data/listone.xlsx
```
Gli URL di export cambiano di stagione: prendi quello vero dal tasto
"Scarica" nella pagina quotazioni del sito.

---

## Metodo (come vengono decise le chiamate)

- **value** (0–100): combinazione normalizzata di **FVM** (mercato) e
  **fantapunti proiettati** (`fantamedia × presenze` sulla stagione Euroleghe).
  Il peso FVM↔fantapunti è regolabile dalla sidebar.
- **VOR** = `value − valore di rimpiazzo nel ruolo`. Il rimpiazzo è il
  giocatore in posizione `manager × fabbisogno_ruolo`: cioè il migliore che
  *resterebbe comunque disponibile*. Premia i ruoli scarsi e i **multi-ruolo**
  (si prende il ruolo dove il VOR è massimo → `value_role`).
- **tier**: fasce per ruolo calcolate sui *salti* di valore (natural breaks).
- **Ordine draft**: round 1 = sorteggio; round ≥2 = FVM di rosa crescente
  (chi ha meno FVM chiama prima). L'app lo ricostruisce dallo storico chiamate.
- **Raccomandazioni**: `VOR × moltiplicatore-bisogno` (ruolo scoperto ↑, ruolo
  saturo ↓) + **probabilità di sopravvivenza** = stima logistica basata su
  quanti giocatori "sopra" al target verranno presi prima del tuo turno.

> Le proiezioni sono un *proxy* di consenso, non una previsione esatta:
> incrociale sempre con probabili formazioni e minutaggio (principio del
> system prompt: dati aggiornati, mai a memoria).

---

## Struttura

```
camantra/
├── config/league.yaml        # regolamento codificato (source of truth)
├── camantra/
│   ├── config.py             # loader + validazione config
│   ├── roles.py              # ruoli Mantra, copertura moduli (matching)
│   ├── store.py              # caricamento listone / stato draft
│   ├── ingest/               # parser file reale, sample, scraper opzionale
│   └── engine/               # value (VOR/tiers) + draft (snake FVM)
├── dashboard/                # app Streamlit (3 pagine)
├── scripts/                  # smoke test + generatore sample
├── tests/                    # pytest (roles, value, draft)
└── data/                     # listone reale + stati draft (gitignored)
```

## Test

```bash
uv pip install --python .venv/bin/python pytest
.venv/bin/python -m pytest -q
```

---

## Roadmap

- **Fase 2 — Gestione giornata**: probabili formazioni, infortuni/squalifiche,
  bonus attesi, scelta modulo, panchina + piano B, deadline. (Si gioca solo
  quando giocano tutti e 5 i campionati.)
- **Fase 3 — Mercato/riparazione**: punti deboli con i dati, proposte di
  scambio, calendario del ritorno.

Contributi e correzioni al `league.yaml` benvenuti: il regolamento *"è soggetto
a modifiche fino all'inizio della competizione"*.
