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
in [OPERATION.md](OPERATION.md).

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

Non è ancora implementata la modalità operativa basata su QR code/barcode delle
singole copie. Per questo il documento resta **PARTIALLY IMPLEMENTED**.

## Ambito

Il modulo `game_library` appartiene a un singolo Event e gestisce:

- ludoteca dell'evento;
- giochi;
- copie fisiche;
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

## Identificatori delle copie

Ogni gioco e ogni copia possiedono sempre un identificativo interno LudoX,
indipendente dai codici visibili all'utente.

Una singola copia fisica può avere più identificativi opzionali
contemporaneamente.

I tipi previsti nello schema corrente sono:

- `LUDOX_QR` — QR code generato da LudoX;
- `EXTERNAL_BARCODE` — barcode già presente sulla scatola o proveniente da un
  sistema esterno.

Esempio concettuale:

```text
copia #102
├── LUDOX_QR          LX-C-000102
└── EXTERNAL_BARCODE  8001234567890
```

La struttura dati è già predisposta, ma l'assegnazione operativa, la scansione,
la generazione dei QR e la stampa delle etichette appartengono alla futura
feature #4.

- TBD: Definire formato e vincoli dei valori `LUDOX_QR` e
  `EXTERNAL_BARCODE`, incluse le relative regole di unicità.

- TBD: Definire i formati fisici supportati per la stampa delle etichette QR,
  ad esempio fogli A4, stampanti termiche o dimensioni personalizzabili.

## Formato di interoperabilità della ludoteca

La composizione della ludoteca può essere esportata e reimportata senza
dipendere dagli identificativi interni del database.

Il formato canonico minimo è un CSV UTF-8 con le colonne tecniche stabili:

```text
game_name,owner_label,quantity
Azul,Biblioteca,3
Azul,LAM,2
Azul,Matteo,1
```

Una riga rappresenta una combinazione gioco + owner label con quantità maggiore
di zero.

Il formato canonico non contiene:

- ID interni SQLite;
- prestiti;
- token;
- sessioni/documenti;
- timestamp operativi;
- storico dei prestiti.

I valori CSV usano il normale quoting quando contengono virgole, virgolette o
altri caratteri che lo richiedono.

CSV è il formato di interoperabilità di riferimento. XLSX rappresenta le stesse
colonne logiche come formato di comodità.

Campi ulteriori potranno essere aggiunti in futuro come colonne opzionali,
senza rendere incompatibile il formato minimo a tre colonne.

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

Le copie fisiche vengono aggregate per gioco + owner label e il risultato
contiene almeno:

- `game_name`;
- `owner_label`;
- `quantity`.

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

## Modalità token

La modalità attualmente operativa usa token fisici numerati.

In questa modalità:

```text
slot 23 ↔ token fisico 23
```

Il token identifica la sessione per chi opera al banco e per la persona. Non
identifica la copia fisica del gioco.

Il sistema conosce il titolo prestato ma, se la copia non viene identificata
individualmente, non attribuisce il singolo prestito a uno specifico
proprietario/owner label.

## Modalità QR code / barcode

La futura modalità `copy_identifier` utilizzerà l'identificazione della singola
copia.

Lo slot continuerà a identificare la posizione fisica del documento, mentre il
QR/barcode della copia diventerà la chiave operativa usata durante prestito e
restituzione.

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
→ AZUL-014 viene associata al nuovo prestito della stessa sessione
```

Il QR/barcode non sostituisce lo slot fisico del documento. Sostituisce il
token come mezzo operativo per identificare la copia e risalire alla sessione.

## Prestiti

Ogni prestito appartiene a una sessione e a un gioco.

Il modello può rappresentare opzionalmente anche la copia fisica specifica:

```text
prestito
├── sessione
├── gioco
└── copia fisica opzionale
```

In modalità token la copia specifica può essere sconosciuta.

In modalità QR/barcode la copia specifica sarà identificata.

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
