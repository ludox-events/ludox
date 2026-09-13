# Operatività Prestiti Ludoteca LudoX

> **STATUS: APPROVED SPECIFICATION — READ ONLY**
>
> **IMPLEMENTATION: IMPLEMENTED**
>
> Questo documento è una specifica approvata di LudoX. Durante
> l'implementazione non deve essere modificato, salvo richiesta esplicita
> dell'utente. I marker `TBD` e `QUESTION` restano decisioni aperte e non
> autorizzano Codex a scegliere autonomamente una soluzione.



Questo documento descrive come organizzare fisicamente la postazione di
prestito e come utilizzare LudoX nelle due modalità operative alternative:
`token` e `copy_identifier`.

L'obiettivo è permettere di gestire i prestiti senza registrare nel software dati identificativi delle persone.

## Principio generale

Ogni Event usa una sola modalità alla volta. La modalità si seleziona dal
Backoffice del modulo Prestiti Ludoteca insieme al numero massimo di slot.
Il passaggio da una modalità all'altra è consentito soltanto quando non
esistono sessioni o prestiti aperti nell'Event.

In entrambe le modalità LudoX assegna uno slot fisico al documento e non
registra nominativo, numero del documento o altri dati identificativi della
persona.

### Modalità token

La modalità token utilizza:

- un **token numerato** consegnato alla persona;
- uno **slot/posizione fisica numerata** in cui viene custodito il documento;
- una corrispondenza diretta tra numero del token e numero dello slot.

Esempio:

```text
TOKEN 27
   │
   └── Documento custodito nello SLOT 27
```

Il software non registra nominativo, numero del documento o altri dati identificativi della persona.

## Materiale necessario

Per la postazione servono:

- un PC con LudoX;
- i giochi disponibili per il prestito;
- token fisici numerati;
- uno schedario/raccoglitore con slot numerati per custodire i documenti;
- una postazione non accessibile liberamente al pubblico.

Per la modalità `copy_identifier` servono inoltre codici univoci applicati alle
singole scatole. Lo scanner è opzionale: se presente deve funzionare come una
tastiera e inviare:

```text
codice → ENTER
```

Non sono richiesti camera, webcam o servizi di rete. Ogni codice può essere
digitato manualmente per verifica o emergenza.

## Organizzazione degli slot

È possibile utilizzare, per esempio:

- un portalistini formato A6;
- un raccoglitore con pagine porta-carte stile Magic/trading card.

Ogni posizione deve essere chiaramente numerata.

```text
Slot 01 → Token 01
Slot 02 → Token 02
Slot 03 → Token 03
...
Slot 27 → Token 27
```

Con molti slot può essere utile separare visivamente le decine.

## Protezione visiva dei documenti

Il documento non dovrebbe rimanere visibile all'interno dello schedario.

È consigliato inserire davanti al documento un cartoncino opaco o un divisore su cui sia riportato soltanto il numero dello slot.

Lo schedario deve essere accessibile soltanto alle persone incaricate e non liberamente consultabile dal pubblico.

## Nuovo prestito

### Procedura con token

1. la persona sceglie un gioco;
2. l'operatore seleziona **NUOVO PRESTITO**;
3. LudoX verifica la disponibilità del gioco;
4. LudoX assegna uno slot/token libero;
5. il documento viene inserito nello slot con lo stesso numero;
6. il token fisico viene consegnato alla persona;
7. viene consegnato il gioco.

```text
LudoX assegna 27
Documento → slot 27
Token 27  → persona
Gioco     → persona
```

## Cambio gioco

### Procedura con token

1. la persona restituisce il gioco utilizzato;
2. comunica o consegna temporaneamente il proprio token;
3. l'operatore seleziona **CAMBIO GIOCO**;
4. inserisce il numero del token;
5. LudoX mostra il gioco attualmente associato;
6. viene selezionato il nuovo gioco;
7. il cambio viene registrato;
8. viene consegnato il nuovo gioco.

Il documento non viene spostato e lo slot rimane invariato per tutta la sessione.

```text
Prima:
Token 27
Documento → slot 27
Gioco     → Azul

Dopo:
Token 27
Documento → slot 27
Gioco     → Cascadia
```

## Restituzione finale

### Procedura con token

1. la persona restituisce il gioco;
2. comunica o consegna il token;
3. l'operatore seleziona **RESTITUZIONE FINALE**;
4. inserisce il numero del token;
5. verifica il rientro del gioco;
6. LudoX mostra lo slot del documento;
7. l'operatore recupera fisicamente il documento;
8. il documento viene restituito alla persona;
9. soltanto dopo la consegna fisica viene confermata la restituzione in LudoX;
10. lo slot/token torna disponibile.

La conferma finale deve avvenire soltanto dopo la restituzione fisica del documento, per evitare di riassegnare lo stesso slot mentre il documento precedente è ancora custodito.

## Preparazione delle copie identificate

Dal Backoffice, nella gestione delle singole copie, è possibile:

