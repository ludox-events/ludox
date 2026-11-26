# Changelog

Le modifiche rilevanti di LudoX sono documentate in questo file.

Il formato segue [Keep a Changelog](https://keepachangelog.com/it/1.1.0/) e il
progetto usa versioni compatibili con il versionamento semantico durante la
fase alpha.

## [0.2.0-alpha] - 2026-11-26

### Aggiunto

- Organization, Event e moduli event-specific con selezione del contesto
  operativo della postazione.
- Ludoteche separate per Event, copie fisiche individuali e owner label.
- Modalità di prestito `copy_identifier` alternativa alla modalità token.
- Gestione di identificatori `external` e `ludox`, generazione di codici
  `LX-C-...` ed export QR in PNG.
- Nuovo prestito, cambio gioco e restituzione finale tramite scanner HID o
  input manuale con Invio.
- Import/export CSV e XLSX event-specific, incluse copie identificate e relativo
  round-trip.
- Storico, statistiche e report event-specific con dettagli della copia quando
  disponibili.
- Schema SQLite v4 e migration versionate con consenso, backup e rollback.
- Guida rapida utente mantenibile in Markdown e generabile in PDF.
- Script riproducibili per pacchetti portable Windows x64 e Linux x64.

### Modificato

- La configurazione locale contiene soltanto impostazioni della postazione;
  Organization, Event e impostazioni della ludoteca rispettano il proprio
  scope.
- Il numero di slot e la modalità di identificazione sono configurati per
  singolo Event.
- Le schermate Backoffice interessate sono scorrevoli e gli Event usano picker
  separati per data e ora.
- Il Backoffice mostra sempre il contesto Organization/Event, distingue la riga
  in modifica dall'Event operativo e richiede conferma prima di attivare un
  Event appena creato.
- L'anteprima di importazione mostra Organization ed Event di destinazione e
  mantiene tale destinazione fino all'applicazione.

### Compatibilità

- I database legacy e gli schemi v1-v3 possono essere migrati allo schema v4.
- Prima di aggiornare un database esistente LudoX richiede conferma e crea un
  backup completo accanto all'originale.
- I CSV legacy a tre colonne restano importabili.

## [0.1.1-alpha]

- Prima release alpha con script locali di build e guida rapida.

## [0.1.0-alpha]

- Prima release alpha pubblicata del prototipo LudoX.

[0.2.0-alpha]: https://github.com/ludox-events/ludox/compare/0.1.1-alpha...0.2.0-alpha
[0.1.1-alpha]: https://github.com/ludox-events/ludox/releases/tag/0.1.1-alpha
[0.1.0-alpha]: https://github.com/ludox-events/ludox/releases/tag/0.1.0-alpha
