"""Validação e dataset consolidado da coleta principal (#B-7, issue #22).

Lê os CSVs brutos de data/raw/*.csv (sem subpastas: testes/ e exploratoria/ ficam
de fora), recorta a coleta principal pelo início de cada execução e aplica as
regras de validação de docs/proposta.md ("Regras de validação"):

- descarte D1–D4 (bloqueada, erro, janela 'fora', gatilho manual), as mesmas do
  analysis.stats.filtro_minimo, que é reusado aqui;
- sinalização S1 (mudança de lighthouse_version) e S2 (uso de reserva), que só
  marcam as linhas.

Também confere a cobertura contra o calendário do desenho: 28 pares
(data_brt, cron), 7 noites × 2 de pico e 7 madrugadas × 2, com 38 linhas cada.

Uso:  python scripts/validate.py
      python scripts/validate.py --raw data/raw --out data/processed/dataset.csv
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from analysis.stats import GATILHOS_VALIDOS, filtro_minimo  # noqa: E402

LINHAS_POR_EXECUCAO = 38  # 19 URLs × 2 perfis
# Cron nominal (UTC) -> janela esperada e deslocamento da data_brt em relação à noite.
# As execuções de pico têm a data_brt da noite (D). As de madrugada, a do dia seguinte (D+1).
CRONS = {
    "7 23 * * *": ("pico", 0),
    "7 1 * * *": ("pico", 0),
    "7 6 * * *": ("madrugada", 1),
    "7 8 * * *": ("madrugada", 1),
}
PRIMEIRA_NOITE = date(2026, 11, 18)
NOITES = 7  # 18/11 a 24/11
TOTAL_ESPERADO = LINHAS_POR_EXECUCAO * NOITES * len(CRONS)  # 1.064

INICIO_PADRAO = "2026-11-18T21:00Z"  # 18h BRT de 18/11, início da janela de pico
FIM_PADRAO = "2026-11-25T11:00Z"  # 08h BRT de 25/11, fim da janela de madrugada


def calendario() -> list[tuple[str, str]]:
    """Os 28 pares (data_brt, cron) esperados na coleta principal."""
    pares = []
    for noite in range(NOITES):
        for cron, (_, desloc) in CRONS.items():
            dia = PRIMEIRA_NOITE + timedelta(days=noite + desloc)
            pares.append((dia.isoformat(), cron))
    return pares


def ler_brutos(raw_dir: str) -> pd.DataFrame:
    """Concatena os *.csv do diretório, sem descer em subpastas."""
    arquivos = sorted(Path(raw_dir).glob("*.csv"))
    if not arquivos:
        raise FileNotFoundError(f"nenhum CSV em {raw_dir}")
    # erro como texto: "400" e não 400.0.
    return pd.concat([pd.read_csv(a, dtype={"erro": str}) for a in arquivos], ignore_index=True)


def _anomalia(tipo: str, **campos) -> dict:
    return {"tipo": tipo, **campos}


def _casar_execucoes(execucoes: pd.DataFrame) -> tuple[dict, list[dict]]:
    """Associa cada execução de calendário a um par (data_brt, cron) esperado.

    1. Casamento direto: mesma data_brt, mesmo cron e janela igual à esperada do cron.
    2. Remanejamento: uma execução cuja janela real difere da do cron (ex.: o pico de
       18/11 que atrasou e mediu na madrugada de 19/11, anomalia 1) ocupa um par
       ainda vago com a mesma data_brt e a mesma janela real.
    3. O que sobrar é execução extra (sinalizada, as linhas ficam).

    Devolve ({run_id: par ou None}, anomalias).
    """
    vagos = set(calendario())
    destino: dict[str, tuple[str, str] | None] = {}
    anomalias: list[dict] = []
    pendentes = []
    for run in execucoes.itertuples():
        par = (run.data_brt, run.cron)
        if par in vagos and CRONS.get(run.cron, (None,))[0] == run.janela:
            vagos.discard(par)
            destino[run.run_id] = par
        else:
            pendentes.append(run)
    for run in pendentes:
        candidatos = sorted(p for p in vagos if p[0] == run.data_brt and CRONS[p[1]][0] == run.janela)
        if candidatos:
            par = candidatos[0]
            vagos.discard(par)
            destino[run.run_id] = par
            anomalias.append(_anomalia(
                "execucao_remanejada", run_id=run.run_id, data_brt=run.data_brt,
                detalhe=f"cron nominal '{run.cron}' mediu na janela '{run.janela}'; conta como '{par[1]}'"))
        else:
            destino[run.run_id] = None
            anomalias.append(_anomalia(
                "execucao_extra", run_id=run.run_id, data_brt=run.data_brt,
                detalhe=f"cron '{run.cron}', janela '{run.janela}' sem par vago no calendário"))
    for data_brt, cron in sorted(vagos):
        anomalias.append(_anomalia(
            "execucao_ausente", run_id="", data_brt=data_brt,
            detalhe=f"nenhuma execução de {CRONS[cron][0]} para o cron '{cron}'"))
    return destino, anomalias


def validate(raw_dir: str, inicio: str = INICIO_PADRAO, fim: str = FIM_PADRAO
             ) -> tuple[pd.DataFrame, list[dict]]:
    """Devolve (dataset validado, anomalias). Não grava nada.

    O recorte usa o ts_inicio_utc de cada execução, no intervalo [inicio, fim): uma
    execução que começou dentro dele entra inteira, mesmo que termine depois.
    """
    bruto = ler_brutos(raw_dir)
    inicio_ts = bruto["ts_inicio_utc"].pipe(pd.to_datetime, utc=True, format="ISO8601")
    no_recorte = (inicio_ts >= pd.Timestamp(inicio)) & (inicio_ts < pd.Timestamp(fim))
    df = bruto.loc[no_recorte].copy()
    df["bloqueada"] = df["bloqueada"].fillna(False).astype(bool)
    anomalias: list[dict] = []

    # Execuções de calendário: disparo agendado e numa janela do estudo.
    por_run = df.groupby("run_id").agg(
        gatilho=("gatilho", "first"), cron=("cron", "first"), data_brt=("data_brt", "first"),
        janela=("janela", "first"), ts_inicio_utc=("ts_inicio_utc", "first"), n=("slot_id", "size"),
    ).reset_index().sort_values("ts_inicio_utc")
    de_calendario = por_run[por_run["gatilho"].isin(GATILHOS_VALIDOS) & (por_run["janela"] != "fora")]
    destino, anomalias_cal = _casar_execucoes(de_calendario)
    anomalias += anomalias_cal

    for run in de_calendario.itertuples():
        if run.n != LINHAS_POR_EXECUCAO:
            anomalias.append(_anomalia(
                "cobertura_incompleta", run_id=run.run_id, data_brt=run.data_brt,
                detalhe=f"{run.n} de {LINHAS_POR_EXECUCAO} linhas"))

    # Descartes D1–D4, registrados linha a linha.
    validas = filtro_minimo(df)
    for idx, linha in df.drop(index=validas.index).iterrows():
        if linha["gatilho"] not in GATILHOS_VALIDOS:
            tipo = "descartada_manual"
        elif linha["janela"] == "fora":
            tipo = "descartada_fora"
        elif linha["bloqueada"]:
            tipo = "descartada_bloqueada"
        else:
            tipo = "descartada_erro"
        anomalias.append(_anomalia(
            tipo, run_id=linha["run_id"], data_brt=linha["data_brt"],
            detalhe=f"{linha['slot_id']} {linha['strategy']}"
                    + (f": {str(linha['erro'])[:80]}" if pd.notna(linha["erro"]) else "")))

    # Sinalizações S1 (versão) e S2 (reserva): as linhas ficam.
    validas = validas.sort_values(["ts_inicio_utc", "posicao"])
    versao_base = validas["lighthouse_version"].iloc[0] if len(validas) else None
    validas["sinal_mudanca_versao"] = validas["lighthouse_version"] != versao_base
    afetadas = validas[validas["sinal_mudanca_versao"]]
    if len(afetadas):
        dias = ", ".join(sorted(afetadas["data_brt"].unique()))
        versoes = ", ".join(sorted(map(str, afetadas["lighthouse_version"].unique())))
        anomalias.append(_anomalia(
            "mudanca_versao", run_id="", data_brt=dias,
            detalhe=f"{len(afetadas)} linhas com {versoes} (base {versao_base})"))
    for linha in validas[validas["usou_reserva"].fillna(False).astype(bool)].itertuples():
        anomalias.append(_anomalia(
            "uso_reserva", run_id=linha.run_id, data_brt=linha.data_brt,
            detalhe=f"{linha.slot_id} {linha.strategy}: {linha.url_usada}"))

    validas["par_calendario"] = validas["run_id"].map(
        lambda r: f"{destino[r][0]} {destino[r][1]}" if destino.get(r) else "")
    validas = validas.reset_index(drop=True)
    validas.attrs["reconciliacao"] = _reconciliar(df, validas, destino, anomalias)
    return validas, anomalias


def _reconciliar(df: pd.DataFrame, validas: pd.DataFrame, destino: dict, anomalias: list[dict]) -> dict:
    """Fecha a conta contra as 1.064 medições esperadas.

    esperado = mantidas + excluídas + faltantes + 38 × ausentes, contando só as
    execuções que ocupam um par do calendário. Linhas no recorte fora do
    calendário (manuais, janela 'fora', execuções extras) são contadas à parte.
    """
    runs_cal = {run for run, par in destino.items() if par}
    linhas_cal = df[df["run_id"].isin(runs_cal)]
    mantidas = int(validas["run_id"].isin(runs_cal).sum())
    faltantes = int(sum(LINHAS_POR_EXECUCAO - n for n in linhas_cal.groupby("run_id").size()))
    ausentes = sum(a["tipo"] == "execucao_ausente" for a in anomalias)
    conta = {
        "dataset": len(validas),
        "execucoes_no_dataset": int(validas["run_id"].nunique()),
        "dataset_de_calendario": mantidas,
        "excluidas_de_calendario": len(linhas_cal) - mantidas,
        "faltantes_em_execucoes": faltantes,
        "execucoes_ausentes": ausentes,
        "linhas_fora_do_calendario": len(df) - len(linhas_cal),
    }
    conta["total"] = mantidas + conta["excluidas_de_calendario"] + faltantes + LINHAS_POR_EXECUCAO * ausentes
    conta["fecha"] = conta["total"] == TOTAL_ESPERADO
    return conta


MARCA_INICIO = "<!-- validate.py: início -->"
MARCA_FIM = "<!-- validate.py: fim -->"


def secao_anomalias(anomalias: list[dict], conta: dict, inicio: str, fim: str) -> str:
    """Seção Markdown gerada para docs/anomalias.md (substituída a cada execução)."""
    linhas = [
        MARCA_INICIO,
        "## Validação da coleta principal (`scripts/validate.py`, #B-7)",
        "",
        f"Seção gerada por `python scripts/validate.py`. Recorte por `ts_inicio_utc` em [{inicio}, {fim}). "
        "Regras D1–D4 e S1–S2 de [`proposta.md`](proposta.md#regras-de-validação).",
        "",
        "**Reconciliação:** "
        f"{conta['dataset_de_calendario']} no dataset + {conta['excluidas_de_calendario']} excluídas "
        f"+ {conta['faltantes_em_execucoes']} faltantes + {LINHAS_POR_EXECUCAO} × {conta['execucoes_ausentes']} "
        f"ausentes = {conta['total']} (esperado {TOTAL_ESPERADO}: "
        f"{'fecha' if conta['fecha'] else 'NÃO fecha'}). "
        f"Dataset final: {conta['dataset']} linhas de {conta['execucoes_no_dataset']} execuções. "
        f"Linhas no recorte fora do calendário: {conta['linhas_fora_do_calendario']}.",
        "",
        "| Tipo | Ação | `run_id` | `data_brt` | Detalhe |",
        "|---|---|---|---|---|",
    ]
    acao = {"execucao_ausente": "registrar", "execucao_remanejada": "sinalizar", "execucao_extra": "sinalizar",
            "cobertura_incompleta": "sinalizar", "mudanca_versao": "sinalizar (S1)",
            "uso_reserva": "sinalizar (S2)", "descartada_bloqueada": "descartar (D1)",
            "descartada_erro": "descartar (D2)", "descartada_fora": "descartar (D3)",
            "descartada_manual": "descartar (D4)"}
    for a in sorted(anomalias, key=lambda a: (a["data_brt"], a["tipo"], a["run_id"])):
        detalhe = str(a["detalhe"]).replace("|", "\\|")
        linhas.append(f"| `{a['tipo']}` | {acao.get(a['tipo'], '')} | {a['run_id'] and '`' + a['run_id'] + '`'} "
                      f"| {a['data_brt']} | {detalhe} |")
    if not anomalias:
        linhas.append("| — | — | — | — | nenhuma anomalia |")
    linhas.append(MARCA_FIM)
    return "\n".join(linhas) + "\n"


def gravar_anomalias(caminho: Path, secao: str) -> None:
    texto = caminho.read_text(encoding="utf-8") if caminho.exists() else ""
    if MARCA_INICIO in texto and MARCA_FIM in texto:
        antes = texto[:texto.index(MARCA_INICIO)]
        depois = texto[texto.index(MARCA_FIM) + len(MARCA_FIM):].lstrip("\n")
        texto = antes + secao + ("\n" + depois if depois else "")
    else:
        texto = texto.rstrip("\n") + "\n\n" + secao
    caminho.write_text(texto, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida a coleta e grava o dataset consolidado.")
    parser.add_argument("--raw", default=str(RAIZ / "data" / "raw"))
    parser.add_argument("--out", default=str(RAIZ / "data" / "processed" / "dataset.csv"))
    parser.add_argument("--anomalias", default=str(RAIZ / "docs" / "anomalias.md"))
    parser.add_argument("--inicio", default=INICIO_PADRAO)
    parser.add_argument("--fim", default=FIM_PADRAO)
    args = parser.parse_args()

    dataset, anomalias = validate(args.raw, args.inicio, args.fim)
    conta = dataset.attrs["reconciliacao"]

    saida = Path(args.out)
    saida.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(saida, index=False)
    gravar_anomalias(Path(args.anomalias), secao_anomalias(anomalias, conta, args.inicio, args.fim))

    print(f"Dataset: {saida} ({conta['dataset']} linhas, {conta['execucoes_no_dataset']} execuções)")
    print("Reconciliação: "
          f"{conta['dataset_de_calendario']} + {conta['excluidas_de_calendario']} excluídas "
          f"+ {conta['faltantes_em_execucoes']} faltantes + {LINHAS_POR_EXECUCAO} × {conta['execucoes_ausentes']} "
          f"ausentes = {conta['total']} (esperado {TOTAL_ESPERADO}) -> {'OK' if conta['fecha'] else 'NÃO FECHA'}")
    print(f"Linhas no recorte fora do calendário: {conta['linhas_fora_do_calendario']}")
    for tipo in sorted({a["tipo"] for a in anomalias}):
        print(f"  {tipo}: {sum(a['tipo'] == tipo for a in anomalias)}")
    return 0 if conta["fecha"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
