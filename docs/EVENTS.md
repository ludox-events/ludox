# Event

**Stato:** draft consolidato.

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
- stato.

Lo slug è obbligatorio ed è pensato come identificatore leggibile e stabile utile anche per future esportazioni, integrazioni o distribuzione esterna.

- TBD: Definire il formato ammesso dello slug e se la sua unicità deve essere garantita per Organization o sull'intero database.

## Dati opzionali

Possono essere aggiunti senza renderli necessari per creare l'evento:

- descrizione;
- luogo;
- indirizzo;
- URL pubblico;
- immagine/logo dell'evento;
- note interne;
- altri metadati che emergeranno da casi d'uso reali.

## Durata

Un evento può durare più giorni. Inizio e fine comprendono quindi sia la data sia l'orario.

## Stati

Gli stati previsti sono:

- `draft` — evento in preparazione;
- `active` — evento operativo;
- `archived` — evento concluso e conservato come storico;
- `cancelled` — evento annullato.

Possono esistere più eventi `active` contemporaneamente all'interno della stessa Organization.

- QUESTION: Stabilire se lo stato debba essere modificato esclusivamente manualmente oppure se LudoX possa proporre cambi di stato in base alle date dell'evento.

## Event corrente sul client

Ogni client lavora con un solo Event alla volta.

- se per l'Organization corrente esiste un solo Event operativo selezionabile, può essere selezionato automaticamente;
- se ne esistono più di uno, il client seleziona l'evento su cui lavorare;
- la selezione può essere ricordata localmente;
- client differenti possono lavorare contemporaneamente su Event differenti.

Cambiare Event sulla postazione è consentito anche se nell'evento precedente esistono sessioni di prestito ancora aperte. I dati appartengono all'Event, non al client.

- TBD: Definire il punto dell'interfaccia in cui avviene il cambio Event: Home, schermata iniziale o altro selettore operativo.

## Moduli

Un Event non contiene copie autonome del software dei moduli: **abilita le funzionalità/moduli offerte da LudoX**.

Un modulo può essere:

- abilitato alla creazione dell'evento;
- abilitato successivamente;
- disabilitato successivamente quando le regole del modulo lo consentono.

La disabilitazione non deve cancellare automaticamente i dati del modulo.

Vedi [MODULES.md](MODULES.md).

## Cancellazione

Un Event può essere eliminato soltanto quando è vuoto e non esiste storico operativo da preservare.

Un Event non vuoto deve essere conservato e può essere archiviato o annullato.

- TBD: Formalizzare tecnicamente la condizione di "evento vuoto", inclusi moduli abilitati ma senza dati, configurazioni create e record ausiliari.

## Importazione e riuso dei dati

Non è previsto il clone completo di un Event.

Quando serve riutilizzare dati di un evento precedente, l'operazione avviene a livello del singolo modulo, per esempio:

- importare una ludoteca nel modulo Prestiti;
- importare un elenco di attività nel modulo Attività.

L'importazione opera sempre sull'Event correntemente selezionato.
