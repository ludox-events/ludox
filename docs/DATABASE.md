# Database LudoX

> **STATUS: APPROVED SPECIFICATION — READ ONLY**
>
> **IMPLEMENTATION: PARTIALLY IMPLEMENTED**
>
> Questo documento è una specifica approvata di LudoX. Durante
> l'implementazione non deve essere modificato, salvo richiesta esplicita
> dell'utente. I marker `TBD` e `QUESTION` restano decisioni aperte e non
> autorizzano Codex a scegliere autonomamente una soluzione.

Questo documento raccoglie i principi che devono guidare lo schema dati. Le tabelle e i vincoli definitivi verranno formalizzati nel passaggio successivo.

## Motore locale

L'implementazione locale utilizza SQLite.

Ogni connessione deve abilitare l'integrità referenziale:

```sql
PRAGMA foreign_keys = ON;
```

Il modello logico non deve però dipendere da caratteristiche che rendano inutilmente difficile una futura implementazione server con un database differente.

## Workspace

Un file SQLite rappresenta un workspace/database LudoX.

Un singolo database può contenere:

- più Organization;
- più Event per ciascuna Organization;
- i dati event-specific dei moduli abilitati.

LudoX deve continuare a permettere la creazione e l'apertura di database differenti.

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

I dati del modulo `game_library` appartengono all'Event e non a un catalogo globale dell'Organization.

## Tabelle candidate

I seguenti nomi sono **provvisori** e servono soltanto come traccia per la progettazione dello schema target:

```text
organizations
events
event_modules

game_library_games
game_library_owner_labels
game_library_game_copies
game_library_copy_identifiers
game_library_sessions
game_library_loans
game_library_settings
```

- TBD: Definire lo schema SQL effettivo delle successive versioni, i nomi definitivi delle tabelle e le foreign key.

- TBD: Decidere in quali tabelle event-specific mantenere un `event_id` diretto anche quando l'appartenenza all'Event potrebbe essere ricavata tramite altre relazioni. La priorità è evitare query ambigue e preservare l'integrità dei dati senza duplicazioni inutili.

## Copie fisiche

Lo schema target del modulo `game_library` deve rappresentare le copie fisiche come record individuali.

La quantità mostrata all'utente è quindi derivabile dal numero di copie che appartengono a un titolo e soddisfano le condizioni di disponibilità.

Ogni copia può avere zero, uno o più identificativi opzionali in una relazione separata dalla copia. I tipi inizialmente previsti sono almeno `LUDOX_QR` ed `EXTERNAL_BARCODE`.

La modalità token non è obbligata a identificare la scatola specifica durante un prestito.

## Sessioni e prestiti

Una sessione anonima mantiene lo slot fisico del documento.

Una sessione può avere più prestiti sequenziali ma un solo prestito aperto alla volta.

Il prestito deve poter identificare:

- il gioco;
- opzionalmente la copia fisica specifica.

Questo permette di supportare sia la modalità token sia la futura modalità QR/barcode.

## Integrità e cancellazione

Lo schema deve impedire operazioni distruttive che rendano incoerente lo storico.

Sono già stabiliti i seguenti principi:

- Organization non viene cancellata dal normale flusso: viene disattivata;
- un Event può essere eliminato finché non contiene transazioni storiche; dati preparatori e configurazioni possono essere eliminati in cascata insieme all'Event;
- nel modulo `game_library`, sessioni e prestiti registrati costituiscono storico operativo;
- un gioco o una copia con storico di prestiti non viene eliminato, ma può essere disattivato;
- la ludoteca non può essere azzerata dopo che è stato registrato almeno un prestito;
- il modulo `game_library` non può essere disabilitato con sessioni/prestiti aperti.

- TBD: Tradurre questi principi in regole precise di `FOREIGN KEY`, `ON DELETE`, controlli applicativi e transazioni.

## Versione dello schema

LudoX utilizza `PRAGMA user_version` per registrare la versione dello schema SQLite.

Le versioni identificano stati precisi e riproducibili dello schema:

