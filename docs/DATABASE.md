# Database LudoX

**Stato:** draft iniziale — schema v1 da definire.

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
