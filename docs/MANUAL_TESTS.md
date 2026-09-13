# Test manuali LudoX

Questo documento raccoglie le verifiche manuali da eseguire sul software quando una modifica non è completamente coperta dai test automatici.

I test automatici (`pytest`) verificano la logica tecnica e le regressioni riproducibili. Questa checklist verifica invece ciò che una persona vede e fa realmente nell'applicazione: navigazione, dialoghi, selezione dei file, persistenza tra riavvii e comportamento complessivo dei flussi operativi.

Le checklist nel repository restano normalmente non selezionate. Servono come traccia per ogni nuova esecuzione dei test e non come registro permanente degli esiti.

## Quando eseguirli

Prima del push di una modifica funzionale, eseguire almeno le sezioni pertinenti alla feature modificata.

Prima di una release, eseguire l'intera checklist compatibile con le funzionalità presenti nella versione.

Quando una nuova feature introduce un comportamento che richiede una verifica umana, aggiornare questo documento insieme alla feature senza duplicare controlli già coperti in modo sufficiente dai test automatici.

## Avvio e navigazione di base

- [ ] Avviare LudoX e verificare che la finestra principale venga mostrata senza errori.
- [ ] Verificare che dalla Home siano raggiungibili Nuovo prestito, Cambio gioco, Restituzione finale, Statistiche e Backoffice.
- [ ] Entrare nel Backoffice e verificare che le principali sezioni siano raggiungibili.
- [ ] Usare i pulsanti Indietro nelle principali schermate e verificare il ritorno alla schermata prevista.

## Prestiti Ludoteca

### Nuovo prestito

Prerequisito: almeno un gioco attivo con una copia disponibile.

- [ ] Avviare un nuovo prestito e selezionare un gioco disponibile.
- [ ] Verificare che venga assegnato il primo token libero atteso.
- [ ] Verificare che il prestito risulti attivo nella Home.
- [ ] Verificare che la disponibilità del gioco diminuisca.

### Cambio gioco

Prerequisito: un prestito aperto e almeno un secondo gioco disponibile.

- [ ] Inserire il token del prestito aperto.
- [ ] Cambiare il gioco associato al token.
- [ ] Verificare che il token rimanga invariato.
- [ ] Verificare che il gioco precedente torni disponibile.
- [ ] Verificare che la disponibilità del nuovo gioco diminuisca.

### Restituzione finale

Prerequisito: un prestito aperto.

- [ ] Eseguire la restituzione finale usando il token corretto.
- [ ] Verificare che il prestito non risulti più attivo.
- [ ] Verificare che il gioco torni disponibile.
- [ ] Verificare che il token possa essere nuovamente assegnato a un nuovo prestito.

## Storici, statistiche e report

Prerequisito: eseguire almeno un prestito completo e, se possibile, un cambio gioco.

- [ ] Aprire lo storico prestiti e verificare che i movimenti appena effettuati siano presenti.
- [ ] Aprire lo storico documenti e verificare che la sessione appena chiusa sia presente.
- [ ] Aprire le statistiche e verificare che i conteggi siano coerenti con le operazioni appena effettuate.
- [ ] Aprire i report principali e verificare che mostrino dati coerenti con i prestiti effettuati.

## Modalità `copy_identifier` — checklist issue #4

Usare esclusivamente un database di prova con almeno due Event. Preparare
almeno tre giochi, due owner label, quattro copie e un lettore HID configurato
per inviare il codice seguito da Invio. Ripetere i campi di scansione anche con
digitazione manuale.

### 1. Selezione della modalità

- [ ] Selezionare `copy_identifier` nelle impostazioni della ludoteca, salvare,
  riaprire la schermata e verificare che la scelta persista.
- [ ] Con un prestito aperto verificare che il passaggio a `token` sia bloccato;
  dopo la restituzione finale verificare che sia consentito.
- [ ] Verificare che il cambio modalità non cancelli copie prive di codice.

### 2. Assegnazione di un codice esterno

- [ ] Dalla gestione singole copie selezionare una scatola, assegnare un codice
  esterno e verificare nell'elenco valore, origine e disponibilità.
- [ ] Sostituire e poi rimuovere il codice; verificare che queste azioni siano
  bloccate quando la copia è in prestito.

