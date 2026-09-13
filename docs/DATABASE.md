# Database LudoX

> **STATUS: APPROVED SPECIFICATION — READ ONLY**
>
> **IMPLEMENTATION: PARTIALLY IMPLEMENTED**
>
> Questo documento è una specifica approvata di LudoX. Durante
> l'implementazione non deve essere modificato, salvo richiesta esplicita
> dell'utente. I marker `TBD` e `QUESTION` restano decisioni aperte e non
> autorizzano Codex a scegliere autonomamente una soluzione.

Questo documento raccoglie i principi dello schema dati di LudoX, descrive lo
schema implementato fino alla versione `v3` e definisce il target strutturale
della issue #4 per la modalità `copy_identifier`.

Le parti relative a funzionalità future, come il modulo `activities`, restano
specifiche di progetto non ancora completamente implementate.

## Motore locale

L'implementazione locale utilizza SQLite.

Ogni connessione deve abilitare l'integrità referenziale:

```sql
PRAGMA foreign_keys = ON;
```

Il modello logico non deve dipendere da caratteristiche che rendano
inutilmente difficile una futura implementazione server con un database
differente.

## Workspace

Un file SQLite rappresenta un workspace/database LudoX.

Un singolo database può contenere:

- più Organization;
- più Event per ciascuna Organization;
- i dati event-specific dei moduli abilitati.

LudoX deve continuare a permettere la creazione e l'apertura di database
differenti.

Il file database non coincide quindi necessariamente con un singolo Event.

## Gerarchia dati

La gerarchia concettuale è:

```text
Organization
   ↓
Event
   ↓
Module data
```

I dati del modulo `game_library` appartengono all'Event e non a un catalogo
globale dell'Organization.

I dati del modulo `game_library`, comprese le copie fisiche e i loro
identificatori, restano event-specific. Non esiste un'identità globale
obbligatoria della stessa scatola condivisa automaticamente tra Event.

## Versione dello schema

LudoX utilizza `PRAGMA user_version` per registrare la versione dello schema
SQLite.

Le versioni implementate sono:

```text
user_version = 0   schema legacy / sperimentale
user_version = 1   Organizations
user_version = 2   Events + Event Modules
user_version = 3   game_library event-specific
user_version = 4   target issue #4: copy_identifier V1
user_version = 5+  successive modifiche strutturali
```

La versione `0` identifica lo schema precedente all'introduzione della nuova
architettura versionata.

La migration `0 → 1` introduce `organizations`.

La migration `1 → 2` introduce `events` e `event_modules`.

La migration `2 → 3` introduce il modello event-specific del modulo
`game_library`.

La issue #4 deve introdurre una migration esplicita `3 → 4` per consolidare
il modello operativo degli identificatori delle copie. La versione `4` non è
considerata implementata finché la #4 non è completata.

Ogni numero di versione identifica uno stato preciso e completo dello schema.
Una versione non deve essere costruita progressivamente da più modifiche
strutturali indipendenti senza incremento di `user_version`.

Ogni futura modifica strutturale deve prevedere una migration esplicita. Le
versioni dello schema usano numeri interi progressivi, indipendenti dalla
versione applicativa di LudoX.

## Schema implementato in v3

Lo schema applicativo corrente comprende:

```text
organizations
events
event_modules

game_library_settings
game_library_owner_labels
game_library_games
game_library_game_copies
game_library_copy_identifiers
game_library_sessions
game_library_loans
```

Le vecchie tabelle del modello Prestiti legacy vengono preservate durante la
migration e non vengono automaticamente reinterpretate come dati di un Event.

### `organizations`

Contenitore logico principale.

Campi implementati minimi:

- `id`;
- `name`;
- `active`.

Una Organization viene normalmente disattivata invece di essere eliminata.

Gli eventuali campi descrittivi aggiuntivi restano estensioni future del
modello Organization.

### `events`

Ogni Event appartiene a una sola Organization.

