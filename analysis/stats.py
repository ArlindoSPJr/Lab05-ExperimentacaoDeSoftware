"""Biblioteca de análise do estudo (issue #13, C-2).

Funções usadas pelo script de análise (#C-4, #C-6), pela simulação de poder
(#C-3) e pela validação do dataset (#B-7). Hipóteses e testes no design
(docs/superpowers/specs/2026-11-16-mercadolivre-desempenho-acessibilidade-design.md):

- H1 (perfil) e H3 (pico): modelo_misto, efeito relatado como razão;
  alternativa robusta com art_alinhar.
- H2 (LCP por tipo) e H4 (reprovadas por tipo): por_url + kruskal_por_tipo.
- H5 (sintético × campo): concordancia_crux.
- Correção de múltiplos testes: holm. Tamanho de efeito de 2 níveis: cliffs_delta.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd
import scikit_posthocs as sp
import statsmodels.formula.api as smf
from scipy import stats as st

GATILHOS_VALIDOS = ["schedule", "agendador"]
FATORES = ["strategy", "janela", "tipo"]
# Limiares do CrUX para o LCP (ms).
LCP_FAST = 2500
LCP_AVERAGE = 4000


def filtro_minimo(df: pd.DataFrame) -> pd.DataFrame:
    """Linhas aproveitáveis: disparo agendado, sem bloqueio, sem erro e numa janela do estudo."""
    bloqueada = df["bloqueada"].fillna(False).astype(bool)
    ok = df["gatilho"].isin(GATILHOS_VALIDOS) & ~bloqueada & df["erro"].isna() & (df["janela"] != "fora")
    return df.loc[ok].copy()


def _menor_moda(serie: pd.Series) -> float:
    modas = serie.dropna().mode()
    return modas.min() if len(modas) else np.nan


def por_url(df: pd.DataFrame, metrica: str, agg: str = "median") -> pd.DataFrame:
    """Uma linha por slot_id × strategy (com o tipo), agregando a métrica.

    agg='median' usa a mediana; agg='mode' usa o valor modal e, em empate,
    o menor deles.
    """
    if agg == "median":
        funcao = "median"
    elif agg == "mode":
        funcao = _menor_moda
    else:
        raise ValueError(f"agg deve ser 'median' ou 'mode', não {agg!r}")
    return df.groupby(["slot_id", "strategy", "tipo"], as_index=False)[metrica].agg(funcao)


def kruskal_por_tipo(df_url: pd.DataFrame, metrica: str, strategy: str | None = "mobile") -> dict:
    """Kruskal-Wallis entre os tipos de página, sobre os valores agregados por URL.

    A home fica fora (é uma URL só). Por padrão usa o perfil móvel, que é o
    teste primário; strategy='desktop' dá a sensibilidade e None usa tudo.
    Devolve H, p, ε² = H·(n+1)/(n²−1) e o post-hoc de Dunn com p de Holm.
    """
    base = df_url[df_url["tipo"] != "home"]
    if strategy is not None and "strategy" in base.columns:
        base = base[base["strategy"] == strategy]
    base = base.dropna(subset=[metrica])
    grupos = [g[metrica].to_numpy() for _, g in base.groupby("tipo")]
    h, p = st.kruskal(*grupos)
    n = len(base)
    eps2 = h * (n + 1) / (n**2 - 1)
    dunn = sp.posthoc_dunn(base, val_col=metrica, group_col="tipo", p_adjust="holm")
    return {"H": float(h), "p": float(p), "eps2": float(eps2), "dunn": dunn}


def _razao(beta: float, ic: tuple[float, float]) -> tuple[float, tuple[float, float]]:
    """Converte o coeficiente Sum de um fator de 2 níveis na razão nível omitido / nível estimado."""
    return float(np.exp(-2 * beta)), (float(np.exp(-2 * ic[1])), float(np.exp(-2 * ic[0])))


def modelo_misto(df: pd.DataFrame, metrica: str) -> dict:
    """Modelo misto de log(métrica) com efeitos aleatórios cruzados de URL e dia.

    Fórmula: log(métrica) ~ C(strategy, Sum) * C(janela, Sum) * C(tipo, Sum),
    com componentes de variância de slot_id e data_brt (groups constante).
    Com a codificação Sum, o efeito de cada fator de 2 níveis é estimado na
    média dos outros fatores:
    - razao_perfil = mobile / desktop = exp(−2·β[desktop]);
    - razao_pico = pico / madrugada = exp(−2·β[madrugada]).

    Usa só valores > 0 e deixa a home fora (uma URL só, como nos testes por
    tipo). Para ttfb_ms, usa só o TTFB observado (ttfb_origem =
    server-response-time). Fatores com um nível só saem da fórmula e a razão
    correspondente volta NaN (ex.: o piloto, que só tem madrugada).
    A chave extra "convergiu" diz se o otimizador convergiu.
    """
    base = df[(df[metrica] > 0) & (df["tipo"] != "home")].copy()
    if metrica == "ttfb_ms" and "ttfb_origem" in base.columns:
        base = base[base["ttfb_origem"] == "server-response-time"]
    # Índice único: CSVs diários concatenados repetem o índice e o mixedlm se perde.
    base = base.reset_index(drop=True)
    base["y"] = np.log(base[metrica])

    fatores = [f for f in FATORES if base[f].nunique() > 1]
    formula = "y ~ " + (" * ".join(f"C({f}, Sum)" for f in fatores) if fatores else "1")
    vc = {"slot": "0 + C(slot_id)"}
    if base["data_brt"].nunique() > 1:
        vc["dia"] = "0 + C(data_brt)"
    modelo = smf.mixedlm(
        formula, base, groups=np.ones(len(base)), vc_formula=vc, re_formula="0"
    )
    # O bfgs (padrão) não convergiu nos dados de 19–23/11; o lbfgs converge e
    # chega a uma verossimilhança maior. Powell fica de reserva.
    ajuste = modelo.fit(reml=True, method=["lbfgs", "powell"])
    ic = ajuste.conf_int()

    resultado = {"convergiu": bool(ajuste.converged)}
    for chave, fator, nivel in (("perfil", "strategy", "desktop"), ("pico", "janela", "madrugada")):
        termo = f"C({fator}, Sum)[S.{nivel}]"
        if termo in ajuste.params.index:
            razao, ic_razao = _razao(ajuste.params[termo], (ic.loc[termo, 0], ic.loc[termo, 1]))
            p = float(ajuste.pvalues[termo])
        else:
            razao, ic_razao, p = np.nan, (np.nan, np.nan), np.nan
        resultado[f"razao_{chave}"] = razao
        resultado[f"ic95_{chave}"] = ic_razao
        resultado[f"p_{chave}"] = p
    return resultado


def categoria_lcp(ms: float) -> str:
    """Categoria do CrUX para um LCP em ms: FAST (≤ 2500), AVERAGE (≤ 4000) ou SLOW."""
    if ms <= LCP_FAST:
        return "FAST"
    if ms <= LCP_AVERAGE:
        return "AVERAGE"
    return "SLOW"


def _kappa(a: list[str], b: list[str]) -> float:
    """Kappa de Cohen (não ponderado) entre duas classificações."""
    a, b = np.asarray(a), np.asarray(b)
    if len(a) == 0:
        return np.nan
    po = float(np.mean(a == b))
    pe = sum(np.mean(a == c) * np.mean(b == c) for c in np.union1d(a, b))
    return float((po - pe) / (1 - pe)) if pe < 1 else np.nan


def concordancia_crux(df: pd.DataFrame) -> dict:
    """Concordância entre o LCP sintético (Lighthouse) e o p75 de campo (CrUX), no perfil móvel.

    O par de cada slot é (mediana do LCP sintético, mediana do crux_lcp_p75_ms).
    Slots sem dado de campo da própria URL entram em slots_sem_crux.
    """
    movel = df[df["strategy"] == "mobile"]
    por_slot = movel.groupby("slot_id").agg(sintetico=("lcp_ms", "median"), crux=("crux_lcp_p75_ms", "median"))
    sem_crux = sorted(por_slot.index[por_slot["crux"].isna()])
    pares = por_slot.dropna()
    n = len(pares)

    diff = pares["sintetico"] - pares["crux"]
    media, dp = float(diff.mean()) if n else np.nan, float(diff.std(ddof=1)) if n > 1 else np.nan
    wilcoxon_p = float(st.wilcoxon(pares["sintetico"], pares["crux"]).pvalue) if n >= 2 else np.nan
    rho = float(st.spearmanr(pares["sintetico"], pares["crux"]).statistic) if n >= 3 else np.nan
    kappa = _kappa(
        [categoria_lcp(v) for v in pares["sintetico"]],
        [categoria_lcp(v) for v in pares["crux"]],
    )
    return {
        "n_pares": n,
        "wilcoxon_p": wilcoxon_p,
        "spearman_rho": rho,
        "bland_altman": {"media": media, "limite_inferior": media - 1.96 * dp, "limite_superior": media + 1.96 * dp},
        "kappa": kappa,
        "slots_sem_crux": sem_crux,
    }


def holm(pvals: dict[str, float]) -> dict[str, float]:
    """Correção de Holm–Bonferroni (step-down), com p ajustado monotônico e limitado a 1."""
    ordem = sorted(pvals, key=pvals.get)
    m = len(ordem)
    ajustados, maximo = {}, 0.0
    for i, chave in enumerate(ordem):
        maximo = max(maximo, (m - i) * pvals[chave])
        ajustados[chave] = min(maximo, 1.0)
    return {chave: ajustados[chave] for chave in pvals}


def cliffs_delta(x, y) -> float:
    """Cliff's delta: P(X > Y) − P(X < Y), de −1 a 1."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    sinais = np.sign(x[:, None] - y[None, :])
    return float(sinais.mean())


