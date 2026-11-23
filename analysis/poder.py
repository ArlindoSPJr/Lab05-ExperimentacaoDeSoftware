"""Simulação do efeito mínimo detectável e do erro tipo I (issue #14, C-3).

A coleta tem duração fixa, então a simulação não escolhe o nº de dias: ela
estima o menor efeito que o desenho detecta com poder ≥ 0,8 (design, "Poder
(Lab04)"). Desenho simulado: 6 URLs por tipo (sem a home), 7 dias e
2 execuções por janela.

- H2 (LCP por tipo): perfil móvel; mediana por URL; Kruskal-Wallis.
- H4 (reprovadas por tipo): valor modal por URL; Kruskal-Wallis.
- H3 (TTFB pico × madrugada): dataset completo; modelo misto (stats.modelo_misto).

O efeito é uma razão r. Em H2 e H4, os três tipos ficam em 1, √r e r (o tipo
mais alto é r× o mais baixo). Em H3, o pico é r× a madrugada. r = 1,00 é o
efeito zero e dá o erro tipo I.

Os parâmetros de variância vêm do piloto (#C-1), calculados aqui mesmo. A
variação entre dias não pode ser estimada com uma noite só e vem dos dados
coletados até agora.

Uso (na raiz do repositório):
    python analysis/poder.py

Saídas em analysis/out/poder/: parametros.csv, poder.csv, curvas_poder.png
e relatorio.md.
"""

from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats as st  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from analysis.stats import filtro_minimo, modelo_misto  # noqa: E402

DIR_DADOS = RAIZ / "data" / "raw"
DIR_SAIDA = RAIZ / "analysis" / "out" / "poder"

SEMENTE = 20261123
ALFA = 0.05
PODER_ALVO = 0.8

# Desenho
TIPOS = ["categoria", "busca", "produto"]
URLS_POR_TIPO = 6
DIAS = 7
JANELAS = ["madrugada", "pico"]
EXECUCOES_POR_JANELA = 2

# Grade do plano e grade estendida (só H2 e H4, que são rápidas)
GRADE = [1.00, 1.06, 1.12, 1.18, 1.24, 1.30]
GRADE_ESTENDIDA = [1.50, 1.75, 2.00]
N_SIM = {"H2": 1000, "H4": 1000, "H3": 200}

# Janela do piloto (igual à da C-1): 18/11 20h07 a 19/11 06h07 BRT
PILOTO_INICIO = pd.Timestamp("2026-11-18T23:07:00Z")
PILOTO_FIM = pd.Timestamp("2026-11-19T09:07:00Z")


# ---------------------------------------------------------------- dados


def carregar() -> pd.DataFrame:
    """Todos os CSVs de data/raw (sem testes/), já com o filtro mínimo e sem a home."""
    df = pd.concat((pd.read_csv(a) for a in sorted(DIR_DADOS.glob("*.csv"))), ignore_index=True)
    df["ts_inicio_utc"] = pd.to_datetime(df["ts_inicio_utc"], utc=True)
    df = filtro_minimo(df)
    return df[df["tipo"] != "home"].reset_index(drop=True)


def piloto(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df["ts_inicio_utc"] >= PILOTO_INICIO) & (df["ts_inicio_utc"] <= PILOTO_FIM)]


def componentes_log(df: pd.DataFrame, metrica: str) -> tuple[float, float]:
    """DP em log entre URLs e entre execuções (ANOVA de um fator, como na C-1)."""
    y = np.log(df.loc[df[metrica] > 0, metrica])
    por_url = y.groupby(df.loc[y.index, "slot_id"]).agg(["mean", "var", "count"])
    por_url = por_url[por_url["count"] >= 2]
    dentro = por_url["var"].mean()
    entre = max(por_url["mean"].var(ddof=1) - dentro / por_url["count"].mean(), 0.0)
    return float(np.sqrt(entre)), float(np.sqrt(dentro))


