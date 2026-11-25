"""Script de análise completo (issue #15, C-4).

Lê os CSVs da coleta, aplica o filtro mínimo e gera a descritiva, o SLI de
LCP, a taxa de falhas da coleta, os testes de H1 a H5 com Holm, a
sensibilidade no desktop, o Cliff's delta e os gráficos. As escolhas seguem
o design (§5.8) e o plano de issues (#C-4); as funções estatísticas estão
em analysis/stats.py (#C-2).

Uso (na raiz do repositório):
    python analysis/analise.py --input data/raw
    python analysis/analise.py --input data/raw/2026-11-19_BRT.csv --out analysis/out/analise_piloto

--input aceita um diretório (concatena *.csv, sem descer em subpastas, então
data/raw/testes/ fica fora) ou um arquivo.
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from analysis.stats import (  # noqa: E402
    GATILHOS_VALIDOS,
    cliffs_delta,
    concordancia_crux,
    filtro_minimo,
    holm,
    kruskal_por_tipo,
    modelo_misto,
    por_url,
)

LIMIAR_SLO_MS = 2500
COMBINACAO = ["tipo", "strategy", "janela"]
METRICAS = [
    "lcp_ms", "fcp_ms", "speed_index_ms", "tbt_ms", "ttfb_ms",
    "total_bytes", "n_requests", "a11y_reprovadas", "perf_score", "a11y_score",
]
ORDEM_TIPOS = ["home", "categoria", "busca", "produto"]


# ---------------------------------------------------------------- entrada


def carregar(entrada: Path) -> pd.DataFrame:
    """Um arquivo CSV, ou todos os *.csv de um diretório (sem subpastas)."""
    arquivos = sorted(entrada.glob("*.csv")) if entrada.is_dir() else [entrada]
    if not arquivos:
        raise FileNotFoundError(f"Nenhum CSV em {entrada}")
    return pd.concat((pd.read_csv(a) for a in arquivos), ignore_index=True)


def taxa_falhas(bruto: pd.DataFrame) -> pd.DataFrame:
    """Linhas e execuções agendadas com bloqueio ou erro (antes do filtro)."""
    agendado = bruto[bruto["gatilho"].isin(GATILHOS_VALIDOS)].copy()
    agendado["falha"] = agendado["bloqueada"].fillna(False).astype(bool) | agendado["erro"].notna()
    por_exec = agendado.groupby("run_id")["falha"].any()
    return pd.DataFrame(
        [
            {"nivel": "linha", "total": len(agendado), "com_falha": int(agendado["falha"].sum())},
            {"nivel": "execucao", "total": len(por_exec), "com_falha": int(por_exec.sum())},
            {"nivel": "linha_bloqueada", "total": len(agendado),
             "com_falha": int(agendado["bloqueada"].fillna(False).astype(bool).sum())},
            {"nivel": "linha_com_erro", "total": len(agendado), "com_falha": int(agendado["erro"].notna().sum())},
        ]
    ).assign(taxa=lambda d: d["com_falha"] / d["total"].where(d["total"] > 0))


# ---------------------------------------------------------------- descritiva


def _serie(df: pd.DataFrame, metrica: str) -> pd.Series:
    """Valores da métrica; o TTFB usa só a fonte observada (docs/dados.md)."""
    if metrica == "ttfb_ms":
        df = df[df["ttfb_origem"] == "server-response-time"]
    return df[metrica].dropna()


def descritiva(df: pd.DataFrame, chaves: list[str]) -> pd.DataFrame:
    linhas = []
    for chave, parte in df.groupby(chaves):
        for m in METRICAS:
            s = _serie(parte, m)
            if s.empty:
                continue
            q = s.quantile([0.25, 0.5, 0.75, 0.9])
            linhas.append(
                dict(zip(chaves, chave))
                | {"metrica": m, "n": len(s), "mediana": q[0.5], "q1": q[0.25], "q3": q[0.75],
                   "iqr": q[0.75] - q[0.25], "p75": q[0.75], "p90": q[0.9]}
            )
    return pd.DataFrame(linhas)


def sli_lcp(df: pd.DataFrame) -> pd.DataFrame:
    """Fração das medições de cada combinação com LCP ≤ 2,5 s (SLO de referência)."""
    base = df.dropna(subset=["lcp_ms"])
    return (
        base.groupby(COMBINACAO)["lcp_ms"]
        .agg(n="size", cumpre=lambda s: int((s <= LIMIAR_SLO_MS).sum()))
        .reset_index()
        .assign(sli=lambda d: d["cumpre"] / d["n"])
    )


# ---------------------------------------------------------------- testes


def _n_modelo(df: pd.DataFrame, metrica: str) -> int:
    base = df[df[metrica] > 0]
    if metrica == "ttfb_ms":
        base = base[base["ttfb_origem"] == "server-response-time"]
    return len(base)


def testes(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """H1–H5 primários (com Holm) e a sensibilidade no desktop (sem Holm)."""
    t = df[df["tipo"] != "home"]
    movel, desktop = t[t["strategy"] == "mobile"], t[t["strategy"] == "desktop"]
    avisos = []

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        h1 = modelo_misto(t, "lcp_ms")
        h3 = modelo_misto(t, "ttfb_ms")
        h5 = concordancia_crux(t)
    h2 = kruskal_por_tipo(por_url(movel, "lcp_ms"), "lcp_ms")
    h4 = kruskal_por_tipo(por_url(movel, "a11y_reprovadas", agg="mode"), "a11y_reprovadas")
    for nome, res in (("H1", h1), ("H3", h3)):
        if not res["convergiu"]:
            avisos.append(f"O modelo misto de {nome} não convergiu.")

    ba = h5["bland_altman"]
    linhas = [
        {"hipotese": "H1", "teste": "Modelo misto, log(LCP)", "n": _n_modelo(t, "lcp_ms"),
         "estatistica_nome": "", "estatistica": np.nan, "p": h1["p_perfil"],
         "efeito_nome": "razão móvel/desktop", "efeito": h1["razao_perfil"],
         "ic_inf": h1["ic95_perfil"][0], "ic_sup": h1["ic95_perfil"][1], "outros": ""},
        {"hipotese": "H2", "teste": "Kruskal-Wallis, mediana do LCP por URL (móvel)", "n": int(movel["slot_id"].nunique()),
         "estatistica_nome": "H", "estatistica": h2["H"], "p": h2["p"],
         "efeito_nome": "ε²", "efeito": h2["eps2"], "ic_inf": np.nan, "ic_sup": np.nan, "outros": ""},
        {"hipotese": "H3", "teste": "Modelo misto, log(TTFB)", "n": _n_modelo(t, "ttfb_ms"),
         "estatistica_nome": "", "estatistica": np.nan, "p": h3["p_pico"],
         "efeito_nome": "razão pico/madrugada", "efeito": h3["razao_pico"],
         "ic_inf": h3["ic95_pico"][0], "ic_sup": h3["ic95_pico"][1], "outros": ""},
        {"hipotese": "H4", "teste": "Kruskal-Wallis, moda das reprovadas por URL (móvel)", "n": int(movel["slot_id"].nunique()),
         "estatistica_nome": "H", "estatistica": h4["H"], "p": h4["p"],
         "efeito_nome": "ε²", "efeito": h4["eps2"], "ic_inf": np.nan, "ic_sup": np.nan, "outros": ""},
        {"hipotese": "H5", "teste": "Wilcoxon pareado, LCP sintético × p75 CrUX (móvel)", "n": h5["n_pares"],
         "estatistica_nome": "", "estatistica": np.nan, "p": h5["wilcoxon_p"],
         "efeito_nome": "kappa (categoria)", "efeito": h5["kappa"], "ic_inf": np.nan, "ic_sup": np.nan,
         "outros": (f"Spearman ρ = {_f(h5['spearman_rho'])}; Bland-Altman: média {_f(ba['media'], 0)} ms, "
                    f"limites {_f(ba['limite_inferior'], 0)} a {_f(ba['limite_superior'], 0)} ms")},
    ]
    tabela = pd.DataFrame(linhas)

    validos = {r.hipotese: r.p for r in tabela.itertuples() if not np.isnan(r.p)}
    ajustados = holm(validos)
    tabela["p_holm"] = tabela["hipotese"].map(ajustados)
    fora = sorted(set(tabela["hipotese"]) - set(validos))
    if fora:
        avisos.append(f"Sem p-valor (ficaram fora do Holm): {', '.join(fora)}.")
    if h5["slots_sem_crux"]:
        avisos.append(f"Slots sem CrUX da própria URL (fora do H5): {', '.join(h5['slots_sem_crux'])}.")
    if t["janela"].nunique() < 2:
        avisos.append("Só há uma janela nos dados: o efeito de pico (H3) não pode ser estimado.")

    sens = []
    for h, metrica, agg in (("H2", "lcp_ms", "median"), ("H4", "a11y_reprovadas", "mode")):
        r = kruskal_por_tipo(por_url(desktop, metrica, agg=agg), metrica, strategy="desktop")
        sens.append({"hipotese": h, "perfil": "desktop", "H": r["H"], "p": r["p"], "eps2": r["eps2"]})

    dunn = {"H2": h2["dunn"], "H4": h4["dunn"]}
    return tabela, pd.DataFrame(sens), {"avisos": avisos, "dunn": dunn, "h5": h5}


def efeitos_cliff(df: pd.DataFrame) -> pd.DataFrame:
    """Cliff's delta sobre as medianas por slot: perfil (LCP) e horário (TTFB)."""
    t = df[df["tipo"] != "home"]
    lcp = t.groupby(["slot_id", "strategy"])["lcp_ms"].median().unstack()
    ttfb_base = t[t["ttfb_origem"] == "server-response-time"]
    ttfb = ttfb_base.groupby(["slot_id", "strategy", "janela"])["ttfb_ms"].median().unstack()

    def delta(tab, a, b):
        if a in tab and b in tab:
            x, y = tab[a].dropna(), tab[b].dropna()
            if len(x) and len(y):
                return cliffs_delta(x, y), len(x), len(y)
        return np.nan, 0, 0

    linhas = []
    for nome, metrica, tab, a, b in (
        ("perfil", "lcp_ms", lcp, "mobile", "desktop"),
        ("horario", "ttfb_ms", ttfb, "pico", "madrugada"),
    ):
        d, na, nb = delta(tab, a, b)
        linhas.append({"efeito": nome, "metrica": metrica, "grupo_a": a, "grupo_b": b,
                       "n_a": na, "n_b": nb, "cliffs_delta": d})
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------- gráficos


