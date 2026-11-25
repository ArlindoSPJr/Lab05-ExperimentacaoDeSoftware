"""Descritiva do piloto incorporado (issue #12, C-1).

O piloto são as execuções agendadas da noite de 18→19/11/2026 (crons das
20h07, 22h07, 03h07 e 05h07 BRT). Por causa da anomalia 1 (docs/anomalias.md),
só 2 delas rodaram, ambas de madrugada. Este script mede a cobertura, os
bloqueios e as falhas, faz a descritiva de LCP, TTFB e auditorias de
acessibilidade reprovadas e estima a variância entre execuções da mesma URL,
que alimenta a simulação de poder (#C-3).

Uso (na raiz do repositório):
    python analysis/piloto.py

Saídas em analysis/out/piloto/:
    cobertura.csv, descritiva.csv, variancia_por_url.csv,
    decomposicao_variancia.csv e relatorio.md
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
DIR_DADOS = RAIZ / "data" / "raw"
DIR_SAIDA = RAIZ / "analysis" / "out" / "piloto"

GATILHOS_VALIDOS = {"schedule", "agendador"}

# 18/11 20h07 BRT até 19/11 05h07 BRT, com 1 h de folga no fim (a mesma do
# porteiro). BRT = UTC-3.
INICIO_UTC = pd.Timestamp("2026-11-18T23:07:00Z")
FIM_UTC = pd.Timestamp("2026-11-19T09:07:00Z")

# Crons nominais do piloto e o horário BRT que cada um representa.
CRONS_PILOTO = {
    "7 23 * * *": "18/11 20h07",
    "7 1 * * *": "18/11 22h07",
    "7 6 * * *": "19/11 03h07",
    "7 8 * * *": "19/11 05h07",
}
LINHAS_POR_EXECUCAO = 38  # 19 URLs × 2 perfis
LINHAS_ESPERADAS = len(CRONS_PILOTO) * LINHAS_POR_EXECUCAO  # 152

METRICAS = ["lcp_ms", "ttfb_ms", "a11y_reprovadas"]
# Métricas de tempo, analisadas também em log (escala do modelo misto da C-2).
METRICAS_LOG = ["lcp_ms", "ttfb_ms"]
GRUPOS = ["tipo", "strategy", "janela"]
# Separa os dois níveis de LCP móvel das categorias (~3 s e ~10 s).
LIMIAR_LCP_LENTO = 8000


def carregar_piloto(dir_dados: Path = DIR_DADOS) -> pd.DataFrame:
    """Lê data/raw/*.csv (sem descer em testes/) e devolve só as linhas do piloto."""
    arquivos = sorted(dir_dados.glob("*.csv"))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum CSV em {dir_dados}")
    df = pd.concat((pd.read_csv(a) for a in arquivos), ignore_index=True)
    df["ts_inicio_utc"] = pd.to_datetime(df["ts_inicio_utc"], utc=True)
    no_piloto = (
        df["gatilho"].isin(GATILHOS_VALIDOS)
        & (df["ts_inicio_utc"] >= INICIO_UTC)
        & (df["ts_inicio_utc"] <= FIM_UTC)
    )
    return df.loc[no_piloto].reset_index(drop=True)


def _taxa(serie: pd.Series) -> float:
    return float(serie.fillna(False).astype(bool).mean()) if len(serie) else float("nan")


def cobertura(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Uma linha por cron nominal do piloto, mais um resumo geral."""
    linhas = []
    for cron, previsto in CRONS_PILOTO.items():
        parte = df[df["cron"] == cron]
        run_ids = sorted(parte["run_id"].unique())
        linhas.append(
            {
                "cron": cron,
                "previsto_brt": previsto,
                "run_id": ";".join(run_ids),
                "janela_gravada": ";".join(sorted(parte["janela"].dropna().unique())),
                "linhas": len(parte),
                "linhas_esperadas": LINHAS_POR_EXECUCAO,
                "bloqueadas": int(parte["bloqueada"].fillna(False).astype(bool).sum()),
                "com_erro": int(parte["erro"].notna().sum()),
                "com_reserva": int(parte["usou_reserva"].fillna(False).astype(bool).sum()),
                "mais_de_1_tentativa": int((parte["tentativas"] > 1).sum()),
            }
        )
    tabela = pd.DataFrame(linhas)
    resumo = {
        "linhas": len(df),
        "linhas_esperadas": LINHAS_ESPERADAS,
        "execucoes": df["run_id"].nunique(),
        "execucoes_esperadas": len(CRONS_PILOTO),
        "taxa_bloqueada": _taxa(df["bloqueada"]),
        "taxa_erro": float(df["erro"].notna().mean()) if len(df) else float("nan"),
        "taxa_reserva": _taxa(df["usou_reserva"]),
        "taxa_retentativa": float((df["tentativas"] > 1).mean()) if len(df) else float("nan"),
        "ttfb_origem": df["ttfb_origem"].value_counts(dropna=False).to_dict(),
        "janelas": df["janela"].value_counts(dropna=False).to_dict(),
    }
    return tabela, resumo


def validas(df: pd.DataFrame) -> pd.DataFrame:
    """Linhas aproveitáveis: sem bloqueio, sem erro e dentro de uma janela do estudo."""
    ok = ~df["bloqueada"].fillna(False).astype(bool) & df["erro"].isna() & (df["janela"] != "fora")
    return df.loc[ok]


def descritiva(df: pd.DataFrame) -> pd.DataFrame:
    """n, mediana, Q1, Q3 e IQR de cada métrica por tipo × perfil × janela."""
    linhas = []
    for chave, parte in df.groupby(GRUPOS):
        for m in METRICAS:
            serie = parte[m].dropna()
            if m == "ttfb_ms":  # H3 usa só o TTFB observado (docs/dados.md)
                serie = parte.loc[parte["ttfb_origem"] == "server-response-time", m].dropna()
            q1, med, q3 = serie.quantile([0.25, 0.5, 0.75]) if len(serie) else (np.nan,) * 3
            linhas.append(
                dict(zip(GRUPOS, chave))
                | {
                    "metrica": m,
                    "n": len(serie),
                    "n_urls": parte.loc[serie.index, "slot_id"].nunique(),
                    "mediana": med,
                    "q1": q1,
                    "q3": q3,
                    "iqr": q3 - q1,
                }
            )
    return pd.DataFrame(linhas)


def variancia_por_url(df: pd.DataFrame) -> pd.DataFrame:
    """Variação entre execuções da mesma URL (slot × perfil × janela)."""
    linhas = []
    for (slot, tipo, strategy, janela), parte in df.groupby(["slot_id", "tipo", "strategy", "janela"]):
        for m in METRICAS:
            serie = parte[m].dropna()
            linha = {
                "slot_id": slot,
                "tipo": tipo,
                "strategy": strategy,
                "janela": janela,
                "metrica": m,
                "n_execucoes": len(serie),
                "media": serie.mean(),
                "variancia": serie.var(ddof=1),
                "desvio": serie.std(ddof=1),
                "cv": serie.std(ddof=1) / serie.mean() if serie.mean() else np.nan,
                "variancia_log": np.nan,
            }
            if m in METRICAS_LOG and (serie > 0).all():
                linha["variancia_log"] = np.log(serie).var(ddof=1)
            linhas.append(linha)
    return pd.DataFrame(linhas)


def decompor_variancia(df: pd.DataFrame) -> pd.DataFrame:
    """Separa a variância de log(métrica) entre URLs e entre execuções.

    Estimador de ANOVA de um fator (URL), por perfil:
    - dentro (entre execuções) = média das variâncias de cada URL;
    - entre URLs = variância das médias por URL − dentro / n_execuções,
      truncada em zero.
    O tipo de página fica dentro do componente "entre URLs". A #C-3 usa esses
    componentes como desvios-padrão dos efeitos de URL e do resíduo.
    """
    linhas = []
    for m in METRICAS_LOG:
        base = df[df[m] > 0].assign(y=lambda d: np.log(d[m]))
        for strategy, parte in base.groupby("strategy"):
            por_url = parte.groupby("slot_id")["y"].agg(["mean", "var", "count"])
            por_url = por_url[por_url["count"] >= 2]
            if por_url.empty:
                continue
            k = por_url["count"].mean()
            dentro = por_url["var"].mean()
            entre = max(por_url["mean"].var(ddof=1) - dentro / k, 0.0)
            linhas.append(
                {
                    "metrica": m,
                    "strategy": strategy,
                    "n_urls": len(por_url),
                    "execucoes_por_url": k,
                    "var_entre_urls_log": entre,
                    "var_entre_execucoes_log": dentro,
                    "dp_entre_urls_log": np.sqrt(entre),
                    "dp_entre_execucoes_log": np.sqrt(dentro),
                    "fracao_entre_execucoes": dentro / (entre + dentro) if entre + dentro else np.nan,
                }
            )
    return pd.DataFrame(linhas)


def _tabela_md(df: pd.DataFrame, decimais: int = 2) -> str:
    """Tabela Markdown simples (sem depender do pacote tabulate)."""

    def fmt(v):
        if isinstance(v, (float, np.floating)):
            return "" if np.isnan(v) else f"{v:,.{decimais}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return str(v)

    cab = "| " + " | ".join(df.columns) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    corpo = ["| " + " | ".join(fmt(v) for v in linha) + " |" for linha in df.itertuples(index=False)]
    return "\n".join([cab, sep, *corpo])


def _ms(x: float) -> str:
    """Inteiro com ponto de milhar (8.000)."""
    return f"{x:,.0f}".replace(",", ".")


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%".replace(".", ",")


def relatorio(tab_cob, resumo, base, desc, var_url, decomp) -> str:
    resumo_var = (
        var_url[var_url["metrica"].isin(METRICAS_LOG)]
        .groupby(["metrica", "strategy"])
        .agg(urls=("slot_id", "nunique"), cv_mediano=("cv", "median"), cv_max=("cv", "max"))
        .reset_index()
    )
    maiores = (
        var_url[var_url["metrica"] == "lcp_ms"]
        .nlargest(5, "cv")[["slot_id", "tipo", "strategy", "media", "desvio", "cv"]]
    )
    a11y_estavel = var_url[var_url["metrica"] == "a11y_reprovadas"]
    a11y_mudou = int((a11y_estavel["variancia"] > 0).sum())

    tabela_desc = desc.pivot_table(
        index=["tipo", "strategy", "janela"], columns="metrica", values=["mediana", "iqr"]
    )
    tabela_desc.columns = [f"{m} {est}" for est, m in tabela_desc.columns]
    ordem = [f"{m} {est}" for m in METRICAS for est in ("mediana", "iqr")]
    tabela_desc = tabela_desc[ordem].reset_index()

    janelas = ", ".join(f"{j}: {n}" for j, n in resumo["janelas"].items())

    # LCP móvel em dois níveis nas categorias (visto ao rodar o piloto).
    cat_mob = base[(base["tipo"] == "categoria") & (base["strategy"] == "mobile")]
    lentas = cat_mob[cat_mob["lcp_ms"] > LIMIAR_LCP_LENTO]
    rapidas = cat_mob[cat_mob["lcp_ms"] <= LIMIAR_LCP_LENTO]
    trocou = int((cat_mob.groupby("slot_id")["lcp_ms"].agg(lambda s: (s > LIMIAR_LCP_LENTO).nunique()) > 1).sum())
    return f"""# Descritiva do piloto incorporado (#C-1)

Gerado por `analysis/piloto.py` a partir de `data/raw/*.csv` (sem `data/raw/testes/`).
Piloto: execuções `schedule`/`agendador` iniciadas entre 18/11 20h07 e 19/11 06h07 BRT.

## Cobertura

**{resumo['linhas']}/{resumo['linhas_esperadas']} linhas** ({resumo['execucoes']} de {resumo['execucoes_esperadas']} execuções). Linhas por janela: {janelas}.

{_tabela_md(tab_cob.drop(columns=['linhas_esperadas']))}

As execuções que faltam são as da anomalia 1 (`docs/anomalias.md`): o `schedule` do GitHub atrasou as duas primeiras, que caíram na madrugada, e não disparou as duas últimas.

## Bloqueios, erros e reservas

| Indicador | Taxa |
|---|---|
| Linhas bloqueadas | {_pct(resumo['taxa_bloqueada'])} |
| Linhas com erro | {_pct(resumo['taxa_erro'])} |
| Linhas com URL reserva | {_pct(resumo['taxa_reserva'])} |
| Linhas com mais de 1 tentativa | {_pct(resumo['taxa_retentativa'])} |

Origem do TTFB: {resumo['ttfb_origem']}.

## Descritiva por tipo × perfil × janela

Mediana e IQR. LCP e TTFB em ms; `a11y_reprovadas` em número de auditorias. Os valores completos (n, Q1, Q3) estão em `descritiva.csv`.

{_tabela_md(tabela_desc, 1)}

## Variância entre execuções da mesma URL

Coeficiente de variação (desvio ÷ média) entre as execuções de cada URL, por perfil:

{_tabela_md(resumo_var, 3)}

URLs com maior variação de LCP:

{_tabela_md(maiores, 3)}

Auditorias de acessibilidade reprovadas: {a11y_mudou} de {len(a11y_estavel)} combinações URL × perfil mudaram de uma execução para a outra.

### LCP em dois níveis nas categorias (celular)

O LCP das páginas de categoria no perfil móvel não varia de forma contínua: ele cai em dois níveis. {len(lentas)} de {len(cat_mob)} medições ficaram acima de {_ms(LIMIAR_LCP_LENTO)} ms (mediana {_ms(lentas['lcp_ms'].median())} ms), e as outras {len(rapidas)} ficaram perto de {_ms(rapidas['lcp_ms'].median())} ms. O FCP acompanha o mesmo salto (mediana {_ms(lentas['fcp_ms'].median())} ms contra {_ms(rapidas['fcp_ms'].median())} ms), enquanto o peso da página e o número de requisições quase não mudam. {trocou} das {cat_mob['slot_id'].nunique()} URLs trocaram de nível entre uma execução e a outra.

As linhas têm status 200, não estão bloqueadas e mostram a página certa, então **não há motivo para descartá-las**. Parece um comportamento real da página, mas a causa não foi investigada. Na análise, isso pesa a favor da mediana e de testes não paramétricos, e contra supor uma distribuição log-normal para o LCP das categorias. A #C-3 precisa considerar essa mistura ao simular.

### Decomposição da variância em log (insumo da #C-3)

{_tabela_md(decomp, 4)}

`dp_entre_urls_log` e `dp_entre_execucoes_log` são os desvios-padrão, na escala log, do efeito aleatório de URL e do resíduo. A simulação de poder (#C-3) usa esses valores. Os detalhes de cada URL estão em `variancia_por_url.csv`.

## Limitações

- **Só {resumo['execucoes']} execuções por URL.** A variância entre execuções de cada URL vem de {int(var_url['n_execucoes'].max())} valores, então é uma estimativa muito instável. Ela serve como ordem de grandeza, não como parâmetro preciso.
- **Não há execução de pico no piloto.** A descritiva cobre só a madrugada. A #C-3 precisa supor que a variância do pico é igual à da madrugada, ou reestimá-la com as noites coletadas a partir de 20/11.
- **Não há variação entre dias** (é uma noite só), então o efeito aleatório de `data_brt` do modelo misto não pode ser estimado com o piloto.
- Nenhuma linha precisou ser descartada.
"""


def main() -> None:
    df = carregar_piloto()
    tab_cob, resumo = cobertura(df)
    base = validas(df)
    desc = descritiva(base)
    var_url = variancia_por_url(base)
    decomp = decompor_variancia(base)

    DIR_SAIDA.mkdir(parents=True, exist_ok=True)
    tab_cob.to_csv(DIR_SAIDA / "cobertura.csv", index=False)
    desc.to_csv(DIR_SAIDA / "descritiva.csv", index=False)
    var_url.to_csv(DIR_SAIDA / "variancia_por_url.csv", index=False)
    decomp.to_csv(DIR_SAIDA / "decomposicao_variancia.csv", index=False)
    (DIR_SAIDA / "relatorio.md").write_text(
        relatorio(tab_cob, resumo, base, desc, var_url, decomp), encoding="utf-8"
    )
    print(f"Piloto: {resumo['linhas']}/{resumo['linhas_esperadas']} linhas. Saídas em {DIR_SAIDA}")


if __name__ == "__main__":
    main()
