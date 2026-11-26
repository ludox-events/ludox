# LudoX

**Gestione eventi ludici / Board game event management**

LudoX è un software open source offline-first per la gestione di eventi ludici.
Il primo modulo operativo è **Prestiti Ludoteca / Game Library**, pensato per
associazioni, eventi, biblioteche e ludoteche che vogliono gestire prestiti di
giochi localmente senza richiedere un server.

> **Stato del progetto:** alpha. Il software è ancora in sviluppo.

## Funzioni principali

- gestione di più **Organization** nello stesso database;
- gestione di più **Event** per Organization;
- moduli abilitabili per singolo Event;
- ludoteca e prestiti separati per Event;
- due modalità alternative di prestito per Event:
  - `token`, con token fisico numerato corrispondente allo slot del documento;
  - `copy_identifier`, con identificazione della singola scatola tramite codice;
- identificatori delle copie event-specific, con origine `external` o `ludox`;
- supporto a barcode/QR tramite scanner HID o inserimento manuale + Invio;
- generazione di codici LudoX e relativa esportazione come QR PNG;
- cambio gioco mantenendo lo stesso slot;
- restituzione finale con conferma fisica del documento;
- copie fisiche multiple e owner label event-specific;
- statistiche, storico e report riferiti all'Event corrente;
- import/export della ludoteca in CSV e XLSX, inclusi gli identificatori delle copie;
- database locale SQLite con schema versionato;
- migration esplicite con backup automatico dei database esistenti;
- configurazione locale della postazione tramite `config.ini`;
- interfaccia in italiano e inglese.

La modalità `copy_identifier` non distingue operativamente tra QR code e
barcode: per LudoX entrambi producono una stringa che identifica una singola
copia fisica nello specifico Event.

La scansione tramite webcam/camera non fa parte della Game Library V1 ed è
tracciata separatamente nella issue #26.

## Modello applicativo

La struttura logica principale è:

```text
Database / workspace LudoX
│
├── Organization
│   ├── Event
│   │   ├── Prestiti Ludoteca / Game Library
│   │   └── Attività / Activities (futuro)
│   └── Event
│       └── Prestiti Ludoteca / Game Library
└── Organization
    └── ...
```

Ogni Event appartiene a una sola Organization. I dati del modulo
`game_library` appartengono allo specifico Event: giochi, copie, owner label,
identificatori delle copie, sessioni, prestiti, configurazione, statistiche e
report non vengono mescolati tra Event differenti.

Non esiste un'identità globale obbligatoria della stessa scatola tra Event.
Una ludoteca esportata e reimportata crea nuove copie nell'Event di
destinazione, preservando però gli eventuali `copy_identifier`.

## Struttura del progetto

```text
app.py                    bootstrap dell'applicazione
VERSION                   versione applicativa
config.ini                configurazione locale, creato al primo avvio

ludox/
├── bootstrap.py          bootstrap e apertura sicura del workspace
├── config.py             configurazione locale della postazione
├── database.py           accesso SQLite
├── migrations.py         versionamento e migration dello schema
├── migration_ui.py       interazione UI per autorizzare le migration
├── organizations.py      dominio Organization e contesto corrente
├── events.py             dominio Event e moduli
├── catalog.py            ludoteca event-specific
├── copy_identifiers.py   identificatori operativi delle singole copie
├── lending.py            sessioni e prestiti
├── library_transfer.py   import/export CSV/XLSX
├── reporting.py          statistiche, storico e report
├── i18n.py               traduzioni
├── ui_helpers.py         helper UI
├── ui.py                 interfaccia grafica
└── locales/
    ├── it.json
    └── en.json
```

`config.ini` e i database SQLite locali (`*.db`, `*.sqlite`, `*.sqlite3`) non
vengono versionati.

## Primo avvio

Se `config.ini` non esiste, LudoX mostra la configurazione iniziale della
postazione.

Vengono richiesti soltanto:

- lingua dell'interfaccia;
- database/workspace SQLite da utilizzare.

Il numero massimo di slot **non** è una configurazione globale della
postazione: appartiene al modulo `game_library` del singolo Event.

Una configurazione completa può assumere questa forma:

```ini
[general]
language = it
database = ludox.db

[organization]
active_organization_id = 2
active_organization_name = Ludoteca Altomilanese

[event]
active_event_id = 7
active_event_slug = amigo-2027
```

Organization ed Event correnti vengono salvati come contesto locale della
postazione e rivalidati quando viene cambiato database.

## Organization ed Event

La gestione delle Organization avviene dal Backoffice. Se esiste una sola
Organization attiva, può essere selezionata automaticamente; con più
Organization la scelta resta locale alla postazione.

Gli Event vengono gestiti dal Backoffice e l'Event operativo corrente viene
selezionato dalla Home. Gli Event in stato `draft` o `active` sono utilizzabili
come contesto operativo; gli Event `archived` o `cancelled` restano disponibili
come storico/amministrazione.

## Prestiti Ludoteca

Ogni Event usa una sola modalità operativa alla volta:

```text
identification_mode = token
```

oppure:

```text
identification_mode = copy_identifier
```

Il cambio di modalità è consentito soltanto quando non esistono sessioni o
prestiti aperti nell'Event.

### Modalità token

La modalità token utilizza una corrispondenza diretta:

```text
token N = slot fisico N del documento
```

Il flusso principale è:

```text
NUOVO PRESTITO
→ assegna il primo slot libero
→ documento nello slot corrispondente
→ token consegnato alla persona

CAMBIO GIOCO
→ stesso slot/token
→ chiusura del prestito precedente
→ apertura del nuovo prestito

RESTITUZIONE FINALE
→ rientro del gioco
→ recupero fisico del documento
→ conferma della restituzione
→ slot nuovamente disponibile
```

