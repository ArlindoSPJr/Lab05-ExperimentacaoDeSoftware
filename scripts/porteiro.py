"""Porteiro da coleta: decide se esta execução do workflow deve medir (issue #10).

O workflow é disparado várias vezes por horário: o schedule do GitHub a cada 10 min
na primeira hora de cada horário, mais os agendadores externos (docs/agendador.md).
Só a primeira tentativa que chega dentro da janela de tolerância mede. As demais
saem sem chamar a PSI, e assim a cadência de 1 execução por horário (docs/etica.md)
continua valendo.

Um horário conta como coletado quando data/raw/<data_brt>_BRT.csv já tem uma linha
sem erro com o mesmo cron, gatilho de coleta e início dentro da tolerância. Se uma
execução falhou inteira, a tentativa seguinte mede de novo.

Uso no workflow: python scripts/porteiro.py --raw data/raw
Escreve COLETAR=true|false e CRON=<cron nominal> em $GITHUB_ENV (ou na saída padrão).
"""
from __future__ import annotations

import argparse
import csv
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

BRT = timezone(timedelta(hours=-3))
# Cron nominal (UTC, como no desenho) -> horário BRT de início.
HORARIOS = {"7 23 * * *": (20, 7), "7 1 * * *": (22, 7), "7 6 * * *": (3, 7), "7 8 * * *": (5, 7)}
ANTES = timedelta(minutes=5)
DEPOIS = timedelta(minutes=60)
GATILHOS_DE_COLETA = {"schedule", "agendador"}


def _nominal(agora_utc: datetime, cron: str) -> datetime:
    hora, minuto = HORARIOS[cron]
    return agora_utc.astimezone(BRT).replace(hour=hora, minute=minuto, second=0, microsecond=0)


def slot_atual(agora_utc: datetime) -> str | None:
    """Devolve o cron nominal cujo horário de hoje (BRT) aceita este instante, ou None."""
    for cron in HORARIOS:
        nominal = _nominal(agora_utc, cron)
        if nominal - ANTES <= agora_utc <= nominal + DEPOIS:
            return cron
    return None


def decidir(agora_utc: datetime, raw_dir) -> tuple[bool, str]:
    """Devolve (coletar, cron). Coleta se há um horário aberto que ainda não foi medido."""
    cron = slot_atual(agora_utc)
    if cron is None:
        return False, ""
    nominal = _nominal(agora_utc, cron)
    caminho = Path(raw_dir) / f"{nominal.date().isoformat()}_BRT.csv"
    if not caminho.exists():
        return True, cron
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            if linha["cron"] != cron or linha["gatilho"] not in GATILHOS_DE_COLETA or linha["erro"]:
                continue
            inicio = datetime.fromisoformat(linha["ts_inicio_utc"])
            if nominal - ANTES <= inicio <= nominal + DEPOIS:
                return False, cron
    return True, cron


def main() -> int:
    parser = argparse.ArgumentParser(description="Decide se esta execução deve medir.")
    parser.add_argument("--raw", default="data/raw")
    args = parser.parse_args()

    agora = datetime.now(timezone.utc)
    coletar, cron = decidir(agora, args.raw)
    motivo = ("horário aberto e ainda não medido" if coletar
              else "fora da tolerância de todos os horários" if not cron
              else "horário já medido por outra tentativa")
    print(f"{agora.astimezone(BRT):%d/%m %H:%M} BRT -> coletar={coletar} cron='{cron}' ({motivo})")

    saida = os.environ.get("GITHUB_ENV")
    texto = f"COLETAR={'true' if coletar else 'false'}\nCRON={cron}\n"
    if saida:
        with open(saida, "a", encoding="utf-8") as arquivo:
            arquivo.write(texto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
