# Prestiti Ludoteca / Game Library

> **STATUS: APPROVED SPECIFICATION — READ ONLY**
>
> **IMPLEMENTATION: PARTIALLY IMPLEMENTED**
>
> Questo documento è una specifica approvata di LudoX. Durante
> l'implementazione non deve essere modificato, salvo richiesta esplicita
> dell'utente. I marker `TBD` e `QUESTION` restano decisioni aperte e non
> autorizzano Codex a scegliere autonomamente una soluzione.

Questo documento descrive il modello concettuale del modulo con identificatore tecnico `game_library`.

Nell'interfaccia italiana il modulo è denominato **Prestiti Ludoteca**. Nell'interfaccia inglese il termine di riferimento è **Game Library**.

La procedura pratica della modalità token attualmente disponibile è descritta in [OPERATION.md](OPERATION.md).

## Ambito

Il modulo `game_library` appartiene a un singolo Event e gestisce:

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

Può inoltre essere associato al gioco un **livello di difficoltà opzionale**. La presenza della difficoltà non deve dipendere obbligatoriamente da BGG o da una singola sorgente: il valore potrà essere inserito o calcolato a partire da fonti diverse. Una futura integrazione potrà utilizzare dati BGG quando disponibili.

Le copie non vengono però memorizzate soltanto come un numero aggregato: nello schema v1 ogni scatola fisica deve poter essere rappresentata da un record distinto.

All'interno dello stesso Event, titoli identici dopo una normalizzazione minima vengono considerati lo stesso gioco. La normalizzazione minima comprende almeno rimozione degli spazi iniziali/finali e confronto case-insensitive.

Esempi equivalenti:

```text
Kingdomino
KINGDOMINO
 kingdomino 
```

Nomi soltanto simili, come `Kingdomino` e `King Domino`, non vengono mai uniti automaticamente.

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

Ogni gioco e ogni copia possiedono sempre un identificativo interno LudoX, indipendente dai codici visibili all'utente.

Un gioco può avere un identificativo esterno opzionale associato a una fonte esterna.

Una singola copia fisica può avere **più identificativi opzionali contemporaneamente**. Gli identificativi della copia devono quindi essere modellati separatamente dalla copia stessa.

I tipi inizialmente previsti sono almeno:

- `LUDOX_QR` — QR code generato da LudoX;
- `EXTERNAL_BARCODE` — barcode già presente sulla scatola o proveniente da un sistema esterno.

Esempio:

```text
copia #102
├── LUDOX_QR        LX-C-000102
└── EXTERNAL_BARCODE 8001234567890
```

Gli identificativi devono poter essere assegnati o modificati successivamente dal Backoffice. È quindi possibile iniziare con copie prive di codici e identificarle individualmente in seguito.

LudoX dovrà poter generare QR code per le copie e produrre etichette stampabili da applicare fisicamente alle scatole.

- TBD: Definire formato e vincoli dei valori `LUDOX_QR` e `EXTERNAL_BARCODE`, incluse le relative regole di unicità.

- TBD: Definire i formati fisici supportati per la stampa delle etichette QR, ad esempio fogli di etichette A4, stampanti termiche o dimensioni personalizzabili.

## Proprietari / etichette operative

Il proprietario di una copia è una semplice **etichetta operativa event-specific**.

Non costituisce un'anagrafica e non deve essere collegato obbligatoriamente a:

- persone fisiche;
- Organization;
- soggetti giuridici.

Il suo scopo è permettere di sapere a chi o a quale gruppo devono tornare le copie al termine dell'evento.

Esempio: l'etichetta `Biblioteca` può rappresentare più biblioteche reali se tutte le relative scatole vengono gestite insieme.

## Formato di interoperabilità della ludoteca

La composizione della ludoteca deve poter essere esportata e reimportata senza dipendere dagli identificativi interni del database.

Il formato canonico minimo è un CSV UTF-8 con le colonne tecniche stabili:

```text
game_name,owner_label,quantity
Azul,Biblioteca,3
Azul,LAM,2
Azul,Matteo,1
```

Una riga rappresenta una combinazione gioco + owner label con quantità maggiore di zero.

Il formato canonico non contiene:

- ID interni SQLite;
- prestiti;
- token;
- documenti/sessioni;
- timestamp operativi;
- storico dei prestiti.

I valori CSV devono usare il normale quoting quando contengono virgole, virgolette o altri caratteri che lo richiedono.

CSV è il formato di interoperabilità di riferimento. XLSX è un formato di comodità e deve rappresentare le stesse colonne logiche.

Campi ulteriori potranno essere aggiunti in futuro come colonne opzionali, senza rendere incompatibile il formato minimo a tre colonne.

## Export legacy prima del modello event-specific

Prima della conversione del modulo Prestiti al modello event-specific deve essere disponibile un export read-only della ludoteca legacy corrente.