### Modalità `copy_identifier`

Ogni scatola prestabile possiede un codice operativo univoco nello specifico
Event. Può essere:

- `external`, ad esempio un barcode inventariale già presente sulla scatola;
- `ludox`, generato dall'app nel formato `LX-C-000123`.

Uno scanner USB/Bluetooth HID viene trattato come una tastiera:

```text
codice → ENTER
```

La digitazione manuale del codice seguita da Invio produce lo stesso
comportamento.

Il flusso principale è:

```text
NUOVO PRESTITO
→ scansione/digitazione della scatola
→ LudoX identifica la copia
→ assegna il primo slot libero
→ documento nello slot
→ nessun token fisico

CAMBIO GIOCO
→ scansione della copia restituita
→ scansione della nuova copia
→ stesso slot documento
→ chiusura/apertura dei prestiti in transazione

RESTITUZIONE FINALE
→ scansione della copia restituita
→ LudoX mostra lo slot del documento
→ recupero fisico del documento
→ conferma DOCUMENTO RESTITUITO
→ slot nuovamente disponibile
```

LudoX non registra nominativo, numero del documento o altri dati identificativi
della persona che utilizza il servizio di prestito.

La procedura completa per entrambe le modalità è descritta in
[`docs/OPERATION.md`](docs/OPERATION.md).

## Import/export ludoteca

La ludoteca dell'Event corrente può essere importata ed esportata usando CSV o
XLSX.

Il formato minimo legacy/aggregato resta valido:

```text
game_name,owner_label,quantity
Azul,Biblioteca,3
Azul,LAM,2
Kingdomino,Matteo,1
```

Per preservare gli identificatori delle singole copie è disponibile il formato
esteso:

```text
game_name,owner_label,quantity,copy_identifier,identifier_source
Azul,Biblioteca,1,BIB-000123,external
Azul,LAM,1,LX-C-000451,ludox
Cascadia,LAM,3,,
```

Una copia identificata viene esportata su una riga con `quantity = 1`; le copie
senza identificatore possono rimanere aggregate.

L'import è additivo. I titoli vengono confrontati con normalizzazione minima
(trim + confronto case-insensitive). Titoli soltanto simili, come
`Kingdomino` e `King Domino`, restano distinti: LudoX non esegue fuzzy matching
o fusioni automatiche.

Gli identificatori devono essere univoci nello stesso Event, ma lo stesso
valore può essere usato in Event differenti.

## Migration e backup

LudoX usa `PRAGMA user_version` per versionare lo schema SQLite.

Lo schema corrente della Game Library V1 è **v4**.

Un database nuovo o realmente vuoto viene inizializzato direttamente allo
schema corrente. Se un database esistente usa uno schema precedente, LudoX:

1. informa che è necessaria una migration;
2. richiede autorizzazione esplicita;
3. crea automaticamente un backup completo;
4. applica le migration in transazione;
5. prosegue soltanto se l'aggiornamento termina correttamente.

Un database con schema più recente di quello supportato viene rifiutato senza
tentare downgrade automatici.

Vedi [`docs/MIGRATIONS.md`](docs/MIGRATIONS.md).

## Traduzioni

Le traduzioni sono risorse JSON statiche e non vengono memorizzate nel
database.

Per aggiungere una lingua è necessario aggiungere il relativo file in
`ludox/locales/` e registrarla nel sistema i18n/configurazione.

L'italiano è la lingua di fallback.

## Requisiti per lo sviluppo

- Python 3;
- Tkinter/Tk;
- dipendenze Python indicate in `requirements.txt`.

### Windows

```bat
git clone https://github.com/ludox-events/ludox.git
cd ludox
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

### Ubuntu / Debian / Linux Mint

```bash
sudo apt update
sudo apt install python3 python3-tk python3-venv python3-pip

git clone https://github.com/ludox-events/ludox.git
cd ludox
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

La distribuzione portable Windows/Linux tramite PyInstaller è tracciata nella
issue #24.

## Test

La suite automatica usa `pytest`:

```bash
python -m pytest
```

Le verifiche manuali visibili all'utente sono raccolte in
[`docs/MANUAL_TESTS.md`](docs/MANUAL_TESTS.md).

## Privacy by design

Il modulo Prestiti Ludoteca non registra dati identificativi delle persone che
prendono giochi in prestito.

Lo slot identifica soltanto la posizione fisica del documento durante una
sessione anonima. In modalità token il numero dello slot coincide anche con il
token fisico; in modalità `copy_identifier` la scatola identifica il prestito,
mentre lo slot continua a rappresentare esclusivamente la posizione del
documento.

Le owner label delle copie sono etichette operative della ludoteca e non
costituiscono un'anagrafica delle persone che prendono giochi in prestito.

## Backoffice

La password predefinita della versione alpha è:

```text
ludox
```

Serve soltanto a evitare accessi accidentali e non rappresenta una misura di
sicurezza forte.

## Documentazione

La documentazione tecnica e funzionale è raccolta in [`docs/`](docs/README.md).
Le specifiche approvate riportano esplicitamente il marker:

```text
STATUS: APPROVED SPECIFICATION — READ ONLY
```

## Licenza e contributi

LudoX è distribuito sotto **AGPL-3.0-only**.

Implementazione iniziale: **Copyright © 2026 Matteo Sassi**.

I contributi destinati all'upstream ufficiale sono soggetti al
[LudoX Contributor License Agreement v1.0](CLA.md).

Vedi anche [CONTRIBUTING.md](CONTRIBUTING.md) e
[GOVERNANCE.md](GOVERNANCE.md).