def dp_dia_log(df: pd.DataFrame, metrica: str) -> float:
    """DP em log do efeito de dia, com os resíduos de slot × perfil × janela."""
    base = df[df[metrica] > 0].copy()
    base["y"] = np.log(base[metrica])
    base["r"] = base["y"] - base.groupby(["slot_id", "strategy", "janela"])["y"].transform("mean")
    por_dia = base.groupby("data_brt")["r"].agg(["mean", "count"])
    if len(por_dia) < 2:
        return 0.0
    var = por_dia["mean"].var(ddof=1) - base["r"].var(ddof=1) / por_dia["count"].mean()
    return float(np.sqrt(max(var, 0.0)))


def estimar_parametros(df: pd.DataFrame) -> dict:
    pil = piloto(df)
    movel = pil[pil["strategy"] == "mobile"]
    p: dict = {"linhas_piloto": len(pil), "dias_coletados": df["data_brt"].nunique()}

    # H2: LCP móvel
    p["lcp_mu_log"] = float(np.log(movel["lcp_ms"]).mean())
    p["lcp_dp_url"], p["lcp_dp_exec"] = componentes_log(movel, "lcp_ms")
    p["lcp_dp_dia"] = dp_dia_log(df[df["strategy"] == "mobile"], "lcp_ms")

    # H3: TTFB observado, os dois perfis
    ttfb = pil[pil["ttfb_origem"] == "server-response-time"]
    p["ttfb_mu_log"] = float(np.log(ttfb.loc[ttfb["ttfb_ms"] > 0, "ttfb_ms"]).mean())
    dps = {s: componentes_log(ttfb[ttfb["strategy"] == s], "ttfb_ms") for s in ("desktop", "mobile")}
    p["ttfb_dp_url"] = float(np.mean([dps[s][0] for s in dps]))  # efeito de URL comum aos perfis
    p["ttfb_dp_exec_desktop"] = dps["desktop"][1]
    p["ttfb_dp_exec_mobile"] = dps["mobile"][1]
    todos_ttfb = df[df["ttfb_origem"] == "server-response-time"]
    p["ttfb_dp_dia"] = dp_dia_log(todos_ttfb, "ttfb_ms")

    # H4: valor modal por URL no perfil móvel
    modas = movel.groupby(["tipo", "slot_id"])["a11y_reprovadas"].agg(lambda s: s.mode().min())
    p["a11y_media"] = float(modas.mean())
    desvios = modas - modas.groupby(level="tipo").transform("median")
    p["a11y_desvios"] = desvios.astype(int).tolist()
    return p


# ---------------------------------------------------------------- simulações


def _multiplicadores_tipo(r: float) -> np.ndarray:
    """Log dos multiplicadores dos tipos: 1, √r e r."""
    return np.log(r) * np.array([0.0, 0.5, 1.0])


def simular_h2(r: float, n_sim: int, p: dict, rng: np.random.Generator) -> np.ndarray:
    """p-valores de Kruskal-Wallis sobre a mediana do LCP móvel por URL."""
    n_exec = DIAS * len(JANELAS) * EXECUCOES_POR_JANELA
    tipo = np.repeat(_multiplicadores_tipo(r), URLS_POR_TIPO)  # (18,)
    u = rng.normal(0, p["lcp_dp_url"], (n_sim, len(tipo), 1))
    dia = rng.normal(0, p["lcp_dp_dia"], (n_sim, 1, DIAS))
    dia = np.repeat(dia, len(JANELAS) * EXECUCOES_POR_JANELA, axis=2)  # (n_sim, 1, 28)
    e = rng.normal(0, p["lcp_dp_exec"], (n_sim, len(tipo), n_exec))
    y = p["lcp_mu_log"] + tipo[None, :, None] + u + dia + e
    medianas = np.median(y, axis=2)  # a mediana comuta com exp
    grupos = medianas.reshape(n_sim, len(TIPOS), URLS_POR_TIPO)
    return np.array([st.kruskal(*g).pvalue for g in grupos])