def boxplots(df: pd.DataFrame, pasta: Path) -> list[str]:
    nomes = []
    rotulos_metrica = {"lcp_ms": "LCP (ms)", "ttfb_ms": "TTFB (ms)", "a11y_reprovadas": "Auditorias reprovadas"}
    combos = [(s, j) for s in ("desktop", "mobile") for j in ("madrugada", "pico")
              if ((df["strategy"] == s) & (df["janela"] == j)).any()]
    cores = {("desktop", "madrugada"): "#9ecae1", ("desktop", "pico"): "#3182bd",
             ("mobile", "madrugada"): "#fdae6b", ("mobile", "pico"): "#e6550d"}
    tipos = [t for t in ORDEM_TIPOS if t in set(df["tipo"])]
    for m, rotulo in rotulos_metrica.items():
        fig, ax = plt.subplots(figsize=(9, 4.5))
        largura = 0.8 / max(len(combos), 1)
        for i, (s, j) in enumerate(combos):
            dados, pos = [], []
            for k, tipo in enumerate(tipos):
                parte = df[(df["tipo"] == tipo) & (df["strategy"] == s) & (df["janela"] == j)]
                valores = _serie(parte, m).to_numpy()
                if len(valores):
                    dados.append(valores)
                    pos.append(k - 0.4 + largura * (i + 0.5))
            if dados:
                bp = ax.boxplot(dados, positions=pos, widths=largura * 0.9, patch_artist=True,
                                showfliers=True, flierprops={"markersize": 2},
                                medianprops={"color": "black"})
                for caixa in bp["boxes"]:
                    caixa.set_facecolor(cores[(s, j)])
                ax.plot([], [], color=cores[(s, j)], lw=8, label=f"{s} · {j}")
        ax.set_xticks(range(len(tipos)), tipos)
        ax.set_ylabel(rotulo)
        if m != "a11y_reprovadas":
            ax.set_yscale("log")
        if m == "lcp_ms":
            ax.axhline(LIMIAR_SLO_MS, color="gray", ls="--", lw=1)
        ax.legend(fontsize=8, ncol=2)
        ax.set_title(f"{rotulo} por tipo × perfil × janela")
        fig.tight_layout()
        nome = f"boxplot_{m}.png"
        fig.savefig(pasta / nome, dpi=130)
        plt.close(fig)
        nomes.append(nome)
    return nomes