Campi implementati:

- `id`;
- `organization_id`;
- `name`;
- `slug`;
- `start_datetime`;
- `end_datetime`;
- `timezone`;
- `status`.

Lo slug usa `a-z`, `0-9`, `-` e `_` ed è univoco all'interno della
Organization.

Organization e slug dell'Event sono immutabili dopo la creazione.

### `event_modules`

Registra quali moduli sono abilitati per un Event.

Gli identificatori riconosciuti sono:

- `game_library` — Prestiti Ludoteca / Game Library;
- `activities` — Attività / Activities.

La coppia Event/modulo è unica.

La disabilitazione di un modulo non deve cancellare automaticamente i dati già
presenti.

### `game_library_settings`

Configurazione event-specific del modulo `game_library`.

Comprende:

- `event_id`;
- `max_slots`, con valore iniziale `50`;
- `identification_mode`.

Le modalità previste nello schema sono:

- `token`;
- `copy_identifier`.

Le due modalità sono alternative per lo specifico Event. La modalità
attualmente operativa è `token`; `copy_identifier` viene completata dalla #4.

### `game_library_owner_labels`

Etichette operative dei proprietari delle copie.

Campi principali:

- `id`;
- `event_id`;
- `name`;
- `name_key` normalizzata;
- `active`.

Le owner label appartengono a un singolo Event e non rappresentano anagrafiche
di persone o soggetti giuridici.

### `game_library_games`

Rappresenta il titolo del gioco, non la singola scatola.

Campi principali:

- `id`;
- `event_id`;
- `name`;
- `name_key` normalizzata;
- `active`;
- `external_id` opzionale;
- `difficulty` opzionale;
- `difficulty_source` opzionale;
- `notes` opzionale.

All'interno dello stesso Event, il nome normalizzato è univoco.

La normalizzazione minima comprende almeno:

- rimozione degli spazi iniziali/finali;
- confronto case-insensitive.

Nomi soltanto simili non vengono fusi automaticamente.

### `game_library_game_copies`

Una riga rappresenta una scatola fisica.

Ogni copia appartiene a:

- un Event;
- un gioco;
- una owner label.

Campi principali:

- `id`;
- `event_id`;
- `game_id`;
- `owner_label_id`;
- `active`.

La quantità di un titolo non viene memorizzata come unico valore aggregato:
viene ricavata contando le copie fisiche.

La stessa scatola eventualmente usata in Event differenti non viene collegata
automaticamente attraverso un record globale: ogni Event possiede i propri
record di copia.

### `game_library_copy_identifiers`

In v3 la tabella è già predisposta per identificatori multipli e distingue
`LUDOX_QR` / `EXTERNAL_BARCODE`.

La #4 sostituisce questa semantica operativa con un modello V1 nel quale ogni
copia può avere zero o un solo `copy_identifier` attivo. QR e barcode sono
soltanto rappresentazioni fisiche del valore: il dato persistito distingue
l'origine `external` / `ludox`, non la simbologia.

La struttura v3 deve essere migrata senza perdita silenziosa dei dati; i
vincoli target sono definiti nella sezione successiva.
### `game_library_sessions`

Rappresenta una sessione anonima di prestito.

Campi principali:

- `id`;
- `event_id`;
- `slot`;
- `opened_at`;
- `closed_at` opzionale.

Lo slot corrisponde alla posizione fisica del documento.

In modalità token:

```text
token N = slot N
```

Uno slot può avere al massimo una sessione aperta alla volta nello stesso
Event.

### `game_library_loans`

Rappresenta un singolo prestito all'interno di una sessione.

Campi principali:

- `id`;
- `event_id`;
- `session_id`;
- `game_id`;
- `copy_id` opzionale;
- `checked_out_at`;
- `returned_at` opzionale.

In modalità token il gioco è noto, ma la copia fisica può non esserlo.