- vedere gioco, owner label, stato e disponibilità di ogni scatola;
- assegnare o sostituire un codice esterno;
- generare un codice LudoX nel formato `LX-C-000123`;
- rimuovere un identificatore quando la copia non è in prestito;
- attivare o disattivare una copia quando non è in prestito;
- esportare in PNG il QR di un identificatore generato da LudoX.

Il valore è confrontato esattamente dopo la rimozione degli spazi esterni:
maiuscole e minuscole restano differenti. Un codice deve identificare una sola
copia nello stesso Event; lo stesso valore può essere usato in Event diversi.
Una copia senza codice può restare in inventario, ma non è prestabile nella
modalità `copy_identifier`.

## Operatività con `copy_identifier`

### Nuovo prestito tramite copia

1. la persona sceglie una specifica scatola;
2. l'operatore seleziona **NUOVO PRESTITO**;
3. scansiona il codice della scatola o lo digita e preme Invio;
4. LudoX verifica Event, copia, gioco e disponibilità;
5. LudoX apre il prestito della copia e assegna il primo slot libero;
6. il documento viene inserito nello slot mostrato;
7. viene consegnata la scatola, senza token fisico.

```text
Scatola FIRST-COPY → prestito aperto
Documento          → slot 12
Token fisico       → non usato
```

Un codice sconosciuto, appartenente soltanto a un altro Event, associato a una
copia inattiva o già in prestito non modifica il database.

### Cambio gioco tramite copie

1. scansionare la copia restituita;
2. verificare gioco e slot mostrati;
3. scansionare la nuova copia;
4. verificare il riepilogo e confermare;
5. consegnare la nuova scatola.

Il vecchio prestito viene chiuso e il nuovo viene aperto sulla stessa sessione
in un'unica operazione. Lo slot del documento non cambia. Se si annulla prima
della conferma, il prestito precedente resta aperto senza modifiche.

### Restituzione finale tramite copia

1. scansionare la copia restituita;
2. verificare gioco e slot mostrati;
3. recuperare fisicamente il documento dallo slot;
4. restituire il documento alla persona;
5. soltanto allora selezionare **DOCUMENTO RESTITUITO** e confermare.

Prestito e sessione vengono chiusi insieme solo alla conferma finale. Annullare
la schermata lascia lo slot occupato e il prestito aperto.

## Importazione ed esportazione

L'import CSV UTF-8 o XLSX accetta il formato aggregato storico:

```text
game_name,owner_label,quantity
```

e il formato esteso:

```text
game_name,owner_label,quantity,copy_identifier,identifier_source
```

Una riga identificata deve avere `quantity = 1`; `identifier_source` vale
`external` o `ludox` e, se omesso per un codice presente, assume `external`.
Una sorgente senza codice non è valida. Un duplicato nel file o nell'Event
blocca l'intero import. L'export event-specific scrive una riga per copia
identificata e può aggregare le copie senza codice per gioco e owner label.

## Storico e report

Quando il prestito conosce la copia, lo storico mostra l'ID interno della
copia, il suo identificatore operativo corrente e la relativa owner label. Il
report utilizzo elenca le copie note coinvolte nei prestiti del titolo. I
prestiti creati in modalità token restano correttamente attribuiti al titolo e
mostrano i dettagli copia come non disponibili.

## Riutilizzo

Uno slot/token può essere riutilizzato dopo la chiusura completa della sessione precedente. Nel database le due permanenze costituiscono sessioni distinte.

## Token smarrito

Il token è un riferimento operativo, non un identificativo personale.

In caso di smarrimento, l'operatore deve verificare la situazione con prudenza prima di restituire qualsiasi documento. La procedura specifica deve essere definita dall'organizzazione che utilizza LudoX.

## Chiusura dell'applicazione

Se risultano sessioni/documenti ancora aperti al momento della chiusura, verificare sempre fisicamente gli slot indicati prima di terminare il servizio.

## Buone pratiche

- non lasciare lo schedario accessibile al pubblico;
- non scrivere nominativi sui token;
- non riportare dati personali nello schedario oltre al documento stesso;
- mantenere sempre la corrispondenza `token N = slot N` nella modalità token;
- non spostare il documento durante un cambio gioco;
- confermare la chiusura soltanto dopo la restituzione fisica del documento;
- controllare periodicamente che token e slot siano completi e ordinati;
- a fine evento verificare che non risultino sessioni ancora aperte.
- verificare che ogni codice esterno identifichi davvero una sola scatola;
- nella modalità `copy_identifier`, scansionare sempre la scatola fisica che
  entra o esce dal banco;
- tenere disponibile la digitazione manuale come procedura di riserva.

## Numero di slot

Il numero massimo di slot deve corrispondere alle posizioni fisiche effettivamente disponibili.

Nel nuovo modello architetturale questo valore è una configurazione del modulo Prestiti del singolo Event.

```text
max_slots = 50

Token disponibili: 1–50
Slot fisici:        1–50
```

In modalità `copy_identifier` gli stessi slot `1-max_slots` restano posizioni
fisiche dei documenti, ma i token fisici non vengono consegnati.
