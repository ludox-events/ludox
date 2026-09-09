# Contribuire a LudoX

Grazie per l'interesse verso LudoX.

Il progetto è ancora in fase alpha e, in questa prima fase, è consigliato
aprire una Issue prima di sviluppare modifiche importanti.

## Principi da preservare

Le contribuzioni dovrebbero rispettare, salvo decisioni architetturali
esplicite, questi principi:

- funzionamento offline delle funzioni essenziali;
- privacy by design;
- assenza di raccolta non necessaria di dati personali;
- semplicità per volontari e operatori;
- dati comprensibili e recuperabili;
- compatibilità con la distribuzione open source;
- coerenza con il flusso operativo descritto in
  [OPERATION.md](OPERATION.md).

## Workflow previsto

1. Apri una Issue o discuti la modifica.
2. Crea un fork.
3. Crea un branch dedicato.
4. Implementa e prova la modifica.
5. Apri una Pull Request.

## Stato attuale delle contribuzioni esterne

LudoX intende adottare un Contributor License Agreement per i contributi
incorporati nell'upstream ufficiale.

**Il CLA presente oggi in `CLA.md` è una bozza e NON è ancora attivo.**

Fino all'attivazione di un CLA definitivo:

- Issue, proposte e Pull Request esterne sono benvenute;
- il codice può essere discusso e revisionato pubblicamente;
- i contributi esterni non vengono incorporati nell'upstream ufficiale.

Questa limitazione temporanea serve a evitare che l'accettazione di contributi
avvenga prima che siano definiti in modo corretto i diritti necessari alla
governance e alla strategia di licensing del progetto.

## CLA

Prima di iniziare ad accettare contributi esterni nell'upstream ufficiale, il
CLA dovrà essere:

- finalizzato;
- sottoposto a revisione legale;
- accompagnato da un meccanismo chiaro di accettazione.

La mancata sottoscrizione del futuro CLA non limiterà i diritti di utilizzo,
fork, modifica e redistribuzione concessi dalla licenza pubblica AGPL.

## Test delle modifiche

Prima di proporre una modifica è consigliato verificare almeno:

- avvio dell'applicazione;
- creazione di un nuovo database;
- nuovo prestito;
- cambio gioco;
- restituzione finale;
- gestione giochi e proprietari;
- statistiche;
- report;
- esportazione CSV.

Per modifiche al flusso operativo è importante verificare anche la coerenza
con [OPERATION.md](OPERATION.md).

## Stile delle modifiche

In questa fase il progetto mantiene intenzionalmente una struttura semplice.

Non è necessario introdurre refactoring o nuove dipendenze se non portano un
vantaggio concreto al progetto.

Le modifiche dovrebbero essere:

- circoscritte;
- leggibili;
- facilmente verificabili;
- compatibili con il funzionamento offline.

## Licenza

Contribuendo a discussioni, Issue o Pull Request non si modifica la licenza
pubblica del progetto.

LudoX è distribuito sotto **AGPL-3.0-only**.

Per i contributi destinati all'upstream ufficiale si applicherà inoltre il CLA
quando sarà formalmente attivato.