L'export legge le tabelle legacy `giochi`, `proprietari` e `copie_gioco` e produce il formato CSV canonico descritto sopra.

Questa operazione:

- non modifica il database;
- non esegue migration;
- non esporta lo storico dei prestiti;
- serve a preservare in modo semplice la composizione della ludoteca da reimportare successivamente in un nuovo Event.

La prima fase della issue #2 implementa questo export prima delle issue #5 e #6.

## Importazione della ludoteca

Dopo l'introduzione del modello event-specific, l'importazione legge dati esterni e li aggiunge alla ludoteca dell'Event corrente.

Il formato canonico deve poter rappresentare almeno:

```text
Gioco | Proprietario | Quantità
Azul  | Biblioteca   | 3
Azul  | LAM          | 2
Azul  | Matteo       | 1
```

Internamente, `Quantità = 3` genera tre record di copia distinti.

Deve essere possibile anche importare un elenco omogeneo e assegnare durante l'importazione un'unica etichetta proprietario all'intero gruppo di copie.

La ludoteca può essere completamente svuotata soltanto se nell'Event non è mai stato registrato alcun prestito. Dopo la creazione dello storico dei prestiti non deve essere disponibile un reset distruttivo della ludoteca.

Durante l'importazione:

- un titolo identico dopo normalizzazione minima viene associato al gioco già presente e le copie vengono aggregate;
- un titolo soltanto simile a uno esistente può essere segnalato come possibile corrispondenza;
- la corrispondenza suggerita deve essere confermata dall'utente;
- non viene mai eseguita una fusione fuzzy automatica.

Esempio: se il file contiene `King Domino` e nella ludoteca esiste `Kingdomino`, LudoX può segnalare la somiglianza e chiedere se usare il titolo esistente oppure crearne uno nuovo.

La segnalazione dei nomi simili è una funzionalità del flusso di importazione e non è richiesta durante il normale inserimento manuale dei giochi.

- TBD: Definire la UX della preview di importazione, la gestione dei conflitti e il criterio utilizzato per proporre nomi potenzialmente simili.

## Esportazione della ludoteca event-specific

L'esportazione del nuovo modello produce lo stesso formato logico usato dall'importazione.

Le copie fisiche vengono aggregate per gioco + owner label e il risultato contiene almeno:

- `game_name`;
- `owner_label`;
- `quantity`.

Non contiene lo storico dei prestiti. Lo storico rimane legato all'Event originale.

L'obiettivo è consentire un vero round-trip:

```text
Event A
→ export ludoteca
→ file CSV/XLSX
→ import in Event B
```

Gli Event restano dataset indipendenti dopo l'importazione.

## Transizione dai dati Prestiti legacy

La transizione al modello event-specific non richiede una conversione semantica automatica dei dati Prestiti esistenti verso un Event.

Quando viene introdotto il nuovo schema `game_library`:

- le tabelle e i dati legacy vengono preservati;
- non viene creato automaticamente un Event generico o `Legacy Event`;
- i dati legacy non vengono assegnati automaticamente a un Event;
- ogni nuovo `game_library` event-specific parte vuoto;
- i nuovi servizi operativi usano soltanto il nuovo modello event-specific.

La composizione della ludoteca da conservare viene trasferita tramite:

```text
ludoteca legacy
→ export CSV
→ nuovo game_library event-specific
→ import CSV
```

Lo storico dei prestiti legacy non viene convertito automaticamente. Rimane recuperabile nel database/backup precedente se serve come archivio.

Questa scelta evita di introdurre un sistema di conversione complesso destinato principalmente alla transizione iniziale del progetto.

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

L'assegnazione automatica utilizza il **primo slot libero partendo dal numero più basso**. Non esiste un requisito database che richieda un'assegnazione casuale.

Il valore predefinito iniziale di `max_slots` per un nuovo modulo `game_library` è `50`; può essere modificato successivamente nella configurazione del modulo.

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

Lo schema v1 deve prevedere fin dall'inizio la configurazione della modalità operativa del modulo e la possibilità di associare identificativi alle copie. La prima modalità effettivamente operativa resta quella basata su token; la modalità QR/barcode può essere implementata successivamente senza richiedere una riprogettazione del modello dati.

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

Il modulo Prestiti Ludoteca non può essere disabilitato finché esistono sessioni o prestiti aperti.

La disabilitazione, quando consentita, non cancella lo storico.

- TBD: Definire in futuro un'eventuale procedura amministrativa esplicita per la chiusura forzata di situazioni rimaste aperte.

## Statistiche e report

Statistiche e report del modulo Prestiti Ludoteca sono sempre riferiti all'Event corrente.

Non vengono aggregate automaticamente informazioni provenienti da eventi differenti.

La logica attuale secondo cui i prestiti sono attribuiti al titolo e non automaticamente a uno specifico proprietario deve essere mantenuta quando la copia fisica non è identificata.
