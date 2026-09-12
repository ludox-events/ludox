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

### `config.ini`

Nell'implementazione locale `config.ini` rappresenta la configurazione della
postazione.

Il formato target rimane semplice e leggibile:

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

Il file non deve contenere configurazioni operative proprie di un Event o di
un modulo.

Non devono essere introdotti mapping tra workspace, UUID, hash o file di
configurazione aggiuntivi soltanto per ricordare i contesti selezionati.

### Organization attiva

Per l'Organization attiva, la configurazione locale memorizza sia
l'identificativo interno sia il nome leggibile:

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

### Event attivo

Per l'Event corrente, la configurazione locale memorizza identificativo
interno e slug leggibile/stabile:

```ini
[event]
active_event_id = 7
active_event_slug = amigo-2027
```

Il riferimento è valido soltanto se l'Event:

- esiste;
- appartiene alla Organization corrente;
- è operativamente selezionabile;
- ha lo slug memorizzato nella configurazione.

Dopo un cambio di Organization o database/workspace il riferimento all'Event
viene rivalidato. Un Event di un'altra Organization o con ID/slug incoerenti
non deve essere selezionato silenziosamente.

La selezione memorizzata si riferisce sempre al database/workspace
attualmente configurato. Non è richiesto mantenere uno storico dei contesti
Organization/Event per ogni workspace.

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

La gestione e la selezione della Organization corrente appartengono alla
schermata Organization del Backoffice, non alla pagina generale delle
impostazioni della postazione.

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
- eventuali dati descrittivi e di localizzazione.

L'Event stabilisce quali moduli sono disponibili, ma le impostazioni
specifiche di un modulo restano nel relativo modulo.

La gestione dei dati dell'Event appartiene al Backoffice Event. La selezione
dell'Event corrente è invece un'azione operativa disponibile dalla Home.

Queste funzioni non devono essere duplicate nella pagina generale delle
impostazioni della postazione.

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

Il valore predefinito iniziale per un nuovo modulo `game_library` è `50`.
Questo valore non viene ricavato automaticamente dal vecchio `max_tokens` globale.

In modalità token:

```text
token N = slot N
```

ma il concetto persistente è lo slot, cioè la posizione fisica in cui
viene conservato il documento.

La gestione di `max_slots` e delle altre impostazioni del modulo appartiene
alle schermate del modulo `game_library`, non alla pagina generale delle
impostazioni della postazione.

## 5. Configurazione del modulo `activities`

Le future impostazioni del modulo Activities appartengono allo specifico
Event e non alla postazione o alla Organization.

La struttura esatta viene definita insieme al modulo Activities.

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

Le responsabilità UI sono separate:

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
└── configurazione game_library (es. max_slots)
```

La pagina generale **Impostazioni postazione** non deve duplicare controlli
per selezionare Organization o Event e non deve contenere configurazioni dei
moduli.

Può mostrare Organization ed Event correnti come informazione contestuale,
ma le modifiche avvengono nelle schermate responsabili indicate sopra.

### Lingua

La lingua viene scelta tramite valore leggibile e salvata nella configurazione
locale. Dopo il salvataggio deve poter essere applicata immediatamente
ricostruendo la schermata dell'interfaccia, senza richiedere modifica manuale
di `config.ini`.

### Database/workspace

La gestione dal Backoffice deve riutilizzare il normale flusso workspace già
previsto da LudoX:

- visualizzazione del database corrente;
- scelta/apertura di un database esistente;
- scelta del percorso di un nuovo database;
- validazione del percorso;
- bootstrap/migration sicura del database;
- rivalidazione dei contesti Organization ed Event;
- ripristino del workspace precedente se l'operazione fallisce o viene
  annullata.

Non deve essere introdotto un secondo meccanismo parallelo di apertura o
creazione dei database.

## 8. Primo avvio della postazione

Il setup iniziale deve chiedere soltanto configurazioni appartenenti alla
postazione:

- lingua;
- database/workspace.

Non deve creare automaticamente Organization o Event generici.

Dopo l'apertura/creazione del database si applicano i normali bootstrap dei
relativi livelli applicativi.

Il setup iniziale non deve chiedere numero di token o slot, perché `max_slots`
appartiene al modulo `game_library` dello specifico Event.

## 9. Compatibilità con `max_tokens`

`max_tokens` è un parametro storico della configurazione locale precedente al
modello event-specific.

Non è richiesta una conversione automatica del suo valore verso `max_slots`.

Dopo l'introduzione del nuovo `game_library` event-specific:

- ogni modulo usa il proprio `max_slots`, con valore iniziale predefinito `50`;
- `AppConfig` non deve più richiedere `max_tokens` come configurazione globale;
- il primo avvio e il Backoffice generale non devono mostrarlo;
- `save_config()` non deve scriverlo;
- un vecchio `config.ini` che contiene ancora la chiave deve rimanere leggibile;
- la chiave storica viene semplicemente ignorata.

La #3 completa la rimozione di `max_tokens` dalla configurazione locale. Non deve eseguire alcuna migrazione dei dati Prestiti legacy.

## 10. Validazione e salvataggio

Prima di salvare una modifica della configurazione locale, tutti i nuovi
valori devono essere validati.

In caso di errore:

- una configurazione valida precedente non deve essere sovrascritta con dati
  parziali;
- il workspace precedente deve rimanere utilizzabile;
- i riferimenti Organization/Event devono rimanere coerenti con il workspace
  effettivamente aperto.

La semplice modifica del testo del percorso non deve creare un database: la
creazione/apertura avviene soltanto attraverso il normale flusso workspace.

I database interni al progetto possono essere mantenuti come percorsi
relativi; i database esterni possono essere memorizzati con percorso assoluto
secondo le regole già esistenti.
