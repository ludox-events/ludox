# Operatività Prestiti Ludoteca LudoX

**Stato:** procedura della modalità token attualmente disponibile.

Questo documento descrive come organizzare fisicamente la postazione di prestito e come utilizzare LudoX nella modalità basata su token numerati.

L'obiettivo è permettere di gestire i prestiti senza registrare nel software dati identificativi delle persone.

## Principio generale

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

## Numero di slot

Il numero massimo di slot deve corrispondere alle posizioni fisiche effettivamente disponibili.

Nel nuovo modello architetturale questo valore è una configurazione del modulo Prestiti del singolo Event.

```text
max_slots = 50

Token disponibili: 1–50
Slot fisici:        1–50
```

La futura modalità QR code/barcode è descritta a livello concettuale in [LENDING.md](LENDING.md), ma non fa parte di questa procedura operativa finché non sarà implementata.