def simular_h4(r: float, n_sim: int, p: dict, rng: np.random.Generator) -> np.ndarray:
    """p-valores de Kruskal-Wallis sobre o nº modal de reprovadas por URL.

    Cada URL: arredondamento estocástico da média do tipo (média do piloto ×
    1, √r ou r) mais um desvio inteiro sorteado dos desvios reais do piloto.
    """
    media = p["a11y_media"] * np.exp(np.repeat(_multiplicadores_tipo(r), URLS_POR_TIPO))
    base = np.floor(media[None, :] + rng.random((n_sim, len(media))))
    desvio = rng.choice(p["a11y_desvios"], size=base.shape)
    contagem = np.clip(base + desvio, 0, None)
    grupos = contagem.reshape(n_sim, len(TIPOS), URLS_POR_TIPO)
    pvals = []
    for g in grupos:
        if np.ptp(g) == 0:  # todos iguais: o teste não rejeita
            pvals.append(1.0)
        else:
            pvals.append(st.kruskal(*g).pvalue)
    return np.array(pvals)


def dataset_h3(r: float, p: dict, rng: np.random.Generator) -> pd.DataFrame:
    """Um dataset completo de TTFB (18 URLs × 2 perfis × 2 janelas × 7 dias × 2 execuções)."""
    linhas = []
    efeito_dia = rng.normal(0, p["ttfb_dp_dia"], DIAS)
    for tipo in TIPOS:
        for j in range(URLS_POR_TIPO):
            u = rng.normal(0, p["ttfb_dp_url"])
            for strategy in ("desktop", "mobile"):
                dp_exec = p[f"ttfb_dp_exec_{strategy}"]
                for janela in JANELAS:
                    pico = np.log(r) if janela == "pico" else 0.0
                    for d in range(DIAS):
                        for _ in range(EXECUCOES_POR_JANELA):
                            y = p["ttfb_mu_log"] + u + efeito_dia[d] + pico + rng.normal(0, dp_exec)
                            linhas.append((f"{tipo}-{j}", tipo, strategy, janela, f"d{d}", np.exp(y)))
    return pd.DataFrame(linhas, columns=["slot_id", "tipo", "strategy", "janela", "data_brt", "ttfb_ms"])


def simular_h3(r: float, n_sim: int, p: dict, rng: np.random.Generator) -> tuple[np.ndarray, int]:
    """p-valores do efeito de pico no modelo misto e nº de ajustes que não convergiram."""
    pvals, falhas = [], 0
    for _ in range(n_sim):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = modelo_misto(dataset_h3(r, p, rng), "ttfb_ms")
        falhas += not res["convergiu"]
        pvals.append(res["p_pico"])
    return np.array(pvals), falhas


# ---------------------------------------------------------------- resumo


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """IC de Wilson de 95% para uma proporção."""
    if n == 0:
        return np.nan, np.nan
    phat = k / n
    centro = (phat + z**2 / (2 * n)) / (1 + z**2 / n)
    meia = z * np.sqrt(phat * (1 - phat) / n + z**2 / (4 * n**2)) / (1 + z**2 / n)
    return float(centro - meia), float(centro + meia)


def efeito_minimo(tabela: pd.DataFrame, hipotese: str, grade: list[float]) -> str:
    parte = tabela[(tabela["hipotese"] == hipotese) & (tabela["razao"].isin(grade)) & (tabela["razao"] > 1)]
    ok = parte[parte["poder"] >= PODER_ALVO]
    if ok.empty:
        return f"> {max(grade):.2f}".replace(".", ",")
    return f"{ok['razao'].min():.2f}".replace(".", ",")


def _num(x: float, casas: int = 3) -> str:
    return f"{x:.{casas}f}".replace(".", ",")