In modalità `copy_identifier` ogni nuovo prestito deve registrare la copia
specifica tramite `copy_id`.

Una sessione può avere una sequenza di prestiti, ma al massimo un prestito
aperto alla volta.

## Target schema v4 per gli identificatori delle copie

Nella V1 operativa una copia può avere **zero o un solo identificatore
operativo**.

QR code e barcode sono soltanto rappresentazioni fisiche dello stesso concetto
`copy_identifier`. Lo schema registra l'origine del valore, non la simbologia.

La struttura target di `game_library_copy_identifiers` deve rappresentare
almeno:

```text
id
 event_id
 copy_id
 source
 value
```

con:

```text
source ∈ {external, ludox}
```

### Vincoli richiesti

Lo schema v4 deve garantire:

- `value` non vuoto;
- una sola riga identificatore per copia nello stesso Event;
- `value` univoco nello stesso Event;
- lo stesso `value` consentito in Event differenti;
- coerenza `event_id + copy_id` tramite foreign key verso la copia;
- eliminazione dell'identificatore in cascata quando una copia eliminabile
  viene eliminata;
- nessun vincolo globale tra copie appartenenti a Event diversi.

Forma logica indicativa dei vincoli:

```text
UNIQUE(event_id, copy_id)
UNIQUE(event_id, value)
FOREIGN KEY(event_id, copy_id)
    → game_library_game_copies(event_id, id)
```

Il confronto del valore è esatto dopo il trim applicativo. Non viene applicato
case folding.

### Migration v3 → v4

La migration deve preservare eventuali identificatori già presenti:

```text
LUDOX_QR         → source = ludox
EXTERNAL_BARCODE → source = external
```

La versione v3 dell'app non espone normalmente una UI per creare più
identificatori sulla stessa copia. Se tuttavia il database contiene dati che
violano i nuovi vincoli, la migration non deve scegliere o cancellare valori
silenziosamente: deve fallire in modo comprensibile e lasciare intatto il
database originale, secondo il normale flusso backup + rollback.

## Generazione di un identificatore LudoX

Dopo la creazione della copia, LudoX può generare un valore:

```text
LX-C-<copy_id a almeno 6 cifre>
```

Esempio:

```text
copy_id = 123
→ LX-C-000123
```

La generazione deve comunque verificare il vincolo di unicità nell'Event prima
del salvataggio.

Il valore generato viene memorizzato con:

```text
source = ludox
```

Un codice fornito dall'utente/scanner viene memorizzato con:

```text
source = external
```

salvo import esplicito di un codice già marcato `ludox` nel file di
interoperabilità.

## Isolamento per Event

La scelta implementata in v3 è di materializzare `event_id` nelle principali
tabelle operative del modulo `game_library`, comprese le relazioni figlie dove
questo permette di controllare esplicitamente la coerenza tra record.

In particolare `event_id` è presente in:

- settings;
- owner label;
- giochi;
- copie;
- identificativi delle copie;
- sessioni;
- prestiti.

Le foreign key composite che includono `event_id` impediscono collegamenti
accidentali tra dati appartenenti a Event differenti.

Questa ridondanza controllata semplifica inoltre:

- query event-scoped;
- import/export;
- validazioni;
- futura architettura client/server.

La stessa regola si applica ai `copy_identifier`: il valore è univoco nello
stesso Event ma può essere riutilizzato in Event differenti.

```text
Event A: BIB-123 → consentito
Event B: BIB-123 → consentito
Event A: seconda copia BIB-123 → vietato
```

## Integrità referenziale e cancellazione

Le regole strutturali implementate in v3 combinano foreign key SQLite e
controlli applicativi.

In sintesi:

- `events.organization_id` riferisce `organizations`;
- `event_modules` viene eliminato in cascata con un Event eliminabile;
- `game_library_settings`, owner label e giochi sono event-scoped;
- le copie usano riferimenti coerenti per Event verso gioco e owner label;
- gli identificativi delle copie vengono eliminati insieme alla copia;
- sessioni e prestiti usano `ON DELETE RESTRICT` nei punti in cui lo storico
  operativo deve impedire cancellazioni distruttive;