def bland_altman(df: pd.DataFrame, h5: dict, pasta: Path) -> str | None:
    movel = df[(df["strategy"] == "mobile") & (df["tipo"] != "home")]
    pares = movel.groupby("slot_id").agg(sintetico=("lcp_ms", "median"), crux=("crux_lcp_p75_ms", "median")).dropna()
    if len(pares) < 2:
        return None
    media = (pares["sintetico"] + pares["crux"]) / 2
    diff = pares["sintetico"] - pares["crux"]
    ba = h5["bland_altman"]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(media, diff, color="#3182bd")
    for slot, x, y in zip(pares.index, media, diff):
        ax.annotate(slot, (x, y), fontsize=7, xytext=(3, 3), textcoords="offset points")
    ax.axhline(ba["media"], color="black", lw=1, label=f"média {ba['media']:.0f} ms")
    ax.axhline(ba["limite_inferior"], color="gray", ls="--", lw=1, label="limites de concordância (±1,96 DP)")
    ax.axhline(ba["limite_superior"], color="gray", ls="--", lw=1)
    ax.axhline(0, color="gray", ls=":", lw=1)
    ax.set_xlabel("Média de LCP sintético e p75 do CrUX (ms)")
    ax.set_ylabel("Sintético − CrUX (ms)")
    ax.set_title("Bland-Altman: LCP sintético (móvel) × CrUX")
    ax.legend(fontsize=8)
    fig.tight_layout()
    nome = "bland_altman.png"
    fig.savefig(pasta / nome, dpi=130)
    plt.close(fig)
    return nome


