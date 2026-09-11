# Moduli LudoX

> **STATUS: APPROVED SPECIFICATION — READ ONLY**
>
> **IMPLEMENTATION: NOT IMPLEMENTED**
>
> Questo documento è una specifica approvata di LudoX. Durante
> l'implementazione non deve essere modificato, salvo richiesta esplicita
> dell'utente. I marker `TBD` e `QUESTION` restano decisioni aperte e non
> autorizzano Codex a scegliere autonomamente una soluzione.



## Definizione

Un modulo è una funzionalità fornita da LudoX che può essere abilitata per uno specifico Event.

L'Event funge da contenitore e abilita i moduli; non vengono create definizioni personalizzate di modulo da parte dell'utente.

## Moduli confermati

I moduli attualmente confermati nel modello sono:

- `game_library` — **Prestiti Ludoteca** nell'interfaccia italiana e **Game Library** nell'interfaccia inglese; gestisce la ludoteca dell'evento e i relativi prestiti;
- `activities` — **Attività** nell'interfaccia italiana e **Activities** nell'interfaccia inglese.

Gli identificatori tecnici sono stabili e indipendenti dalla lingua mostrata all'utente. I nomi visualizzati vengono tradotti tramite il sistema i18n.

Il possibile modulo Accoglienza/Iscrizioni rimane un'area futura ancora da formalizzare e non fa parte delle decisioni consolidate di questo documento.

## Abilitazione

Un modulo può essere abilitato:

- durante la creazione dell'Event;
- in un momento successivo.

L'abilitazione crea o rende disponibile il contesto necessario al modulo per quell'Event.

## Configurazione

Ogni configurazione operativa del modulo è **event-specific**.

Esempio per `game_library` / Prestiti Ludoteca:

```text
AMIGO
└── Prestiti Ludoteca
    ├── numero massimo di slot
    └── modalità operativa
```

La stessa Organization può quindi usare configurazioni differenti in eventi differenti.

Le configurazioni dei moduli non devono essere salvate come impostazioni globali nel `config.ini` della postazione.

## Disabilitazione

Un modulo può essere disabilitato senza cancellarne automaticamente i dati.

Ogni modulo può imporre propri vincoli di sicurezza prima della disabilitazione.

Per `game_library`, la disabilitazione non è consentita mentre esistono sessioni o prestiti aperti.

- TBD: Definire il comportamento di una futura operazione amministrativa di chiusura forzata del modulo Prestiti Ludoteca.

## Isolamento dei dati

I dati dei moduli appartengono all'Event.

Statistiche, ricerche e operazioni normali devono quindi essere eseguite sempre nel contesto dell'Event corrente e non devono mescolare automaticamente dati di eventi differenti.

Eventuali analisi aggregate tra eventi saranno funzionalità esplicite di livello superiore e non il comportamento predefinito dei moduli.
