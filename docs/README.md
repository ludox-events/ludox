# Documentazione LudoX

Questa cartella raccoglie la documentazione tecnica e funzionale di LudoX.

L'obiettivo è separare chiaramente:

- ciò che LudoX **è e deve garantire**;
- le decisioni architetturali già approvate;
- le parti ancora da definire;
- i dettagli implementativi del database e dei singoli moduli.

Le GitHub Issues conservano la roadmap, le discussioni e la storia delle decisioni. I documenti in `docs/` rappresentano invece la descrizione corrente del progetto quando una decisione è sufficientemente consolidata.

## Documenti

| Documento | Stato | Contenuto |
| --- | --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Draft consolidato | Architettura generale, contesti client, offline-first e futura evoluzione client/server |
| [ORGANIZATIONS.md](ORGANIZATIONS.md) | Draft consolidato | Modello Organization e selezione dell'organizzazione attiva |
| [EVENTS.md](EVENTS.md) | Draft consolidato | Modello Event, stati, selezione e ciclo di vita |
| [MODULES.md](MODULES.md) | Draft | Regole comuni dei moduli event-specific |
| [LENDING.md](LENDING.md) | Draft consolidato | Modello funzionale Prestiti Ludoteca / Game Library |
| [DATABASE.md](DATABASE.md) | Draft iniziale | Principi del database e base per lo schema v1 |
| [OPERATION.md](OPERATION.md) | Corrente | Procedura operativa della modalità token attualmente disponibile |

Gli stati indicano la maturità della documentazione, non necessariamente lo stato di implementazione nel software.

## Marker per decisioni e attività aperte

LudoX utilizza quattro marker ricercabili a livello di progetto:

- `TBD` — decisione progettuale ancora da prendere;
- `QUESTION` — domanda aperta da discutere;
- `TODO` — attività già definita ma ancora da eseguire;
- `FIXME` — comportamento o documentazione noti come errati e da correggere.

Nei file Markdown i marker vengono scritti come elementi di elenco, ad esempio:

```text
- TBD: Definire il comportamento in caso di conflitto durante l'importazione.
```

Quando la decisione viene presa, il marker deve essere rimosso e il contenuto trasformato in documentazione normale.

### Visual Studio Code

Il repository può usare l'estensione **Better Todo Tree** per raccogliere i marker in una vista unica del workspace.

La configurazione proposta è inclusa in:

- `.vscode/extensions.json` — suggerisce l'estensione;
- `.vscode/settings.json` — abilita `TODO`, `TBD`, `FIXME` e `QUESTION`, compreso il formato a elenco Markdown.

È sempre possibile usare anche la ricerca globale di VS Code con una regex equivalente, per esempio:

```regex
\b(TBD|TODO|FIXME|QUESTION):
```

## Regola di manutenzione

Una decisione non deve essere duplicata in più documenti se non necessario. Il documento più specifico è la fonte principale e gli altri documenti dovrebbero rimandare ad esso.

In particolare:

- architettura generale → `ARCHITECTURE.md`;
- organizzazioni → `ORGANIZATIONS.md`;
- eventi → `EVENTS.md`;
- comportamento comune dei moduli → `MODULES.md`;
- prestiti → `LENDING.md`;
- schema fisico e migrazioni → `DATABASE.md`;
- procedura per chi opera al banco → `OPERATION.md`.


## Priorità di implementazione

La documentazione architetturale descrive il modello target, ma non determina automaticamente l'ordine delle modifiche al software.

Le funzionalità possono essere implementate in modo incrementale, privilegiando interventi utili e a basso rischio prima della migrazione allo schema database v1.

Una priorità candidata è l'**export/backup del database corrente**, utile anche come base di sicurezza prima delle future migration.

Va mantenuta distinta la differenza tra:

- **export/backup del database** — copia completa del workspace SQLite;
- **export dei dati di un modulo** — per esempio esportazione della ludoteca in CSV/XLSX per riutilizzo o scambio.

## Specifiche approvate e Codex

Le specifiche approvate contengono l'intestazione:

```text
STATUS: APPROVED SPECIFICATION — READ ONLY
```

Lo stato dell'implementazione viene indicato separatamente:

```text
IMPLEMENTATION: NOT IMPLEMENTED
IMPLEMENTATION: PARTIALLY IMPLEMENTED
IMPLEMENTATION: IMPLEMENTED
```

La presenza di `TBD` o `QUESTION` non rende modificabile il documento e non
autorizza Codex a prendere autonomamente la decisione mancante.

Le regole operative complete per Codex sono definite nel file
[`../AGENTS.md`](../AGENTS.md).

### Uso consigliato di Codex per una feature

Per una normale implementazione è sufficiente dare a Codex un prompt simile:

```text
Implementa <feature / issue>.

Prima leggi AGENTS.md e le specifiche pertinenti in docs/.
Le specifiche con STATUS: APPROVED SPECIFICATION — READ ONLY non devono
essere modificate.

Mantieni la modifica limitata alla feature richiesta e non implementare
architettura futura non necessaria.

Se trovi un conflitto con una specifica approvata, fermati e spiegami il
conflitto prima di modificare codice o documentazione.

Alla fine indicami:
- file modificati;
- test eseguiti;
- eventuali conflitti o decisioni rimaste aperte.
```

Per modificare intenzionalmente una specifica, la richiesta deve invece
dirlo esplicitamente, per esempio:

```text
Aggiorna docs/LENDING.md per recepire questa decisione: <decisione>.
Non implementare ancora il codice.
```

In questo modo progettazione e implementazione restano due attività separate.
