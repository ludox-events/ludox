# Operatività dei prestiti LudoX

Questo documento descrive come organizzare fisicamente la postazione di
prestito e come utilizzare LudoX durante un evento.

L'obiettivo è permettere di gestire i prestiti senza registrare nel software
dati identificativi delle persone.

## Principio generale

LudoX utilizza un sistema basato su:

- un **token numerato** consegnato alla persona;
- una **posizione fisica numerata** in cui viene custodito il documento;
- un'associazione diretta tra numero del token e posizione del documento.

Esempio:

```text
TOKEN 27
   │
   └── Documento custodito nella posizione 27
```

Il software registra il numero del token, ma non registra nominativo, numero
del documento o altri dati identificativi della persona.

## Materiale necessario

Per la postazione di prestito servono:

- un PC con LudoX;
- i giochi disponibili per il prestito;
- token fisici numerati;
- uno schedario numerato per custodire i documenti;
- una postazione non accessibile liberamente al pubblico.

## Come organizzare lo schedario

È possibile utilizzare due soluzioni principali.

### Portalistini formato A6

Un portalistini A6 permette di dedicare una tasca a ciascun token.

Esempio:

```text
Tasca 01 → Token 01
Tasca 02 → Token 02
Tasca 03 → Token 03
...
Tasca 27 → Token 27
```

### Porta-carte stile Magic / trading card

È possibile utilizzare anche un raccoglitore con pagine porta-carte, come
quelli utilizzati per Magic: The Gathering o altri giochi di carte
collezionabili.

Ogni tasca deve essere chiaramente numerata e associata a un solo token.

Questa soluzione può risultare particolarmente compatta quando si devono
gestire molti documenti.

## Numerazione

La numerazione deve essere semplice e immediatamente leggibile.

È consigliato utilizzare numeri progressivi:

```text
01
02
03
...
99
100
```

La posizione fisica deve corrispondere esattamente al numero del token.

Non utilizzare una classificazione alfabetica o basata sul nome della persona.

## Protezione visiva dei documenti

Il documento non dovrebbe rimanere visibile all'interno dello schedario.

È consigliato inserire davanti al documento:

- un cartoncino opaco;
- oppure un divisore;

su cui sia riportato soltanto il numero della posizione.

Esempio:

```text
┌─────────────┐
│             │
│     27      │
│             │
└─────────────┘
```

Il documento viene inserito dietro il cartoncino.

## Posizione dello schedario

Lo schedario deve essere:

- dietro la postazione di accoglienza;
- accessibile soltanto alle persone incaricate;
- tenuto chiuso o comunque non liberamente consultabile dal pubblico;
- organizzato in modo che sia possibile recuperare rapidamente una posizione.

Con molti token può essere utile separare visivamente le decine:

```text
01–10
11–20
21–30
...
```

## Nuovo prestito

La sequenza operativa consigliata è:

1. la persona sceglie un gioco;
2. l'operatore seleziona **NUOVO PRESTITO** in LudoX;
3. viene verificata la disponibilità del gioco;
4. LudoX assegna automaticamente un token libero;
5. l'operatore prende il token fisico corrispondente;
6. il documento viene inserito nella posizione con lo stesso numero;
7. il token viene consegnato alla persona;
8. viene consegnato il gioco.

Esempio:

```text
LudoX assegna TOKEN 27

Documento → posizione 27
Token 27  → persona
Gioco     → persona
```

## Cambio gioco

Quando una persona vuole cambiare gioco:

1. restituisce il gioco utilizzato;
2. comunica o consegna temporaneamente il proprio token;
3. l'operatore seleziona **CAMBIO GIOCO**;
4. inserisce il numero del token;
5. LudoX mostra il gioco attualmente associato;
6. viene selezionato il nuovo gioco;
7. il cambio viene registrato;
8. viene consegnato il nuovo gioco.

Durante il cambio:

**il documento non deve essere spostato.**

Esempio:

```text
Prima del cambio:
Token 27
Documento → posizione 27
Gioco     → Azul

Dopo il cambio:
Token 27
Documento → posizione 27
Gioco     → Cascadia
```

La posizione del documento resta invariata per tutta la permanenza della
persona.

## Restituzione finale

Quando la persona termina i prestiti:

1. restituisce il gioco;
2. comunica o consegna il token;
3. l'operatore seleziona **RESTITUZIONE FINALE**;
4. inserisce il numero del token;
5. verifica che il gioco sia effettivamente rientrato;
6. LudoX mostra il numero della posizione del documento;
7. l'operatore recupera fisicamente il documento;
8. il documento viene restituito alla persona;
9. soltanto dopo la consegna fisica viene premuto
   **DOCUMENTO RESTITUITO**;
10. il token torna disponibile per un nuovo prestito.

Esempio:

```text
Gioco rientrato
      ↓
LudoX mostra POSIZIONE 27
      ↓
Recupera il documento dalla posizione 27
      ↓
Restituisci il documento
      ↓
DOCUMENTO RESTITUITO
      ↓
Token 27 nuovamente disponibile
```

## Perché esiste la doppia conferma

La chiusura del prestito è separata dalla conferma della restituzione del
documento per evitare che un token venga reso nuovamente disponibile prima
che il documento sia stato effettivamente riconsegnato.

Il flusso corretto è quindi:

```text
1. gioco fisicamente rientrato
2. documento fisicamente recuperato
3. documento fisicamente consegnato
4. conferma finale in LudoX
```

## Token riutilizzati

Un token può essere utilizzato nuovamente dopo la chiusura completa della
sessione precedente.

Esempio:

```text
Ore 14:20
Token 27 → Persona A

Ore 16:10
Restituzione finale
Token 27 libero

Ore 16:25
Token 27 → Persona B
```

Nel database si tratta di due sessioni separate.

## Se una persona perde il token

Il token è un riferimento operativo, non un identificativo personale.

In caso di smarrimento, l'operatore deve verificare la situazione con prudenza
prima di restituire qualsiasi documento.

La procedura specifica per questi casi deve essere definita
dall'organizzazione che utilizza LudoX in base alle proprie modalità
operative.

## Chiusura dell'applicazione

Se LudoX segnala la presenza di documenti ancora aperti al momento della
chiusura, verificare sempre fisicamente le posizioni indicate prima di
terminare il servizio.

## Buone pratiche

- non lasciare lo schedario accessibile al pubblico;
- non scrivere nominativi sui token;
- non riportare dati personali nello schedario oltre al documento stesso;
- mantenere sempre la corrispondenza `token = posizione`;
- non spostare il documento durante un cambio gioco;
- effettuare la conferma finale solo dopo la restituzione fisica del documento;
- controllare periodicamente che token e posizioni siano completi e ordinati;
- a fine evento verificare che non risultino documenti ancora aperti.

## Sintesi del flusso

```text
NUOVO PRESTITO
Persona → documento → posizione N
                    → token N alla persona
                    → gioco alla persona

CAMBIO GIOCO
Gioco A rientra
Documento resta in posizione N
Token resta N
Gioco B viene consegnato

RESTITUZIONE FINALE
Gioco rientra
→ recupera documento da posizione N
→ restituisci documento
→ conferma in LudoX
→ token N libero
```
