# Modulo Prestiti

**Stato:** draft consolidato del modello funzionale v1.

Questo documento descrive il modello concettuale del modulo Prestiti. La procedura pratica della modalità token attualmente disponibile è descritta in [OPERATION.md](OPERATION.md).

## Ambito

Il modulo Prestiti appartiene a un singolo Event e gestisce:

- ludoteca dell'evento;
- giochi;
- copie fisiche;
- etichette proprietario;
- sessioni anonime;
- slot fisici dei documenti;
- prestiti e cambi gioco;
- configurazione del modulo;
- statistiche e report dell'evento.

Non esiste un catalogo giochi globale obbligatorio dell'Organization.

## Ludoteca dell'evento

Quando il modulo Prestiti viene abilitato, la sua ludoteca nasce vuota.

La ludoteca può essere popolata:

- manualmente;
- tramite importazione di file esterni;
- tramite importazione di dati precedentemente esportati da un altro evento.

Non viene clonato automaticamente un Event e non esiste una sincronizzazione permanente tra ludoteche di eventi differenti.

## Giochi

Un gioco rappresenta un titolo presente nella ludoteca di quell'Event.

Dati funzionali minimi:

- nome;
- stato attivo/disattivo;
- copie disponibili;
- proprietari/etichette associati alle copie.

Può essere previsto un identificativo esterno opzionale utile per collegare il titolo a una sorgente esterna.

Le copie non vengono però memorizzate soltanto come un numero aggregato: nello schema v1 ogni scatola fisica deve poter essere rappresentata da un record distinto.

- TBD: Definire la regola definitiva di unicità dei titoli all'interno dello stesso Event e la normalizzazione dei nomi durante inserimento/importazione.

## Copie fisiche

Ogni scatola fisica è una copia distinta del gioco.

Esempio:

```text
Kingdomino
├── copia 1 — LAM
├── copia 2 — LAM
├── copia 3 — Biblioteca
├── copia 4 — Biblioteca
└── copia 5 — Matteo
```

L'interfaccia può continuare a mostrare quantità aggregate:

```text
Kingdomino — 5 copie
LAM          2
Biblioteca   2
Matteo       1
```

Una singola copia può essere disattivata, per esempio perché non disponibile, danneggiata o rimossa dalla ludoteca.

Se tutte le copie utilizzabili di un gioco sono disattivate/non disponibili, il titolo non deve comparire nella normale ricerca dei giochi prestabili.

Un gioco che possiede storico di prestiti non viene eliminato: può essere disattivato preservando lo storico.

## Identificativi

Ogni gioco e ogni copia possiedono sempre un identificativo interno LudoX.

Sono inoltre previsti identificativi opzionali:

- identificativo esterno del gioco, associato a una fonte esterna;
- codice della singola copia, utilizzabile in futuro come QR code o barcode.

Il codice della copia deve poter essere assegnato o modificato successivamente dal Backoffice. È quindi possibile iniziare con copie prive di codice e identificarle individualmente in seguito.

- TBD: Definire formato, vincoli e strategie di generazione/importazione dei codici delle copie.

## Proprietari / etichette operative

Il proprietario di una copia è una semplice **etichetta operativa event-specific**.

Non costituisce un'anagrafica e non deve essere collegato obbligatoriamente a:

- persone fisiche;
- Organization;
- soggetti giuridici.

Il suo scopo è permettere di sapere a chi o a quale gruppo devono tornare le copie al termine dell'evento.

Esempio: l'etichetta `Biblioteca` può rappresentare più biblioteche reali se tutte le relative scatole vengono gestite insieme.

## Importazione della ludoteca

L'importazione legge dati esterni e li aggiunge alla ludoteca dell'Event corrente.

Un formato aggregato deve poter rappresentare almeno:

```text
Gioco | Proprietario | Quantità
Azul  | Biblioteca   | 3
Azul  | LAM          | 2
Azul  | Matteo       | 1
```

Internamente, `Quantità = 3` genera tre record di copia distinti.

Deve essere possibile anche importare un elenco omogeneo e assegnare durante l'importazione un'unica etichetta proprietario all'intero gruppo di copie.

La ludoteca può essere completamente svuotata soltanto se nell'Event non è mai stato registrato alcun prestito. Dopo la creazione dello storico dei prestiti non deve essere disponibile un reset distruttivo della ludoteca.

