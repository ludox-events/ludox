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

Ogni impostazione deve essere salvata nel livello più vicino al dato o al
comportamento che controlla.

## Principio di semplicità e leggibilità

La configurazione di LudoX deve rimanere comprensibile e gestibile anche da
una persona non esperta di sistemi.

Quando esistono più soluzioni equivalenti, va preferita quella che mantiene:

- pochi parametri;
- nomi espliciti;
- valori leggibili;
- file di configurazione ispezionabili manualmente;
- comportamento prevedibile e facilmente recuperabile.

Identificativi opachi, UUID, hash, mapping indiretti o strutture aggiuntive
non devono essere introdotti soltanto per anticipare possibili esigenze
future.

Se una configurazione contiene un identificativo tecnico, quando utile deve
essere affiancato da un valore leggibile che aiuti l'utente a comprenderne il
significato e permetta controlli di coerenza.

## 1. Configurazione della postazione / client

Comprende almeno:

- lingua dell'interfaccia;
- database/workspace selezionato;
- Organization attiva;
- Event attivo;
- eventuali preferenze locali dell'interfaccia.

Queste impostazioni possono essere differenti su postazioni diverse che
utilizzano lo stesso database o, in futuro, lo stesso server.

### config.ini

Nell'implementazione locale attuale `config.ini` rappresenta la
configurazione della postazione.

Nel modello target può contenere riferimenti o preferenze come:

- lingua;
- database/workspace selezionato;
- ultimo contesto Organization/Event utilizzato.

Non deve contenere configurazioni operative proprie di un Event o di un
modulo.

Per l'Organization attiva, la configurazione locale memorizza sia
l'identificativo interno sia il nome leggibile, per esempio:

```ini
[organization]
active_organization_id = 2
active_organization_name = Ludoteca Altomilanese
```

L'ID resta l'identificativo tecnico dell'Organization nel database. Il nome
salvato nella configurazione rende il riferimento leggibile e costituisce un
controllo aggiuntivo di coerenza.

All'apertura del database LudoX verifica che:

- l'Organization con l'ID configurato esista;
- sia attiva;
- il suo nome corrisponda al nome memorizzato nella configurazione.

Se ID e nome non corrispondono, la selezione locale non viene usata
silenziosamente.

La selezione memorizzata si riferisce sempre al database/workspace
attualmente configurato. Dopo un cambio di database viene quindi validata
contro il nuovo database; se non corrisponde a una Organization valida, viene
ignorata e viene applicata la normale logica di selezione.

Non è necessario introdurre mapping tra workspace, UUID o altri
identificativi aggiuntivi per questo scopo.

## 2. Configurazione della Organization

La Organization contiene informazioni descrittive e strutturali condivise
dagli Event che le appartengono.

Comprende, per esempio:

- nome;
- nome breve;
- stato attivo/disattivo;
- descrizione;
- logo;
- sito web;
- email;
- telefono;
- indirizzo;
- note.

La Organization non contiene la configurazione operativa della ludoteca
di un singolo Event.

## 3. Configurazione dell'Event

L'Event contiene i dati e le impostazioni che descrivono l'evento nel suo
complesso.

Comprende almeno:

- Organization di appartenenza;
- nome;
- slug;
- data/ora di inizio;
- data/ora di fine;
- timezone;
- stato;
- moduli abilitati;
- dati descrittivi e di localizzazione.

L'Event stabilisce quali moduli sono disponibili, ma le impostazioni
specifiche di un modulo restano nel relativo modulo.

## 4. Configurazione del modulo `game_library`

Le impostazioni proprie del modulo Prestiti Ludoteca / Game Library
appartengono allo specifico Event.

Comprendono almeno:

- numero massimo di slot;
- modalità operativa di identificazione;
- eventuali future opzioni specifiche del modulo.

Esempio:

```text
Event: AMIGO 2027
Module: game_library

max_slots = 100
identification_mode = token
```

### `max_slots`

`max_slots` sostituisce concettualmente il precedente `max_tokens`.

Non è una preferenza della postazione e non deve essere considerato un
parametro generale di `config.ini`.

Il numero massimo di slot appartiene alla configurazione del modulo
`game_library` dello specifico Event.

In modalità token:

```text
token N = slot N
```

ma il concetto persistente è lo slot, cioè la posizione fisica in cui
viene conservato il documento.

## 5. Configurazione del modulo `activities`

Le future impostazioni del modulo Activities appartengono allo specifico
Event e non alla postazione o alla Organization.

La struttura esatta verrà definita insieme al modulo Activities.

## 6. Regola di scoping

Quando viene introdotta una nuova impostazione, deve essere classificata
secondo questa domanda:

> Se cambio postazione, Organization o Event, questa impostazione deve
> necessariamente rimanere la stessa?

La risposta determina il livello corretto.

| Impostazione | Scope |
|---|---|
| Lingua UI | Postazione/client |
| Database/workspace selezionato | Postazione/client |
| Organization attiva | Postazione/client |
| Event attivo | Postazione/client |
| Nome Organization | Organization |
| Logo Organization | Organization |
| Nome Event | Event |
| Slug Event | Event |
| Timezone Event | Event |
| Moduli abilitati | Event |
| Numero massimo slot | `game_library` dell'Event |
| Modalità token / QR-barcode | `game_library` dell'Event |

## 7. Backoffice

Il Backoffice può offrire interfacce per modificare impostazioni appartenenti
a scope differenti, ma la posizione nell'interfaccia non determina dove il
dato viene salvato.

La futura implementazione della gestione configurazione deve rispettare lo
scope definito in questo documento.

## 8. Compatibilità con l'implementazione corrente

L'implementazione attuale può ancora contenere parametri storici in
`config.ini`, incluso `max_tokens`.

Questa situazione è considerata transitoria.

La migrazione verso il modello target deve essere effettuata quando verranno
implementati Event e configurazione event-specific del modulo
`game_library`.

Non è necessario modificare immediatamente il formato corrente soltanto per
allinearlo a questa specifica.
