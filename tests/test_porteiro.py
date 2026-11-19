"""Testes do porteiro da coleta (issue #10). Nenhum teste acessa a rede."""
from __future__ import annotations

import csv
from datetime import datetime, timezone

from porteiro import decidir, slot_atual

COLUNAS = ["run_id", "gatilho", "cron", "ts_inicio_utc", "erro"]


def utc(texto: str) -> datetime:
    return datetime.fromisoformat(texto).replace(tzinfo=timezone.utc)


def gravar(pasta, data_brt, linhas):
    caminho = pasta / f"{data_brt}_BRT.csv"
    with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS)
        escritor.writeheader()
        for linha in linhas:
            escritor.writerow(linha)


def test_slot_atual_dentro_da_tolerancia():
    # 20h07 BRT = 23h07 UTC; até 60 min depois ainda vale.
    assert slot_atual(utc("2026-11-19T23:07:00")) == "7 23 * * *"
    assert slot_atual(utc("2026-11-20T00:05:00")) == "7 23 * * *"
    assert slot_atual(utc("2026-11-20T01:37:00")) == "7 1 * * *"
    assert slot_atual(utc("2026-11-20T06:07:00")) == "7 6 * * *"
    assert slot_atual(utc("2026-11-20T08:20:00")) == "7 8 * * *"
    # Até 5 min antes, para relógios um pouco adiantados.
    assert slot_atual(utc("2026-11-19T23:03:00")) == "7 23 * * *"


def test_slot_atual_fora_da_tolerancia():
    assert slot_atual(utc("2026-11-20T00:08:00")) is None  # 21h08, depois do pico-1
    assert slot_atual(utc("2026-11-20T04:04:00")) is None  # 01h04, o atraso de 18→19/11
    assert slot_atual(utc("2026-11-20T09:10:00")) is None  # 06h10, depois da madrugada-2
    assert slot_atual(utc("2026-11-19T15:00:00")) is None  # 12h, fora de qualquer horário


def test_decidir_coleta_quando_slot_vazio(tmp_path):
    assert decidir(utc("2026-11-19T23:17:00"), tmp_path) == (True, "7 23 * * *")


def test_decidir_pula_slot_ja_coletado(tmp_path):
    gravar(tmp_path, "2026-11-19", [
        {"run_id": "a", "gatilho": "schedule", "cron": "7 23 * * *",
         "ts_inicio_utc": "2026-11-19T23:08:10+00:00", "erro": ""},
    ])
    assert decidir(utc("2026-11-19T23:27:00"), tmp_path) == (False, "7 23 * * *")


def test_decidir_ignora_execucao_atrasada_do_mesmo_cron(tmp_path):
    # Em 19/11 o cron "7 23" rodou às 01h04 BRT. Isso não conta como o pico-1 de 19/11 às 20h07.
    gravar(tmp_path, "2026-11-19", [
        {"run_id": "x", "gatilho": "schedule", "cron": "7 23 * * *",
         "ts_inicio_utc": "2026-11-19T04:04:44+00:00", "erro": ""},
    ])
    assert decidir(utc("2026-11-19T23:07:00"), tmp_path) == (True, "7 23 * * *")


def test_decidir_repete_se_a_execucao_falhou_inteira(tmp_path):
    gravar(tmp_path, "2026-11-19", [
        {"run_id": "a", "gatilho": "agendador", "cron": "7 23 * * *",
         "ts_inicio_utc": "2026-11-19T23:07:30+00:00", "erro": "429"},
    ])
    assert decidir(utc("2026-11-19T23:27:00"), tmp_path) == (True, "7 23 * * *")


def test_decidir_ignora_manuais_e_fora_de_horario(tmp_path):
    gravar(tmp_path, "2026-11-19", [
        {"run_id": "t", "gatilho": "workflow_dispatch", "cron": "7 23 * * *",
         "ts_inicio_utc": "2026-11-19T23:07:30+00:00", "erro": ""},
    ])
    assert decidir(utc("2026-11-19T23:17:00"), tmp_path) == (True, "7 23 * * *")
    assert decidir(utc("2026-11-19T15:00:00"), tmp_path) == (False, "")


def test_decidir_madrugada_usa_o_arquivo_do_dia_seguinte(tmp_path):
    # 03h07 de 20/11 grava em 2026-11-20_BRT.csv; o pico de 19/11 não interfere.
    gravar(tmp_path, "2026-11-19", [
        {"run_id": "a", "gatilho": "agendador", "cron": "7 6 * * *",
         "ts_inicio_utc": "2026-11-19T06:07:30+00:00", "erro": ""},
    ])
    assert decidir(utc("2026-11-20T06:17:00"), tmp_path) == (True, "7 6 * * *")
