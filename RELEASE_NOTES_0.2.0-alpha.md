# LudoX 0.2.0-alpha

Questa alpha completa la Game Library V1 event-specific. Ogni Event può usare
la modalità tradizionale con token oppure identificare la singola scatola
tramite barcode/QR, senza registrare dati personali della persona che riceve il
gioco.

## Novità principali

- gestione di Organization ed Event nello stesso workspace;
- selezione esplicita dell'Event operativo da Home o Backoffice, con contesto
  sempre visibile e destinazione dell'importazione confermata;
- ludoteca, impostazioni, prestiti e report isolati per Event;
- identificatori di copia `external` o generati da LudoX;
- nuovo prestito, cambio e restituzione tramite scanner HID o tastiera;
- import/export CSV e XLSX con identificatori;
- migration sicura allo schema v4 con consenso, backup e rollback;
- guida rapida PDF inclusa nei pacchetti portable.

Il confronto completo con la release precedente è disponibile nel
[CHANGELOG](CHANGELOG.md).

## Download

- `LudoX-0.2.0-alpha-windows-x64.zip`
- `LudoX-0.2.0-alpha-linux-x64.tar.gz`
- `LudoX-Guida-rapida.pdf`

Estrai completamente il pacchetto della tua piattaforma e avvia `LudoX.exe`
su Windows oppure `./LudoX` su Linux. Python non è richiesto.

Le build alpha non sono firmate digitalmente; un avviso SmartScreen o analogo
può essere atteso. Scarica gli artefatti soltanto dalla release ufficiale.

## Aggiornamento da una versione precedente

1. conserva una copia manuale del database prima di iniziare;
2. avvia LudoX 0.2.0-alpha e seleziona il database esistente;
3. verifica le versioni mostrate nella richiesta di migration;
4. autorizza l'operazione: LudoX crea un ulteriore backup automatico;
5. dopo l'apertura controlla Organization, Event, ludoteca e storico.

Non aprire nuovamente con una versione precedente un database già migrato allo
schema v4.

## Verifica del candidato

- suite automatica Windows: 276 test superati;
- migrazione verificata da schema v0 e v3 a v4 con controllo d'integrità;
- smoke test manuali finali: vedere la checklist consegnata con il candidato.

## Limitazioni note dell'alpha

- scanner supportati in modalità HID/tastiera; la scansione da webcam non è
  inclusa;
- pacchetti non firmati;
- installer, aggiornamento automatico, macOS e architetture ARM non inclusi;
- prima dell'uso in un evento reale è raccomandata una prova completa con dati
  dimostrativi e backup verificato.
