# Contribuire a LudoX

Grazie per l'interesse verso LudoX.

Il progetto è in fase alpha. Prima di sviluppare modifiche importanti è
consigliato aprire una Issue e discuterne l'impostazione.

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

## Workflow

1. Apri una Issue o discuti la modifica.
2. Crea un fork.
3. Crea un branch dedicato.
4. Implementa e prova la modifica.
5. Apri una Pull Request.
6. Se è il tuo primo Contribution, accetta il CLA come descritto sotto.
7. Attendi review e decisione del maintainer.

## Contributor License Agreement

I Contribution incorporati nell'upstream ufficiale di LudoX sono soggetti al
[LudoX Contributor License Agreement v1.0](CLA.md).

Il Contributor mantiene il copyright sul proprio materiale originale, ma
concede al Project Steward i diritti descritti nel CLA, inclusa la possibilità
di sublicenziare il Contribution e di distribuire in futuro l'upstream
ufficiale anche sotto licenze differenti o aggiuntive.

### Come accettare il CLA

Alla prima Pull Request destinata all'upstream ufficiale, pubblica un commento
con una delle seguenti dichiarazioni.

**Italiano**

> Ho letto e accetto il LudoX Contributor License Agreement v1.0, in vigore dal
> 9 settembre 2026, per questo Contribution e per i futuri Contribution che
> invierò intenzionalmente all'upstream ufficiale di LudoX tramite questo
> account GitHub, salvo che una versione successiva del CLA richieda una nuova
> accettazione.

**English**

> I have read and agree to the LudoX Contributor License Agreement v1.0,
> effective 2026-09-09, for this Contribution and for future
> Contributions that I intentionally submit to the official LudoX upstream
> through this GitHub account, unless a later CLA version requires renewed
> acceptance.

La dichiarazione deve essere pubblicata dall'account GitHub che invia il
Contribution e deve restare visibile nella cronologia della Pull Request.

Una volta accettata la versione 1.0, non è necessario ripetere la dichiarazione
per ogni PR successiva dallo stesso account, salvo richiesta di nuova
accettazione per una versione successiva del CLA.

**Una Pull Request esterna non viene incorporata nell'upstream ufficiale finché
l'accettazione del CLA non è verificata.**

## Provenienza del codice

Non inviare codice o altri materiali che non hai il diritto di contribuire.

Se una modifica include materiale di terzi:

- identifica chiaramente la fonte;
- indica la licenza applicabile;
- verifica che il materiale sia compatibile con il Progetto e con i diritti
  concessi dal CLA.

Se contribuisci nell'ambito di un rapporto di lavoro o per conto di
un'organizzazione, assicurati di avere le autorizzazioni necessarie.

## Test delle modifiche

### Test automatici

Da un ambiente virtuale attivo, nella root del repository:

```bash
python -m pip install -r requirements-dev.txt
pytest
```

Questa suite non richiede le dipendenze GUI. Copre lo schema SQLite corrente,
le funzioni dati, i token, la disponibilità, la formattazione delle date e la
configurazione. Ogni test usa percorsi temporanei; le connessioni SQLite fuori
dalla directory temporanea del test vengono rifiutate. I file INI vengono
sempre passati esplicitamente, senza leggere la configurazione dell'utente.

I test della FASE A preparano tramite SQL dati e stati aperti/chiusi per
verificare le funzioni dati. `tests/test_lending.py` esercita invece le operazioni
effettive di apertura, cambio e restituzione estratte dalla UI nella prima fase
della issue #11: `ludox/lending.py` contiene i controlli operativi e usa le
funzioni SQL di `ludox/database.py`. Il service non importa Tkinter.

Sono verificati anche storico, riuso dei token, timestamp condivisi, stati
obsoleti, lock del cambio e rollback in caso di errore intermedio. Le conferme
e la navigazione restano nella UI e richiedono verifica manuale su un database
di prova. Non sono inclusi test Tkinter. Statistiche, report generali e
impostazioni rimangono da separare dalla UI.

