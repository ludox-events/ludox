# LudoX

**Gestione eventi ludici**

LudoX è un software open source pensato per associazioni, ludoteche,
biblioteche ed eventi dedicati al gioco.

La prima versione nasce per gestire in modo semplice e offline il prestito
di giochi durante eventi e serate ludiche.

> **Stato del progetto:** alpha. Il software è ancora in sviluppo.

## Funzioni attuali

- prestito di giochi con assegnazione automatica di un token;
- cambio gioco mantenendo lo stesso token;
- restituzione finale con doppia conferma del documento;
- gestione anonima delle persone che prendono giochi in prestito;
- più proprietari per lo stesso titolo;
- quantità di copie per proprietario;
- disponibilità delle copie;
- statistiche operative per intervallo temporale;
- selezione di data, ora e risoluzione delle statistiche;
- report storici sull'utilizzo dei giochi;
- report storici su persone/documenti anonimi;
- statistiche descrittive su prestiti e durata dei prestiti;
- grafici di distribuzione delle occorrenze;
- filtro dei report per proprietario;
- ordinamento dei report;
- esportazione CSV;
- backoffice per la gestione di giochi, proprietari e dati storici.

## Principi del progetto

### Offline-first

LudoX è pensato per continuare a funzionare anche quando durante un evento
la connessione Internet è assente o instabile.

L'applicazione utilizza un database SQLite locale e non richiede un server
per le funzioni essenziali di prestito.

### Privacy by design

LudoX non registra dati identificativi delle persone che prendono giochi in
prestito: non vengono memorizzati nominativi, email, numeri di telefono o dati
del documento di identità.

Il software registra soltanto un token anonimo associato alla posizione fisica
in cui il documento viene custodito durante il prestito.

Il Backoffice può invece contenere i nomi dei proprietari dei giochi, quando
necessari per gestire le copie messe a disposizione.

### Semplicità operativa

L'interfaccia è pensata per essere utilizzata da volontari e operatori anche
in situazioni di forte affluenza.

Il flusso software è progettato insieme a una procedura fisica basata su token
numerati e posizioni numerate per i documenti. La procedura completa è
descritta in [OPERATION.md](OPERATION.md).

## Modello operativo

Ogni persona che prende un gioco riceve un token numerato.

Il numero del token corrisponde alla posizione fisica in cui viene custodito
il documento:

```text
Token 27 = posizione 27
```

Il documento rimane nella stessa posizione anche quando la persona cambia
gioco.

Per organizzare fisicamente i documenti è possibile utilizzare:

- un portalistini formato A6 con posizioni numerate;
- un raccoglitore porta-carte in stile Magic / trading card, con tasche
  numerate.

Vedi [OPERATION.md](OPERATION.md) per la procedura completa.

## Requisiti

- Python 3
- Tkinter
- ttkbootstrap
- matplotlib

Le dipendenze Python principali sono elencate in
[requirements.txt](requirements.txt).

## Installazione

### Windows

```bat
git clone https://github.com/ludox-events/ludox.git
cd ludox
python -m venv venv
venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

### Ubuntu / Debian / Linux Mint

```bash
sudo apt update
sudo apt install python3 python3-tk python3-venv python3-pip

git clone https://github.com/ludox-events/ludox.git
cd ludox

python3 -m venv venv
source venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

## Database

Al primo avvio viene creato automaticamente il database locale:

```text
ludox.db
```

Il database è escluso dal repository tramite `.gitignore`.

Il database contiene dati operativi e storici relativi ai prestiti e deve
essere gestito con attenzione dall'organizzazione che utilizza LudoX.

## Backoffice

La password predefinita della versione alpha è:

```text
ludox
```

Questa password serve soltanto a evitare accessi accidentali al Backoffice e
non deve essere considerata una misura di sicurezza forte.

## Procedura fisica dei prestiti

LudoX è pensato per essere utilizzato insieme a:

- token numerati;
- uno schedario con posizioni numerate;
- documenti custoditi fisicamente dietro la postazione di accoglienza.

La procedura dettagliata per nuovo prestito, cambio gioco e restituzione finale
è descritta in [OPERATION.md](OPERATION.md).

## Licenza

LudoX è distribuito sotto:

**GNU Affero General Public License v3.0 only (`AGPL-3.0-only`)**

Vedi [LICENSE](LICENSE).

Implementazione iniziale:

**Copyright © 2026 Matteo Sassi**

La licenza permette di utilizzare, studiare, modificare e redistribuire LudoX
nel rispetto dei termini AGPL.

## Contributi

LudoX accoglie contributi dalla comunità.

I contributi destinati all'upstream ufficiale sono soggetti al
[LudoX Contributor License Agreement v1.0](CLA.md).

Il Contributor mantiene il copyright sul proprio materiale originale e concede
al Project Steward i diritti descritti nel CLA.

Prima del primo merge, il Contributor deve accettare il CLA attraverso la
propria Pull Request secondo la procedura descritta in
[CONTRIBUTING.md](CONTRIBUTING.md).

Leggi anche:

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [GOVERNANCE.md](GOVERNANCE.md)
- [OPERATION.md](OPERATION.md)

## Project Steward

Il Project Steward iniziale di LudoX è:

**Matteo Sassi**
