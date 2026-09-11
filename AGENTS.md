# LudoX - istruzioni per Codex

## Specifiche

La cartella `docs/specs/` contiene le specifiche funzionali e architetturali
approvate del progetto.

Le specifiche sono autoritative.

NON modificare, riscrivere, semplificare o reinterpretare i file presenti
in `docs/specs/` durante un'attività di implementazione, salvo richiesta
esplicita dell'utente.

Se una specifica:
- è ambigua;
- è incoerente con un'altra specifica;
- non è implementabile con l'architettura attuale;
- richiede una modifica non prevista allo schema del database;
- sembra contenere un errore;

NON correggerla autonomamente.

Segnala il problema all'utente e spiega quale decisione è necessaria.

## Implementazione

Quando viene richiesto di implementare una feature:
1. leggere prima la relativa specifica;
2. verificare il codice esistente;
3. implementare il comportamento descritto;
4. evitare modifiche non necessarie fuori dallo scope della feature;
5. eseguire i test pertinenti.

Non aggiungere funzionalità non richieste anche se sembrano miglioramenti.

## Database

Non modificare lo schema del database salvo quando:
- è espressamente previsto dalla specifica; oppure
- l'utente lo richiede esplicitamente.

Non introdurre migrazioni o cambiamenti incompatibili autonomamente.

## Git

- Non creare commit salvo richiesta esplicita.
- Non effettuare push.
- Non creare branch salvo richiesta esplicita.
- Lasciare le modifiche nel working tree per la revisione dell'utente.

## Modifiche alle specifiche

Codice e specifiche sono due attività distinte.

Durante un'attività di implementazione:
- è consentito modificare il codice;
- non è consentito modificare le specifiche.

Se l'implementazione richiede una modifica delle specifiche, fermarsi e
segnalare la questione all'utente.