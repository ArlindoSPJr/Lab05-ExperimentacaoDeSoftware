"""Testes da biblioteca de análise (issue #13, C-2). Nenhum teste lê dados reais."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analysis.stats import (
    art_alinhar,
    categoria_lcp,
    cliffs_delta,
    filtro_minimo,
    holm,
    kruskal_por_tipo,
    modelo_misto,
    por_url,
)

TIPOS = ["categoria", "busca", "produto"]


def linha(**campos) -> dict:
    """Uma linha válida do CSV bruto, com os campos que a análise usa."""
    base = {
        "gatilho": "agendador",
        "bloqueada": False,
        "erro": np.nan,
        "janela": "pico",
        "slot_id": "cat-1",
        "tipo": "categoria",
        "strategy": "mobile",
        "data_brt": "2026-11-20",
        "lcp_ms": 1000.0,
    }
    return base | campos


def test_holm():
    assert holm({"a": 0.01, "b": 0.04, "c": 0.03}) == pytest.approx(
        {"a": 0.03, "b": 0.06, "c": 0.06}
    )


def test_cliffs_delta():
    assert cliffs_delta([1, 2, 3], [4, 5, 6]) == -1.0


def test_kruskal_eps2():
    linhas = []
    for i, tipo in enumerate(TIPOS):
        for j in range(6):
            linhas.append(
                {"slot_id": f"{tipo}-{j}", "tipo": tipo, "strategy": "mobile", "lcp_ms": 1000 * (i + 1) + j}
            )
    linhas.append({"slot_id": "home", "tipo": "home", "strategy": "mobile", "lcp_ms": 99999})
    resultado = kruskal_por_tipo(pd.DataFrame(linhas), "lcp_ms")
    assert resultado["p"] < 0.05
    assert 0 < resultado["eps2"] <= 1
    assert isinstance(resultado["dunn"], pd.DataFrame)


def test_por_url_mediana():
    df = pd.DataFrame([linha(lcp_ms=v) for v in (1, 2, 100)])
    assert por_url(df, "lcp_ms")["lcp_ms"].tolist() == [2]


def test_por_url_moda():
    df = pd.DataFrame(
        [linha(slot_id="a", a11y_reprovadas=v) for v in (3, 3, 5)]
        + [linha(slot_id="b", a11y_reprovadas=v) for v in (2, 4)]
    )
    resultado = por_url(df, "a11y_reprovadas", agg="mode").set_index("slot_id")
    assert resultado.loc["a", "a11y_reprovadas"] == 3
    assert resultado.loc["b", "a11y_reprovadas"] == 2


def test_filtro_minimo():
    df = pd.DataFrame(
        [
            linha(slot_id="ok"),
            linha(slot_id="ok-schedule", gatilho="schedule"),
            linha(slot_id="bloqueada", bloqueada=True),
            linha(slot_id="erro", erro="500"),
            linha(slot_id="fora", janela="fora"),
            linha(slot_id="manual", gatilho="workflow_dispatch"),
        ]
    )
    assert sorted(filtro_minimo(df)["slot_id"]) == ["ok", "ok-schedule"]


def dados_sinteticos(razao_movel: float = 2.0, semente: int = 0) -> pd.DataFrame:
    """6 URLs por tipo, 2 perfis, 2 janelas, 3 dias e 2 execuções por janela."""
    rng = np.random.default_rng(semente)
    dias = ["2026-11-20", "2026-11-21", "2026-11-22"]
    efeito_dia = dict(zip(dias, rng.normal(0, 0.05, len(dias))))
    linhas = []
    for tipo in TIPOS:
        for j in range(6):
            slot = f"{tipo}-{j}"
            efeito_slot = rng.normal(0, 0.2)
            for strategy in ("desktop", "mobile"):
                for janela in ("madrugada", "pico"):
                    for dia in dias:
                        for _ in range(2):
                            log_lcp = (
                                np.log(1500)
                                + efeito_slot
                                + efeito_dia[dia]
                                + (np.log(razao_movel) if strategy == "mobile" else 0.0)
                                + rng.normal(0, 0.1)
                            )
                            linhas.append(
                                linha(
                                    slot_id=slot,
                                    tipo=tipo,
                                    strategy=strategy,
                                    janela=janela,
                                    data_brt=dia,
                                    lcp_ms=float(np.exp(log_lcp)),
                                )
                            )
    return pd.DataFrame(linhas)


def test_modelo_misto_recupera_efeito():
    resultado = modelo_misto(dados_sinteticos(razao_movel=2.0), "lcp_ms")
    assert 1.8 <= resultado["razao_perfil"] <= 2.2
    assert resultado["ic95_perfil"][0] < resultado["razao_perfil"] < resultado["ic95_perfil"][1]


def test_concordancia_categoria():
    assert categoria_lcp(2400) == "FAST"
    assert categoria_lcp(2600) == "AVERAGE"
    assert categoria_lcp(4100) == "SLOW"


def test_art_alinhar():
    # Tipo e janela têm efeito; o perfil não. O ruído é o mesmo nos dois perfis.
    rng = np.random.default_rng(1)
    efeito_tipo = {"categoria": 0, "busca": 500, "produto": 1500}
    linhas = []
    for tipo in TIPOS:
        for j in range(6):
            for janela, efeito_janela in (("madrugada", 0), ("pico", 300)):
                for rep in range(2):
                    ruido = rng.normal(0, 100)
                    for strategy in ("desktop", "mobile"):
                        linhas.append(
                            linha(
                                slot_id=f"{tipo}-{j}",
                                tipo=tipo,
                                strategy=strategy,
                                janela=janela,
                                lcp_ms=2000 + efeito_tipo[tipo] + efeito_janela + ruido,
                            )
                        )
    alinhado = art_alinhar(pd.DataFrame(linhas), "lcp_ms", "strategy")
    medianas = alinhado.groupby("strategy")["lcp_ms_art"].median()
    assert abs(medianas["desktop"] - medianas["mobile"]) <= 1