La seconda fase della issue #11 estrae in `ludox/catalog.py` aggiunta/modifica
di giochi e proprietari, quantità e inventario per proprietario. Le query
rimangono in `ludox/database.py`. `tests/test_catalog.py` verifica nomi,
duplicati, disattivazioni, quantità, inventario e conservazione dello storico.
Per disattivare un proprietario con copie, il service solleva
`ConfermaDisattivazione` senza scrivere: la UI chiede conferma e solo in caso
affermativo ripete la richiesta con `conferma_disattivazione=True`.
Un gioco con prestiti aperti non può invece essere disattivato.
I controlli delle quantità precedono la transazione di scrittura, come prima.
La quantità zero rimuove l'associazione gioco/proprietario; le copie restano
aggregate e i prestiti dell'inventario sono conteggiati per titolo.

La terza fase della issue #11 estrae in `ludox/reporting.py` statistiche,
storici, report persone/documenti, report utilizzo e preparazione degli export
CSV. Le query corrispondenti sono in `ludox/database.py`; la UI conserva solo
filtri, rendering, grafici e finestre di dialogo. `tests/test_reporting.py`
verifica intervalli temporali, aggregazioni, ordinamenti, filtri, durate e
formato CSV senza importare Tkinter e usando esclusivamente database temporanei.

Per preservare il comportamento attuale, l'apertura controlla disponibilità e
token prima della transazione, mentre il cambio li ricontrolla sotto lock.
La restituzione aggiorna gli identificativi ricevuti senza aggiungere un nuovo
controllo di appartenenza del prestito al documento: il chiamante deve passare
gli identificativi della stessa situazione restituita da `consulta_token`.

La caratterizzazione preserva anche particolarità correnti: le copie di un
proprietario disattivato contribuiscono alla disponibilità; la ricerca include
titoli con tutte le copie in prestito; un limite token booleano viene accettato
da `validate_config` e salvato, ma non riletto da `load_config`.

### Verifiche manuali

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

## Licenza pubblica del progetto

LudoX è distribuito sotto **AGPL-3.0-only**.

Il CLA non elimina né riduce i diritti concessi agli utenti dalla licenza
pubblica sulle versioni di LudoX distribuite sotto AGPL.

## Struttura del codice

LudoX mantiene una struttura modulare volutamente semplice:

- `app.py` avvia l'applicazione;
- `ludox/database.py` contiene schema SQLite e funzioni dati;
- `ludox/config.py` gestisce `config.ini`, il primo avvio e la scelta del database;
- `ludox/i18n.py` gestisce la localizzazione;
- `ludox/ui.py` contiene l'interfaccia grafica;
- `ludox/locales/` contiene i cataloghi delle traduzioni.

In questa fase non è necessario suddividere ulteriormente l'interfaccia salvo
che una modifica ne tragga un vantaggio concreto e verificabile.

## Testi dell'interfaccia e traduzioni

I nuovi testi visibili all'utente non dovrebbero essere inseriti come stringhe
non traducibili.

Per il nuovo codice è preferibile utilizzare una chiave semantica:

```python
tr("settings.save")
```

e aggiungere la stessa chiave sia a `ludox/locales/it.json` sia a
`ludox/locales/en.json`.

L'italiano è la lingua di fallback. Una Pull Request che aggiunge o modifica
stringhe dell'interfaccia dovrebbe mantenere allineati entrambi i cataloghi.

## Configurazione locale

`config.ini` è generato localmente e non deve essere incluso nei commit.
Anche `ludox.db` contiene dati locali e resta escluso dal repository.

Se viene introdotto un nuovo parametro di configurazione, deve essere:

- dotato di un valore predefinito sensato;
- validato prima dell'uso;
- gestito nel primo avvio se necessario;
- documentato nel README.
