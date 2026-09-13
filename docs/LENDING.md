# Prestiti Ludoteca / Game Library

> **STATUS: APPROVED SPECIFICATION — READ ONLY**
>
> **IMPLEMENTATION: PARTIALLY IMPLEMENTED**
>
> Questo documento è una specifica approvata di LudoX. Durante
> l'implementazione non deve essere modificato, salvo richiesta esplicita
> dell'utente. I marker `TBD` e `QUESTION` restano decisioni aperte e non
> autorizzano Codex a scegliere autonomamente una soluzione.

Questo documento descrive il modello funzionale del modulo con identificatore
tecnico `game_library`.

Nell'interfaccia italiana il modulo è denominato **Prestiti Ludoteca**.
Nell'interfaccia inglese il termine di riferimento è **Game Library**.

La procedura pratica della modalità token attualmente disponibile è descritta
in [OPERATION.md](OPERATION.md). Al completamento della issue #4,
`OPERATION.md` deve essere aggiornato per descrivere anche la modalità
`copy_identifier`.

## Stato di implementazione

Sono implementati:

- ludoteca event-specific;
- owner label event-specific;
- copie fisiche individuali;
- configurazione `max_slots` per Event;
- modalità operativa `token`;
- sessioni anonime e prestiti event-specific;
- cambio gioco e restituzione finale;
- statistiche, storico e report event-specific;
- import/export CSV e XLSX;
- struttura dati predisposta per identificatori delle copie.

Non è ancora implementata la modalità operativa `copy_identifier`. Per questo
il documento resta **PARTIALLY IMPLEMENTED**.

## Ambito

Il modulo `game_library` appartiene a un singolo Event e gestisce:

- ludoteca dell'Event;
- giochi;
- copie fisiche;
- owner label;
- identificatori delle copie;
- sessioni anonime;
- slot fisici dei documenti;
- prestiti e cambi gioco;
- configurazione del modulo;
- statistiche e report dell'Event.

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

Un gioco rappresenta un titolo presente nella ludoteca di uno specifico Event.

Dati funzionali principali:

- nome;
- stato attivo/disattivo;
- copie fisiche;
- owner label associate alle copie;
- identificativo esterno opzionale del titolo;
- difficoltà e relativa sorgente opzionali;
- note opzionali.

Le copie non vengono memorizzate soltanto come quantità aggregata: ogni scatola
fisica è rappresentata da un record distinto.

All'interno dello stesso Event, titoli identici dopo una normalizzazione minima
vengono considerati lo stesso gioco. La normalizzazione minima comprende:

- rimozione degli spazi iniziali/finali;
- confronto case-insensitive.

Nomi soltanto simili, come `Kingdomino` e `King Domino`, restano distinti. Non
viene eseguito fuzzy matching automatico.

## Copie fisiche

Ogni scatola fisica è una copia distinta del gioco e appartiene esclusivamente
alla ludoteca di uno specifico Event.

Esempio:

```text
Kingdomino
├── copia 1 — LAM
├── copia 2 — LAM
├── copia 3 — Biblioteca
├── copia 4 — Biblioteca
└── copia 5 — Matteo
```

L'interfaccia può continuare a mostrare quantità aggregate, ma la persistenza
rimane a livello della singola copia.

Una copia può essere attiva o disattivata.

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

LudoX deve poter rappresentare il valore generato come QR code e permettere
l'esportazione di una semplice immagine PNG contenente QR e valore leggibile,
così da poter stampare e applicare il codice alla scatola.

Layout avanzati per fogli di etichette, stampanti termiche o altri formati di
stampa non fanno parte della V1 della issue #4.

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

Il token identifica la sessione. Non identifica la copia fisica.

Il sistema conosce il titolo prestato ma la specifica scatola può rimanere
sconosciuta. In questo caso il prestito non viene attribuito automaticamente a
una specifica owner label.

## Modalità `copy_identifier`

In modalità `copy_identifier` non viene utilizzato il token fisico per
identificare la sessione.