- TBD: Definire preview, match dei titoli, conflitti e gestione di refusi come `Kingdomino` / `King Domino`. Non deve essere applicata automaticamente una fusione fuzzy che possa unire giochi differenti.

## Esportazione della ludoteca

L'esportazione destinata al riuso della ludoteca contiene i dati necessari a ricostruire la disponibilità, per esempio:

- titolo;
- etichetta proprietario;
- quantità;
- eventuali identificativi esterni/codici quando opportuno.

Non contiene lo storico dei prestiti.

Lo storico rimane legato all'Event originale.

- TBD: Definire il formato canonico di interoperabilità CSV/XLSX e quali campi opzionali devono essere esportati.

## Sessione anonima e documento

Una sessione rappresenta la permanenza anonima di una persona nel flusso di prestito.

Durante la sessione:

- viene custodito fisicamente un documento;
- il documento viene collocato in uno slot numerato;
- la sessione rimane anonima nel software;
- possono avvenire più prestiti sequenziali tramite cambio gioco;
- può esistere un solo prestito aperto alla volta.

La sessione termina soltanto dopo la restituzione finale e la riconsegna fisica del documento.

## Slot

Lo **slot** è la posizione fisica numerata in cui viene custodito il documento.

Gli slot vanno da `1` al numero massimo configurato per il modulo Prestiti dell'Event.

Lo slot rimane invariato per tutta la sessione.

Il numero massimo di slot è una configurazione del modulo Prestiti del singolo Event, non una configurazione globale di LudoX.

Gli slot ripartono da 1 in ogni Event.

- TBD: Confermare definitivamente la politica automatica di assegnazione dello slot libero. La soluzione preferita è il primo slot disponibile a partire dal numero più basso; non esiste un requisito database che imponga un'assegnazione casuale.

## Modalità token

La modalità inizialmente operativa utilizza token fisici numerati.

In questa modalità:

```text
slot 23 ↔ token fisico 23
```

Il token identifica la sessione per l'operatore e per la persona. Non identifica la copia fisica del gioco.

Il sistema conosce il titolo prestato ma, se la copia non viene identificata individualmente, non attribuisce il singolo prestito a uno specifico proprietario.

## Modalità QR code / barcode

Il modello v1 deve essere predisposto per una futura modalità basata sull'identificazione della singola copia.

In questa modalità lo slot continua a identificare la posizione fisica del documento, mentre il QR code/barcode della copia diventa la chiave operativa usata durante prestito e restituzione.

Esempio:

```text
QR KDM-002
   ↓
copia fisica #102
   ↓
prestito aperto
   ↓
sessione anonima
   ↓
slot documento 23
```

Quando il gioco viene cambiato:

```text
KDM-002 rientra
→ sessione e slot 23 restano aperti
→ viene consegnata AZUL-014
→ AZUL-014 è ora associata al prestito aperto della stessa sessione
```

Il QR/barcode non sostituisce quindi lo slot fisico: sostituisce il token fisico come mezzo operativo per risalire alla sessione.

La modalità QR/barcode non è necessariamente implementata nello schema v1, ma lo schema deve evitare di rendere costosa la sua introduzione successiva.

## Prestiti

Ogni prestito appartiene a una sessione e a un gioco.

Il modello deve poter rappresentare opzionalmente anche la specifica copia fisica:

```text
prestito
├── sessione
├── gioco
└── copia fisica opzionale
```

In modalità token la copia specifica può essere sconosciuta.

In modalità QR/barcode la copia specifica è identificata.

Una sessione può avere un solo prestito aperto alla volta.

## Cambio Event durante prestiti aperti

Un client può cambiare Event anche se nell'Event precedente esistono sessioni/prestiti aperti.

Le sessioni appartengono all'Event e possono essere gestite da altri client o recuperate tornando successivamente su quell'Event.

## Disabilitazione del modulo

Il modulo Prestiti non può essere disabilitato finché esistono sessioni o prestiti aperti.

La disabilitazione, quando consentita, non cancella lo storico.

- TBD: Definire in futuro un'eventuale procedura amministrativa esplicita per la chiusura forzata di situazioni rimaste aperte.

## Statistiche e report

Statistiche e report del modulo Prestiti sono sempre riferiti all'Event corrente.

Non vengono aggregate automaticamente informazioni provenienti da eventi differenti.

La logica attuale secondo cui i prestiti sono attribuiti al titolo e non automaticamente a uno specifico proprietario deve essere mantenuta quando la copia fisica non è identificata.
