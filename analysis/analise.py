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
    modelo_art,
    modelo_misto,
    por_url,
)
from scipy import stats as st  # noqa: E402

LIMIAR_SLO_MS = 2500
LIMIAR_ART = 0.05  # fração de resíduos padronizados além de ±3 que aciona o ART
N_BOOT = 2000
SEMENTE = 20261126
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
    url_lcp = por_url(movel, "lcp_ms")
    url_a11y = por_url(movel, "a11y_reprovadas", agg="mode")
    h2 = kruskal_por_tipo(url_lcp, "lcp_ms")
    h4 = kruskal_por_tipo(url_a11y, "a11y_reprovadas")
    for nome, res in (("H1", h1), ("H3", h3)):
        if not res["convergiu"]:
            avisos.append(f"O modelo misto de {nome} não convergiu.")

    # Critério fixado antes de olhar os p (design §5.8): mais de 5% dos
    # resíduos padronizados além de ±3 → o p primário vem do ART.
    diagnostico, p_mm = [], {}
    for nome, res, metrica, efeito, chave in (
        ("H1", h1, "lcp_ms", "strategy", "p_perfil"),
        ("H3", h3, "ttfb_ms", "janela", "p_pico"),
    ):
        frac = res["frac_residuos_3"]
        usa_art = frac > LIMIAR_ART and not np.isnan(res[chave])
        p_art = np.nan
        if usa_art:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                p_art = modelo_art(t, metrica, efeito)["p"]
        diagnostico.append({"hipotese": nome, "frac_residuos_3": frac, "limiar": LIMIAR_ART,
                            "usa_art": usa_art, "p_modelo_log": res[chave], "p_art": p_art})
        p_mm[nome] = (p_art if usa_art else res[chave], "ART (postos alinhados)" if usa_art else "modelo em log")

    ic_h2 = bootstrap_eps2(url_lcp, "lcp_ms")
    ic_h4 = bootstrap_eps2(url_a11y, "a11y_reprovadas")

    ba = h5["bland_altman"]
    linhas = [
        {"hipotese": "H1", "teste": "Modelo misto, log(LCP)", "metodo_p": p_mm["H1"][1], "n": _n_modelo(t, "lcp_ms"),
         "estatistica_nome": "", "estatistica": np.nan, "p": p_mm["H1"][0],
         "efeito_nome": "razão móvel/desktop", "efeito": h1["razao_perfil"],
         "ic_inf": h1["ic95_perfil"][0], "ic_sup": h1["ic95_perfil"][1], "ic_metodo": "Wald (modelo em log)",
         "outros": ""},
        {"hipotese": "H2", "teste": "Kruskal-Wallis, mediana do LCP por URL (móvel)", "metodo_p": "Kruskal-Wallis",
         "n": int(url_lcp["slot_id"].nunique()),
         "estatistica_nome": "H", "estatistica": h2["H"], "p": h2["p"],
         "efeito_nome": "ε²", "efeito": h2["eps2"], "ic_inf": ic_h2[0], "ic_sup": ic_h2[1],
         "ic_metodo": f"bootstrap percentil ({N_BOOT} reamostragens)", "outros": ""},
        {"hipotese": "H3", "teste": "Modelo misto, log(TTFB)", "metodo_p": p_mm["H3"][1], "n": _n_modelo(t, "ttfb_ms"),
         "estatistica_nome": "", "estatistica": np.nan, "p": p_mm["H3"][0],
         "efeito_nome": "razão pico/madrugada", "efeito": h3["razao_pico"],
         "ic_inf": h3["ic95_pico"][0], "ic_sup": h3["ic95_pico"][1], "ic_metodo": "Wald (modelo em log)",
         "outros": ""},
        {"hipotese": "H4", "teste": "Kruskal-Wallis, moda das reprovadas por URL (móvel)", "metodo_p": "Kruskal-Wallis",
         "n": int(url_a11y["slot_id"].nunique()),
         "estatistica_nome": "H", "estatistica": h4["H"], "p": h4["p"],
         "efeito_nome": "ε²", "efeito": h4["eps2"], "ic_inf": ic_h4[0], "ic_sup": ic_h4[1],
         "ic_metodo": f"bootstrap percentil ({N_BOOT} reamostragens)", "outros": ""},
        {"hipotese": "H5", "teste": "Wilcoxon pareado, LCP sintético × p75 CrUX (móvel)", "n": h5["n_pares"],
         "estatistica_nome": "", "estatistica": np.nan, "p": h5["wilcoxon_p"],
         "metodo_p": "Wilcoxon pareado",
         "efeito_nome": "kappa (categoria)", "efeito": h5["kappa"], "ic_inf": np.nan, "ic_sup": np.nan,
         "ic_metodo": "", "outros": (f"Spearman ρ = {_f(h5['spearman_rho'])}; Bland-Altman: média {_f(ba['media'], 0)} ms, "
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
    return tabela, pd.DataFrame(sens), {
        "avisos": avisos, "dunn": dunn, "h5": h5,
        "diagnostico": pd.DataFrame(diagnostico), "modelos": {"H1": h1, "H3": h3},
    }


def bootstrap_eps2(df_url: pd.DataFrame, metrica: str, n_boot: int = None, semente: int = SEMENTE) -> tuple[float, float]:
    """IC percentil de 95% do ε² do Kruskal-Wallis, reamostrando URLs dentro de cada tipo."""
    n_boot = n_boot or N_BOOT
    rng = np.random.default_rng(semente)
    base = df_url[df_url["tipo"] != "home"].dropna(subset=[metrica])
    grupos = [g[metrica].to_numpy() for _, g in base.groupby("tipo")]
    n = sum(len(g) for g in grupos)
    valores = []
    for _ in range(n_boot):
        amostra = [rng.choice(g, size=len(g), replace=True) for g in grupos]
        if np.ptp(np.concatenate(amostra)) == 0:
            valores.append(0.0)  # todos iguais: H = 0
            continue
        h = st.kruskal(*amostra).statistic
        valores.append(h * (n + 1) / (n**2 - 1))
    return tuple(float(v) for v in np.percentile(valores, [2.5, 97.5]))


def efeitos_cliff(df: pd.DataFrame, n_boot: int = None, semente: int = SEMENTE) -> pd.DataFrame:
    """Cliff's delta sobre as medianas por slot: perfil (LCP) e horário (TTFB), com IC por bootstrap.

    O bootstrap reamostra as unidades (slot, ou slot × perfil no horário)
    com os dois grupos juntos, porque as medianas vêm das mesmas URLs.
    """
    n_boot = n_boot or N_BOOT
    rng = np.random.default_rng(semente)
    t = df[df["tipo"] != "home"]
    lcp = t.groupby(["slot_id", "strategy"])["lcp_ms"].median().unstack()
    ttfb_base = t[t["ttfb_origem"] == "server-response-time"]
    ttfb = ttfb_base.groupby(["slot_id", "strategy", "janela"])["ttfb_ms"].median().unstack()

    linhas = []
    for nome, metrica, tab, a, b in (
        ("perfil", "lcp_ms", lcp, "mobile", "desktop"),
        ("horario", "ttfb_ms", ttfb, "pico", "madrugada"),
    ):
        d, ic, n = np.nan, (np.nan, np.nan), 0
        if a in tab and b in tab:
            pares = tab[[a, b]].dropna().to_numpy()
            n = len(pares)
            if n:
                d = cliffs_delta(pares[:, 0], pares[:, 1])
                boot = []
                for _ in range(n_boot):
                    amostra = pares[rng.integers(0, n, n)]
                    boot.append(cliffs_delta(amostra[:, 0], amostra[:, 1]))
                ic = tuple(float(v) for v in np.percentile(boot, [2.5, 97.5]))
        linhas.append({"efeito": nome, "metrica": metrica, "grupo_a": a, "grupo_b": b, "n_unidades": n,
                       "cliffs_delta": d, "ic_inf": ic[0], "ic_sup": ic[1]})
    return pd.DataFrame(linhas)


def graficos_residuos(modelos: dict, pasta: Path) -> list[str]:
    """QQ-plot e resíduos × ajustados dos modelos mistos de H1 e H3."""
    nomes = []
    rotulo = {"H1": "H1: log(LCP)", "H3": "H3: log(TTFB)"}
    for h, res in modelos.items():
        r, f = res["residuos_padronizados"], res["ajustados"]
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
        st.probplot(r, dist="norm", plot=ax1)
        ax1.set_title(f"QQ-plot dos resíduos padronizados — {rotulo[h]}")
        ax1.set_xlabel("Quantis teóricos (normal)")
        ax1.set_ylabel("Resíduos padronizados")
        ax2.scatter(f, r, s=6, alpha=0.5)
        for y in (-3, 3):
            ax2.axhline(y, color="gray", ls="--", lw=1)
        ax2.axhline(0, color="black", lw=0.8)
        ax2.set_title(f"Resíduos × ajustados — {rotulo[h]}")
        ax2.set_xlabel("Valor ajustado (log)")
        ax2.set_ylabel("Resíduo padronizado")
        fig.tight_layout()
        nome = f"residuos_{h}.png"
        fig.savefig(pasta / nome, dpi=130)
        plt.close(fig)
        nomes.append(nome)
    return nomes


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
    t = t[["hipotese", "teste", "metodo_p", "n", "estatistica_nome", "estatistica", "p", "p_holm",
           "efeito_nome", "efeito", "IC 95%"]]
    n_dias = df["data_brt"].nunique()
    diag = extras["diagnostico"].copy()
    diag["usa_art"] = diag["usa_art"].map({True: "sim", False: "não"})
    for col in ("p_modelo_log", "p_art"):
        diag[col] = [_p(v) for v in diag[col]]
    decisao = " ".join(
        f"{r.hipotese}: {_f(100 * r.frac_residuos_3, 1)}% dos resíduos além de ±3, "
        + ("acima de 5%, então o p primário vem do ART." if r.usa_art else "dentro do limite de 5%, então vale o modelo em log.")
        for r in extras["diagnostico"].itertuples()
    )
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
    return f"""# Análise (#C-4, #C-6)

Gerado por `analysis/analise.py --input {entrada}`. Datas: {df['data_brt'].min()} a {df['data_brt'].max()} ({n_dias} {'dia' if n_dias == 1 else 'dias'}, {df['run_id'].nunique()} execuções). Linhas lidas: {len(bruto)}; após o filtro mínimo: {len(df)}.

## Avisos

{avisos}

## Testes de hipótese (primários, bilaterais, Holm sobre os 5)

{_tabela(t)}

H5: {outros_h5}.

As razões de H1 e H3 têm IC de Wald do modelo em log; o ε² de H2 e H4 e o Cliff's delta têm IC percentil por bootstrap ({N_BOOT} reamostragens, semente {SEMENTE}).

### Diagnóstico dos modelos mistos e alternativa robusta

Critério fixado antes de olhar os p (design §5.8): se mais de 5% dos resíduos padronizados passarem de ±3, o p primário vem do modelo misto sobre postos alinhados (ART). {decisao}

{_tabela(diag)}

QQ-plots e resíduos × ajustados em `residuos_H1.png` e `residuos_H3.png`.

### Mudança de versão do Lighthouse

{extras['versao']}

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

    # Regra S1: se a versão do Lighthouse mudou, H1–H5 rodam de novo sem os dias afetados.
    sem_mudanca = None
    if "sinal_mudanca_versao" in df and df["sinal_mudanca_versao"].fillna(False).astype(bool).any():
        afetadas = sorted(df.loc[df["sinal_mudanca_versao"].fillna(False).astype(bool), "data_brt"].unique())
        sem_mudanca, _, _ = testes(df[~df["data_brt"].isin(afetadas)])
        extras["versao"] = (f"Houve mudança de versão em {', '.join(afetadas)}. H1–H5 sem esses dias estão em "
                            "`tabela_hipoteses_sem_mudanca.csv`, para comparar lado a lado.")
    else:
        versoes = ", ".join(sorted(df["lighthouse_version"].dropna().astype(str).unique()))
        extras["versao"] = (f"Não houve mudança de versão: todas as linhas usam o Lighthouse {versoes}. "
                            "A rodada sem os dias afetados não se aplica.")

    graficos = boxplots(df, args.out)
    ba = bland_altman(df, extras["h5"], args.out)
    if ba:
        graficos.append(ba)
    graficos += graficos_residuos(extras["modelos"], args.out)

    falhas.to_csv(args.out / "falhas.csv", index=False)
    desc_slot.to_csv(args.out / "descritiva_slot.csv", index=False)
    desc_agr.to_csv(args.out / "descritiva_agregado.csv", index=False)
    sli.to_csv(args.out / "sli_lcp.csv", index=False)
    tab.to_csv(args.out / "tabela_hipoteses.csv", index=False)
    sens.to_csv(args.out / "sensibilidade_desktop.csv", index=False)
    cliff.to_csv(args.out / "cliffs_delta.csv", index=False)
    extras["diagnostico"].to_csv(args.out / "diagnostico_residuos.csv", index=False)
    if sem_mudanca is not None:
        sem_mudanca.to_csv(args.out / "tabela_hipoteses_sem_mudanca.csv", index=False)
    (args.out / "relatorio.md").write_text(
        relatorio(args.input.as_posix(), bruto, df, falhas, desc_agr, sli, tab, sens, cliff, extras, graficos),
        encoding="utf-8",
    )
    print(f"{len(df)} linhas analisadas. Saídas em {args.out}")


if __name__ == "__main__":
    main()