### 3. Codice LudoX e QR PNG

- [ ] Generare un identificatore LudoX e verificare il formato
  `LX-C-` seguito dall'ID copia a almeno sei cifre.
- [ ] Esportare il QR PNG, aprirlo e verificare che riporti anche il testo
  leggibile del codice.

### 4. Unicità e isolamento Event

- [ ] Tentare di assegnare lo stesso valore a due copie dello stesso Event e
  verificare il rifiuto senza modifiche alla seconda copia.
- [ ] Assegnare lo stesso valore in un altro Event e verificare che sia
  consentito.

### 5. Nuovo prestito con scanner e tastiera

- [ ] Scansionare una copia valida e verificare l'apertura del prestito, la
  visualizzazione del gioco e l'assegnazione del primo slot libero.
- [ ] Ripetere con digitazione manuale del codice seguita da Invio.
- [ ] Verificare che non venga richiesto o mostrato un token fisico da
  consegnare.

### 6. Errori di apertura

- [ ] Provare codice sconosciuto, codice presente solo nell'altro Event, copia
  inattiva, gioco inattivo e copia già in prestito; verificare messaggi chiari
  e assenza di nuovi prestiti/sessioni.
- [ ] Verificare che una copia attiva ma priva di codice non possa essere
  prestata in questa modalità.

### 7. Cambio copia

- [ ] Scansionare la copia restituita e poi una nuova copia disponibile;
  confermare e verificare che gioco e prestito cambino mantenendo lo stesso
  slot.
- [ ] Ripetere annullando al riepilogo e verificare che il vecchio prestito
  resti invariato.

### 8. Restituzione finale

- [ ] Scansionare la copia, verificare lo slot, annullare e controllare che lo
  slot resti occupato.
- [ ] Ripetere, recuperare fisicamente il documento e confermare
  **DOCUMENTO RESTITUITO**; verificare chiusura e riuso dello slot.

### 9. Import legacy

- [ ] Importare un CSV con le sole colonne `game_name`, `owner_label` e
  `quantity`; verificare che le copie siano create senza identificatore e che
  l'anteprima non modifichi i dati prima della conferma.

### 10. Import esteso e conflitti

- [ ] Importare CSV e XLSX con `copy_identifier` e `identifier_source`, inclusa
  una sorgente vuota che deve diventare `external`.
- [ ] Provare quantità diversa da 1 per una copia identificata, sorgente non
  valida, sorgente senza codice e duplicati; verificare che l'intero import sia
  bloccato senza scritture parziali.

### 11. Export e round-trip

- [ ] Esportare una ludoteca mista e verificare una riga per copia identificata
  e righe aggregate per le copie prive di codice.
- [ ] Reimportare il file in un altro Event e verificare che codici e origini
  siano conservati, mentre le copie restano record indipendenti.

### 12. Storico e report

- [ ] Completare almeno un prestito identificato e verificare nello storico ID
  copia, codice corrente e owner label.
- [ ] Sostituire il codice dopo la chiusura e verificare che lo storico mostri
  il nuovo codice senza perdere il movimento; controllare anche le copie note
  nel report utilizzo e nel relativo CSV.

### 13. Regressione modalità token e layout

- [ ] Tornare a `token` senza operazioni aperte ed eseguire nuovo prestito,
  cambio e restituzione completi, verificando il comportamento storico.
- [ ] Ridurre la finestra e aumentare il ridimensionamento di Windows:
  verificare che impostazioni, gestione copie e Backoffice restino utilizzabili
  e che ogni azione sia raggiungibile tramite scorrimento.

## Catalogo e Backoffice

- [ ] Creare un proprietario e verificare che compaia nell'elenco.
- [ ] Creare un gioco e associargli almeno una copia.
- [ ] Modificare i dati di un gioco e verificare che la modifica sia visibile nelle schermate operative.
- [ ] Modificare la quantità di copie e verificare che la disponibilità mostrata sia coerente.

## Organizzazioni