def relatorio(tabela: pd.DataFrame, p: dict, tempos: dict, falhas_h3: int) -> str:
    linhas_mde = []
    nomes = {
        "H2": "H2: LCP difere entre os tipos (móvel)",
        "H3": "H3: TTFB maior no pico",
        "H4": "H4: nº de reprovadas difere entre os tipos",
    }
    for h in ("H2", "H3", "H4"):
        zero = tabela[(tabela["hipotese"] == h) & (tabela["razao"] == 1.00)].iloc[0]
        estendido = efeito_minimo(tabela, h, GRADE + GRADE_ESTENDIDA) if h != "H3" else "—"
        linhas_mde.append(
            f"| {nomes[h]} | {N_SIM[h]} | {efeito_minimo(tabela, h, GRADE)} | {estendido} | "
            f"{_num(zero['poder'])} ({_num(zero['ic_inf'])}–{_num(zero['ic_sup'])}) | {_num(tempos[h], 1)} s |"
        )

    curva = tabela.pivot_table(index="razao", columns="hipotese", values="poder").reset_index()
    linhas_curva = [
        "| " + _num(row["razao"], 2) + " | " + " | ".join(
            "" if np.isnan(row.get(h, np.nan)) else _num(row[h]) for h in ("H2", "H3", "H4")
        ) + " |"
        for _, row in curva.iterrows()
    ]

    erros_tipo1 = tabela[tabela["razao"] == 1.00].set_index("hipotese")["poder"]
    fora = [h for h, v in erros_tipo1.items() if not 0.03 <= v <= 0.07]
    aviso_tipo1 = (
        "O erro tipo I observado fica entre 0,03 e 0,07 nas três hipóteses."
        if not fora
        else f"O erro tipo I fica **fora** de 0,03–0,07 em {', '.join(fora)}. Ver a discussão abaixo."
    )

    return f"""# Efeito mínimo detectável e erro tipo I (#C-3)

Gerado por `analysis/poder.py` (semente {SEMENTE}). Desenho simulado: {URLS_POR_TIPO} URLs por tipo (categoria, busca e produto; sem a home), {DIAS} dias e {EXECUCOES_POR_JANELA} execuções por janela. Nível de significância {_num(ALFA, 2)}; poder-alvo {_num(PODER_ALVO, 1)}.

O efeito é uma **razão r**. Em H2 e H4, os três tipos ficam em 1, √r e r (o tipo mais alto é r× o mais baixo). Em H3, o TTFB do pico é r× o da madrugada. Com r = 1,00 não há efeito, e a taxa de rejeição é o erro tipo I.

## Efeito mínimo detectável

| Hipótese | Datasets por nível | Menor r com poder ≥ 0,8 (grade 1,00–1,30) | Grade estendida (até 2,00) | Erro tipo I (IC 95%) | Tempo |
|---|---|---|---|---|---|
{chr(10).join(linhas_mde)}

{aviso_tipo1} Tempo total: {_num(sum(tempos.values()), 1)} s.

## Curvas de poder

| r | H2 | H3 | H4 |
|---|---|---|---|
{chr(10).join(linhas_curva)}

![Curvas de poder](curvas_poder.png)

Os valores com IC de Wilson estão em `poder.csv`.

## Parâmetros usados

Calculados por este script a partir do piloto (#C-1: {p['linhas_piloto']} linhas sem a home, 2 execuções de madrugada de 19/11). DP em escala log.

| Parâmetro | Valor | Origem |
|---|---|---|
| LCP móvel: DP entre URLs | {_num(p['lcp_dp_url'])} | piloto |
| LCP móvel: DP entre execuções | {_num(p['lcp_dp_exec'])} | piloto |
| LCP móvel: DP entre dias | {_num(p['lcp_dp_dia'])} | dados de 19/11 em diante ({p['dias_coletados']} dias) |
| TTFB: DP entre URLs (média dos perfis) | {_num(p['ttfb_dp_url'])} | piloto |
| TTFB: DP entre execuções, desktop / móvel | {_num(p['ttfb_dp_exec_desktop'])} / {_num(p['ttfb_dp_exec_mobile'])} | piloto |
| TTFB: DP entre dias | {_num(p['ttfb_dp_dia'])} | dados de 19/11 em diante ({p['dias_coletados']} dias) |
| Reprovadas: média do valor modal por URL | {_num(p['a11y_media'], 2)} | piloto |
| Reprovadas: desvios por URL em relação à mediana do tipo | {sorted(p['a11y_desvios'])} | piloto |

## Como cada hipótese foi simulada

- **H2:** para cada URL, 28 execuções no perfil móvel: log(LCP) = média + efeito do tipo + efeito da URL + efeito do dia + ruído, todos normais. A URL entra no teste pela mediana, e o teste é o Kruskal-Wallis entre os tipos, o mesmo de `stats.kruskal_por_tipo`.
- **H4:** cada URL entra com um só valor, o modal, porque as reprovadas quase não mudam entre execuções (3 de 38 combinações mudaram no piloto). O valor é a média do tipo arredondada de forma estocástica, mais um desvio inteiro sorteado dos desvios reais do piloto. Não se usou Poisson, porque no piloto a variância dentro de cada tipo (0 a 0,8) é bem menor que a média (2 a 4,3).
- **H3:** um dataset completo de TTFB (18 URLs × 2 perfis × 2 janelas × 7 dias × 2 execuções = 1.008 linhas), ajustado com `stats.modelo_misto`, o mesmo modelo da análise. O teste é o p-valor do efeito de pico. {falhas_h3} de {N_SIM['H3'] * len(GRADE)} ajustes não convergiram.

## Limitações

- **Parâmetros instáveis.** O piloto tem só 2 execuções por URL, então os DPs entre execuções são uma ordem de grandeza, não um valor preciso.
- **Sem variação entre dias no piloto.** O DP entre dias vem dos dias coletados até agora, que ainda são poucos.
- **LCP em dois níveis.** A C-1 mostrou que o LCP das categorias no celular alterna entre ~3 s e ~10 s. A simulação supõe um LCP log-normal, o que não reproduz essa mistura. Como H2 usa a mediana por URL, o efeito mais provável é uma variação entre URLs maior que a simulada, e um poder real menor.
- **H3 com 200 datasets por nível.** A margem de erro do poder e do erro tipo I é de cerca de ±0,03.
- **Efeitos de tipo, perfil e interações** foram fixados em zero em H3, e o pico foi simulado igual em todas as células.
"""