```text
user_version = 0   schema legacy / sperimentale
user_version = 1   Organizations
user_version = 2   Events + Event Modules
user_version = 3+  successive modifiche strutturali
```

La versione `0` identifica lo schema precedente all'introduzione della nuova
architettura versionata.

La migration `0 → 1` introduce `Organizations`.

La migration `1 → 2` introduce `Events` e `Event Modules`.

Le strutture dei moduli, compreso `game_library`, vengono introdotte o
evolute attraverso successive versioni quando le relative feature vengono
implementate. Il numero esatto delle versioni successive non viene riservato
in anticipo.

Ogni numero di versione identifica uno schema completo e determinato: una
versione non deve essere costruita progressivamente da più modifiche
strutturali indipendenti senza incremento di `user_version`.

Ogni modifica strutturale da `v0` in avanti deve prevedere una migration
esplicita. Le versioni dello schema usano numeri interi progressivi,
indipendenti dalla versione applicativa di LudoX.

### Compatibilità richiesta all'avvio

LudoX può operare soltanto su un database con lo schema richiesto dalla
versione corrente dell'applicazione.

All'apertura del database l'applicazione deve quindi ispezionare lo schema
**prima** di inizializzare i servizi operativi.

Il comportamento dipende dallo stato rilevato:

- database nuovo o realmente vuoto → inizializzazione diretta allo schema corrente;
- schema già corrente → avvio normale;
- schema precedente su database esistente → migration necessaria;
- schema futuro/non supportato → errore e chiusura dell'applicazione.

Un database esistente con schema precedente **non deve essere migrato
silenziosamente**.

Prima della migration LudoX deve:

1. informare l'utente della versione attuale e di quella richiesta;
2. chiedere autorizzazione esplicita;
3. creare automaticamente una copia completa di backup;
4. eseguire le migration necessarie soltanto dopo il completamento del backup.

Se l'utente rifiuta la migration, LudoX termina l'avvio senza modificare il
database.

Se il backup fallisce, nessuna migration viene eseguita e LudoX termina
l'avvio.

Se la migration fallisce, l'operazione viene annullata tramite rollback, il
backup viene conservato e LudoX termina l'avvio.

L'applicazione non deve proseguire utilizzando uno schema precedente,
parzialmente aggiornato o più recente di quello supportato.

### Backup delle migration

Il backup è obbligatorio prima di **qualsiasi** migration di un database
esistente, anche se la modifica è semplice o puramente additiva.

Per una sequenza composta da più migration pendenti viene creato un unico
backup prima dell'intera sequenza.

Il backup deve essere automatico, leggibile e non deve sovrascrivere file
esistenti. Per impostazione predefinita viene salvato accanto al database
originale con un nome che renda riconoscibili versione di partenza,
versione di destinazione e momento della creazione.

Esempio:

```text
ludox.backup-v0-to-v1-20260912-175900.db
```

### Esecuzione e rollback

Le migration vengono applicate in ordine crescente e senza saltare versioni.
La sequenza viene eseguita in transazione.

`PRAGMA user_version` viene aggiornato insieme alle modifiche dello schema e
non deve rimanere avanzato se la migration fallisce.

Se manca una migration intermedia, l'aggiornamento deve fallire prima di
modificare il database.

Il meccanismo tecnico di detection, sequenza, transazione e rollback è stato
introdotto con la issue #12. Il flusso di autorizzazione e backup obbligatorio
è tracciato nella issue #19.

Il comportamento completo e le regole per aggiungere future migration sono
definiti in [MIGRATIONS.md](MIGRATIONS.md).

## Service layer

La UI non deve eseguire direttamente query SQL per implementare i casi d'uso del dominio.

La direzione è:

```text
UI
 ↓
Services / domain operations
 ↓
Database access
```

Questo permette di mantenere la logica funzionale stabile anche se in futuro SQLite locale viene affiancato o sostituito da un servizio LAN/web.

- TBD: Definire la suddivisione minima dei service senza introdurre complessità non necessaria.

## Timestamp e timezone

Ogni Event possiede una timezone esplicita basata su identificatori IANA, per esempio `Europe/Rome`.

