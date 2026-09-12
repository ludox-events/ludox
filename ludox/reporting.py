# Copyright (C) 2026 Matteo Sassi
# SPDX-License-Identifier: AGPL-3.0-only

"""Statistics and reporting operations independent of Tkinter."""

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from statistics import median, pstdev

from . import database as data


@dataclass(frozen=True)
class StatistichePeriodo:
    inizio: datetime
    fine: datetime
    minuti_bucket: int
    prestiti: int
    documenti: int
    punti: list[dict]


@dataclass(frozen=True)
class Storico:
    totale: int
    attivi: int
    righe: list[dict]


@dataclass(frozen=True)
class ReportDocumenti:
    inizio: datetime
    fine_esclusiva: datetime
    righe: list[dict]
    totale_documenti: int
    totale_prestiti: int
    prestiti_per_persona: list[int]
    media_prestiti_persona: float
    mediana_prestiti_persona: float
    dev_std_prestiti_persona: float
    persone_almeno_3: int
    percentuale_almeno_2: float
    percentuale_almeno_3: float
    permanenza_mediana_secondi: float | None
    durata_mediana_prestito_secondi: float | None


@dataclass(frozen=True)
class ReportUtilizzo:
    inizio: datetime
    fine_esclusiva: datetime
    righe: list[dict]
    totale_titoli: int
    totale_prestiti: int
    prestiti_per_titolo: list[int]
    media_prestiti_titolo: float
    mediana_prestiti_titolo: float
    dev_std_prestiti_titolo: float
    titoli_utilizzati: int
    percentuale_titoli_utilizzati: float
    durata_mediana_prestito_secondi: float | None
    tempo_totale_fuori_secondi: float


