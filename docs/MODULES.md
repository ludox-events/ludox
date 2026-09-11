# Moduli LudoX

**Stato:** draft.

## Definizione

Un modulo è una funzionalità fornita da LudoX che può essere abilitata per uno specifico Event.

L'Event funge da contenitore e abilita i moduli; non vengono create definizioni personalizzate di modulo da parte dell'utente.

## Moduli confermati

I moduli attualmente confermati nel modello sono:

- **Prestiti** — gestione della ludoteca e dei prestiti di giochi;
- **Attività** — gestione delle attività previste durante l'evento.

Il nome mostrato nell'interfaccia deve poter essere tradotto tramite il sistema i18n.

- TBD: Definire gli identificatori tecnici stabili dei moduli nello schema e nel codice.

Il possibile modulo Accoglienza/Iscrizioni rimane un'area futura ancora da formalizzare e non fa parte delle decisioni consolidate di questo documento.

## Abilitazione

Un modulo può essere abilitato:

- durante la creazione dell'Event;
- in un momento successivo.

L'abilitazione crea o rende disponibile il contesto necessario al modulo per quell'Event.

## Configurazione

Ogni configurazione operativa del modulo è **event-specific**.

Esempio per Prestiti:

```text
AMIGO
└── Prestiti
    ├── numero massimo di slot
    └── modalità operativa
```

La stessa Organization può quindi usare configurazioni differenti in eventi differenti.

Le configurazioni dei moduli non devono essere salvate come impostazioni globali nel `config.ini` della postazione.

## Disabilitazione

Un modulo può essere disabilitato senza cancellarne automaticamente i dati.

Ogni modulo può imporre propri vincoli di sicurezza prima della disabilitazione.

Per Prestiti, la disabilitazione non è consentita mentre esistono sessioni o prestiti aperti.

- TBD: Definire il comportamento di una futura operazione amministrativa di chiusura forzata del modulo Prestiti.

## Isolamento dei dati

I dati dei moduli appartengono all'Event.

Statistiche, ricerche e operazioni normali devono quindi essere eseguite sempre nel contesto dell'Event corrente e non devono mescolare automaticamente dati di eventi differenti.

Eventuali analisi aggregate tra eventi saranno funzionalità esplicite di livello superiore e non il comportamento predefinito dei moduli.
