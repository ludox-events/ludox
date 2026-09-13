# Prestiti Ludoteca / Game Library

> **STATUS: APPROVED SPECIFICATION — READ ONLY**
>
> **IMPLEMENTATION: IMPLEMENTED — GAME LIBRARY V1**
>
> Questo documento è una specifica approvata di LudoX. Durante
> l'implementazione non deve essere modificato, salvo richiesta esplicita
> dell'utente. I marker `TBD` e `QUESTION` restano decisioni aperte e non
> autorizzano Codex a scegliere autonomamente una soluzione.

Questo documento descrive il modello funzionale del modulo con identificatore
tecnico `game_library`.

Nell'interfaccia italiana il modulo è denominato **Prestiti Ludoteca**.
Nell'interfaccia inglese il termine di riferimento è **Game Library**.

La procedura pratica delle modalità `token` e `copy_identifier` è descritta in
[OPERATION.md](OPERATION.md). Gli scenari di verifica manuale sono raccolti in
[MANUAL_TESTS.md](MANUAL_TESTS.md).

## Stato di implementazione

La Game Library V1 è implementata e comprende:

- ludoteca event-specific;
- owner label event-specific;
- copie fisiche individuali;
- configurazione `max_slots` per Event;
- modalità operative alternative `token` e `copy_identifier`;
- identificatori delle copie event-specific con origine `external` / `ludox`;
- gestione Backoffice delle singole copie;
- scanner HID / input manuale + Invio;
- generazione di identificatori LudoX e QR PNG;
- sessioni anonime e prestiti event-specific;
- nuovo prestito, cambio gioco e restituzione finale in entrambe le modalità;
- statistiche, storico e report event-specific;
- import/export CSV e XLSX, incluso il round-trip degli identificatori;
- cambio sicuro della modalità operativa senza sessioni/prestiti aperti.

La scansione tramite webcam/camera non fa parte della Game Library V1 ed è
tracciata separatamente nella issue #26.

## Ambito

Il modulo `game_library` appartiene a un singolo Event e gestisce:

- ludoteca dell'evento;
- giochi;
- copie fisiche;
- identificatori delle copie;
- owner label;
- sessioni anonime;
- slot fisici dei documenti;
- prestiti e cambi gioco;
- configurazione del modulo;
- statistiche e report dell'evento.

Non esiste un catalogo giochi globale obbligatorio dell'Organization.

## Ludoteca dell'Event

Quando il modulo Prestiti viene abilitato, la sua ludoteca nasce vuota.

La ludoteca può essere popolata:

- manualmente;
- tramite importazione di file CSV/XLSX;
- tramite importazione di dati precedentemente esportati da un altro Event.

Non viene clonato automaticamente un Event e non esiste una sincronizzazione
permanente tra ludoteche di Event differenti.

## Giochi

Un gioco rappresenta un titolo presente nella ludoteca di quell'Event.

Dati funzionali principali:

- nome;
- stato attivo/disattivo;
- copie disponibili;
- owner label associate alle copie;
- identificativo esterno opzionale;
- difficoltà e relativa sorgente opzionali;
- note opzionali.

Le copie non vengono memorizzate soltanto come quantità aggregata: ogni scatola
fisica è rappresentata da un record distinto.

All'interno dello stesso Event, titoli identici dopo una normalizzazione minima
vengono considerati lo stesso gioco.

La normalizzazione minima comprende:

- rimozione degli spazi iniziali/finali;
- confronto case-insensitive.

Esempi equivalenti:

```text
Kingdomino
KINGDOMINO
 kingdomino 
```

Nomi soltanto simili, come `Kingdomino` e `King Domino`, sono considerati
distinti.

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

L'interfaccia può mostrare le copie in forma aggregata:

```text
Kingdomino — 5 copie
LAM          2
Biblioteca   2
Matteo       1
```

Una copia può essere attiva o disattivata.

La quantità disponibile di un titolo viene ricavata dalle copie fisiche
utilizzabili e dai prestiti aperti.

