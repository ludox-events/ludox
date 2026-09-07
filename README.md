# LudoX

**Gestione eventi ludici**

LudoX è un software open source pensato per associazioni, ludoteche,
biblioteche ed eventi dedicati al gioco.

La prima versione nasce per gestire in modo semplice e offline il prestito
di giochi durante eventi e serate ludiche.

> **Stato del progetto:** alpha iniziale. Il software è ancora in sviluppo.

## Funzioni attuali

- prestito di giochi con assegnazione automatica di un token;
- cambio gioco mantenendo lo stesso token;
- restituzione finale con doppia conferma del documento;
- gestione anonima di documenti/persone;
- più proprietari per lo stesso titolo;
- quantità di copie per proprietario;
- disponibilità delle copie;
- statistiche sui prestiti;
- backoffice con:
  - gestione giochi;
  - gestione proprietari;
  - elenco di tutti i prestiti;
  - elenco di tutti i documenti/persone anonimi;
  - giochi per proprietario.

## Principi del progetto

### Offline-first

LudoX è pensato per continuare a funzionare anche quando durante un evento
la connessione Internet è assente o instabile.

### Privacy by design

Il database non registra nominativi, email, numeri di telefono o dati del
documento di identità.

Il token identifica solamente la posizione fisica del documento durante il
prestito.

### Semplicità

L'interfaccia è pensata per essere utilizzata da volontari e operatori anche
in situazioni di forte affluenza.

## Requisiti

- Python 3
- Tkinter
- ttkbootstrap
- matplotlib

Su Ubuntu / Debian / Linux Mint:

```bash
sudo apt update
sudo apt install python3 python3-tk python3-venv python3-pip
```

## Installazione

Clona il repository:

```bash
git clone <URL-DEL-REPOSITORY>
cd LudoX
```

Crea e attiva un ambiente virtuale:

```bash
python3 -m venv venv
source venv/bin/activate
```

Installa le dipendenze:

```bash
pip install -r requirements.txt
```

Avvia LudoX:

```bash
python app.py
```

Al primo avvio viene creato automaticamente il database locale:

```text
ludox.db
```

Il database è escluso dal repository tramite `.gitignore`.

## Backoffice

La password predefinita della versione alpha è:

```text
ludox
```

Questa password serve soltanto a evitare accessi accidentali al Backoffice:
non deve essere considerata una misura di sicurezza forte.

## Licenza

LudoX è distribuito sotto:

**GNU Affero General Public License v3.0 only (`AGPL-3.0-only`)**

Vedi [LICENSE](LICENSE).

Implementazione iniziale:

**Copyright © 2026 Matteo Sassi**

La licenza permette di utilizzare, studiare, modificare e redistribuire LudoX
nel rispetto dei termini AGPL.

## Contributi

LudoX vuole accogliere contributi dalla comunità.

Per i contributi destinati al repository ufficiale è prevista una struttura
con **Contributor License Agreement (CLA)** ispirata, come modello di
governance, a quella usata da Redis: chi contribuisce mantiene il copyright
sul proprio contributo, ma concede al maintainer del progetto diritti ampi e
sublicenziabili sul contributo accettato nell'upstream ufficiale.

Il file [CLA.md](CLA.md) presente nel repository è ancora una **bozza** e dovrà
essere sottoposto a revisione legale prima di essere attivato.

Leggi anche:

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [GOVERNANCE.md](GOVERNANCE.md)

## Project Steward

Il Project Steward iniziale di LudoX è:

**Matteo Sassi**