def art_alinhar(df: pd.DataFrame, metrica: str, efeito: str) -> pd.DataFrame:
    """Postos alinhados (Aligned Rank Transform, Wobbrock et al., 2011) para um efeito.

    efeito é um fator ("strategy") ou uma interação ("strategy:janela") entre
    os fatores strategy, janela e tipo. Para cada linha:
        alinhado = y − média da célula + estimativa do efeito,
    em que a estimativa vem das médias marginais por inclusão–exclusão. Os
    postos (média nos empates) ficam na coluna <metrica>_art; depois, o modelo
    é ajustado sobre esses postos e só o efeito alinhado é interpretado.
    """
    termos = efeito.split(":")
    desconhecidos = set(termos) - set(FATORES)
    if desconhecidos:
        raise ValueError(f"Fatores desconhecidos: {sorted(desconhecidos)}")
    fatores = [f for f in FATORES if df[f].nunique() > 1]
    saida = df.dropna(subset=[metrica]).reset_index(drop=True)
    y = saida[metrica].astype(float)

    media_celula = saida.groupby(fatores)[metrica].transform("mean")
    estimativa = pd.Series(0.0, index=saida.index)
    for k in range(len(termos) + 1):
        for sub in combinations(termos, k):
            sinal = (-1) ** (len(termos) - k)
            media = saida.groupby(list(sub))[metrica].transform("mean") if sub else y.mean()
            estimativa += sinal * media
    saida[f"{metrica}_alinhado"] = y - media_celula + estimativa
    saida[f"{metrica}_art"] = saida[f"{metrica}_alinhado"].rank(method="average")
    return saida