Le copie appartengono esclusivamente alla ludoteca dello specifico Event.
Non esiste un'identità globale della scatola condivisa automaticamente tra
Event. Se una ludoteca viene esportata e reimportata in un altro Event, le
copie del nuovo Event sono nuovi record event-specific; gli eventuali
`copy_identifier` possono però essere conservati dal file di interoperabilità.

## Owner label

Il proprietario operativo di una copia è una semplice **owner label
event-specific**.

Non costituisce un'anagrafica e non deve essere collegato obbligatoriamente a:

- persone fisiche;
- Organization;
- soggetti giuridici.

Il suo scopo è sapere a chi o a quale gruppo devono tornare le copie al termine
dell'evento.

Esempio: l'etichetta `Biblioteca` può rappresentare più biblioteche reali se
tutte le relative scatole vengono gestite insieme.

## Identificatore operativo della copia

Un `copy_identifier` è un codice che identifica **una sola scatola fisica
all'interno dello stesso Event**.

QR code e barcode non sono concetti differenti per il dominio LudoX: sono
soltanto rappresentazioni fisiche diverse di una stringa identificativa.
LudoX lavora sul valore decodificato.

Esempi validi:

```text
BIB-000123
4711085941237
LX-C-000123
```

L'unicità fisica del codice esterno è responsabilità di chi prepara la
ludoteca. Un EAN di prodotto uguale su più scatole non è un valido
`copy_identifier`; un barcode inventariale di biblioteca che identifica una
singola copia lo è.

### Un solo identificatore operativo per copia

Nella V1 ogni copia può avere **al massimo un identificatore operativo
attivo**.

L'identificatore può essere:

- `external` — codice già applicato alla scatola e dichiarato univoco da chi
  prepara la ludoteca;
- `ludox` — codice generato da LudoX quando la scatola non possiede un codice
  utilizzabile.

La distinzione riguarda l'origine del valore, non la simbologia QR/barcode.

Un identificatore può essere sostituito dal Backoffice. La sostituzione cambia
il codice operativo della copia; i prestiti storici restano collegati alla
copia tramite il suo ID interno e non dipendono dal vecchio valore.

Non è consentito rimuovere o sostituire l'identificatore di una copia mentre
quella copia è coinvolta in un prestito aperto.

### Regole del valore

Il valore viene normalizzato soltanto rimuovendo spazi e terminatori alle
estremità. Il contenuto interno e il case vengono preservati.

Il valore:

- deve essere non vuoto;
- non deve contenere ritorni a capo interni;
- deve essere univoco nello stesso Event;
- può essere riutilizzato in Event differenti;
- viene confrontato esattamente dopo il trim esterno.

### Codici generati da LudoX

Quando viene richiesto un nuovo identificatore LudoX, il formato V1 è:

```text
LX-C-<copy_id a almeno 6 cifre>
```

Esempio:

```text
LX-C-000123
```

Il valore usa l'ID interno della copia già creata. Poiché l'ID della copia è
univoco nel database, il codice generato è deterministico e non richiede UUID,
hash o registri aggiuntivi.

LudoX può rappresentare il valore generato come QR code e permette
l'esportazione di una semplice immagine PNG contenente QR e valore leggibile,
così da poter stampare e applicare il codice alla scatola.

Layout avanzati per fogli di etichette, stampanti termiche o altri formati di
stampa non fanno parte della Game Library V1.

## Formato di interoperabilità della ludoteca

La composizione della ludoteca può essere esportata e reimportata senza
dipendere dagli identificativi interni del database.

CSV UTF-8 resta il formato canonico. XLSX rappresenta gli stessi campi logici
come formato di comodità.

### Formato minimo legacy/aggregato

Il formato minimo a tre colonne resta valido:

```text
game_name,owner_label,quantity
Azul,Biblioteca,3
Azul,LAM,2
Azul,Matteo,1
```

