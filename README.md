# Embedded Researcher — Rete di affinità di ricerca · Università di Trento

Una mappa interattiva di chi, all'Università di Trento, lavora su temi vicini: chi pubblica su argomenti simili, chi ha già
pubblicato insieme, chi insegna insieme. Serve a far emergere **collaborazioni possibili che ancora non esistono**.

È fatta di due parti:

- una **pipeline** Python che parte dagli open data dell'ateneo e calcola, per ogni coppia di persone, più misure
  di vicinanza separate (i *layer*);
- una **pagina web** statica (`Embedded Researcher`) che mostra la rete e, per ogni collegamento, le prove concrete che lo motivano
  (coppie di articoli, insegnamenti in comune, colleghi ponte).

Non è una classifica e non misura la qualità di nessuno: le citazioni non sono usate per valutare le persone e la dimensione dei punti dipende
solo dal numero di pubblicazioni.

> **Questa repository contiene solo codice.** Nessun dato sulle persone, nessun abstract, nessun grafo precalcolato:
> tutto ciò che la pipeline scarica o produce resta in `data/` e `reports/` (esclusi da git) e si genera sulla propria
> macchina con **un clic dalla pagina web** oppure con **un comando da terminale**.
> Vedi [Dati, licenze e privacy](#dati-licenze-e-privacy) prima di pubblicare o diffondere i risultati.

## Indice

- [Che cosa si vede nella pagina](#che-cosa-si-vede-nella-pagina)
- [Installazione](#installazione)
- [Esecuzione](#esecuzione)
- [Tenerlo sempre acceso come server](#tenerlo-sempre-acceso-come-server)
- [Come sono calcolati i punteggi](#come-sono-calcolati-i-punteggi)
- [Valutazione](#valutazione)
- [Limiti noti](#limiti-noti)
- [Dati, licenze e privacy](#dati-licenze-e-privacy)
- [Struttura del progetto](#struttura-del-progetto)

## Che cosa si vede nella pagina

- **Un punto = una persona**; un collegamento = una coppia vicina secondo almeno un layer. All'apertura si vede
  tutto l'ateneo, colorato per comunità.
- **Un dipartimento o una comunità da soli**: si scelgono dai due menu in alto (o con un clic nella legenda) e si
  vede **solo quello**, ridisposto e ingrandito, con i nomi. Un dipartimento è colorato per comunità (i suoi temi),
  una comunità per dipartimento (da dove vengono le persone). La scheda a lato dice quante persone sono, quali
  comunità o dipartimenti contiene, con quali altre strutture ha più legami e quanti sono «inesplorati».
- **Una persona da sola**: un clic su un punto (o la ricerca per nome, tasto `/`) mostra la persona al centro con chi
  le è vicino, e a lato ruolo, struttura, settore, insegnamenti correnti e, per ogni layer, i vicini con le prove
  (titoli con link DOI, insegnamenti). Un selettore rapido (**Tutti** · **Altri dip.** · **Inesplorati**) filtra simultaneamente l'elenco laterale e i collegamenti visibili sul grafo. `Esc` o un clic nel vuoto torna alla vista precedente.
- **Trova ponte tra due ricercatori** (in *Esplora* e dal pulsante *Trova ponte…* nella scheda di una persona): mantenendo visibile l'intera mappa dell'ateneo, permette di scegliere due persone qualsiasi (cercandole per nome o cliccando due punti direttamente sul grafo) per evidenziare il legame diretto o la catena di colleghi ponte più forte che le connette, con le prove passo per passo.
- **Evidenziazione incrociata Lista ↔ Grafo e ispezione degli archi**: passando il mouse su una coppia in *Esplora*, su un vicino nella scheda persona o su una tappa del *Trova ponte*, i due ricercatori e il filo che li unisce si accendono sul grafo; viceversa, passando il mouse su qualsiasi linea del grafo compaiono i due nomi, i percentili dei layer e il motivo concreto del legame (un clic sulla linea apre il confronto dettagliato).
- **Esplora**: sceglie che cosa cercare; sotto compare l'elenco delle coppie, dalla più forte, con il motivo, e si
  può scaricare in CSV.

  | Vista | Regola |
  |---|---|
  | Tutti i collegamenti | la rete completa, i legami più forti secondo i pesi |
  | Collaborazioni inesplorate | nessuna pubblicazione insieme, nessuna struttura in comune, semantica (o bibliografia) ≥ 90° percentile |
  | Insegnano insieme, mai pubblicato insieme | tengono lo stesso insegnamento, nessuna pubblicazione in comune |
  | Didattica affine, mai pubblicato insieme | layer didattica nell'1% più alto, non lo stesso insegnamento, nessuna pubblicazione in comune |
  | Coautori di strutture diverse | hanno pubblicato insieme pur non avendo strutture in comune |

  Si combina con il dipartimento scelto: «inesplorate» + Fisica = le collaborazioni inesplorate di Fisica, con le
  persone esterne coinvolte mostrate più chiare.
- **Matrice**: tutte le strutture a confronto, in una tabella: quante collaborazioni inesplorate (o collegamenti, o
  coautori) ci sono fra ogni coppia di strutture. Un clic su una casella apre proprio quelle coppie.
- **Condivisione del link ed esportazione immagine PNG**: l'URL aggiorna in tempo reale dipartimento, comunità, vista, persona selezionata o coppia del *Trova ponte*; il pulsante **Condividi vista** copia il link diretto negli appunti, mentre il pulsante **Scarica immagine PNG** cattura il grafo ad alta risoluzione pronto per slide o presentazioni.
- **Controlli, modelli e risoluzioni**: soglia e visibilità dei collegamenti, dimensione dei punti, pesi dei layer (con pulsanti *Ripristina*), passaggio in tempo reale tra **dettaglio comunità** *Temi (risoluzione Leiden 2.0, 14 comunità)* e *Macro-aree (risoluzione Leiden 1.0, 10 macro-aree)*, e confronto diretto tra i **modelli semantici** *Qwen3-0.6B* e *Google EmbeddingGemma-2*. I layer per cui non ci sono dati non vengono mostrati.
- **Tema Chiaro / Notte manuale, spiegazioni al passaggio del mouse e bilinguismo**: pulsante sole/luna in alto (e selettore nei Controlli) per passare manualmente tra modalità chiara e modalità notte indipendentemente dal tema del sistema operativo; tooltip esplicativi soffermandosi sugli indicatori tecnici (`pct`, `cos`, `SSD`, `Temi 2.0`, `Macro-aree 1.0`); interruttore IT/EN; utilizzabile anche da telefono.

## Installazione

Servono Linux (o WSL2), Python 3.12 e [uv](https://docs.astral.sh/uv/). Una GPU NVIDIA è consigliata per il passo
`embed` (senza, gira su CPU, lentamente).

```bash
git clone <url> && cd EmbeddedResearcher
uv sync --extra dev        # crea .venv con le dipendenze e pytest
uv run pytest -q           # test su dati sintetici, pochi secondi, nessuna rete
```

Poi, in `config.toml`, compilare `contact.email`: finisce nello User-Agent di ogni richiesta HTTP, così chi gestisce
i server sa chi contattare.

## Esecuzione

Poiché per ragioni di privacy il repository Git non include i dati scaricati né i grafi calcolati, chi clona il progetto può costruire tutto sulla propria macchina **con un clic dalla pagina web** oppure **con un solo comando da terminale**.

### Avvio rapido in 1 clic (da pagina web o da terminale)

- **Opzione A — Direttamente dalla pagina web (1 clic nel browser):**
  ```bash
  ./run.sh
  # oppure: uv run python -m unitn_net serve
  ```
  Aprendo `http://127.0.0.1:8000/` quando `graph.json` non è ancora presente, compare automaticamente la scheda **«Costruisci la rete sulla tua macchina»**: basta cliccare **«Avvia calcolo ora (1 clic)»** (spuntando facoltativamente anche il modello alternativo *Gemma-2*) per scaricare i dati aperti UniTrento e IRIS, eseguire l'intera pipeline locale seguendo barra di avanzamento e log in tempo reale, e aprire automaticamente il grafo appena pronto.

- **Opzione B — Da terminale in un solo comando:**
  ```bash
  ./run.sh --build          # scarica i dati mancanti, esegue l'intera pipeline e avvia il server
  ./run.sh --alt            # costruisce anche il modello alternativo Gemma-2 e avvia il server
  # oppure, per eseguire solo il calcolo senza restare in ascolto:
  uv run python -m unitn_net build
  uv run python -m unitn_net build --alt
  ```

### Esecuzione passo per passo

Ogni singolo passo si può anche lanciare separatamente con `uv run python -m unitn_net <passo>`; legge i risultati del precedente e riscrive i propri.

**1. Scaricare i dati** (una volta, o quando si vuole aggiornare):

| Passo | Che cosa fa | Durata |
|---|---|---|
| `fetch-opendata` | Scarica i 4 dataset aperti dell'ateneo (personale, pubblicazioni, insegnamenti, unità organizzative) | minuti |
| `audit` | Scrive `reports/00_data_audit.md`: campi realmente presenti, conteggi, ruoli. Da rileggere se i dati cambiano formato | secondi |
| `fetch-iris` | Raccoglie gli abstract da IRIS (archivio delle pubblicazioni) via OAI-PMH, una richiesta ogni 5 s come chiede il `robots.txt`; riprende se interrotto | ~2 ore |
| `fetch-openalex` | *Facoltativo.* Riferimenti bibliografici da OpenAlex, per i layer `coupling` e `direct` e gli abstract di fallback (serve `OPENALEX_API_KEY` in `.env`) | ~30 min |

**Come eseguire OpenAlex in autonomia (facoltativo):**
1. Creare un account su [openalex.org](https://openalex.org) e copiare la propria chiave API.
2. Creare nella radice del progetto un file `.env` (già escluso da git) con:
   ```ini
   OPENALEX_API_KEY=la_tua_chiave_api
   ```
3. Lanciare:
   ```bash
   uv run python -m unitn_net fetch-openalex
   uv run python -m unitn_net all
   ```
   Il passo scarica in primo luogo in blocco tutti i lavori affiliati a UniTrento su OpenAlex dal 2010 (indicativamente 220 pagine da 200 lavori, 2 minuti, costo **$0,03**) e poi recupera singolarmente i DOI mancanti dalla cache d'ateneo (chiamate singole gratuite su OpenAlex, ~25–35 minuti; se interrotto riprende esattamente dal DOI a cui era arrivato). Il tetto di sicurezza è fissato a `max_cost_usd = 2.0` in `config.toml`. Se `OPENALEX_API_KEY` è presente in `.env`, anche il comando `build` (e il pulsante 1-clic nella pagina web) esegue automaticamente `fetch-openalex`.

**2. Calcolare** (tutto in un colpo, sui dati già scaricati):

```bash
uv run python -m unitn_net all
```

equivale a questi passi, che si possono anche lanciare uno per uno:

| Passo | Che cosa fa | Risultato |
|---|---|---|
| `normalize` | Dati grezzi → tabelle; tiene solo le persone con un ruolo in `scope.roles`; scarta telefoni e ogni campo non usato | `data/interim/` |
| `link` | Associa a ogni pubblicazione l'abstract IRIS (per DOI, o titolo identico e anno ±1) e ne rileva la lingua | `data/processed/publications.parquet`, `reports/01_linking.md` |
| `embed` | Calcola i vettori di abstract e insegnamenti (con cache: rifà solo i testi nuovi) | `data/processed/embeddings.*` |
| `layers` | I layer per ogni coppia, la scelta dei collegamenti, le prove | `edges.parquet`, `reports/03_layers.md` |
| `graph` | Comunità (risoluzioni 2.0 e 1.0), loro nomi e parole chiave, posizioni dei punti | `communities.parquet`, `reports/03_graph.md` |
| `evaluate` | Copertura per dipartimento, test di previsione, confronto fra modelli | `reports/04_evaluation.md` |
| `export` | Il file unico letto dalla pagina (solo i campi che servono) | `data/processed/graph.json` |

**3. Guardare:**

```bash
uv run python -m unitn_net serve        # http://127.0.0.1:8000/
```

Confronto con un secondo modello di embedding (facoltativo): `uv run python -m unitn_net build --alt` (oppure `embed --alt`, `layers --alt`, `graph --alt`, `export --alt`, `evaluate`) per generare `graph_alt.json` e attivare il selettore del modello nella pagina. Vedi [Valutazione](#valutazione).

## Tenerlo sempre acceso come server

`serve` è un piccolo server locale: espone **soltanto** i file di `web/`, `graph.json` (ed eventualmente
`graph_alt.json`) e gli endpoint locali `/api/status` e `/api/build` (quest'ultimo accetta richieste esclusivamente da `127.0.0.1`/`::1` con header `X-Unitn-Net: 1`). I dati grezzi, le tabelle intermedie e i report non sono raggiungibili (a differenza di
`python -m http.server` lanciato dalla radice).
Le librerie JavaScript sono in `web/vendor/`, quindi la pagina funziona anche senza Internet.

Per farlo partire da solo all'accensione e ripartire se cade, lo script `deploy/install-service.sh` genera e installa
il servizio systemd adattando automaticamente il percorso alla cartella in cui si trova il progetto sulla macchina finale:

```bash
bash deploy/install-service.sh          # scrive ~/.config/systemd/user/unitn-net.service col percorso reale e lo avvia
loginctl enable-linger "$USER"          # parte all'avvio anche senza login
systemctl --user status unitn-net       # log: journalctl --user -u unitn-net
```

Dopo un nuovo `export` basta ricaricare la pagina: il server non va riavviato.

Il server ascolta solo su `127.0.0.1` (lo stesso PC). Per raggiungerlo da altre macchine: `--host 0.0.0.0` su una rete
fidata, oppure — meglio — dietro un reverse proxy con HTTPS e controllo degli accessi. La pagina mostra nomi di persone
reali con affinità *dedotte*: renderla raggiungibile da altri è una forma di diffusione, vedi
[Dati, licenze e privacy](#dati-licenze-e-privacy). Su WSL2 systemd va abilitato (`[boot] systemd=true` in
`/etc/wsl.conf`) e il servizio vive finché Windows tiene accesa la distribuzione; per un server sempre attivo è più
adatto un PC Linux.

## Come sono calcolati i punteggi

Tutte le soglie e i pesi citati qui stanno in `config.toml`; il codice non ne contiene.

### Chi c'è

Le persone con almeno un ruolo fra quelli in `scope.roles`: professori (ordinari, associati, emeriti, senior,
aggregati, visiting), ricercatori, assegnisti, docenti a contratto, post-doc, collaboratori/contrattisti/incaricati/
borsisti di ricerca. **Dottorandi, personale tecnico-amministrativo, ospiti e ruoli organizzativi sono esclusi.**
Pubblicazioni dal 2010 (`scope.pub_year_min`).

Ogni persona ha una struttura principale (se ne ha più d'una vince, nell'ordine: dipartimento, facoltà, scuola,
centro) e l'elenco di tutte le strutture a cui risulta afferente. Strutture che negli open data mancano si possono
aggiungere a mano in `data/manual_affiliations.csv` (modello: `data/manual_affiliations.example.csv`).
Eventuali persone che chiedono di essere escluse si indicano in `data/optout.csv` (colonna `person_id` oppure
`given_name,family_name`, escluso da git): `normalize` le rimuove all'origine.

### Regola generale: «non definito» non è zero

Ogni layer è un numero fra 0 e 1 per ogni coppia, oppure **non definito** quando mancano i dati per calcolarlo
(per esempio: una delle due persone non ha abstract). Un layer non definito non conta come zero: semplicemente non
entra nella media. Le pubblicazioni firmate insieme sono **escluse** dal confronto semantico fra i due coautori,
altrimenti due coautori risulterebbero simili per definizione.

### Layer `sem` — semantica delle pubblicazioni

È il layer principale. In parole semplici: due persone sono vicine se, per ciascun articolo dell'una, c'è un articolo
dell'altra che parla di cose simili, e viceversa.

1. **Testo.** Per ogni pubblicazione il testo è `titolo. abstract`, con l'**abstract intero** (fino a 4096 token;
   i rarissimi testi più lunghi sono troncati e contati in `embed_stats.json`). Le pubblicazioni **senza abstract non
   partecipano**: i soli titoli non vengono confrontati. Non valgono come abstract i testi sotto le 20 parole
   (`layers.min_abstract_words`: «-», «Guest editorial», «in stampa»…).
2. **Vettore.** Il modello [`Qwen/Qwen3-Embedding-0.6B`](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
   (revisione fissata in `config.toml`) trasforma ogni testo in un vettore di 1024 numeri; testi di argomento simile
   hanno vettori vicini. La vicinanza fra due vettori è il loro *coseno*.
3. **Stessa lingua.** Si confrontano solo pubblicazioni nella stessa lingua, italiano con italiano e inglese con
   inglese (`layers.sem_within_language`); le altre lingue restano fuori. La lingua è rilevata dal testo e, se
   incerta, presa da quella dichiarata negli open data.
4. **Chi ha il layer.** Servono almeno 3 abstract nella stessa lingua (`layers.min_papers_sem`).
5. **Calibrazione.** Un coseno non vale lo stesso in ogni lingua (due abstract italiani presi a caso si somigliano
   in media più di due inglesi). Per questo ogni coseno è sostituito dal suo **percentile fra 200.000 coppie casuali
   di abstract della stessa lingua**: 0,99 significa «più simili del 99% delle coppie prese a caso».
6. **Da articoli a persone.** Fra le pubblicazioni di A e quelle di B (tolte quelle in comune): per ogni articolo di
   A si prende il più simile di B, e si fa la media; lo stesso da B verso A; il punteggio è la media delle due.
   Gli articoli recenti pesano di più: peso `exp(−anni/8)` (`layers.recency_tau`).
7. **Più lingue.** Se la coppia ha in comune sia italiano sia inglese, il punteggio è la media dei due, pesata sul
   numero di articoli (il minore fra i due autori) in ciascuna lingua.
8. **Per quali coppie.** Il calcolo esatto è costoso, quindi si fa solo per i 50 candidati più vicini di ogni persona
   (`layers.sem_candidates`), scelti confrontando i «centroidi» (la media pesata dei vettori di una persona). Per
   tutte le altre coppie `sem` è non definito.

**Prove mostrate:** le tre coppie di articoli più simili, con il coseno vero e il link DOI.

**Affidabilità** (etichetta accanto al punteggio): `n / (n + 5)`, dove `n` è il numero di abstract della persona in
quella lingua; per la coppia vale il lato più debole. Con 5 abstract è 50%, con 20 è 80%. È una regola pratica, non
calibrata sui dati, e non modifica il punteggio (l'interruttore «Pesa la semantica per affidabilità» la usa per
ridurre il peso di `sem` nel punteggio complessivo).

### Layer `teach` — didattica

Media pesata di tre componenti semplici (pesi in `[teach]`), calcolata sulle componenti definite per la coppia:

| Componente | Peso | Calcolo |
|---|---|---|
| Insegnamenti tenuti insieme | 0,3 | `1 − 0,5^k`, con `k` = insegnamenti diversi in cui compaiono entrambi (stesso insegnamento, stesso corso di studi, stesso anno): 0,5 con uno, 0,75 con due… |
| Corsi di studio in comune | 0,3 | indice di Jaccard: corsi di studio in cui insegnano entrambi ÷ corsi di studio in cui insegna almeno uno dei due |
| Contenuto degli insegnamenti | 0,4 | coseno fra le medie dei vettori degli insegnamenti di ciascuno. Il testo è `nome. descrizione`; come per gli abstract, un insegnamento **senza descrizione** (meno di 20 parole) non ha vettore: il solo nome non viene confrontato. Se uno dei due non ha insegnamenti con descrizione, questa componente è non definita |

Si usano tutti gli anni accademici disponibili negli open data. **Prove mostrate:** gli insegnamenti in comune,
i corsi di studio in comune, le tre coppie di insegnamenti più simili.

### Layer `coauth` — coautorialità

`log(1 + numero di pubblicazioni firmate insieme)`, diviso per il massimo fra tutte le coppie. **Prove:** le
pubblicazioni in comune più recenti.

### Layer `field` — settore disciplinare

1 se le due persone hanno lo stesso SSD, altrimenti 0. Non definito per chi non ha un SSD negli open data (il campo
CUN, previsto dal codice con valore 0,5, nei dati reali è sempre vuoto). Non crea collegamenti da solo: è un'informazione
in più sui collegamenti creati dagli altri layer.

### Layer `coupling` e `direct` — bibliografie (solo con OpenAlex)

Attivi solo dopo `fetch-openalex`; senza, restano non definiti e la pagina non li mostra.
`coupling`: coseno fra i profili dei riferimenti bibliografici citati dai due (ogni riferimento pesa meno se è citato
da molti, peso IDF). `direct`: `log(1 + citazioni dirette fra i lavori dell'uno e dell'altro)`, riportato a 0–1.
In entrambi le pubblicazioni in comune sono escluse.

### Da dove vengono i dati attuali e cosa manca senza OpenAlex

Senza il passo facoltativo `fetch-openalex`, la rete è costruita interamente da due fonti istituzionali:

1. **Open data UniTrento (`dati.trentino.it`, CC BY 4.0)**: forniscono l'anagrafica del personale (nome, cognome,
   `person_id`, ruolo, strutture di afferenza, settore scientifico-disciplinare SSD; il campo CUN è sempre vuoto),
   gli insegnamenti (nome, descrizione del programma, corso di studi, anno accademico, docenti) e i metadati delle
   pubblicazioni dal 2010 (**63.912** pubblicazioni uniche: titolo, anno, tipo, lingua dichiarata, coautori interni
   all'ateneo, citazione testuale e DOI esplicito o estratto dalla citazione). **Gli open data non contengono quasi mai
   gli abstract né le bibliografie degli articoli.**
2. **IRIS UniTrento (`iris.unitn.it`, OAI-PMH)**: abilita il layer semantico associando alle pubblicazioni degli open
   data (per DOI o per titolo normalizzato identico e anno ±1) gli **abstract** depositati nell'archivio istituzionale
   e recuperando **314 DOI** mancanti negli open data. Nello snapshot attuale IRIS fornisce un abstract valido per
   **38.898 pubblicazioni su 63.912 (60,9%)**: il **72,6%** di quelle in inglese e il **28,6%** di quelle in italiano.

**Che cosa si perde senza OpenAlex (`fetch-openalex` non eseguito):**

- **I due layer bibliografici `coupling` (peso previsto 0,20) e `direct` (peso previsto 0,10) restano spenti (`NaN`):**
  né gli open data né IRIS espongono la lista dei riferimenti bibliografici (`referenced_works`) citati da ciascun
  articolo. Senza OpenAlex non si misurano quindi né l'accoppiamento bibliografico (quante fonti scientifiche due
  persone citano in comune, pesate per rarità IDF) né le citazioni dirette reciproche fra lavori di docenti dell'ateneo.
  Poiché un layer non definito non conta come zero ma esce dalla media, il punteggio complessivo viene calcolato sui
  soli layer attivi (`sem`, `teach`, `coauth`, `field`).
- **Gli abstract di recupero (*fallback*) per il 39,1% di pubblicazioni senza abstract su IRIS:** quando una
  pubblicazione ha il DOI ma è priva di abstract su IRIS, il passo `link` può ricostruire l'abstract dall'indice
  invertito (`abstract_inverted_index`) di OpenAlex. Senza OpenAlex, le pubblicazioni non coperte da IRIS restano
  escluse dal layer semantico `sem`.
- **Le «Collaborazioni inesplorate» su base bibliografica:** la definizione di collaborazione inesplorata richiede
  `sem` *oppure* `coupling` almeno al 90° percentile. Senza `coupling`, chi ha meno di 3 abstract nella stessa lingua
  su IRIS (il 36% delle persone in ambito) non può emergere nelle collaborazioni inesplorate nemmeno quando cita
  esattamente la stessa letteratura scientifica.

### Dai layer alla rete

- **Quali collegamenti.** Per ogni layer (tranne `field`) e per ogni persona si tengono le 10 coppie con il punteggio
  più alto (`layers.top_k`); la rete è l'unione.
- **Percentili.** Per rendere confrontabili i layer, ogni punteggio è trasformato nella sua posizione (0–1) fra tutte
  le coppie per cui quel layer è definito.
- **Punteggio complessivo.** Media pesata dei percentili sui soli layer definiti per la coppia. Pesi di partenza:
  `sem` 0,35 · `coupling` 0,20 · `direct` 0,10 · `coauth` 0,10 · `teach` 0,15 · `field` 0,10; si cambiano dalla pagina.
- **Collaborazione inesplorata.** Nessuna pubblicazione insieme; entrambe le persone hanno almeno una struttura
  e non ne hanno nessuna in comune; `sem` (o `coupling`) almeno al 90° percentile.
- **Comunità.** Algoritmo di Leiden (modularità) sulla rete pesata con il punteggio complessivo, ripetuto con 10 semi
  casuali per misurare quanto il risultato è stabile (indice ARI nel report). La «risoluzione» (`graph.resolution`)
  decide quanto sono fini i gruppi: con 1 escono circa dieci comunità che ricalcano i dipartimenti; con 2 (valore
  scelto) i dipartimenti grandi si dividono per tema (per esempio idraulica e strutture, materiali e fisica quantistica)
  e compaiono gruppi trasversali (ricerca clinica, politica internazionale, didattica), con la stessa stabilità. Il nome di una comunità è il
  dipartimento prevalente fra i membri (da solo se supera il 40%, altrimenti i primi due); le parole chiave sono i
  termini usati da almeno il 12% dei membri e rari nel resto dell'ateneo.
- **Posizioni.** Disposizione «a forze» (Fruchterman–Reingold); i collegamenti interni a una comunità tirano di più,
  solo per rendere leggibile il disegno. La distanza sullo schermo è indicativa: contano i collegamenti.

## Valutazione

`evaluate` scrive `reports/04_evaluation.md`:

1. **Copertura per dipartimento**: quante persone hanno ciascun layer. È il primo numero da guardare (vedi limiti).
2. **Previsione di coautorie future**: i layer sono ricalcolati usando solo le pubblicazioni fino a 4 anni fa, e si
   verifica se le coppie con punteggio alto hanno poi iniziato a pubblicare insieme, a confronto con il caso, lo
   «stesso SSD» e lo «stesso dipartimento». Intervalli di confidenza con bootstrap sulle persone.
   Attenzione a come leggerla: misura se la vicinanza anticipa le collaborazioni, **non** se due persone lavorano
   davvero sullo stesso tema.
3. **Correlazioni** fra layer.
4. **Confronto fra modelli di embedding**, se è stato eseguito `embed --alt` (in `config.toml`:
   [`google/embeddinggemma-2`](https://huggingface.co/google/embeddinggemma-2)).
5. **Foglio per il controllo a mano** (`reports/audit.csv`): 20 persone a caso con i loro vicini e le prove, e una
   colonna vuota per il giudizio.

**Ultima esecuzione (11/11/2026, snapshot open data del 17/09/2026).** 1.732 persone, 16.728 collegamenti, 636
collaborazioni inesplorate, 14 comunità con almeno 5 persone (stabilità fra semi: ARI 0,95). Il layer semantico è
disponibile per il 64% delle persone. Previsione di coautorie future (AUC-PR, più alto è meglio; il caso vale 0,001):
semantica 0,045 [0,034–0,061], didattica 0,029 [0,024–0,039], stesso SSD 0,007, stesso dipartimento 0,007.
Con EmbeddingGemma 2 al posto di Qwen3 la semantica scende a 0,025 [0,020–0,033], mentre sulla capacità di ritrovare
persone dello stesso SSD i due modelli sono pari (0,270 e 0,262, intervalli sovrapposti): per questo il modello
principale resta Qwen3. Nessun controllo a mano è ancora stato fatto.

`scripts/jev_judge_edges.py` è un esperimento a parte e facoltativo: fa giudicare a un modello esterno (Jev, di
TypeSafe) se le coppie di abstract dietro un collegamento trattano lo stesso tema. **Invia titoli e abstract a un
servizio esterno a pagamento**, non parte senza `--yes` e non è necessario per nient'altro.

## Limiti noti

- **Chi non ha abstract non ha il layer semantico.** Gli abstract arrivano da IRIS: nello snapshot del 17/09/2026 ha
  un abstract il 60,9% delle 63.912 pubblicazioni, il 72,6% di quelle in inglese e il 28,6% di quelle in italiano.
  Nell'ultima esecuzione il layer è disponibile per il 64% delle persone, dal 22% (Scuola di Studi Internazionali) e
  38% (CISMed) al 76% (Giurisprudenza); la tabella per dipartimento è nel report di valutazione e va letta prima di
  trarre conclusioni. Fra le 621 persone senza layer semantico, il 90% ha meno di 3 pubblicazioni negli open data.
- **Italiano e inglese non si confrontano fra loro**: chi pubblica solo in italiano e chi solo in inglese non
  possono risultare vicini per semantica.
- **I collegamenti sono ipotesi, non fatti.** La validazione finora è indiretta (previsione di coautorie); un
  controllo sistematico da parte di persone non è ancora stato fatto.
- La coautorialità riguarda solo coautori interni all'ateneo e in ambito.
- L'affidabilità e i pesi dei layer sono scelte ragionate, non stimate dai dati.
- Negli open data alcune afferenze mancano (per esempio a centri interdipartimentali) e gli insegnamenti
  2023/24 e 2024/25 non erano scaricabili alla data dello snapshot.

## Dati, licenze e privacy

**Fonti**

| Fonte | Che cosa | Condizioni |
|---|---|---|
| [Open data dell'Università di Trento](https://dati.trentino.it) | personale, pubblicazioni, insegnamenti, unità organizzative | CC BY 4.0: va citata la fonte (la pagina lo fa nel piè di pagina) |
| [IRIS UniTrento](https://iris.unitn.it), interfaccia OAI-PMH | abstract, DOI | interfaccia pubblica pensata per la raccolta automatica; si rispetta il `Crawl-delay` di 5 s. Gli abstract restano di autori ed editori: qui sono usati solo in locale per calcolare i vettori e **non vengono ridistribuiti** (non sono in questa repository né nel file letto dalla pagina, che contiene solo titoli e DOI). Le condizioni di riuso dei metadati IRIS non sono state verificate con l'ateneo |
| [OpenAlex](https://openalex.org) (facoltativo) | riferimenti bibliografici (`coupling`, `direct`) e abstract di fallback | CC0 |

`robots.txt` è rispettato da ogni download: se vieta una risorsa, la pipeline si ferma.

**Software di terzi.** Modello di embedding Qwen3-Embedding-0.6B (Apache 2.0); modello di confronto
EmbeddingGemma 2 (Apache 2.0 secondo la sua scheda); librerie JavaScript graphology e sigma (MIT, testi in
`web/vendor/LICENSES.md`); dipendenze Python in `pyproject.toml`.

**Dati personali.** I dati di partenza sono pubblici, ma **associare a persone identificate affinità dedotte da un
algoritmo è un trattamento nuovo** rispetto alla pubblicazione originale. Per questo:

- la repository non contiene dati: `data/` e `reports/` sono in `.gitignore`;
- all'ingestione si tengono solo i campi usati (telefoni, email e il resto sono scartati) e nel file per la pagina
  finisce solo ciò che la pagina mostra;
- nessuna classifica e nessuna misura di qualità individuale; i dottorandi sono esclusi;
- il server ascolta solo sul PC locale, salvo scelta esplicita.

**Prima di rendere la pagina accessibile ad altri** (in rete o su Internet) servono, da concordare con l'ateneo
(`opendata@unitn.it`, responsabile della protezione dei dati `rpd@unitn.it`): un'informativa alle persone
interessate (art. 14 GDPR), un modo semplice per chiedere di essere esclusi, e una base giuridica per il trattamento.
Questo README non è un parere legale.

## Struttura del progetto

```
run.sh                   avvio rapido in 1 comando (sincronizza, calcola se richiesto, avvia il server)
config.toml              soglie, pesi, modelli, indirizzi: tutto ciò che si può regolare
pyproject.toml, uv.lock  dipendenze
src/unitn_net/           un modulo per passo (python -m unitn_net <passo>)
web/                     la pagina: index.html, app.js, style.css, vendor/ (nessuna compilazione)
deploy/                  servizio systemd per tenere acceso il server
scripts/                 esperimenti facoltativi
tests/                   test unitari + prova end-to-end su dati sintetici
data/                    raw/ (download, per data), interim/, processed/   — esclusi da git
reports/                 report prodotti dalla pipeline                    — esclusi da git
```

## Progetto e licenza

**Sebastiano Franchini · Roberto Zamparelli** — Università degli Studi di Trento.

Il codice di questo progetto è rilasciato con licenza open-source **GNU Affero General Public License v3.0 ([`AGPL-3.0-or-later`](LICENSE))**: chiunque lo esegua, modifichi o metta a disposizione come servizio di rete è tenuto a preservare le indicazioni di paternità e a rilasciare il codice sorgente con la medesima licenza. Per citare il progetto, fare riferimento a [`CITATION.cff`](CITATION.cff).