Lo slot continua invece a esistere e identifica la posizione fisica del
documento custodito.

Una copia attiva priva di identificatore può essere mantenuta nel Backoffice
come dato preparatorio, ma **non è prestabile** finché non riceve un
`copy_identifier` valido.

### Input dello scanner

La prima implementazione usa scanner USB/Bluetooth HID che si comportano come
una tastiera:

```text
scanner
→ scrive il valore
→ ENTER
→ LudoX
```

Lo stesso flusso deve funzionare digitando manualmente il valore e premendo
Enter. Questo costituisce anche il metodo minimo di test senza hardware.

L'uso di webcam/camera per decodificare QR o barcode è fuori scope e viene
tracciato separatamente nella issue #26. La futura camera dovrà produrre lo
stesso valore testuale e riutilizzare i medesimi service della #4.

### Nuovo prestito

Flusso approvato:

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

La modifica deve essere applicata in transazione soltanto dopo che entrambe le
copie sono state identificate e validate. Se il flusso viene annullato prima
della conferma, il database resta invariato.

Lo slot del documento non cambia.

### Restituzione finale

Flusso approvato:

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

In modalità `copy_identifier` ogni nuovo prestito deve avere `copy_id`
valorizzato.

Quando la copia è nota, storico e viste amministrative possono mostrare anche:

- `copy_identifier` corrente;
- owner label della copia;
- riferimento interno della copia.

La modifica successiva dell'identificatore non cambia l'identità storica della
copia associata al prestito.

## Formato di interoperabilità della ludoteca

CSV UTF-8 resta il formato canonico. XLSX rappresenta gli stessi campi logici
come formato di comodità.

### Formato minimo legacy/aggregato

Il formato a tre colonne resta valido:

```text
game_name,owner_label,quantity
Azul,Biblioteca,3
Azul,LAM,2
```

Una riga senza identificatore può rappresentare più copie aggregate.

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

Il round-trip export → import deve conservare gli identificatori delle copie.

Esempio:

```text
Event A
  Azul / Biblioteca / BIB-000123
  Azul / Biblioteca / BIB-000124

→ export CSV/XLSX
→ import in Event B

Event B
  Azul / Biblioteca / BIB-000123
  Azul / Biblioteca / BIB-000124
```

I record di copia di Event A e Event B restano indipendenti.

### Importazione

L'import lavora sul solo Event corrente ed è additivo.

Per i titoli:

- trim + confronto case-insensitive identifica un titolo già esistente;
- nomi soltanto simili restano distinti;
- non viene eseguito fuzzy matching.

L'import deve produrre una preview/validazione prima della scrittura. Errori,
identificatori duplicati o righe incoerenti devono impedire scritture parziali.
L'applicazione finale avviene in transazione.

### Esportazione

L'export non contiene prestiti, sessioni, token, timestamp operativi o storico.
Serve a trasferire la composizione della ludoteca e, quando presenti, gli
identificatori delle scatole.

## Reset della ludoteca

La ludoteca dell'Event può essere completamente svuotata soltanto se non è mai
stato registrato alcun prestito.

Dopo la presenza di storico operativo non deve essere disponibile un reset
distruttivo della ludoteca.

## Cambio Event durante prestiti aperti

Un client può cambiare Event anche se nell'Event precedente esistono sessioni o
prestiti aperti. I dati restano associati all'Event di appartenenza.

## Disabilitazione del modulo

Il modulo Prestiti Ludoteca non può essere disabilitato finché esistono
sessioni o prestiti aperti.

La disabilitazione, quando consentita, non cancella lo storico.

- TBD: Definire in futuro un'eventuale procedura amministrativa esplicita per
  la chiusura forzata di situazioni rimaste aperte.

## Statistiche e report

Statistiche e report sono sempre riferiti all'Event corrente.

Quando la copia fisica non è identificata, i prestiti restano attribuiti al
titolo e non automaticamente a una specifica owner label.

Quando `copy_id` è noto, report e storico possono attribuire il movimento alla
specifica copia e alla relativa owner label.