def arrotonda_giu_bucket(dt, minuti_bucket):
    mezzanotte = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    secondi = int((dt - mezzanotte).total_seconds())
    ampiezza = minuti_bucket * 60
    return mezzanotte + timedelta(seconds=secondi // ampiezza * ampiezza)


def arrotonda_su_bucket(dt, minuti_bucket):
    arrotondato = arrotonda_giu_bucket(dt, minuti_bucket)
    return arrotondato if dt == arrotondato else arrotondato + timedelta(minutes=minuti_bucket)


def intervallo_statistiche(riferimento, ore, minuti_bucket):
    return (
        arrotonda_giu_bucket(riferimento - timedelta(hours=ore), minuti_bucket),
        arrotonda_su_bucket(riferimento, minuti_bucket),
    )


def statistiche_periodo(riferimento, ore, minuti_bucket):
    inizio, fine = intervallo_statistiche(riferimento, ore, minuti_bucket)
    inizio_iso = inizio.isoformat(timespec="seconds")
    fine_iso = fine.isoformat(timespec="seconds")
    prestiti, documenti = data.conta_attivita_periodo(inizio_iso, fine_iso)
    righe_prestiti, righe_documenti = data.timestamp_attivita_periodo(inizio_iso, fine_iso)
    delta = timedelta(minutes=minuti_bucket)
    punti = []
    corrente = inizio
    while corrente < fine:
        punti.append({"inizio": corrente, "fine": corrente + delta,
                      "prestiti": 0, "documenti": 0})
        corrente += delta
    secondi_bucket = delta.total_seconds()
    for righe, campo, contatore in (
        (righe_prestiti, "uscita", "prestiti"),
        (righe_documenti, "ingresso", "documenti"),
    ):
        for row in righe:
            try:
                indice = int((datetime.fromisoformat(row[campo]) - inizio).total_seconds()
                             // secondi_bucket)
                if 0 <= indice < len(punti):
                    punti[indice][contatore] += 1
            except (ValueError, TypeError):
                continue
    return StatistichePeriodo(inizio, fine, minuti_bucket, prestiti, documenti, punti)


def storico_prestiti():
    totale, attivi, righe = data.storico_prestiti()
    risultato = []
    for row in righe:
        voce = dict(row)
        voce["uscita_testo"] = data.formatta_data_ora(row["uscita"])
        voce["rientro_testo"] = data.formatta_data_ora(row["rientro"])
        risultato.append(voce)
    return Storico(totale, attivi, risultato)


def storico_documenti():
    totale, attivi, righe = data.storico_documenti()
    risultato = []
    for row in righe:
        voce = dict(row)
        voce["ingresso_testo"] = data.formatta_data_ora(row["ingresso"])
        voce["uscita_testo"] = data.formatta_data_ora(row["uscita"])
        risultato.append(voce)
    return Storico(totale, attivi, risultato)


def formatta_durata(secondi):
    if secondi is None:
        return "—"
    secondi = max(0, int(round(secondi)))
    ore, resto = divmod(secondi, 3600)
    minuti, _ = divmod(resto, 60)
    return f"{ore}h {minuti:02d}m" if ore > 0 else f"{minuti}m"


def _periodo_giorni(data_inizio, data_fine):
    inizio = data_inizio.replace(hour=0, minute=0, second=0, microsecond=0)
    fine = data_fine.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return inizio, fine


def report_documenti(data_inizio, data_fine, *, ordina_per="ingresso",
                      ordine_desc=True, adesso=None):
    inizio, fine = _periodo_giorni(data_inizio, data_fine)
    documenti = data.documenti_ingressi_periodo(
        inizio.isoformat(timespec="seconds"), fine.isoformat(timespec="seconds")
    )
    prestiti_per_documento = {}
    for row in data.prestiti_per_documenti([row["id"] for row in documenti]):
        prestiti_per_documento.setdefault(row["documento_id"], []).append(row)
    adesso = adesso or datetime.now()
    righe = []
    tutte_durate = []
    for documento in documenti:
        try:
            ingresso_dt = datetime.fromisoformat(documento["ingresso"])
        except (ValueError, TypeError):
            continue
        try:
            uscita_dt = (datetime.fromisoformat(documento["uscita"])
                         if documento["uscita"] else None)
        except (ValueError, TypeError):
            uscita_dt = None
        permanenza = max(0, ((uscita_dt if uscita_dt is not None else adesso)
                            - ingresso_dt).total_seconds())
        prestiti = prestiti_per_documento.get(documento["id"], [])
        durate = []
        for prestito in prestiti:
            if not prestito["rientro"]:
                continue
            try:
                durata = (datetime.fromisoformat(prestito["rientro"])
                          - datetime.fromisoformat(prestito["uscita"])).total_seconds()
                if durata >= 0:
                    durate.append(durata)
            except (ValueError, TypeError):
                continue
        tutte_durate.extend(durate)
        media = sum(durate) / len(durate) if durate else None
        righe.append({
            "documento_id": documento["id"], "token": documento["token"],
            "ingresso_dt": ingresso_dt, "ingresso": data.formatta_data_ora(documento["ingresso"]),
            "uscita": data.formatta_data_ora(documento["uscita"]), "prestiti": len(prestiti),
            "tempo_documento_secondi": permanenza, "tempo_documento": formatta_durata(permanenza),
            "media_partita_secondi": media, "media_partita": formatta_durata(media),
            "aperto": documento["uscita"] is None,
        })
    def chiave(row):
        if ordina_per == "prestiti": return row["prestiti"]
        if ordina_per == "tempo_documento_secondi": return row["tempo_documento_secondi"]
        if ordina_per == "media_partita_secondi":
            return -1 if row["media_partita_secondi"] is None else row["media_partita_secondi"]
        return row["ingresso_dt"]
    righe.sort(key=chiave, reverse=ordine_desc)
    conteggi = [row["prestiti"] for row in righe]
    permanenze = [row["tempo_documento_secondi"] for row in righe]
    totale_documenti = len(righe)
    totale_prestiti = sum(conteggi)
    almeno_2 = sum(1 for valore in conteggi if valore >= 2)
    almeno_3 = sum(1 for valore in conteggi if valore >= 3)
    return ReportDocumenti(
        inizio, fine, righe, totale_documenti, totale_prestiti, conteggi,
        totale_prestiti / totale_documenti if totale_documenti else 0,
        median(conteggi) if conteggi else 0, pstdev(conteggi) if conteggi else 0,
        almeno_3, almeno_2 / totale_documenti * 100 if totale_documenti else 0,
        almeno_3 / totale_documenti * 100 if totale_documenti else 0,
        median(permanenze) if permanenze else None,
        median(tutte_durate) if tutte_durate else None,
    )


def report_utilizzo(data_inizio, data_fine, *, proprietario_id=None,
                     escludi_tempo_zero=False, ordina_per="gioco", ordine_desc=False):
    inizio, fine = _periodo_giorni(data_inizio, data_fine)
    giochi = data.giochi_con_copie()
    proprietari = {}
    for row in data.proprietari_dei_giochi():
        proprietari.setdefault(row["gioco_id"], []).append({
            "id": row["proprietario_id"], "nome": row["proprietario_nome"],
            "quantita": row["quantita"],
        })
    prestiti = {}
    for row in data.prestiti_usciti_periodo(
        inizio.isoformat(timespec="seconds"), fine.isoformat(timespec="seconds")
    ):
        prestiti.setdefault(row["gioco_id"], []).append(row)
    righe = []
    for gioco in giochi:
        proprietari_gioco = proprietari.get(gioco["id"], [])
        if proprietario_id is not None and not any(
            p["id"] == proprietario_id for p in proprietari_gioco
        ):
            continue
        prestiti_gioco = prestiti.get(gioco["id"], [])
        durate = []
        for prestito in prestiti_gioco:
            if not prestito["rientro"]:
                continue
            try:
                durata = (datetime.fromisoformat(prestito["rientro"])
                          - datetime.fromisoformat(prestito["uscita"])).total_seconds()
                if durata >= 0:
                    durate.append(durata)
            except (ValueError, TypeError):
                continue
        totale = sum(durate)
        media = totale / len(durate) if durate else None
        deviazione = pstdev(durate) if durate else None
        righe.append({
            "gioco": gioco["nome"],
            "proprietari": ", ".join(f'{p["nome"]} ({p["quantita"]})'
                                      for p in proprietari_gioco) or "—",
            "copie_totali": gioco["copie_totali"], "prestiti": len(prestiti_gioco),
            "tempo_totale_secondi": totale, "tempo_totale": formatta_durata(totale),
            "media_secondi": media, "media": formatta_durata(media),
            "deviazione_secondi": deviazione, "deviazione": formatta_durata(deviazione),
            "durate_prestiti": durate,
        })
    if escludi_tempo_zero:
        righe = [row for row in righe if row["tempo_totale_secondi"] > 0]
    def chiave(row):
        if ordina_per == "prestiti": return row["prestiti"]
        if ordina_per == "tempo_totale_secondi": return row["tempo_totale_secondi"]
        if ordina_per == "media_secondi":
            return -1 if row["media_secondi"] is None else row["media_secondi"]
        return row["gioco"].casefold()
    righe.sort(key=chiave, reverse=ordine_desc)
    conteggi = [row["prestiti"] for row in righe]
    durate = [durata for row in righe for durata in row["durate_prestiti"]]
    totale_titoli = len(righe)
    totale_prestiti = sum(conteggi)
    utilizzati = sum(1 for valore in conteggi if valore > 0)
    return ReportUtilizzo(
        inizio, fine, righe, totale_titoli, totale_prestiti, conteggi,
        totale_prestiti / totale_titoli if totale_titoli else 0,
        median(conteggi) if conteggi else 0, pstdev(conteggi) if conteggi else 0,
        utilizzati, utilizzati / totale_titoli * 100 if totale_titoli else 0,
        median(durate) if durate else None,
        sum(row["tempo_totale_secondi"] for row in righe),
    )


def minuti_csv(secondi):
    return "" if secondi is None else f"{secondi / 60:.2f}".replace(".", ",")


def righe_csv_documenti(report, stato_aperto, stato_chiuso):
    return [[
        row["documento_id"], row["token"], row["ingresso"], row["uscita"],
        row["prestiti"], row["tempo_documento"], minuti_csv(row["tempo_documento_secondi"]),
        row["media_partita"], minuti_csv(row["media_partita_secondi"]),
        stato_aperto if row["aperto"] else stato_chiuso,
    ] for row in report.righe]


def righe_csv_utilizzo(report):
    return [[
        row["gioco"], row["proprietari"], row["copie_totali"], row["prestiti"],
        row["tempo_totale"], minuti_csv(row["tempo_totale_secondi"]),
        row["media"], minuti_csv(row["media_secondi"]),
        row["deviazione"], minuti_csv(row["deviazione_secondi"]),
    ] for row in report.righe]


def esporta_csv(percorso, intestazioni, righe):
    with Path(percorso).open("w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.writer(csvfile, delimiter=";")
        writer.writerow(intestazioni)
        writer.writerows(righe)