def grafico(tabela: pd.DataFrame, caminho: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for h, cor in (("H2", "#1f77b4"), ("H3", "#d62728"), ("H4", "#2ca02c")):
        parte = tabela[tabela["hipotese"] == h].sort_values("razao")
        ax.plot(parte["razao"], parte["poder"], marker="o", color=cor, label=h)
        ax.fill_between(parte["razao"], parte["ic_inf"], parte["ic_sup"], color=cor, alpha=0.15)
    ax.axhline(PODER_ALVO, color="gray", ls="--", lw=1)
    ax.axhline(ALFA, color="gray", ls=":", lw=1)
    ax.set_xlabel("Razão do efeito (r)")
    ax.set_ylabel("Poder (taxa de rejeição)")
    ax.set_ylim(0, 1.02)
    ax.set_title("Poder por hipótese (6 URLs por tipo, 7 dias)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(caminho, dpi=150)
    plt.close(fig)


def main() -> None:
    rng = np.random.default_rng(SEMENTE)
    p = estimar_parametros(carregar())

    linhas, tempos, falhas_h3 = [], {}, 0
    for h, simular, grade in (
        ("H2", simular_h2, GRADE + GRADE_ESTENDIDA),
        ("H4", simular_h4, GRADE + GRADE_ESTENDIDA),
        ("H3", simular_h3, GRADE),
    ):
        inicio = time.perf_counter()
        for r in grade:
            saida = simular(r, N_SIM[h], p, rng)
            if h == "H3":
                pvals, falhas = saida
                falhas_h3 += falhas
            else:
                pvals = saida
            k = int(np.sum(np.nan_to_num(pvals, nan=1.0) < ALFA))
            ic = wilson(k, len(pvals))
            linhas.append({"hipotese": h, "razao": r, "n_sim": len(pvals), "rejeicoes": k,
                           "poder": k / len(pvals), "ic_inf": ic[0], "ic_sup": ic[1]})
            print(f"{h} r={r:.2f}: poder {k / len(pvals):.3f}")
        tempos[h] = time.perf_counter() - inicio

    tabela = pd.DataFrame(linhas)
    DIR_SAIDA.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{k: v for k, v in p.items() if k != "a11y_desvios"}]).to_csv(DIR_SAIDA / "parametros.csv", index=False)
    tabela.to_csv(DIR_SAIDA / "poder.csv", index=False)
    grafico(tabela, DIR_SAIDA / "curvas_poder.png")
    (DIR_SAIDA / "relatorio.md").write_text(relatorio(tabela, p, tempos, falhas_h3), encoding="utf-8")
    print(f"Tempo total: {sum(tempos.values()):.1f} s. Saídas em {DIR_SAIDA}")


if __name__ == "__main__":
    main()