# ---------------------------------------------------------------- relatório


def _f(x, casas: int = 3) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    if isinstance(x, (int, np.integer)):
        return f"{x:,}".replace(",", ".")
    if abs(x) < 0.001 and x != 0:
        return f"{x:.1e}".replace(".", ",")
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _p(x: float) -> str:
    """p-valor para o relatório: '< 0,001' quando muito pequeno."""
    if np.isnan(x):
        return "—"
    return "< 0,001" if x < 0.001 else _f(x)


def _tabela(df: pd.DataFrame, casas: int = 3) -> str:
    cab = "| " + " | ".join(df.columns) + " |\n|" + "|".join("---" for _ in df.columns) + "|"
    corpo = "\n".join("| " + " | ".join(_f(v, casas) if isinstance(v, (float, int, np.number)) else str(v)
                                          for v in r) + " |" for r in df.itertuples(index=False))
    return cab + "\n" + corpo


def relatorio(entrada, bruto, df, falhas, desc_agr, sli, tab, sens, cliff, extras, graficos) -> str:
    t = tab.copy()
    t["IC 95%"] = [
        "" if np.isnan(a) else f"{_f(a)} a {_f(b)}" for a, b in zip(t["ic_inf"], t["ic_sup"])
    ]
    for col in ("p", "p_holm"):
        t[col] = [_p(v) for v in t[col]]
    t = t[["hipotese", "teste", "n", "estatistica_nome", "estatistica", "p", "p_holm",
           "efeito_nome", "efeito", "IC 95%"]]
    n_dias = df["data_brt"].nunique()
    lcp = desc_agr[desc_agr["metrica"].isin(["lcp_ms", "ttfb_ms", "a11y_reprovadas"])]
    resumo = lcp.pivot_table(index=COMBINACAO, columns="metrica", values="mediana").reset_index()
    resumo = resumo.merge(sli[COMBINACAO + ["sli"]], on=COMBINACAO)
    avisos = "\n".join(f"- {a}" for a in extras["avisos"]) or "- Nenhum."
    outros_h5 = tab.loc[tab["hipotese"] == "H5", "outros"].iloc[0]
    dunn = "\n\n".join(
        f"**{h}** (p de Holm):\n\n" + _tabela(d.round(4).reset_index().rename(columns={"index": "tipo"}))
        for h, d in extras["dunn"].items()
    )
    figuras = "\n".join(f"![{g}]({g})" for g in graficos)
    return f"""# Análise (#C-4)

Gerado por `analysis/analise.py --input {entrada}`. Datas: {df['data_brt'].min()} a {df['data_brt'].max()} ({n_dias} {'dia' if n_dias == 1 else 'dias'}, {df['run_id'].nunique()} execuções). Linhas lidas: {len(bruto)}; após o filtro mínimo: {len(df)}.

## Avisos

{avisos}

## Testes de hipótese (primários, bilaterais, Holm sobre os 5)

{_tabela(t)}

H5: {outros_h5}.

### Post-hoc de Dunn

{dunn}

### Sensibilidade no desktop (fora do Holm)

{_tabela(sens)}

### Cliff's delta sobre as medianas por slot

{_tabela(cliff)}

## Descritiva: medianas e SLI por combinação

LCP e TTFB em ms; SLI = fração das medições com LCP ≤ 2,5 s. Os valores completos (IQR, p75, p90) estão em `descritiva_agregado.csv` e, por URL, em `descritiva_slot.csv`.

{_tabela(resumo, 2)}

## Falhas da coleta (disparos agendados, antes do filtro)

{_tabela(falhas)}

## Gráficos

{figuras}
"""


