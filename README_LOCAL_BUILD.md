# LudoX — kit locale PDF + PyInstaller

Questo kit è pensato per essere copiato nella **root del repository LudoX**.

Struttura attesa:

```text
ludox/
├─ app.py
├─ requirements.txt
├─ requirements-docs.txt
├─ requirements-build.txt
├─ docs/
│  ├─ USER_GUIDE.md
│  └─ user-guide/
│     └─ images/
├─ scripts/
│  ├─ build_user_guide.py
│  ├─ build_pdf.cmd
│  └─ build_windows.ps1
└─ ...
```

## 1. Copia i file

Dal contenuto di questo ZIP copia nella root di LudoX:

```text
requirements-docs.txt
requirements-build.txt
scripts/
```

Non sostituire il tuo `requirements.txt`.

---

# PDF della guida

## Prima installazione

Apri PowerShell nella root del repository:

```powershell
python -m venv .venv-docs
.\.venv-docs\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-docs.txt
python -m playwright install chromium
```

Se PowerShell impedisce l'attivazione:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv-docs\Scripts\Activate.ps1
```

## Generazione

Con l'ambiente attivo:

```powershell
python scripts\build_user_guide.py
```

oppure, con `.venv` disponibile:

```powershell
.\scripts\build_pdf.cmd
```

Output:

```text
dist\LudoX-Guida-rapida.pdf
```

Il file intermedio HTML è:

```text
build\user-guide\USER_GUIDE.html
```

Questo è utile per controllare l'impaginazione prima del PDF.

## Modificare l'impaginazione

Apri:

```text
scripts/build_user_guide.py
```

e modifica la costante:

```python
CSS = r""" ... """
```

Le parti più utili da cambiare sono:

```css
@page {
    size: A4;
    margin: 16mm 16mm 20mm 16mm;
}

body {
    font-size: 10.5pt;
    line-height: 1.45;
}

h1 { font-size: 24pt; }
h2 { font-size: 17pt; }
h3 { font-size: 13pt; }

img {
    max-width: 100%;
    max-height: 185mm;
}
```

Dopo ogni modifica basta rilanciare:

```powershell
python scripts\build_user_guide.py
```

---

# PyInstaller su Windows

Per la prima volta conviene eseguire i passaggi manualmente.

## 1. Crea un ambiente di build

```powershell
python -m venv .venv-build
```

## 2. Attivalo

```powershell
.\.venv-build\Scripts\Activate.ps1
```

Se necessario:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv-build\Scripts\Activate.ps1
```

## 3. Aggiorna pip

```powershell
python -m pip install --upgrade pip
```

## 4. Installa LudoX

```powershell
python -m pip install -r requirements.txt
```

## 5. Installa PyInstaller

```powershell
python -m pip install -r requirements-build.txt
```

Verifica:

```powershell
python -m PyInstaller --version
```

## 6. Prima build

```powershell
python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --onedir `
  --name LudoX `
  --collect-data ludox `
  --workpath "build\windows\pyinstaller" `
  --distpath "build\windows" `
  --specpath "build\windows" `
  app.py
```

Dopo la build troverai:

```text
build\windows\
└─ LudoX\
   ├─ LudoX.exe
   └─ ...
```

Avvia:

```powershell
.\build\windows\LudoX\LudoX.exe
```

Il kit include anche:

```powershell
.\scripts\build_windows.ps1
```

che esegue automaticamente la stessa preparazione.

---

# Cosa verificare nell'EXE

Prima di comprimere la cartella, prova almeno:

1. avvio senza Python;
2. configurazione iniziale;
3. creazione di un database nuovo;
4. Home;
5. Backoffice;
6. aggiunta proprietario;
7. aggiunta gioco e copie;
8. nuovo prestito;
9. cambio gioco;
10. restituzione finale;
11. statistiche;
12. chiusura e riapertura;
13. persistenza di `config.ini`;
14. persistenza del database.

## Attenzione importante

La prima build serve anche a capire dove la versione PyInstaller salva:

```text
config.ini
database SQLite
```

Prima di considerare definitivo il packaging dobbiamo verificare questo comportamento.

---

# Aggiungere il PDF alla cartella Windows

Quando il PDF è definitivo:

```powershell
Copy-Item `
  ".\dist\LudoX-Guida-rapida.pdf" `
  ".\build\windows\LudoX\LudoX-Guida-rapida.pdf"
```

A quel punto la cartella:

```text
build\windows\LudoX\
```

può diventare lo ZIP Windows della release.

Non creare ancora automaticamente lo ZIP finché non hai verificato l'EXE.