I timestamp delle transazioni vengono memorizzati in UTC in formato ISO 8601. La conversione nella timezone dell'Event avviene per visualizzazione, input e report.

Esempio:

```text
DB:       2026-09-11T15:42:18Z
Event TZ: Europe/Rome
UI:       11/09/2026 17:42:18
```

Questa convenzione evita ambiguità tra client, server e cambi tra ora solare e ora legale.

## Identificatori

Ogni entità persistente possiede un identificativo interno.

Event possiede inoltre uno slug obbligatorio. Lo slug utilizza `a-z`, `0-9`, `-` e `_` ed è univoco all'interno della Organization.

Giochi e copie possono avere identificativi esterni opzionali. Gli identificativi delle copie vengono mantenuti in una relazione separata, così una stessa copia può avere più codici contemporaneamente.

- TBD: Definire le regole di unicità degli identificativi esterni dei giochi e dei codici `LUDOX_QR` / `EXTERNAL_BARCODE`.

## Schema logico target

> **Stato:** design approvato a livello concettuale. Questa sezione descrive il modello dati target e **non implica che tutte le strutture siano già implementate nella stessa versione dello schema**. L'implementazione avviene progressivamente attraverso migration versionate.

Il database LudoX rappresenta un workspace che può contenere più Organization e più Event. Ogni Event appartiene a una sola Organization e abilita i moduli necessari.

Schema logico di riferimento:

```text
DATABASE LUDOX
│
├── organizations
│    └── events
│         ├── event_modules
│         │
│         ├── [game_library]
│         │    ├── game_library_settings
│         │    ├── game_library_owner_labels
│         │    ├── game_library_games
│         │    │    └── game_library_game_copies
│         │    │         └── game_library_copy_identifiers
│         │    └── game_library_sessions
│         │         └── game_library_loans
│         │
│         └── [activities]
│              └── schema da definire
│
└── PRAGMA user_version
```

### organizations

Contenitore logico principale.

Campi concettuali:

- `id`;
- `name`;
- `active`;
- `short_name` opzionale;
- `description` opzionale;
- riferimenti di contatto opzionali;
- `logo_ref` opzionale;
- `notes` opzionale.

Una Organization viene normalmente disattivata invece di essere eliminata.

### events

Ogni Event appartiene a una sola Organization.

Campi concettuali:

- `id`;
- `organization_id`;
- `name`;
- `slug`;
- data/ora di inizio;
- data/ora di fine;
- `timezone`;
- `status`;
- dati descrittivi e di localizzazione opzionali.

Lo slug usa `a-z`, `0-9`, `-` e `_` ed è univoco all'interno della Organization.

Un Event può essere eliminato definitivamente soltanto finché non contiene transazioni storiche. Dati preparatori come configurazioni, giochi, copie o moduli possono essere eliminati insieme all'Event se non esiste ancora storico operativo.

### event_modules

Registra quali moduli sono abilitati per un Event.

Identificatori tecnici iniziali:

- `game_library` — Prestiti Ludoteca / Game Library;
- `activities` — Attività / Activities.

La disabilitazione di un modulo non cancella i dati già presenti.

### game_library_settings

Configurazione event-specific del modulo `game_library`.

Comprende almeno:

- `event_id`;
- numero massimo di slot;
- modalità di identificazione operativa.

Modalità iniziali previste:

- `token`;
- `copy_identifier`.

La modalità `copy_identifier` potrà usare QR LudoX o barcode esterni.

### game_library_owner_labels

Etichette operative dei proprietari delle copie.

Esempi:

```text
LAM
Biblioteca
Matteo
Editore X
```

Non rappresentano anagrafiche di persone o soggetti giuridici.

Ogni owner label appartiene a un singolo Event.

### game_library_games

Rappresenta il titolo del gioco, non la singola scatola.

Comprende almeno:

- identificativo interno;
- `event_id`;
- nome;
- chiave normalizzata del nome;
- stato attivo/non attivo;
- identificativo esterno opzionale;
- livello di difficoltà opzionale;
- sorgente della difficoltà opzionale;
- note opzionali.