# ---------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, type=Path, help="diretório com *.csv ou um arquivo CSV")
    parser.add_argument("--out", default=RAIZ / "analysis" / "out", type=Path, help="pasta de saída")
    args = parser.parse_args(argv)

    bruto = carregar(args.input)
    df = filtro_minimo(bruto).reset_index(drop=True)
    args.out.mkdir(parents=True, exist_ok=True)

    falhas = taxa_falhas(bruto)
    desc_slot = descritiva(df, ["slot_id"] + COMBINACAO)
    desc_agr = descritiva(df, COMBINACAO)
    sli = sli_lcp(df)
    tab, sens, extras = testes(df)
    cliff = efeitos_cliff(df)
    graficos = boxplots(df, args.out)
    ba = bland_altman(df, extras["h5"], args.out)
    if ba:
        graficos.append(ba)

    falhas.to_csv(args.out / "falhas.csv", index=False)
    desc_slot.to_csv(args.out / "descritiva_slot.csv", index=False)
    desc_agr.to_csv(args.out / "descritiva_agregado.csv", index=False)
    sli.to_csv(args.out / "sli_lcp.csv", index=False)
    tab.to_csv(args.out / "tabela_hipoteses.csv", index=False)
    sens.to_csv(args.out / "sensibilidade_desktop.csv", index=False)
    cliff.to_csv(args.out / "cliffs_delta.csv", index=False)
    (args.out / "relatorio.md").write_text(
        relatorio(args.input.as_posix(), bruto, df, falhas, desc_agr, sli, tab, sens, cliff, extras, graficos),
        encoding="utf-8",
    )
    print(f"{len(df)} linhas analisadas. Saídas em {args.out}")


if __name__ == "__main__":
    main()
