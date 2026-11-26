"""Testes da validação da coleta (#B-7, issue #22). Nenhum teste acessa a rede."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from validate import TOTAL_ESPERADO, calendario, gravar_anomalias, secao_anomalias, validate

BRT = timezone(timedelta(hours=-3))
INICIO_BRT = {"7 23 * * *": (20, 7), "7 1 * * *": (22, 7), "7 6 * * *": (3, 7), "7 8 * * *": (5, 7)}


def execucao(inicio_utc: datetime, cron: str, gatilho: str = "agendador", n: int = 38,
             janela: str | None = None, data_brt: str | None = None, versao: str = "13.6.0") -> pd.DataFrame:
    """Uma execução sintética com n linhas, 30 s entre chamadas."""
    local = inicio_utc.astimezone(BRT)
    if data_brt is None:
        data_brt = (local.date() if local.hour >= 18 else local.date()).isoformat()
    if janela is None:
        janela = "pico" if local.hour >= 18 else "madrugada" if local.hour < 8 else "fora"
    run_id = inicio_utc.strftime("%Y%m%dT%H%M%SZ")
    linhas = []
    for i in range(n):
        linhas.append({
            "run_id": run_id, "gatilho": gatilho, "cron": cron,
            "ts_inicio_utc": inicio_utc.isoformat(),
            "ts_utc": (inicio_utc + timedelta(seconds=30 * i)).isoformat(),
            "data_brt": data_brt, "janela": janela, "posicao": i,
            "slot_id": f"s{i // 2}", "tipo": "categoria", "strategy": "mobile" if i % 2 else "desktop",
            "url_usada": f"https://www.mercadolivre.com.br/{i // 2}", "usou_reserva": False,
            "tentativas": 1, "erro": None, "bloqueada": False, "lcp_ms": 2000.0 + i,
            "lighthouse_version": versao,
        })
    return pd.DataFrame(linhas)


def inicio_nominal(data_brt: str, cron: str, atraso_min: int = 0) -> datetime:
    hora, minuto = INICIO_BRT[cron]
    local = datetime.fromisoformat(data_brt).replace(hour=hora, minute=minuto, tzinfo=BRT)
    return (local + timedelta(minutes=atraso_min)).astimezone(timezone.utc)


def coleta_completa() -> list[pd.DataFrame]:
    return [execucao(inicio_nominal(d, c), c) for d, c in calendario()]


def gravar(pasta, partes: list[pd.DataFrame]) -> None:
    df = pd.concat(partes, ignore_index=True)
    for data_brt, grupo in df.groupby("data_brt"):
        grupo.to_csv(pasta / f"{data_brt}_BRT.csv", index=False)


def tipos(anomalias) -> list[str]:
    return [a["tipo"] for a in anomalias]


def test_calendario_tem_28_pares():
    pares = calendario()
    assert len(pares) == 28 == len(set(pares))
    assert ("2026-11-18", "7 23 * * *") in pares and ("2026-11-25", "7 8 * * *") in pares
    assert ("2026-11-18", "7 6 * * *") not in pares


def test_validate_coleta_completa_fecha(tmp_path):
    gravar(tmp_path, coleta_completa())
    dataset, anomalias = validate(str(tmp_path))
    assert len(dataset) == TOTAL_ESPERADO
    assert anomalias == []
    assert dataset.attrs["reconciliacao"]["fecha"]


def test_validate_cobertura(tmp_path):
    partes = coleta_completa()
    partes[3] = partes[3].iloc[:37]
    gravar(tmp_path, partes)
    dataset, anomalias = validate(str(tmp_path))
    assert tipos(anomalias) == ["cobertura_incompleta"]
    assert len(dataset) == TOTAL_ESPERADO - 1
    assert dataset.attrs["reconciliacao"]["fecha"]


def test_validate_execucao_ausente(tmp_path):
    partes = coleta_completa()
    del partes[5]
    gravar(tmp_path, partes)
    dataset, anomalias = validate(str(tmp_path))
    assert tipos(anomalias) == ["execucao_ausente"]
    assert anomalias[0]["data_brt"] == calendario()[5][0]
    assert dataset.attrs["reconciliacao"] == dataset.attrs["reconciliacao"] | {
        "execucoes_ausentes": 1, "total": TOTAL_ESPERADO, "fecha": True}


def test_validate_remaneja_pico_atrasado_para_a_madrugada(tmp_path):
    # Anomalia 1: o pico de 18/11 atrasou e mediu na madrugada de 19/11, com o cron do pico.
    partes = [p for p in coleta_completa()
              if not ((p["data_brt"].iloc[0] == "2026-11-18" and p["janela"].iloc[0] == "pico")
                      or (p["data_brt"].iloc[0] == "2026-11-19" and p["janela"].iloc[0] == "madrugada"))]
    partes.append(execucao(inicio_nominal("2026-11-18", "7 23 * * *", atraso_min=297), "7 23 * * *",
                           gatilho="schedule"))
    partes.append(execucao(inicio_nominal("2026-11-18", "7 1 * * *", atraso_min=448), "7 1 * * *",
                           gatilho="schedule"))
    gravar(tmp_path, partes)
    dataset, anomalias = validate(str(tmp_path))
    assert sorted(tipos(anomalias)) == ["execucao_ausente"] * 2 + ["execucao_remanejada"] * 2
    ausentes = {a["data_brt"] for a in anomalias if a["tipo"] == "execucao_ausente"}
    assert ausentes == {"2026-11-18"}
    # As atrasadas ficam no dataset com a janela real e não ocupam o pico de 19/11.
    assert len(dataset) == 26 * 38
    assert dataset.attrs["reconciliacao"]["fecha"]


def test_validate_exclui_bloqueadas_e_fora(tmp_path):
    partes = coleta_completa()
    partes[0].loc[0, "bloqueada"] = True
    partes.append(execucao(datetime(2026, 11, 20, 15, 0, tzinfo=timezone.utc), "7 8 * * *"))  # 12h BRT
    gravar(tmp_path, partes)
    dataset, anomalias = validate(str(tmp_path))
    assert len(dataset) == TOTAL_ESPERADO - 1
    assert not dataset["bloqueada"].any() and (dataset["janela"] != "fora").all()
    assert tipos(anomalias).count("descartada_bloqueada") == 1
    assert tipos(anomalias).count("descartada_fora") == 38
    conta = dataset.attrs["reconciliacao"]
    assert conta["fecha"] and conta["linhas_fora_do_calendario"] == 38


def test_validate_exclui_erro(tmp_path):
    partes = coleta_completa()
    partes[2].loc[4, "erro"] = "HTTP 400"
    gravar(tmp_path, partes)
    dataset, anomalias = validate(str(tmp_path))
    assert len(dataset) == TOTAL_ESPERADO - 1
    assert dataset["erro"].isna().all()
    assert tipos(anomalias) == ["descartada_erro"]


def test_validate_exclui_manual(tmp_path):
    partes = coleta_completa()
    partes.append(execucao(inicio_nominal("2026-11-20", "7 23 * * *", atraso_min=20), "",
                           gatilho="workflow_dispatch"))
    gravar(tmp_path, partes)
    dataset, anomalias = validate(str(tmp_path))
    assert set(dataset["gatilho"]) <= {"schedule", "agendador"}
    assert len(dataset) == TOTAL_ESPERADO
    assert tipos(anomalias) == ["descartada_manual"] * 38


def test_validate_ignora_subpastas(tmp_path):
    gravar(tmp_path, coleta_completa())
    (tmp_path / "testes").mkdir()
    execucao(inicio_nominal("2026-11-20", "7 23 * * *"), "7 23 * * *").to_csv(
        tmp_path / "testes" / "2026-11-20_BRT.csv", index=False)
    dataset, _ = validate(str(tmp_path))
    assert len(dataset) == TOTAL_ESPERADO


def test_validate_inclui_ultima_execucao(tmp_path):
    partes = [p for p in coleta_completa() if p["run_id"].iloc[0] != "20261125T080700Z"]
    ultima = execucao(datetime(2026, 11, 25, 8, 31, tzinfo=timezone.utc), "7 8 * * *")
    assert ultima["ts_utc"].iloc[-1] > "2026-11-25T08:49"  # termina perto de 08h50Z
    depois = execucao(datetime(2026, 11, 25, 23, 7, tzinfo=timezone.utc), "7 23 * * *")
    gravar(tmp_path, partes + [ultima, depois])
    dataset, anomalias = validate(str(tmp_path))
    assert (dataset["run_id"] == "20261125T083100Z").sum() == 38
    assert "20261125T230700Z" not in set(dataset["run_id"])
    assert anomalias == []


def test_validate_versao_lighthouse(tmp_path):
    partes = coleta_completa()
    partes[-1]["lighthouse_version"] = "13.7.0"
    gravar(tmp_path, partes)
    dataset, anomalias = validate(str(tmp_path))
    assert tipos(anomalias) == ["mudanca_versao"]
    assert anomalias[0]["data_brt"] == "2026-11-25"
    assert len(dataset) == TOTAL_ESPERADO
    assert dataset["sinal_mudanca_versao"].sum() == 38


def test_validate_sinaliza_reserva(tmp_path):
    partes = coleta_completa()
    partes[1].loc[6, "usou_reserva"] = True
    gravar(tmp_path, partes)
    dataset, anomalias = validate(str(tmp_path))
    assert tipos(anomalias) == ["uso_reserva"]
    assert len(dataset) == TOTAL_ESPERADO


def test_gravar_anomalias_substitui_a_secao(tmp_path):
    doc = tmp_path / "anomalias.md"
    doc.write_text("# Anomalias\n\ntexto manual\n", encoding="utf-8")
    conta = {"dataset_de_calendario": 1, "excluidas_de_calendario": 0, "faltantes_em_execucoes": 0,
             "execucoes_ausentes": 0, "total": 1, "fecha": False, "dataset": 1,
             "execucoes_no_dataset": 1, "linhas_fora_do_calendario": 0}
    gravar_anomalias(doc, secao_anomalias([], conta, "a", "b"))
    gravar_anomalias(doc, secao_anomalias([], conta, "a", "b"))
    texto = doc.read_text(encoding="utf-8")
    assert texto.count("Validação da coleta principal") == 1
    assert texto.startswith("# Anomalias\n\ntexto manual\n")
