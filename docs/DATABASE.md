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
della issue #4.

## Motore locale

L'implementazione locale utilizza SQLite.

Ogni connessione deve abilitare l'integrità referenziale:

```sql
PRAGMA foreign_keys = ON;
```

Il modello logico non deve però dipendere da caratteristiche che rendano
inutilmente difficile una futura implementazione server con un database
differente.

## Workspace e gerarchia

Un file SQLite rappresenta un workspace/database LudoX.

Un singolo database può contenere più Organization e più Event. La gerarchia
concettuale è:

```text
Organization
   ↓
Event
   ↓
Module data
```

I dati del modulo `game_library`, comprese le copie fisiche e i loro
identificatori, appartengono all'Event.

Non esiste un'identità globale obbligatoria della scatola condivisa tra Event.

## Versione dello schema

LudoX utilizza `PRAGMA user_version`.

Versioni correnti:

```text
user_version = 0   schema legacy / sperimentale
user_version = 1   Organizations
user_version = 2   Events + Event Modules
user_version = 3   game_library event-specific
```

La issue #4 introduce una modifica strutturale agli identificatori delle copie
e deve quindi implementare una migration esplicita:

```text
v3 → v4
```

La numerazione successiva non viene riservata in anticipo.

## Schema implementato in v3

Lo schema applicativo comprende:

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

Le tabelle legacy precedenti restano preservate come archivio e non vengono
mischiate automaticamente con i nuovi dati event-specific.

### `organizations`

Campi minimi implementati:

- `id`;
- `name`;
- `active`.

### `events`

Campi implementati:

- `id`;
- `organization_id`;
- `name`;
- `slug`;
- `start_datetime`;
- `end_datetime`;
- `timezone`;
- `status`.

Ogni Event appartiene a una sola Organization. Organization e slug sono
immutabili dopo la creazione.

### `event_modules`

Registra i moduli abilitati per Event.

Identificatori riconosciuti:

- `game_library`;
- `activities`.

### `game_library_settings`

Comprende:

- `event_id`;
- `max_slots`, default `50`;
- `identification_mode`.

Valori previsti:

```text
token
copy_identifier
```

La scelta è event-specific. Le due modalità sono alternative.

### `game_library_owner_labels`

Campi principali:

- `id`;
- `event_id`;
- `name`;
- `name_key`;
- `active`.

### `game_library_games`

Campi principali:

- `id`;
- `event_id`;
- `name`;
- `name_key`;
- `active`;
- `external_id` opzionale;
- `difficulty` opzionale;
- `difficulty_source` opzionale;
- `notes` opzionali.

Il nome normalizzato è univoco nello stesso Event.

### `game_library_game_copies`

Una riga rappresenta una scatola fisica appartenente allo specifico Event.

Campi principali:

- `id`;
- `event_id`;
- `game_id`;
- `owner_label_id`;
- `active`.

La stessa scatola eventualmente usata in Event differenti non viene collegata
automaticamente attraverso un record globale: ogni Event possiede le proprie
copie.

### `game_library_copy_identifiers` in v3

La tabella v3 è già predisposta per identificatori multipli e distingue
`LUDOX_QR` / `EXTERNAL_BARCODE`, ma questa semantica viene sostituita dalla
issue #4.

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

## Prestiti e copie

### `game_library_sessions`

Campi principali:

- `id`;
- `event_id`;
- `slot`;
- `opened_at`;
- `closed_at` opzionale.

Uno slot può avere al massimo una sessione aperta alla volta nello stesso
Event.

### `game_library_loans`

Campi principali:

- `id`;
- `event_id`;
- `session_id`;
- `game_id`;
- `copy_id` opzionale;
- `checked_out_at`;
- `returned_at` opzionale.

In modalità `token`, `copy_id` può essere `NULL`.

In modalità `copy_identifier`, ogni nuovo prestito deve avere `copy_id`
valorizzato.

La relazione storica usa `copy_id`, non il testo del `copy_identifier`.
Cambiare successivamente il codice operativo di una copia non cambia i
prestiti storici.

## Isolamento per Event

`event_id` è materializzato nelle principali tabelle operative del modulo
`game_library`, incluse le relazioni figlie dove serve a impedire riferimenti
incrociati accidentali.

Le foreign key composite che includono `event_id` devono continuare a impedire
collegamenti tra dati di Event differenti.

La regola di unicità dei `copy_identifier` è coerente con questo modello:

```text
Event A: BIB-123 → consentito
Event B: BIB-123 → consentito
Event A: seconda copia BIB-123 → vietato
```

## Integrità e cancellazione

Principio generale:

```text
dato preparatorio senza storico
→ eliminabile quando le regole del dominio lo consentono

dato entrato nello storico operativo
→ non eliminabile; disattivabile quando applicabile
```

Sessioni e prestiti costituiscono storico operativo.

Un Event con storico operativo non può essere eliminato.

La ludoteca non può essere azzerata dopo il primo prestito registrato.

Il modulo `game_library` non può essere disabilitato con sessioni o prestiti
aperti.

L'identificatore di una copia non può essere rimosso o sostituito mentre
esiste un prestito aperto per quella copia.

Quando una copia possiede soltanto storico chiuso, il suo identificatore può
essere sostituito: lo storico resta collegato al `copy_id`.

Per i prestiti storici effettuati in modalità `token`, la specifica scatola
fisica può essere ignota. In tali casi le regole esistenti di prudenza sulla
cancellazione delle copie devono essere preservate.

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

Per un database precedente:

1. viene determinata la migration necessaria;
2. viene richiesta autorizzazione esplicita;
3. viene creato il backup obbligatorio;
4. le migration vengono applicate in ordine e in transazione;
5. in caso di errore viene eseguito rollback e l'applicazione non prosegue.

Il comportamento completo è definito in [MIGRATIONS.md](MIGRATIONS.md).

## Service layer

La separazione minima implementata è:

```text
UI
 ↓
Domain / service modules
 ↓
Database access / migrations
```

La UI non deve introdurre query SQL dirette per implementare la issue #4.
Risoluzione degli identificatori, validazioni, prestiti e import/export devono
passare attraverso service testabili senza Tkinter.

## Evoluzione futura

La issue #26 potrà aggiungere una sorgente camera/webcam per decodificare QR e
barcode, ma dovrà produrre lo stesso valore testuale usato dagli scanner HID e
riutilizzare i service definiti dalla #4.

Il networking multi-postazione resta una futura evoluzione separata e non deve
portare alla condivisione diretta del file SQLite.

## Scope della configurazione

`max_slots` e `identification_mode` appartengono al modulo `game_library`
dell'Event e non a `config.ini`.

Le regole complete sono in [CONFIGURATION.md](CONFIGURATION.md).