All'interno dello stesso Event, titoli identici dopo una normalizzazione minima vengono trattati come lo stesso gioco.

La normalizzazione minima comprende almeno:

- rimozione degli spazi iniziali/finali;
- confronto case-insensitive.

Nomi soltanto simili non vengono mai fusi automaticamente. Nel flusso di importazione LudoX potrà segnalare una possibile corrispondenza, lasciando la decisione all'utente.

### game_library_game_copies

Una riga logica rappresenta una scatola fisica.

Ogni copia appartiene a:

- un Event;
- un gioco;
- una owner label.

La quantità totale di un titolo non viene memorizzata come unico valore aggregato: viene ricavata contando le copie fisiche.

Ogni copia può essere attiva o disattivata.

### game_library_copy_identifiers

Una copia può avere zero, uno o più identificativi opzionali.

Tipi iniziali:

- `LUDOX_QR`;
- `EXTERNAL_BARCODE`.

Una stessa copia può quindi avere contemporaneamente un QR generato da LudoX e un barcode proveniente da un sistema esterno.

LudoX dovrà poter generare QR code per le copie e produrre etichette stampabili.

- TBD: Definire i formati fisici supportati per la stampa delle etichette QR.

### game_library_sessions

Rappresenta una sessione anonima di prestito.

Non vengono memorizzati dati identificativi della persona.

La sessione contiene almeno:

- `event_id`;
- numero di slot;
- timestamp di apertura;
- timestamp di chiusura opzionale.

Lo slot corrisponde alla posizione fisica del documento.

In modalità token:

```text
token N = slot N
```

Uno slot può avere al massimo una sessione aperta alla volta.

### game_library_loans

Rappresenta un singolo prestito all'interno di una sessione.

Contiene almeno:

- `event_id`;
- riferimento alla sessione;
- riferimento al gioco;
- riferimento opzionale alla copia fisica;
- timestamp di uscita;
- timestamp di rientro opzionale.

In modalità token il gioco è noto, ma la copia fisica può non esserlo.

In modalità QR/barcode la copia specifica può essere registrata.

Una sessione può avere una sequenza di prestiti, ma al massimo un prestito aperto alla volta.

### Regole di cancellazione

Principio generale:

```text
dato preparatorio senza storico
→ eliminabile

dato entrato nello storico operativo
→ non eliminabile; disattivabile quando applicabile
```

Nel modulo `game_library`, sessioni e prestiti costituiscono storico operativo.

Un gioco già prestato non può essere eliminato definitivamente.

Per prudenza, se un titolo è stato prestato in modalità token e quindi non è nota la scatola fisica utilizzata, le sue copie non devono essere considerate sicuramente estranee allo storico.

- TBD: Confermare la regola definitiva di cancellazione delle singole copie dopo prestiti effettuati in modalità token.

### Isolamento per Event

Il modello target prevede `event_id` anche nelle principali tabelle operative event-scoped, inclusi i record figli dove ciò aiuta a impedire collegamenti accidentali tra dati appartenenti a Event differenti.

Questa scelta introduce una ridondanza controllata, ma semplifica:

- query event-scoped;
- import/export;
- validazioni;
- futura architettura client/server;
- protezione da riferimenti incrociati tra Event.

- TBD: Confermare durante l'implementazione in quali tabelle figlie `event_id` debba essere materializzato direttamente e in quali possa essere derivato senza perdere i controlli di coerenza.

### Implementazione separata

La struttura sopra è una specifica di progetto. Prima dell'implementazione delle relative parti devono essere definiti in dettaglio:

- chiavi primarie e foreign key;
- vincoli `UNIQUE`;
- comportamento `ON DELETE`;
- indici;
- migration necessarie dalla versione precedente;
- test di integrità;
- strategia di backup.

## Scope della configurazione

La persistenza delle impostazioni deve rispettare gli scope definiti in [CONFIGURATION.md](CONFIGURATION.md). In particolare, `max_slots` appartiene al modulo `game_library` dell'Event e non alla configurazione locale della postazione.