# Database LudoX

> **STATUS: APPROVED SPECIFICATION — READ ONLY**
>
> **IMPLEMENTATION: NOT IMPLEMENTED**
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

I seguenti nomi sono **provvisori** e servono soltanto come traccia per la progettazione dello schema v1:

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

- TBD: Definire lo schema SQL v1 effettivo, i nomi definitivi delle tabelle e le foreign key.

- TBD: Decidere in quali tabelle event-specific mantenere un `event_id` diretto anche quando l'appartenenza all'Event potrebbe essere ricavata tramite altre relazioni. La priorità è evitare query ambigue e preservare l'integrità dei dati senza duplicazioni inutili.

## Copie fisiche

Lo schema v1 deve rappresentare le copie fisiche come record individuali.

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

La nuova architettura Organization → Event → Module costituisce la prima struttura che LudoX intende mantenere nel tempo.

Lo schema utilizzerà `PRAGMA user_version` per registrare la propria versione.

Esempio concettuale:

```text
user_version = 1   schema iniziale Organization/Event/Modules
user_version = 2   modifica futura
user_version = 3   modifica successiva
```

All'apertura del database, l'applicazione può confrontare la versione presente con quella richiesta dal software ed eseguire in sequenza le migrazioni necessarie.

Non è richiesta compatibilità automatica con i database sperimentali precedenti allo schema v1.

A partire dallo schema v1, ogni modifica strutturale deve prevedere una migrazione esplicita.

Le versioni dello schema usano numeri interi progressivi (`1`, `2`, `3`, ...), indipendenti dalla versione applicativa di LudoX.

Le migration vengono applicate in ordine crescente. Prima di una migration non banale, distruttiva o non reversibile deve essere creato un backup del database.

- TBD: Definire il meccanismo concreto di registrazione/esecuzione delle migration e il formato/posizione dei backup.

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



## Schema logico target v1

> **Stato:** design approvato a livello concettuale. Questa sezione descrive il modello dati target e **non implica che lo schema sia già implementato nel codice corrente**. L'implementazione verrà affrontata separatamente, quando sarà deciso di intervenire sul database.

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

La struttura sopra è una specifica di progetto. Prima dell'implementazione devono essere definiti in dettaglio:

- chiavi primarie e foreign key;
- vincoli `UNIQUE`;
- comportamento `ON DELETE`;
- indici;
- migration dallo schema sperimentale corrente;
- test di integrità;
- strategia di backup.

Lo schema SQL non viene definito in questa fase.

## Scope della configurazione

La persistenza delle impostazioni deve rispettare gli scope definiti in [CONFIGURATION.md](CONFIGURATION.md). In particolare, `max_slots` appartiene al modulo `game_library` dell'Event e non alla configurazione locale della postazione.