Una riga senza identificatore può rappresentare una combinazione gioco + owner
label con una o più copie aggregate.

Il formato di interoperabilità non contiene:

- ID interni SQLite;
- prestiti;
- token;
- sessioni/documenti;
- timestamp operativi;
- storico dei prestiti.

I valori CSV usano il normale quoting quando contengono virgole, virgolette o
altri caratteri che lo richiedono.

### Formato esteso con copie identificate

Il formato esteso aggiunge colonne opzionali:

```text
game_name,owner_label,quantity,copy_identifier,identifier_source
Azul,Biblioteca,1,BIB-000123,external
Azul,Biblioteca,1,BIB-000124,external
Azul,LAM,1,LX-C-000451,ludox
Cascadia,LAM,3,,
```

Regole:

- se `copy_identifier` è vuoto, `quantity` può essere maggiore di `1`;
- se `copy_identifier` è presente, `quantity` deve essere esattamente `1`;
- `identifier_source` può essere `external` oppure `ludox`;
- se un identificatore è presente e `identifier_source` è vuoto durante un
  import esterno, il valore viene interpretato come `external`;
- `identifier_source` senza `copy_identifier` non è valido;
- l'export scrive sempre `identifier_source` per le copie identificate;
- le copie identificate vengono esportate una per riga;
- le copie senza identificatore possono essere aggregate per gioco + owner
  label;
- un identificatore duplicato nello stesso file o già presente nell'Event di
  destinazione è un conflitto e blocca l'import;
- lo stesso valore presente in un altro Event non è un conflitto;
- l'import non deve associare automaticamente lo stesso identificatore a due
  copie.

Il round-trip export → import deve conservare `copy_identifier` e
`identifier_source` quando presenti. I record di copia degli Event di origine e
destinazione restano indipendenti.

## Export legacy

LudoX mantiene un export read-only della ludoteca legacy per consentire di
preservare la composizione dei vecchi database.

L'export legge le tabelle legacy `giochi`, `proprietari` e `copie_gioco` e
produce il formato CSV canonico.

Questa operazione:

- non modifica il database;
- non esegue migration;
- non esporta lo storico dei prestiti;
- permette di trasferire la composizione della ludoteca nel nuovo modello
  event-specific.

## Importazione della ludoteca

L'importazione lavora sul solo Event corrente.

`quantity = N` genera N copie fisiche distinte.

È possibile anche importare un elenco senza owner label nel file e assegnare
un'unica owner label all'intero import.

L'import è additivo: importazioni successive aggiungono copie e nuovi titoli
senza azzerare automaticamente la ludoteca esistente.

### Copie identificate

Le righe con `copy_identifier` rappresentano sempre una singola scatola e
richiedono `quantity = 1`.

Prima della scrittura devono essere verificati almeno:

- validità di `identifier_source`;
- unicità dell'identificatore nello stesso file;
- assenza dello stesso identificatore nell'Event corrente;
- coerenza tra identificatore e quantità.

Lo stesso valore presente soltanto in un altro Event non costituisce conflitto.

### Corrispondenza dei titoli

Il comportamento approvato è intenzionalmente semplice e deterministico:

- un titolo identico dopo trim + confronto case-insensitive viene associato al
  gioco già presente;
- un titolo soltanto simile viene trattato come un gioco distinto;
- non viene eseguito fuzzy matching;
- non vengono proposte fusioni automatiche basate sulla somiglianza del nome.

Esempio:

```text
KINGDOMINO       → stesso gioco di Kingdomino
 kingdomino      → stesso gioco di Kingdomino
King Domino      → gioco distinto
```

Se in futuro verrà introdotta una funzione di suggerimento per nomi simili,
dovrà essere una feature esplicita e non dovrà mai fondere automaticamente i
dati.

### Preview e applicazione

L'import viene preparato tramite una preview/validazione prima della scrittura.

Righe non valide devono impedire una scrittura parziale dell'import. In caso di
errore database l'operazione deve mantenere la coerenza dei dati tramite
transazione/rollback.

