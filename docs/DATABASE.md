# Database LudoX

> **STATUS: APPROVED SPECIFICATION — READ ONLY**
>
> **IMPLEMENTATION: PARTIALLY IMPLEMENTED**
>
> Questo documento è una specifica approvata di LudoX. Durante
> l'implementazione non deve essere modificato, salvo richiesta esplicita
> dell'utente. I marker `TBD` e `QUESTION` restano decisioni aperte e non
> autorizzano Codex a scegliere autonomamente una soluzione.

Questo documento raccoglie i principi dello schema dati di LudoX e descrive lo
schema implementato fino alla versione `v3`.

Le parti relative a funzionalità future, come identificazione operativa delle
copie tramite QR/barcode e modulo `activities`, restano specifiche di progetto
non ancora completamente implementate.

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

## Versione dello schema

LudoX utilizza `PRAGMA user_version` per registrare la versione dello schema
SQLite.

Le versioni implementate sono:

```text
user_version = 0   schema legacy / sperimentale
user_version = 1   Organizations
user_version = 2   Events + Event Modules
user_version = 3   game_library event-specific
user_version = 4+  successive modifiche strutturali
```

La versione `0` identifica lo schema precedente all'introduzione della nuova
architettura versionata.

La migration `0 → 1` introduce `organizations`.

La migration `1 → 2` introduce `events` e `event_modules`.

La migration `2 → 3` introduce il modello event-specific del modulo
`game_library`.

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

La modalità attualmente operativa è `token`.

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

### `game_library_copy_identifiers`

Una copia può avere zero, uno o più identificativi opzionali.

Campi principali:

- `id`;
- `event_id`;
- `copy_id`;
- `identifier_type`;
- `value`.

Tipi inizialmente riconosciuti:

- `LUDOX_QR`;
- `EXTERNAL_BARCODE`.

Lo schema è predisposto per l'identificazione individuale delle copie, ma la
modalità QR/barcode non è ancora operativa.

- TBD: Definire formato, vincoli e regole di unicità dei valori
  `LUDOX_QR`, `EXTERNAL_BARCODE` e degli eventuali identificativi esterni dei
  giochi.

- TBD: Definire i formati fisici supportati per la stampa delle etichette QR.

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

In modalità QR/barcode la copia specifica potrà essere registrata.

Una sessione può avere una sequenza di prestiti, ma al massimo un prestito
aperto alla volta.

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

- TBD: Confermare la regola definitiva di cancellazione/disattivazione delle
  singole copie dopo prestiti effettuati in modalità token.

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

Giochi e copie possono avere identificativi esterni opzionali. Gli
identificativi delle copie vengono mantenuti in una relazione separata, così
una stessa copia può avere più codici contemporaneamente.

Le regole operative e di unicità dei codici visibili restano da definire con la
feature QR/barcode.

## Evoluzione futura

Lo schema v3 implementa Organization, Event, Event Modules e il modulo
`game_library` event-specific.

Le future evoluzioni strutturali devono usare versioni successive dello schema,
per esempio per:

- funzionalità operative QR/barcode;
- eventuali ulteriori vincoli sugli identificativi delle copie;
- modulo `activities`;
- altri moduli event-specific.

Non devono essere riservati numeri di versione in anticipo: ogni migration
viene introdotta quando esiste una modifica strutturale concreta e testabile.

## Scope della configurazione

La persistenza delle impostazioni deve rispettare gli scope definiti in
[CONFIGURATION.md](CONFIGURATION.md).

In particolare, `max_slots` appartiene al modulo `game_library` dell'Event e
non alla configurazione locale della postazione.
