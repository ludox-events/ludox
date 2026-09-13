# Migrazioni database LudoX

> **STATUS: APPROVED SPECIFICATION — READ ONLY**
>
> **IMPLEMENTATION: IMPLEMENTED**
>
> Questo documento definisce il comportamento approvato delle migration del
> database LudoX. Durante l'implementazione non deve essere modificato salvo
> richiesta esplicita dell'utente.

## Scopo

LudoX utilizza migration versionate per portare un database SQLite da una
versione dello schema a quella richiesta dalla versione corrente del software.

La priorità è preservare i dati e rendere il comportamento comprensibile anche
a una persona non tecnica.

Il principio fondamentale è:

> LudoX non opera su un database con schema diverso da quello richiesto dalla
> versione corrente dell'applicazione.

Se è necessaria una migration di un database esistente, l'avvio può proseguire
solo dopo autorizzazione esplicita, backup completato e migration conclusa con
successo.

## Versione dello schema

La versione dello schema SQLite viene registrata tramite:

```sql
PRAGMA user_version;
```

La numerazione è indipendente dalla versione dell'applicazione.

Schema attualmente pianificato:

```text
v0 = schema legacy / sperimentale
v1 = Organizations
v2 = Events + Event Modules
v3+ = successive modifiche strutturali
```

Ogni numero identifica uno stato preciso e completo dello schema.

## Classificazione all'apertura

Prima di inizializzare i servizi applicativi, LudoX deve ispezionare il
database e distinguere almeno questi casi:

```text
database nuovo/vuoto
schema corrente
schema precedente
schema futuro/non supportato
```

### Database nuovo o vuoto

Un database nuovo o realmente vuoto non contiene dati utente da preservare.
Può quindi essere inizializzato direttamente allo schema corrente senza
richiedere conferma di migration e senza creare un backup preventivo.

### Schema corrente

Se `user_version` corrisponde allo schema richiesto dall'applicazione, LudoX
prosegue normalmente senza mostrare richieste relative alle migration.

### Schema precedente

Se il database esistente usa una versione precedente, LudoX non deve eseguire
la migration automaticamente.

Deve mostrare una richiesta comprensibile che indichi almeno:

- versione attuale del database;
- versione richiesta;
- necessità di aggiornare il database;
- creazione preventiva di una copia di backup.

La migration parte soltanto dopo conferma esplicita dell'utente.

Se l'utente annulla o rifiuta, LudoX termina l'avvio e si chiude senza
modificare il database.

### Schema futuro o non supportato

Se il database ha una versione superiore a quella supportata dal software,
LudoX non tenta downgrade o adattamenti automatici.

Mostra un errore comprensibile e termina l'avvio senza usare operativamente il
database.

## Backup obbligatorio

Prima di qualsiasi migration di un database esistente deve essere creata una
copia completa del database.

Il backup è obbligatorio anche per migration considerate semplici o additive.
Non è quindi una proprietà opzionale della singola migration.

Il backup deve essere:

- creato prima di qualsiasi modifica allo schema;
- automatico;
- facilmente riconoscibile;
- salvato, per impostazione predefinita, accanto al database originale;
- creato con un nome che non sovrascriva file esistenti.

Formato consigliato:

```text
<nome>.backup-v<origine>-to-v<destinazione>-YYYYMMDD-HHMMSS.db
```

Esempio:

```text
ludox.backup-v0-to-v1-20260912-175900.db
```

Se il backup non può essere creato, la migration non parte e l'applicazione
termina l'avvio.

## Sequenza di migration

Le migration vengono applicate in ordine crescente senza saltare versioni.

Esempio:

```text
v0 → v1 → v2 → v3
```

Se manca uno dei passaggi richiesti, l'aggiornamento deve fallire prima di
modificare il database.

Per una sequenza composta da più migration pendenti viene creato un solo
backup iniziale, prima dell'intera sequenza.

## Transazione e rollback

La sequenza di migration deve essere eseguita in transazione.

Il valore `PRAGMA user_version` viene aggiornato insieme allo schema e non deve
rimanere avanzato se l'operazione fallisce.

Se una migration genera un errore:

```text
migration fallita
→ rollback
→ database originale non aggiornato
→ backup conservato
→ messaggio di errore
→ chiusura di LudoX
```

L'applicazione non deve tentare di proseguire usando uno schema parzialmente
aggiornato o incompatibile.

## Flusso di avvio

Il comportamento target è:

```text
Avvio LudoX
    ↓
Ispezione database
    ↓
┌────────────────────────────────────────────┐
│ Database nuovo/vuoto                       │
│ → inizializza schema corrente              │
│ → avvio normale                            │
├────────────────────────────────────────────┤
│ Schema corrente                            │
│ → avvio normale                            │
├────────────────────────────────────────────┤
│ Schema precedente                          │
│ → richiesta autorizzazione                 │
│    ├─ annulla → chiusura                   │
│    └─ autorizza                            │
│       → backup                             │
│       → migration                          │
│       → successo → avvio normale           │
│       → errore → rollback + chiusura       │
├────────────────────────────────────────────┤
│ Schema futuro/non supportato               │
│ → errore                                   │
│ → chiusura                                 │
└────────────────────────────────────────────┘
```

## Separazione tra UI e migration runner

La logica tecnica delle migration non deve dipendere da Tkinter.

Il livello applicativo/UI gestisce:

- messaggio all'utente;
- richiesta di conferma;
- visualizzazione dell'esito o dell'errore;
- decisione di proseguire o terminare l'applicazione.

Il migration runner gestisce:

- inspection dello schema;
- determinazione delle migration necessarie;
- backup;
- esecuzione sequenziale;
- transazione e rollback;
- aggiornamento di `user_version`.

Questo mantiene la logica testabile senza interfaccia grafica.

## Aggiungere una nuova migration

Ogni modifica strutturale al database deve:

1. incrementare la versione dello schema di una unità;
2. definire il passaggio dalla versione precedente alla nuova;
3. preservare i dati che devono rimanere disponibili;
4. essere eseguibile in modo deterministico;
5. avere test automatici dedicati;
6. essere inclusa nella sequenza del migration runner.

Non devono esistere due strutture differenti con lo stesso `user_version`.

## Test minimi

Ogni evoluzione del sistema di migration deve coprire almeno:

- database nuovo/vuoto;
- database già corrente;
- database legacy o precedente;
- sequenza di migration riuscita;
- rollback su errore;
- preservazione dei dati esistenti;
- backup creato prima della migration;
- errore di backup senza modifica del database;
- rifiuto dell'utente senza modifica del database;
- database con versione futura rifiutato;
- assenza di una migration intermedia;
- impossibilità di proseguire l'avvio con schema incompatibile.

Le verifiche visibili all'utente sono raccolte anche in
[MANUAL_TESTS.md](MANUAL_TESTS.md).

## Riferimenti

- [DATABASE.md](DATABASE.md) — regole generali dello schema dati;
- issue #12 — infrastruttura di versionamento e migration runner;
- issue #19 — autorizzazione esplicita e backup obbligatorio prima delle migration.