## Esportazione della ludoteca event-specific

L'esportazione del nuovo modello produce lo stesso formato logico usato
dall'importazione.

Le copie prive di identificatore possono essere aggregate per gioco + owner
label. Le copie identificate vengono invece esportate singolarmente per
preservare l'identità della scatola.

Il risultato contiene almeno:

- `game_name`;
- `owner_label`;
- `quantity`;
- `copy_identifier` opzionale;
- `identifier_source` opzionale.

Lo storico dei prestiti non viene esportato.

L'obiettivo è consentire il round-trip:

```text
Event A
→ export ludoteca
→ CSV/XLSX
→ import in Event B
```

Gli Event restano dataset indipendenti dopo l'importazione.

## Reset della ludoteca

La ludoteca dell'Event può essere completamente svuotata soltanto se non è mai
stato registrato alcun prestito.

Dopo la presenza di storico operativo non deve essere disponibile un reset
distruttivo della ludoteca.

## Transizione dai dati Prestiti legacy

La transizione al modello event-specific non esegue una conversione semantica
automatica dei vecchi prestiti verso un Event.

Durante la migration:

- le tabelle e i dati legacy vengono preservati;
- non viene creato automaticamente un Event generico o `Legacy Event`;
- i dati legacy non vengono assegnati automaticamente a un Event;
- ogni nuovo `game_library` event-specific parte vuoto;
- i nuovi servizi operativi usano soltanto il nuovo modello event-specific.

La composizione della ludoteca da conservare può essere trasferita tramite:

```text
ludoteca legacy
→ export CSV
→ nuovo game_library event-specific
→ import CSV
```

Lo storico dei prestiti legacy non viene convertito automaticamente.

## Sessione anonima e documento

Una sessione rappresenta la permanenza anonima di una persona nel flusso di
prestito.

Durante la sessione:

- viene custodito fisicamente un documento;
- il documento viene collocato in uno slot numerato;
- la sessione rimane anonima nel software;
- possono avvenire più prestiti sequenziali tramite cambio gioco;
- può esistere un solo prestito aperto alla volta.

La sessione termina soltanto dopo la restituzione finale e la riconsegna fisica
del documento.

## Slot

Lo **slot** è la posizione fisica numerata in cui viene custodito il documento.

Gli slot vanno da `1` a `max_slots` dello specifico modulo `game_library`.

Lo slot rimane invariato per tutta la sessione e riparte da `1` in ogni Event.

L'assegnazione automatica usa il primo slot libero partendo dal numero più
basso.

Il valore predefinito iniziale di `max_slots` è `50` e può essere modificato dal
Backoffice del modulo, rispettando i vincoli imposti dalle sessioni aperte.

## Modalità operative del modulo

Il modulo `game_library` possiede una sola modalità operativa attiva per Event:

```text
identification_mode = token
```

oppure:

```text
identification_mode = copy_identifier
```

Le modalità sono alternative. Non vengono usate contemporaneamente nello
stesso Event.

Il cambio di modalità è consentito soltanto quando nell'Event non esistono
sessioni o prestiti aperti.

Gli identificatori possono comunque essere preparati, importati o modificati
anche mentre l'Event usa la modalità `token`.

## Modalità token

In modalità `token`:

```text
slot 23 ↔ token fisico 23
```

Il token identifica la sessione per chi opera al banco e per la persona. Non
identifica la copia fisica del gioco.

Il sistema conosce il titolo prestato ma, se la copia non viene identificata
individualmente, non attribuisce il singolo prestito a uno specifico
proprietario/owner label.

## Modalità `copy_identifier`

In modalità `copy_identifier` non viene utilizzato il token fisico per
identificare la sessione.

Lo slot continua invece a esistere e identifica la posizione fisica del
documento custodito.

Una copia attiva priva di identificatore può essere mantenuta nel Backoffice
come dato preparatorio, ma **non è prestabile** finché non riceve un
`copy_identifier` valido.

