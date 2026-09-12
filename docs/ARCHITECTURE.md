# Architettura di LudoX

> **STATUS: APPROVED SPECIFICATION — READ ONLY**
>
> **IMPLEMENTATION: PARTIALLY IMPLEMENTED**
>
> Questo documento è una specifica approvata di LudoX. Durante
> l'implementazione non deve essere modificato, salvo richiesta esplicita
> dell'utente. I marker `TBD` e `QUESTION` restano decisioni aperte e non
> autorizzano Codex a scegliere autonomamente una soluzione.

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

### Semplicità e leggibilità

La semplicità di installazione e configurazione è un obiettivo architetturale primario di LudoX.

Il sistema deve poter essere configurato e compreso anche da una persona che non abbia competenze da amministratore di sistema o sviluppatore.

Quando più soluzioni soddisfano gli stessi requisiti, deve essere preferita quella:

- più semplice da spiegare;
- più semplice da configurare dall'interfaccia;
- più leggibile nei file di configurazione;
- più facile da diagnosticare e correggere manualmente;
- basata su concetti e identificativi comprensibili.

UUID, hash, mapping opachi, registri aggiuntivi, livelli di indirezione e astrazioni pensate soltanto per possibili esigenze future non devono essere introdotti se una soluzione più semplice soddisfa i requisiti correnti.

La possibilità di evolvere LudoX in futuro non deve rendere inutilmente complessa la configurazione presente.

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

Lo schema viene evoluto per passi espliciti e riproducibili:

```text
v0 = schema legacy / sperimentale
v1 = Organizations
v2 = Events + Event Modules
v3+ = successive modifiche strutturali
```

Ogni versione identifica uno stato preciso dello schema. Una versione non deve essere costruita progressivamente da più implementazioni indipendenti.

Ogni passaggio strutturale deve essere gestito tramite il meccanismo di migrazione definito per LudoX.

Vedi [DATABASE.md](DATABASE.md).

## Scope della configurazione

La distinzione tra configurazione della postazione, Organization, Event e moduli è definita in [CONFIGURATION.md](CONFIGURATION.md).
