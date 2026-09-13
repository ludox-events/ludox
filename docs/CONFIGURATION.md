# Configurazione di LudoX

> **STATUS: APPROVED SPECIFICATION — READ ONLY**
>
> **IMPLEMENTATION: PARTIALLY IMPLEMENTED**
>
> Questo documento è una specifica approvata di LudoX. Durante
> l'implementazione non deve essere modificato, salvo richiesta esplicita
> dell'utente. I marker `TBD` e `QUESTION` restano decisioni aperte e non
> autorizzano Codex a scegliere autonomamente una soluzione.

## Scopo

Questo documento definisce a quale livello appartengono le diverse
impostazioni di LudoX.

La regola generale è:

```text
POSTAZIONE / CLIENT
    ↓ seleziona
ORGANIZATION
    ↓ contiene
EVENT
    ↓ abilita e configura
MODULE
```

Ogni impostazione viene salvata nel livello più vicino al dato o al
comportamento che controlla.

## Principio di semplicità

La configurazione deve rimanere leggibile e comprensibile. Evitare UUID, hash,
registry o mapping indiretti quando identificativi e valori semplici sono
sufficienti.

## Configurazione della postazione

La configurazione locale comprende almeno:

- lingua dell'interfaccia;
- database/workspace selezionato;
- Organization attiva;
- Event attivo;
- eventuali preferenze locali della UI.

Esempio:

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

`config.ini` non deve contenere configurazioni operative dei moduli.

## Organization attiva

La selezione dell'Organization è locale alla postazione e viene gestita dal
Backoffice Organization.

Il riferimento configurato deve essere rivalidato quando cambia workspace.

## Event attivo

La selezione dell'Event è locale alla postazione ed è un'azione operativa della
Home.

Il riferimento configurato è valido soltanto se l'Event:

- esiste;
- appartiene all'Organization corrente;
- è selezionabile;
- corrisponde a ID e slug memorizzati.

## Configurazione della Organization

I dati descrittivi dell'Organization appartengono all'Organization, per
esempio:

- nome;
- nome breve;
- stato;
- descrizione;
- logo;
- contatti;
- indirizzo;
- note.

Non appartengono a `config.ini`.

## Configurazione dell'Event

L'Event contiene almeno:

- Organization proprietaria;
- nome;
- slug;
- inizio/fine;
- timezone;
- stato;
- moduli abilitati;
- eventuali metadati descrittivi.

Le impostazioni specifiche dei moduli restano nei rispettivi moduli.

## Configurazione del modulo `game_library`

Le impostazioni del modulo Prestiti Ludoteca appartengono allo specifico
Event.

Comprendono almeno:

```text
max_slots
identification_mode
```

Esempio:

```text
Event: AMIGO 2027
Module: game_library

max_slots = 100
identification_mode = token
```

### `max_slots`

`max_slots` è il numero massimo di posizioni fisiche disponibili per custodire
i documenti.

Il valore predefinito per un nuovo modulo è `50`.

Non appartiene alla configurazione globale della postazione e sostituisce il
vecchio concetto globale `max_tokens`.

### `identification_mode`

Valori ammessi:

```text
token
copy_identifier
```

Le due modalità sono **alternative per lo specifico Event**.

#### `token`

Il token fisico identifica la sessione:

```text
token N = slot N
```

La specifica scatola prestata può rimanere sconosciuta.

#### `copy_identifier`

La copia fisica viene identificata attraverso il suo codice operativo. Lo slot
continua a identificare il documento, ma non viene consegnato un token fisico.

Il codice può essere rappresentato fisicamente come QR o barcode; questa
differenza non modifica la configurazione e non introduce modalità distinte.

La configurazione resta quindi:

```text
identification_mode = copy_identifier
```

non:

```text
qr
barcode
```

Il cambio tra `token` e `copy_identifier` è consentito soltanto quando
nell'Event non esistono sessioni o prestiti aperti.

Gli identificatori delle copie sono dati della ludoteca, non impostazioni. Possono
essere preparati anche mentre l'Event usa la modalità `token`.

## Modulo `activities`

Le future impostazioni del modulo Activities appartengono allo specifico Event
e saranno definite insieme al modulo.

## Tabella di scoping

| Impostazione / dato | Scope |
|---|---|
| Lingua UI | Postazione/client |
| Database/workspace | Postazione/client |
| Organization attiva | Postazione/client |
| Event attivo | Postazione/client |
| Nome Organization | Organization |
| Nome/slug/timezone Event | Event |
| Moduli abilitati | Event |
| `max_slots` | `game_library` dell'Event |
| `identification_mode` | `game_library` dell'Event |
| `copy_identifier` di una scatola | copia della ludoteca dell'Event |

## Backoffice

Le responsabilità UI restano separate:

```text
Backoffice → Impostazioni postazione
├── lingua
└── database/workspace

Backoffice → Organization
└── gestione/selezione Organization

Backoffice → Event
└── dati Event e moduli abilitati

Home
└── selezione Event corrente

Backoffice/modulo → Prestiti Ludoteca
├── max_slots
├── identification_mode
├── ludoteca
└── identificatori delle copie
```

La pagina generale delle impostazioni non deve duplicare configurazioni proprie
di Event o moduli.

## Primo avvio

Il setup iniziale della postazione chiede soltanto:

- lingua;
- database/workspace.

Non deve chiedere numero di token/slot o modalità operativa del modulo.

## Compatibilità con `max_tokens`

`max_tokens` è una chiave storica.

- non viene più scritta;
- non viene più mostrata;
- un vecchio `config.ini` che la contiene rimane leggibile;
- il valore viene ignorato e non viene migrato automaticamente a `max_slots`.

## Validazione e salvataggio

Ogni modifica deve essere validata prima del salvataggio.

In caso di errore:

- una configurazione valida precedente non deve essere sovrascritta con dati
  parziali;
- il workspace precedente deve rimanere utilizzabile;
- i riferimenti Organization/Event devono restare coerenti con il workspace
  effettivamente aperto.
