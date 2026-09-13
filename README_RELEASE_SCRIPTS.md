# LudoX - script release locale

Copia questi file nella root del repository mantenendo `scripts/`.

Gli script leggono automaticamente la versione dal file `VERSION`.

## Solo PDF

```cmd
scripts\build_pdf.cmd
```

## Solo Windows ZIP

```cmd
scripts\build_windows.cmd
```

## Solo Linux tar.gz

Da WSL:

```bash
cd /mnt/c/Users/gurus/gitrepo/LudoX
bash scripts/build_linux.sh
```

## Tutti e tre

Da terminale Windows:

```cmd
scripts\build_release.cmd
```

Output attesi:

```text
dist/LudoX-Guida-rapida.pdf
dist/windows/LudoX-<VERSION>-windows-x64.zip
dist/linux/LudoX-<VERSION>-linux-x64.tar.gz
```

Prerequisiti:
- `.venv` su Windows
- `.venv-linux` su WSL/Linux
- `requirements-docs.txt`
- `scripts/build_user_guide.py`

Prima di pubblicare una release, prova manualmente gli eseguibili Windows e Linux.

Gli intermedi sono in `build/user-guide/`, `build/windows/` e `build/linux/`.
Le cartelle applicative sono `build/windows/LudoX/` e `build/linux/LudoX/`;
work file e spec di PyInstaller restano sotto la rispettiva piattaforma.
`dist/` contiene solo artifact finali. Il PDF, se presente, viene incluso in entrambi gli archivi.
