# Organization

**Stato:** draft consolidato.

## Definizione

Una `Organization` è il contenitore logico superiore degli eventi gestiti da LudoX.

Non deve necessariamente corrispondere a un'associazione registrata, un'azienda o un altro soggetto giuridico. Può rappresentare qualunque soggetto o gruppo che utilizza LudoX per organizzare i propri eventi.

## Relazioni

Un database LudoX può contenere più Organization.

Ogni Event appartiene a una sola Organization:

```text
Organization
   ├── Event A
   ├── Event B
   └── Event C
```

L'Organization di appartenenza di un Event viene determinata al momento della creazione e non può essere cambiata successivamente.

## Dati

I soli dati concettualmente obbligatori sono:

- identificativo interno;
- nome;
- stato attivo/disattivo.

Sono previsti come informazioni opzionali:

- abbreviazione / nome breve;
- descrizione;
- logo;
- sito web;
- email;
- telefono;
- indirizzo;
- città;
- CAP;
- paese;
- note.

L'assenza dei campi opzionali non deve impedire l'utilizzo dell'Organization.

> TBD: Definire come viene memorizzato e distribuito il logo, evitando una dipendenza da percorsi locali non portabili tra client/server.

## Stato

Una Organization può essere attiva o disattiva.

Una Organization non viene cancellata dal normale flusso applicativo. La disattivazione preserva i suoi eventi e lo storico.

## Organization attiva sul client

Ogni postazione/client lavora nel contesto di una Organization attiva.

- se nel database esiste una sola Organization attiva, viene selezionata automaticamente;
- se ne esistono più di una, viene utilizzata la selezione locale della postazione;
- la selezione può essere modificata dal Backoffice/impostazioni;
- il cambio Organization non deve essere un'azione ordinaria della Home operativa.

La scelta corrente può essere ricordata nel `config.ini` locale della postazione.

In una futura architettura client/server, client differenti potranno selezionare Organization differenti contemporaneamente.

## Creazione degli eventi

Un nuovo Event viene creato automaticamente all'interno dell'Organization attiva sul client. Non è necessario chiedere nuovamente l'Organization durante la creazione.

## Organization e proprietari dei giochi

Organization e proprietari dei giochi sono concetti indipendenti.

Nel modulo Prestiti, un proprietario è una semplice **etichetta operativa event-specific** che indica a chi o a quale gruppo devono essere ricondotte determinate copie.

Esempio:

```text
Organization: Ludoteca Altomilanese

Evento: AMIGO
Kingdomino
├── LAM          2 copie
├── Biblioteca   3 copie
└── Matteo       1 copia
```

L'etichetta `Biblioteca` può rappresentare anche più biblioteche reali se, dal punto di vista operativo, tutte le relative copie devono essere gestite come un unico gruppo di restituzione.

Non è prevista una relazione obbligatoria tra queste etichette e Organization, persone fisiche o soggetti giuridici.