### Input dello scanner

La Game Library V1 usa scanner USB/Bluetooth HID che si comportano come una
tastiera:

```text
scanner
→ scrive il valore
→ ENTER
→ LudoX
```

Lo stesso flusso funziona digitando manualmente il valore e premendo Enter.
Questo costituisce anche il metodo minimo di test senza hardware.

L'uso di webcam/camera per decodificare QR o barcode è fuori scope e viene
tracciato separatamente nella issue #26. La futura camera dovrà produrre lo
stesso valore testuale e riutilizzare i medesimi service.

### Nuovo prestito

Flusso implementato:

```text
scan copy_identifier
→ trova una copia dell'Event corrente
→ verifica copia/gioco attivi e non già in prestito
→ assegna il primo slot libero
→ apre sessione anonima
→ apre prestito con copy_id valorizzato
→ mostra lo slot in cui custodire il documento
```

Non viene consegnato un token fisico.

Un identificatore sconosciuto, appartenente solo a un altro Event, associato a
una copia inattiva o già in prestito produce un errore comprensibile e non
modifica i dati.

### Cambio gioco

Il gioco restituito identifica direttamente la sessione:

```text
scan copia restituita
→ trova il prestito aperto
→ trova la sessione e lo slot
→ scan nuova copia
→ validazione
→ conferma
→ chiude vecchio prestito e apre il nuovo sulla stessa sessione
```

La modifica viene applicata in transazione soltanto dopo che entrambe le copie
sono state identificate e validate. Se il flusso viene annullato prima della
conferma, il database resta invariato.

Lo slot del documento non cambia.

### Restituzione finale

Flusso implementato:

```text
scan copia restituita
→ trova prestito aperto e sessione
→ mostra lo slot del documento
→ operatore recupera e restituisce fisicamente il documento
→ conferma DOCUMENTO RESTITUITO
→ chiude prestito e sessione
→ libera lo slot
```

Prestito e sessione vengono chiusi solo alla conferma finale, così lo slot non
può essere riassegnato prima della restituzione fisica del documento.

## Prestiti e storico

Ogni prestito appartiene a una sessione e a un gioco.

Il riferimento alla copia fisica è opzionale nel modello generale:

```text
prestito
├── sessione
├── gioco
└── copia fisica opzionale
```

In modalità `token` la copia può essere sconosciuta.

In modalità `copy_identifier` ogni nuovo prestito ha `copy_id` valorizzato.

Quando la copia è nota, storico e viste amministrative possono mostrare anche:

- `copy_identifier` corrente;
- owner label della copia;
- riferimento interno della copia.

La modifica successiva dell'identificatore non cambia l'identità storica della
copia associata al prestito.

Una sessione può avere un solo prestito aperto alla volta.

## Cambio Event durante prestiti aperti

Un client può cambiare Event anche se nell'Event precedente esistono sessioni o
prestiti aperti.

Le sessioni appartengono all'Event e possono essere recuperate tornando
successivamente su quell'Event o, in una futura architettura multi-client,
gestite da un altro client.

## Disabilitazione del modulo

Il modulo Prestiti Ludoteca non può essere disabilitato finché esistono
sessioni o prestiti aperti.

La disabilitazione, quando consentita, non cancella lo storico.

- TBD: Definire in futuro un'eventuale procedura amministrativa esplicita per
  la chiusura forzata di situazioni rimaste aperte.

## Statistiche e report

Statistiche e report del modulo Prestiti Ludoteca sono sempre riferiti
all'Event corrente.

Non vengono aggregate automaticamente informazioni provenienti da Event
differenti.

Quando la copia fisica non è identificata, i prestiti restano attribuiti al
titolo e non automaticamente a una specifica owner label.

Quando `copy_id` è noto, storico e viste amministrative mostrano anche il
`copy_identifier` corrente e l'owner label della copia. La sostituzione
successiva del codice non cambia il riferimento storico al `copy_id`.
