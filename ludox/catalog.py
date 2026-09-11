# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Current catalog operations, without Tkinter or SQL.

Checks intentionally precede writes as in the original callbacks. Confirmation
of owner deactivation belongs to the UI; it can retry with explicit consent.
"""

from dataclasses import dataclass

from . import database as data

NomeDuplicato = data.NomeDuplicato


class NomeMancante(Exception):
    """A catalog name is empty after trimming."""


class ConfermaDisattivazione(Exception):
    """Owner still has copies; no write was performed."""


class GiocoInPrestito(Exception):
    """A game with open loans cannot be deactivated."""


class ProprietarioNonSelezionato(Exception):
    """No owner was selected for the quantity update."""


class QuantitaNonValida(Exception):
    """Quantity is not a nonnegative integer."""


class CopieInsufficienti(Exception):
    def __init__(self, fuori, nuovo_totale):
        self.fuori = fuori
        self.nuovo_totale = nuovo_totale
        super().__init__(
            f"Ci sono attualmente {fuori} copie di questo gioco in prestito.\n\n"
            f"Il totale non può essere ridotto a {nuovo_totale}."
        )


def _nome_valido(nome):
    nome = nome.strip()
    if not nome:
        raise NomeMancante()
    return nome


def aggiungi_proprietario(nome: str) -> int:
    return data.inserisci_proprietario(_nome_valido(nome))


def modifica_proprietario(proprietario_id: int, nome: str, attivo: bool,
                         *, conferma_disattivazione=False) -> None:
    nome = _nome_valido(nome)
    if not conferma_disattivazione and not attivo:
        if data.totale_copie_proprietario(proprietario_id) > 0:
            raise ConfermaDisattivazione()
    data.aggiorna_proprietario(proprietario_id, nome, 1 if attivo else 0)


def aggiungi_gioco(nome: str) -> int:
    return data.inserisci_gioco(_nome_valido(nome))


def modifica_gioco(gioco_id: int, nome: str, attivo: bool) -> None:
    nome = _nome_valido(nome)
    fuori = data.copie_in_prestito(gioco_id)
    if not attivo and fuori > 0:
        raise GiocoInPrestito()
    data.aggiorna_gioco(gioco_id, nome, 1 if attivo else 0)


def imposta_quantita(gioco_id: int, proprietario_id: int | None, valore: str) -> None:
    if proprietario_id is None:
        raise ProprietarioNonSelezionato()
    try:
        quantita = int(valore)
        if quantita < 0:
            raise ValueError
    except ValueError as exc:
        raise QuantitaNonValida() from exc
    nuovo_totale = data.copie_altri_proprietari(gioco_id, proprietario_id) + quantita
    fuori = data.copie_in_prestito(gioco_id)
    if nuovo_totale < fuori:
        raise CopieInsufficienti(fuori, nuovo_totale)
    data.aggiorna_quantita_copie(gioco_id, proprietario_id, quantita)


@dataclass(frozen=True)
class InventarioProprietario:
    righe: list[dict]
    totale_titoli: int
    totale_copie: int


def inventario_proprietario(proprietario_id: int) -> InventarioProprietario:
    righe = [dict(row) for row in data.giochi_per_proprietario(proprietario_id)]
    return InventarioProprietario(righe, len(righe), sum(r["copie_proprietario"] for r in righe))


def elenco_proprietari():
    return [dict(row) for row in data.elenco_proprietari()]


def proprietario_per_id(proprietario_id):
    row = data.proprietario_per_id(proprietario_id)
    return dict(row) if row is not None else None


def totale_copie_proprietario(proprietario_id):
    return data.totale_copie_proprietario(proprietario_id)


def elenco_giochi_backoffice():
    return [dict(row) for row in data.elenco_giochi_backoffice()]


def gioco_per_id(gioco_id):
    row = data.gioco_per_id(gioco_id)
    return dict(row) if row is not None else None


def copie_per_proprietario_del_gioco(gioco_id):
    return [dict(row) for row in data.copie_per_proprietario_del_gioco(gioco_id)]


def riepilogo_proprietari_gioco(gioco_id):
    return data.riepilogo_proprietari_gioco(gioco_id)


def copie_in_prestito(gioco_id):
    return data.copie_in_prestito(gioco_id)
