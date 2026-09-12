# Event

> **STATUS: APPROVED SPECIFICATION — READ ONLY**
>
> **IMPLEMENTATION: NOT IMPLEMENTED**
>
> Questo documento è una specifica approvata di LudoX. Durante
> l'implementazione non deve essere modificato, salvo richiesta esplicita
> dell'utente. I marker `TBD` e `QUESTION` restano decisioni aperte e non
> autorizzano Codex a scegliere autonomamente una soluzione.

## Definizione

Un `Event` è il contenitore operativo principale di LudoX. Rappresenta un evento ludico per il quale vengono abilitate una o più funzionalità/moduli.

Ogni Event appartiene esattamente a una Organization.

## Dati obbligatori

Un Event contiene almeno:

- identificativo interno;
- Organization di appartenenza;
- nome;
- slug/codice pubblico;
- data e ora di inizio;
- data e ora di fine;
- timezone dell'evento;
- stato.

Lo slug è obbligatorio ed è pensato come identificatore leggibile e stabile utile anche per future esportazioni, integrazioni o distribuzione esterna.

Lo slug:

- usa lettere ASCII minuscole `a-z`, numeri `0-9`, trattino `-` e underscore `_`;
- è univoco all'interno della Organization;
- può quindi essere riutilizzato da Organization differenti;
- viene definito al momento della creazione e non viene modificato successivamente.

La UI può proporre automaticamente uno slug derivato dal nome, lasciandolo modificabile prima del primo salvataggio.

Esempio:

```text
amigo-2027
primavera-in-gioco-2027
```

Se in futuro un sistema esterno richiede un codice con regole differenti, tale valore deve essere mantenuto in un campo opzionale separato e non deve modificare le regole dello slug.

## Dati opzionali

Possono essere aggiunti senza renderli necessari per creare l'evento:

- descrizione;
- luogo;
- indirizzo;
- URL pubblico;
- immagine/logo dell'evento;
- note interne;
- altri metadati che emergeranno da casi d'uso reali.

I campi opzionali non sono necessari per la prima implementazione di Event.

## Durata e timezone

Un evento può durare più giorni. Inizio e fine comprendono quindi sia la data sia l'orario.

La data/ora di fine deve essere successiva alla data/ora di inizio.

La timezone è obbligatoria e deve essere rappresentata con un identificatore timezone valido. Quando il sistema non riesce a ricavare una timezone locale riconoscibile, `UTC` è il fallback semplice previsto per la creazione dell'Event.

## Stati

Gli stati previsti sono:

- `draft` — evento in preparazione;
- `active` — evento operativo;
- `archived` — evento concluso e conservato come storico;
- `cancelled` — evento annullato.

Un nuovo Event nasce in stato `draft`.

Possono esistere più eventi `active` contemporaneamente all'interno della stessa Organization.

Lo stato viene modificato esclusivamente in modo manuale. Le date dell'evento non cambiano automaticamente lo stato e, nella prima implementazione, LudoX non propone transizioni automatiche basate sulle date.

Non è prevista una state machine rigida: lo stato può essere corretto manualmente quando necessario.

## Event corrente sul client

Ogni client lavora con un solo Event corrente alla volta.

Sono considerati operativamente selezionabili:

- `draft`;
- `active`.

Gli Event `archived` e `cancelled` rimangono disponibili nel Backoffice per consultazione e gestione, ma non vengono selezionati automaticamente come contesto operativo della Home.

La selezione dell'Event corrente avviene dalla **Home**. L'Event è un contesto operativo che può essere cambiato durante il normale utilizzo dell'applicazione.

La Organization corrente rimane invece un contesto amministrativo selezionabile dal Backoffice.

La selezione corrente viene ricordata nel `config.ini` locale tramite un riferimento semplice e leggibile:

```ini
[event]
active_event_id = 7
active_event_slug = amigo-2027
```

L'ID è l'identificativo tecnico dell'Event. Lo slug è il riferimento leggibile e stabile usato anche come controllo di coerenza.

Una selezione locale è valida soltanto se:

- l'Event esiste;
- appartiene alla Organization corrente;
- è in stato `draft` oppure `active`;
- ID e slug corrispondono.

La logica di selezione per la Organization corrente è:

```text
0 Event selezionabili
→ nessun Event corrente

1 Event selezionabile
→ selezione automatica e aggiornamento della configurazione locale

2+ Event selezionabili
→ usa la selezione locale se ID e slug sono coerenti
→ altrimenti richiede la selezione dalla Home
```

Il cambio di Organization rivalida sempre il riferimento all'Event corrente. Un Event appartenente a un'altra Organization non deve essere selezionato silenziosamente.

Cambiare Event sulla postazione è consentito anche se nell'evento precedente esistono sessioni di prestito ancora aperte. I dati appartengono all'Event, non al client.

Client differenti possono lavorare contemporaneamente su Event differenti.

## Gestione dalla Home

La Home deve mostrare chiaramente almeno:

- Organization corrente;
- Event corrente;
- possibilità di cambiare Event quando esistono più Event selezionabili;
- indicazione comprensibile quando non esiste alcun Event selezionabile.

Il cambio Event non richiede accesso al Backoffice.

## Gestione dal Backoffice

Il Backoffice gestisce gli Event della Organization corrente.

Deve permettere almeno:

- elenco Event;
- creazione;
- modifica dei campi modificabili;
- cambio manuale dello stato;
- visualizzazione della Organization proprietaria;
- visualizzazione dello slug stabile;
- abilitazione/disabilitazione dei moduli;
- eliminazione quando consentita.

L'Organization proprietaria e lo slug non vengono modificati dopo la creazione.

## Moduli

Un Event non contiene copie autonome del software dei moduli: **abilita le funzionalità/moduli offerte da LudoX**.

I moduli inizialmente riconosciuti sono:

- `game_library` — Prestiti Ludoteca / Game Library;
- `activities` — Attività / Activities.

Un Event può essere creato anche senza moduli abilitati.

Un modulo può essere:

- abilitato alla creazione dell'Event;
- abilitato successivamente;
- disabilitato successivamente quando le regole del modulo lo consentono.

La coppia Event/modulo è unica.

La disabilitazione non deve cancellare automaticamente configurazione o dati del modulo. La riabilitazione rende nuovamente disponibile lo stesso contesto.

La issue #5 introduce soltanto il concetto comune di abilitazione dei moduli. La struttura dati operativa del modulo `game_library` viene resa event-specific dalla #6; il modulo `activities` viene implementato dalla #7.

Vedi [MODULES.md](MODULES.md).

## Cancellazione

Un Event può essere eliminato definitivamente finché non contiene transazioni storiche da preservare.

La presenza di configurazioni, moduli abilitati, giochi, copie o altri dati preparatori non impedisce di per sé la cancellazione: se non esistono transazioni storiche, i dati preparatori collegati possono essere rimossi insieme all'Event.

Quando esiste almeno una transazione storica, l'Event non deve più essere eliminato e può soltanto essere conservato, archiviato o annullato.

Per `game_library`, sessioni e prestiti registrati costituiscono storico operativo.

Ogni nuovo modulo deve definire esplicitamente quali propri record costituiscono storico operativo che rende l'Event non eliminabile.

## Importazione e riuso dei dati

Non è previsto il clone completo di un Event.

Quando serve riutilizzare dati di un evento precedente, l'operazione avviene a livello del singolo modulo, per esempio:

- importare una ludoteca nel modulo Prestiti;
- importare un elenco di attività nel modulo Attività.

L'importazione opera sempre sull'Event correntemente selezionato.

## Confini della prima implementazione

La prima implementazione di Event comprende il modello, il contesto client, la gestione da Backoffice/Home e l'abilitazione dei moduli.

Non comprende:

- conversione dell'attuale modulo Prestiti in struttura event-specific;
- import/export della ludoteca;
- funzionalità Activities;
- QR/barcode operativi;
- automatismi di stato basati sulle date;
- clonazione completa di Event.
