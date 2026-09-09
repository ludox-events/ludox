# LudoX

**Gestione eventi ludici / Board game event management**

LudoX è un software open source offline-first per la gestione del prestito di
giochi durante eventi, serate ludiche, biblioteche e ludoteche.

> **Stato del progetto:** alpha. Il software è ancora in sviluppo.

## Funzioni principali

- prestiti anonimi tramite token numerati;
- cambio gioco mantenendo lo stesso token;
- restituzione finale con conferma fisica del documento;
- copie multiple e più proprietari per titolo;
- statistiche e report storici;
- esportazione CSV;
- funzionamento locale con SQLite;
- configurazione al primo avvio;
- interfaccia in italiano e inglese.

## Struttura del progetto

```text
app.py                  bootstrap dell'applicazione
config.ini              configurazione locale, creato al primo avvio
ludox.db                database locale, creato al primo avvio

ludox/
├── database.py         accesso SQLite e funzioni dati
├── config.py           configurazione e procedura di primo avvio
├── i18n.py             gestione delle traduzioni
├── ui.py               interfaccia grafica
└── locales/
    ├── it.json         traduzioni italiane
    └── en.json         traduzioni inglesi
```

`config.ini` e `ludox.db` sono dati locali e non vengono versionati.

## Primo avvio

Se `config.ini` non esiste, LudoX mostra una finestra di configurazione prima
di avviare l'interfaccia principale.

Vengono richiesti:

- lingua dell'interfaccia, con **Italiano** come valore iniziale;
- numero massimo di token/posizioni fisiche, con **100** come valore suggerito.

Il file generato ha questa forma:

```ini
[general]
language = it
max_tokens = 100
```

Le impostazioni possono essere modificate successivamente dal Backoffice.
La lingua viene applicata immediatamente alle schermate ricreate dopo il
salvataggio.

## Traduzioni

Le traduzioni sono risorse JSON statiche e non vengono memorizzate nel
database.

Per aggiungere una lingua è necessario aggiungere il relativo file in
`ludox/locales/` e registrarla in `ludox/i18n.py` e `ludox/config.py`.

L'italiano è la lingua di fallback: se una traduzione manca, LudoX continua a
mostrare il testo italiano anziché interrompere l'esecuzione.

## Procedura fisica dei prestiti

LudoX utilizza token numerati associati a posizioni fisiche numerate per i
documenti. È possibile usare un portalistini A6 oppure un raccoglitore
porta-carte stile Magic/trading card.

La procedura completa è descritta in [OPERATION.md](OPERATION.md).

## Requisiti

- Python 3
- Tkinter
- ttkbootstrap
- matplotlib

## Installazione — Windows

```bat
git clone https://github.com/ludox-events/ludox.git
cd ludox
python -m venv venv
venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

## Installazione — Ubuntu / Debian / Linux Mint

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

## Privacy by design

LudoX non registra dati identificativi delle persone che prendono giochi in
prestito. Il token identifica soltanto la posizione fisica del documento
durante la sessione.

Il Backoffice può invece contenere i nomi dei proprietari dei giochi.

## Backoffice

La password predefinita della versione alpha è:

```text
ludox
```

Serve soltanto a evitare accessi accidentali e non rappresenta una misura di
sicurezza forte.

## Licenza e contributi

LudoX è distribuito sotto **AGPL-3.0-only**.

Implementazione iniziale: **Copyright © 2026 Matteo Sassi**.

I contributi destinati all'upstream ufficiale sono soggetti al
[LudoX Contributor License Agreement v1.0](CLA.md).

Vedi anche [CONTRIBUTING.md](CONTRIBUTING.md) e
[GOVERNANCE.md](GOVERNANCE.md).
