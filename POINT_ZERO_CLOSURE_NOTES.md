# Point-zero closure notes

Materiale di lavoro per il successivo aggiornamento delle issue GitHub.
Non è una specifica e non modifica lo stato delle issue.

## #1 — Define the event and module data model

Il modello concettuale Event/Module è consolidato in `ARCHITECTURE.md`,
`EVENTS.md`, `MODULES.md`, `LENDING.md` e `DATABASE.md`.

Gerarchia target:

```text
Organization
└── Event
    └── Module
        ├── game_library
        └── activities
```

L'implementazione resta nelle issue dedicate (#15, #5, #6, #7).

## #10 — Define organization and tenancy model

Il modello Organization è consolidato in `ORGANIZATIONS.md` e
`ARCHITECTURE.md`.

Il database può contenere più Organization; ogni Event appartiene a una sola
Organization; il contesto attivo è client/session-specific; una Organization
viene normalmente disattivata invece di essere eliminata.

L'implementazione resta tracciata dalla #15.

## #13 — Define configuration scopes

Gli scope sono consolidati in `docs/CONFIGURATION.md`.

La configurazione è distinta tra:

- postazione/client;
- Organization;
- Event;
- singolo modulo.

In particolare `max_slots` appartiene al modulo `game_library` dello
specifico Event e non alla configurazione generale della postazione.