- [ ] Con nessuna Organization configurata, verificare che la Home segnali l'assenza di un contesto attivo senza creare automaticamente una Organization generica.
- [ ] Dal Backoffice creare la prima Organization e verificare che diventi automaticamente quella attiva.
- [ ] Creare una seconda Organization, selezionarla dal Backoffice e verificare che la Home mostri il nuovo contesto senza offrire controlli per cambiarlo.
- [ ] Chiudere e riavviare LudoX e verificare che la coppia ID e nome dell'Organization attiva venga ripristinata.
- [ ] Modificare il nome dell'Organization attiva e verificare che il contesto salvato venga aggiornato.
- [ ] Disattivare l'Organization attiva e verificare che non sia più selezionabile; se ne resta una sola attiva, verificare che venga scelta automaticamente.
- [ ] Verificare che la gestione permetta di disattivare una Organization ma non di eliminarla.
- [ ] Verificare che i proprietari dei giochi restino separati dalle Organizations e non vengano convertiti durante la migration.

## Workspace e database

Eseguire queste verifiche solo su database di test o copie dei database, mai sull'unica copia di dati importanti.

- [ ] Creare o selezionare un database di test dal Backoffice.
- [ ] Inserire dati riconoscibili nel database di test.
- [ ] Passare a un secondo database e verificare che i dati del primo non siano visibili.
- [ ] Tornare al database iniziale e verificare che i dati precedenti siano nuovamente disponibili.
- [ ] Chiudere e riavviare LudoX e verificare che venga riaperto il workspace previsto.

### Database nuovo/vuoto

Prerequisito: un percorso di test in cui non esiste ancora un database LudoX.

- [ ] Selezionare o creare un nuovo database e verificare che venga inizializzato senza richiesta di migration.
- [ ] Verificare che l'applicazione prosegua normalmente con lo schema corrente.

### Migration di un database esistente

Prerequisito: una copia di test di un database creato con uno schema precedente e contenente dati riconoscibili.

- [ ] Aprire il database e verificare che LudoX segnali chiaramente la necessità di aggiornare lo schema prima di mostrare l'interfaccia operativa.
- [ ] Verificare che il messaggio mostri in modo comprensibile versione corrente e versione richiesta.
- [ ] Annullare la migration e verificare che LudoX si chiuda senza modificare il database.
- [ ] Riavviare LudoX sullo stesso database e autorizzare la migration.
- [ ] Verificare che venga creata automaticamente una copia di backup prima dell'aggiornamento.
- [ ] Verificare che il nome del backup sia leggibile e che il file non sovrascriva backup preesistenti.
- [ ] Verificare che, terminata la migration, LudoX si avvii normalmente.
- [ ] Verificare che i dati riconoscibili presenti prima della migration siano ancora disponibili.
- [ ] Chiudere e riavviare LudoX e verificare che il database aggiornato non richieda una nuova migration.
- [ ] Con una copia di un database schema v3 contenente identificatori validi,
  verificare l'aggiornamento a v4 e la conservazione/mappatura delle origini
  `LUDOX_QR → ludox` e `EXTERNAL_BARCODE → external`.
- [ ] Con una copia v3 contenente più codici sulla stessa copia o codici
  duplicati nello stesso Event, verificare che la migration fallisca in modo
  comprensibile, mantenga il backup e non scelga o cancelli valori.

### Errore o schema incompatibile

Questi controlli vanno eseguiti soltanto con database e cartelle di test preparati appositamente.

- [ ] Simulare l'impossibilità di creare il backup e verificare che la migration non parta e che LudoX non acceda operativamente al database.
- [ ] Verificare che un errore di migration produca un messaggio comprensibile e non permetta l'avvio con uno schema parzialmente aggiornato.
- [ ] Verificare che, dopo un errore di migration, il backup creato resti disponibile.
- [ ] Aprire un database con `user_version` superiore a quello supportato e verificare che LudoX segnali l'incompatibilità e termini senza tentare downgrade.

## Regola per le nuove feature

Quando una issue introduce un nuovo comportamento visibile o un nuovo flusso operativo:

1. aggiungere qui solo i test manuali che danno valore rispetto alla suite automatica;
2. descrivere prerequisiti, azione ed esito atteso in modo verificabile;
3. evitare controlli interni che richiedono SQL, `PRAGMA` o modifica manuale del database: questi appartengono ai test automatici;
4. mantenere i test indipendenti da dati personali o database reali dell'utente.
