# Architettura di LudoX

**Stato:** draft consolidato.

Questo documento descrive i principi architetturali generali di LudoX. I dettagli dei singoli domini sono documentati nei file dedicati.

## Obiettivo

LudoX è un sistema modulare per la gestione di eventi ludici. Il modulo Prestiti è il primo modulo operativo, ma l'architettura non deve assumere che LudoX sia esclusivamente un software di prestito giochi.

La gerarchia concettuale di base è:

```text
Database / workspace LudoX
│
├── Organization A
│   ├── Event 1
│   │   ├── Prestiti Ludoteca / Game Library
│   │   └── Attività / Activities
│   └── Event 2
│       └── Prestiti Ludoteca / Game Library
│
└── Organization B
    └── Event 3
        └── ...
```

Un database può contenere più organizzazioni e più eventi. LudoX deve continuare a poter creare e aprire database differenti quando serve una separazione fisica completa dei workspace.

## Principi

### Event-oriented

L'Evento è il contenitore operativo principale. I moduli e i loro dati appartengono all'evento.

Non esiste un catalogo giochi globale obbligatorio dell'Organization. La ludoteca utilizzata dal modulo `game_library` appartiene al singolo evento.

### Organization come contenitore logico

Una Organization raggruppa eventi. Non rappresenta necessariamente un soggetto giuridico o fiscalmente rilevante.

Ogni evento appartiene esattamente a una Organization.

Vedi [ORGANIZATIONS.md](ORGANIZATIONS.md).

### Moduli

LudoX mette a disposizione funzionalità modulari che vengono abilitate per ciascun evento.

I moduli attualmente confermati nel modello sono:

- **Prestiti Ludoteca** nell'interfaccia italiana, identificatore tecnico `game_library` e termine inglese **Game Library**;
- **Attività**, identificatore tecnico `activities` e termine inglese **Activities**.

Le configurazioni operative di un modulo appartengono all'evento nel quale il modulo è abilitato.

Vedi [MODULES.md](MODULES.md).

## Contesto della postazione/client

Organization ed Event correnti sono un **contesto del singolo client**, non uno stato globale del database.

Un client lavora con una Organization e un Event alla volta. Client differenti potranno, in futuro, lavorare contemporaneamente sullo stesso server selezionando organizzazioni o eventi differenti.

Esempio:

```text
                    ┌─ Client A → Organization LAM → AMIGO
LudoX Server / DB ──┼─ Client B → Organization LAM → Primavera in Gioco
                    └─ Client C → Organization ABC → Evento ABC
```

La configurazione locale può ricordare l'ultima Organization e l'ultimo Event selezionati, ma questi valori non definiscono l'appartenenza dei dati.

## Database locale e futura architettura di rete

La prima implementazione è offline-first e utilizza SQLite localmente.

L'architettura deve però evitare che la logica funzionale dipenda direttamente da SQLite o dalla UI Tkinter.

La direzione prevista è:

```text
UI
 ↓
Domain / service layer
 ↓
Persistence
 ↓
SQLite
```

Una futura configurazione LAN potrà diventare:

```text
Client 1 ─┐
Client 2 ─┼── API / servizio LudoX ── Database
Client 3 ─┘
```

I client non dovranno condividere direttamente un file SQLite attraverso una cartella di rete.

Una futura interfaccia web potrà riutilizzare lo stesso livello di servizio e lo stesso modello logico.

- TBD: Definire l'architettura concreta del server LAN e il protocollo tra client e server quando verrà affrontata la funzionalità multi-postazione.

## Separazione tra configurazione locale e dati applicativi

Il file `config.ini` contiene solo impostazioni relative alla singola installazione/postazione, per esempio:

- lingua dell'interfaccia;
- database/workspace da aprire;
- ultima Organization selezionata;
- ultimo Event selezionato.

Le impostazioni operative come il numero di slot del modulo Prestiti appartengono invece al modulo dell'evento e vengono memorizzate nel database.

## Privacy

Il modulo Prestiti Ludoteca / Game Library mantiene il principio di privacy by design: la sessione di prestito è anonima e il software non necessita di dati identificativi della persona per gestire il documento custodito fisicamente.

Eventuali futuri moduli che trattano partecipanti o prenotazioni costituiscono un dominio distinto e non devono trasformare automaticamente una sessione di prestito anonima in un record identificato.

## Evoluzione dello schema

La nuova struttura Organization → Event → Module costituirà la base dello **schema v1**.

Non viene garantita la migrazione automatica dai database sperimentali precedenti allo schema v1.

A partire dallo schema v1, l'evoluzione del database deve essere versionata e gestita tramite migrazioni.

Vedi [DATABASE.md](DATABASE.md).
