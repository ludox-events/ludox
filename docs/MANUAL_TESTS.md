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

## Catalogo e Backoffice

- [ ] Creare un proprietario e verificare che compaia nell'elenco.
- [ ] Creare un gioco e associargli almeno una copia.
- [ ] Modificare i dati di un gioco e verificare che la modifica sia visibile nelle schermate operative.
- [ ] Modificare la quantità di copie e verificare che la disponibilità mostrata sia coerente.

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