- esistono indici univoci parziali per impedire più sessioni aperte sullo
  stesso slot e più prestiti aperti nella stessa sessione.

Il service layer aggiunge le regole funzionali che non sono esprimibili o non
conviene esprimere esclusivamente tramite foreign key.

Principio generale:

```text
dato preparatorio senza storico
→ eliminabile quando le regole del dominio lo consentono

dato entrato nello storico operativo
→ non eliminabile; disattivabile quando applicabile
```

Nel modulo `game_library`, sessioni e prestiti costituiscono storico operativo.

Un Event che contiene storico operativo non può essere eliminato.

La ludoteca non può essere azzerata dopo che è stato registrato almeno un
prestito.

Il modulo `game_library` non può essere disabilitato con sessioni o prestiti
aperti.

Per prudenza, se un titolo è stato prestato in modalità token e quindi non è
nota la scatola fisica utilizzata, le sue copie non devono essere considerate
automaticamente estranee allo storico.

L'identificatore di una copia non può essere rimosso o sostituito mentre
esiste un prestito aperto per quella copia.

Quando una copia possiede soltanto storico chiuso, il suo identificatore può
essere sostituito: lo storico resta collegato al `copy_id` e non al testo del
codice.

- TBD: Definire in futuro una politica più fine di cancellazione delle singole
  copie dopo prestiti storici effettuati in modalità token, se emergerà un
  caso d'uso concreto.

## Import/export e identificatori

Il formato minimo a tre colonne resta supportato:

```text
game_name,owner_label,quantity
```

La issue #4 estende il formato con colonne opzionali:

```text
copy_identifier
identifier_source
```

Regole strutturali:

- riga con `copy_identifier` → `quantity = 1`;
- riga senza identificatore → `quantity >= 1`;
- `identifier_source ∈ {external, ludox}` quando valorizzato;
- identificatore duplicato nello stesso Event → errore;
- identificatore duplicato solo in un altro Event → consentito;
- import ed export devono preservare il valore dell'identificatore e la sua
  sorgente;
- l'import deve essere validato completamente prima di applicare modifiche.

Le regole funzionali complete sono definite in [LENDING.md](LENDING.md).

## Compatibilità richiesta all'avvio

LudoX può operare soltanto su un database con lo schema richiesto dalla
versione corrente dell'applicazione.

All'apertura del database l'applicazione ispeziona lo schema **prima** di
inizializzare i servizi operativi.

Il comportamento dipende dallo stato rilevato:

- database nuovo o realmente vuoto → inizializzazione diretta allo schema
  corrente;
- schema già corrente → avvio normale;
- schema precedente su database esistente → migration necessaria;
- schema futuro/non supportato → errore e chiusura dell'applicazione.

Un database esistente con schema precedente non viene migrato silenziosamente.

Prima della migration LudoX deve:

1. informare l'utente della versione attuale e di quella richiesta;
2. chiedere autorizzazione esplicita;
3. creare automaticamente una copia completa di backup;
4. eseguire le migration necessarie soltanto dopo il completamento del backup.

Se l'utente rifiuta la migration, il backup fallisce o la migration fallisce,
LudoX non prosegue l'avvio operativo sul database incompatibile.

Il comportamento completo è definito in [MIGRATIONS.md](MIGRATIONS.md).

## Backup delle migration

Il backup è obbligatorio prima di qualsiasi migration di un database esistente,
anche se la modifica è semplice o puramente additiva.

Per una sequenza composta da più migration pendenti viene creato un unico
backup prima dell'intera sequenza.

Il backup viene salvato normalmente accanto al database originale con un nome
leggibile che include versione di origine, versione di destinazione e
Timestamp.

Esempio:

```text
ludox.backup-v0-to-v3-20260912-175900.db
```

Il nome non deve sovrascrivere backup già esistenti.

## Esecuzione e rollback

Le migration vengono applicate in ordine crescente e senza saltare versioni.
La sequenza viene eseguita in transazione.

`PRAGMA user_version` viene aggiornato insieme alle modifiche dello schema e
non deve rimanere avanzato se la migration fallisce.

Se manca una migration intermedia, l'aggiornamento deve fallire prima di
modificare il database.

## Service layer

La separazione minima tra UI, logica applicativa e persistenza è implementata.

La direzione corrente è:

```text
UI
 ↓
Domain / service modules
 ↓
Database access / migrations
```

La logica funzionale è distribuita in moduli dedicati, tra cui:

- `organizations`;
- `events`;
- `catalog`;
- `lending`;
- `library_transfer`;
- `reporting`.

La UI non deve eseguire direttamente query SQL per implementare i casi d'uso
del dominio.

Questa separazione permette di mantenere la logica funzionale stabile anche se
in futuro SQLite locale viene affiancato o sostituito da un servizio LAN/web.

La #4 deve rispettare la stessa separazione: risoluzione degli identificatori,
validazioni, prestiti e import/export passano attraverso service testabili
senza Tkinter; la UI non introduce query SQL dirette.

## Timestamp e timezone

Ogni Event possiede una timezone esplicita basata su identificatori IANA, per
esempio `Europe/Rome`.

I timestamp delle transazioni devono avere una rappresentazione non ambigua e
coerente con le regole del dominio. La conversione nella timezone dell'Event
avviene per visualizzazione, input e report.

Le decisioni sul formato persistente devono rimanere compatibili con una futura
architettura multi-client/server.

## Identificatori

Ogni entità persistente possiede un identificativo interno.

Event possiede inoltre uno slug obbligatorio. Lo slug utilizza `a-z`, `0-9`,
`-` e `_` ed è univoco all'interno della Organization.

Giochi e copie possono avere identificativi esterni opzionali secondo le regole
del relativo dominio.

Per le copie, la V1 della #4 definisce un solo `copy_identifier` operativo
attivo per copia. Il valore:

- identifica una sola scatola nello stesso Event;
- è univoco nello stesso Event;
- può essere riutilizzato in Event differenti;
- conserva il case e viene confrontato esattamente dopo trim esterno;
- possiede `source = external | ludox`.

QR code e barcode non costituiscono tipi persistenti distinti: sono
rappresentazioni fisiche del valore del `copy_identifier`.

Lo storico dei prestiti si collega alla copia tramite `copy_id`, non tramite il
testo dell'identificatore.

## Evoluzione futura

Lo schema v3 implementa Organization, Event, Event Modules e il modulo
`game_library` event-specific.

Le future evoluzioni strutturali devono usare versioni successive dello schema,
per esempio per:

- completamento della modalità `copy_identifier` con la #4;
- eventuali ulteriori vincoli sugli identificativi delle copie;
- modulo `activities`;
- altri moduli event-specific.

Non devono essere riservati numeri di versione in anticipo: ogni migration
viene introdotta quando esiste una modifica strutturale concreta e testabile.

La issue #26 potrà aggiungere una sorgente camera/webcam per decodificare QR e
barcode, ma dovrà produrre lo stesso valore testuale usato dagli scanner HID
e riutilizzare i service della #4.

## Scope della configurazione

La persistenza delle impostazioni deve rispettare gli scope definiti in
[CONFIGURATION.md](CONFIGURATION.md).

In particolare, `max_slots` appartiene al modulo `game_library` dell'Event e
non alla configurazione locale della postazione.

`identification_mode` appartiene anch'essa al modulo `game_library` dello
specifico Event e assume i valori alternativi `token` o `copy_identifier`.
Gli identificatori delle copie sono dati della ludoteca, non configurazione
della postazione.
