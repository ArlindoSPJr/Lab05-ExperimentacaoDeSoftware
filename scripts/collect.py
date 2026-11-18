"""Coletor do estudo: mede as URLs de config/urls.csv pela API do PageSpeed Insights (PSI).

Regras éticas aplicadas aqui (docs/etica.md §7):
- o coletor só chama a API da PSI e nunca faz requisição direta aos hosts do Mercado Livre;
- as chamadas são sequenciais, com pelo menos 2 s entre o fim de uma e o início da próxima;
- as capturas de tela são removidas antes de gravar o JSON;
- a chave da API nunca é impressa nem gravada.

Uso:
    python scripts/collect.py --urls config/urls.csv --out data/raw --json out/json
Variáveis de ambiente: PSI_API_KEY (obrigatória), GATILHO e CRON.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests

PSI_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
STRATEGIES = ("mobile", "desktop")
ESPERA_ENTRE_CHAMADAS_S = 2
BRT = timezone(timedelta(hours=-3))  # UTC-3 fixo: o Brasil não tem horário de verão
DIAS_SEMANA = ("seg", "ter", "qua", "qui", "sex", "sab", "dom")

HOSTS_ML = {
    "www.mercadolivre.com.br",
    "lista.mercadolivre.com.br",
    "produto.mercadolivre.com.br",
}
TRECHOS_CAMINHO_BLOQUEIO = ("login", "registration", "/jms/", "lgz", "captcha", "account-verification")
# "entrar" e "segurança" exigem a expressão inteira para não marcar produtos como "Bota de segurança".
TITULO_BLOQUEIO = re.compile(r"captcha|\bentrar\b|^segurança\s*[—–-]\s*mercado livre", re.IGNORECASE)
AUDITORIAS_DE_IMAGEM = ("final-screenshot", "screenshot-thumbnails", "full-page-screenshot")

COLUNAS_EXECUCAO = [
    "run_id", "gatilho", "cron", "ts_inicio_utc", "ts_utc", "data_brt", "dia_semana", "janela",
    "posicao", "slot_id", "tipo", "strategy", "url_usada", "usou_reserva", "tentativas", "erro", "bloqueada",
]
COLUNAS_METRICAS = [
    "lcp_ms", "fcp_ms", "speed_index_ms", "tbt_ms", "ttfb_ms", "ttfb_origem", "total_bytes", "n_requests",
    "perf_score", "a11y_score", "a11y_reprovadas", "a11y_reprovadas_ids", "lighthouse_version", "user_agent",
    "final_url", "status_http", "titulo", "throttling", "crux_lcp_p75_ms", "crux_lcp_categoria",
    "crux_inp_p75_ms", "crux_cls_p75", "crux_origin_fallback", "crux_origin_lcp_p75_ms",
]


@dataclass(frozen=True)
class UrlSlot:
    slot_id: str
    tipo: str
    url: str
    url_reserva: str | None
    host: str
    mlb_id: str | None


def load_urls(path: str) -> list[UrlSlot]:
    """Lê o CSV de URLs. Campos opcionais vazios viram None."""
    with open(path, encoding="utf-8-sig", newline="") as arquivo:
        return [
            UrlSlot(
                slot_id=linha["slot_id"],
                tipo=linha["tipo"],
                url=linha["url"],
                url_reserva=linha["url_reserva"] or None,
                host=linha["host"],
                mlb_id=linha["mlb_id"] or None,
            )
            for linha in csv.DictReader(arquivo)
        ]


def janela_brt(ts_utc: datetime) -> tuple[str, str]:
    """Devolve a data BRT e a janela: 18h-23h59 pico, 00h-07h59 madrugada, demais fora."""
    local = ts_utc.astimezone(BRT)
    if local.hour >= 18:
        janela = "pico"
    elif local.hour < 8:
        janela = "madrugada"
    else:
        janela = "fora"
    return local.date().isoformat(), janela


def _valor(audits: dict, nome: str) -> float | None:
    return audits.get(nome, {}).get("numericValue")


def _itens_de_rede(audits: dict) -> list[dict]:
    return audits.get("network-requests", {}).get("details", {}).get("items", []) or []


def _documento_principal(itens: list[dict], final_url: str) -> dict | None:
    for item in itens:
        if item.get("url") == final_url:
            return item
    return next((item for item in itens if item.get("resourceType") == "Document"), None)


def _ttfb(audits: dict) -> tuple[float | None, str | None]:
    """Obtém o TTFB observado. O valor de `metrics` é simulado e só serve de alternativa registrada."""
    valor = _valor(audits, "server-response-time")
    if valor is not None:
        return valor, "server-response-time"
    itens = audits.get("metrics", {}).get("details", {}).get("items", []) or [{}]
    valor = itens[0].get("timeToFirstByte")
    return (valor, "metrics") if valor is not None else (None, None)


def _crux(psi: dict) -> dict:
    """Separa o CrUX da URL do CrUX da origem (usado só como referência)."""
    experiencia = psi.get("loadingExperience") or {}
    metricas = experiencia.get("metrics") or {}
    tem_dado_da_url = bool(metricas) and experiencia.get("origin_fallback") is not True
    if not tem_dado_da_url:
        metricas = {}

    lcp = metricas.get("LARGEST_CONTENTFUL_PAINT_MS", {})
    cls = metricas.get("CUMULATIVE_LAYOUT_SHIFT_SCORE", {}).get("percentile")
    origem = (psi.get("originLoadingExperience") or {}).get("metrics") or {}
    return {
        "crux_lcp_p75_ms": lcp.get("percentile"),
        "crux_lcp_categoria": lcp.get("category"),
        "crux_inp_p75_ms": metricas.get("INTERACTION_TO_NEXT_PAINT", {}).get("percentile"),
        "crux_cls_p75": cls / 100 if cls is not None else None,  # a PSI devolve o CLS multiplicado por 100
        "crux_origin_fallback": not tem_dado_da_url,
        "crux_origin_lcp_p75_ms": origem.get("LARGEST_CONTENTFUL_PAINT_MS", {}).get("percentile"),
    }


def extract_metrics(psi: dict) -> dict:
    """Transforma a resposta da PSI nas métricas do estudo (dicionário em docs/dados.md)."""
    lhr = psi.get("lighthouseResult") or {}
    audits = lhr.get("audits") or {}
    categorias = lhr.get("categories") or {}
    acessibilidade = categorias.get("accessibility") or {}

    final_url = lhr.get("mainDocumentUrl") or lhr.get("finalDisplayedUrl") or lhr.get("finalUrl") or ""
    itens = _itens_de_rede(audits)
    documento = _documento_principal(itens, final_url)
    ttfb, ttfb_origem = _ttfb(audits)
    reprovadas = [
        ref["id"] for ref in acessibilidade.get("auditRefs", [])
        if audits.get(ref["id"], {}).get("score") == 0
    ]

    return {
        "lcp_ms": _valor(audits, "largest-contentful-paint"),
        "fcp_ms": _valor(audits, "first-contentful-paint"),
        "speed_index_ms": _valor(audits, "speed-index"),
        "tbt_ms": _valor(audits, "total-blocking-time"),
        "ttfb_ms": ttfb,
        "ttfb_origem": ttfb_origem,
        "total_bytes": _valor(audits, "total-byte-weight"),
        "n_requests": len(itens),
        "perf_score": (categorias.get("performance") or {}).get("score"),
        "a11y_score": acessibilidade.get("score"),
        "a11y_reprovadas": len(reprovadas),
        "a11y_reprovadas_ids": reprovadas,
        "lighthouse_version": lhr.get("lighthouseVersion", ""),
        "user_agent": lhr.get("userAgent", ""),
        "final_url": final_url,
        "status_http": documento.get("statusCode") if documento else None,
        "titulo": lhr.get("title") or "",
        "throttling": json.dumps((lhr.get("configSettings") or {}).get("throttling")),
        **_crux(psi),
    }


def call_psi(url: str, strategy: str, api_key: str, session, max_retries: int = 2, espera_s: float = 5,
             sleep=time.sleep) -> tuple[dict | None, int, str | None]:
    """Chama a PSI com novas tentativas em 429, 5xx e falha de rede. Devolve (json, tentativas, erro)."""
    parametros = [
        ("url", url), ("strategy", strategy), ("category", "PERFORMANCE"),
        ("category", "ACCESSIBILITY"), ("key", api_key),
    ]
    erro = None
    for tentativa in range(1, max_retries + 2):
        try:
            resposta = session.get(PSI_ENDPOINT, params=parametros, timeout=120)
        except (requests.RequestException, OSError) as excecao:
            # Só o tipo do erro: a mensagem da exceção pode conter a URL com a chave.
            erro = type(excecao).__name__
        else:
            if resposta.status_code == 200:
                return resposta.json(), tentativa, None
            erro = str(resposta.status_code)
            if resposta.status_code != 429 and resposta.status_code < 500:
                return None, tentativa, erro
        if tentativa <= max_retries:
            sleep(espera_s)
    return None, max_retries + 1, erro


def detect_block(metrics: dict, slot: UrlSlot) -> bool:
    """Indica captcha, login, página de erro ou redirecionamento para fora do site esperado."""
    status = metrics.get("status_http")
    if status is not None and status != 200:
        return True
    partes = urlsplit(metrics.get("final_url") or "")
    if partes.hostname and partes.hostname != slot.host and partes.hostname not in HOSTS_ML:
        return True
    caminho = partes.path.lower()
    if any(trecho in caminho for trecho in TRECHOS_CAMINHO_BLOQUEIO):
        return True
    return bool(TITULO_BLOQUEIO.search(metrics.get("titulo") or ""))


def strip_screenshots(psi: dict) -> dict:
    """Remove as imagens da resposta, que podem mostrar nomes de pessoas."""
    lhr = psi.get("lighthouseResult") or {}
    lhr.pop("fullPageScreenshot", None)
    audits = lhr.get("audits") or {}
    for nome in AUDITORIAS_DE_IMAGEM:
        audits.pop(nome, None)
    for categoria in (lhr.get("categories") or {}).values():
        if "auditRefs" in categoria:
            categoria["auditRefs"] = [ref for ref in categoria["auditRefs"] if ref.get("id") not in AUDITORIAS_DE_IMAGEM]
    return psi


def resolve_url(slot: UrlSlot, estado_reservas: dict) -> tuple[str, bool]:
    """Escolhe a URL do slot. Só produtos com reserva podem trocar."""
    marcado = (estado_reservas.get(slot.slot_id) or {}).get("indisponivel") is True
    if slot.tipo == "produto" and slot.url_reserva and marcado:
        return slot.url_reserva, True
    return slot.url, False


def _produto_sumiu(medicao: dict, slot: UrlSlot) -> bool:
    if medicao.get("status_http") in (404, 410):
        return True
    # Uma tela de captcha também não traz o ID, mas não prova que o produto esgotou.
    return not medicao.get("bloqueada") and bool(slot.mlb_id) and slot.mlb_id not in (medicao.get("final_url") or "")


def atualizar_estado(estado: dict, observacoes: dict) -> dict:
    """Conta execuções seguidas sem o produto. Com 2, o slot passa para a reserva na execução seguinte.

    `observacoes` mapeia slot_id para (slot, medições da URL original nesta execução).
    """
    for slot_id, (slot, medicoes) in observacoes.items():
        registro = estado.setdefault(slot_id, {"indisponivel": False, "falhas_seguidas": 0})
        registro.setdefault("indisponivel", False)
        registro.setdefault("falhas_seguidas", 0)
        if not medicoes:
            continue  # execução sem medição válida não confirma nem descarta a falta do produto
        if all(_produto_sumiu(medicao, slot) for medicao in medicoes):
            registro["falhas_seguidas"] += 1
        elif not any(medicao.get("bloqueada") for medicao in medicoes):
            registro["falhas_seguidas"] = 0
        if registro["falhas_seguidas"] >= 2:
            registro["indisponivel"] = True
    return estado


def _ler_estado(caminho: Path) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else {}


def _medir(slot: UrlSlot, url: str, strategy: str, api_key: str, session, sleep) -> tuple[dict, int, str | None, bool, dict | None]:
    """Faz uma medição e devolve (métricas, tentativas, erro, bloqueada, json sem imagens)."""
    psi, tentativas, erro = call_psi(url, strategy, api_key, session, sleep=sleep)
    if psi is None:
        return {}, tentativas, erro, False, None
    psi = strip_screenshots(psi)
    falha_lighthouse = (psi.get("lighthouseResult") or {}).get("runtimeError")
    if falha_lighthouse:
        return {}, tentativas, str(falha_lighthouse.get("code", "runtimeError")), False, psi
    metricas = extract_metrics(psi)
    return metricas, tentativas, None, detect_block(metricas, slot), psi


def run(urls_path, out_dir, json_dir, api_key, seed=None, session=None, sleep=time.sleep,
        now=lambda: datetime.now(timezone.utc), gatilho="local", cron="", estado_path=None) -> str:
    """Executa uma rodada completa (19 URLs x 2 perfis) e devolve o caminho do CSV gravado."""
    session = session or requests.Session()
    slots = load_urls(urls_path)
    inicio = now()
    # Data e janela valem para a execução inteira, mesmo que ela passe da meia-noite.
    data_brt, janela = janela_brt(inicio)
    dia_semana = DIAS_SEMANA[date.fromisoformat(data_brt).weekday()]
    run_id = inicio.strftime("%Y%m%dT%H%M%SZ")

    pasta_csv = Path(out_dir)
    pasta_csv.mkdir(parents=True, exist_ok=True)
    pasta_json = Path(json_dir) / run_id
    pasta_json.mkdir(parents=True, exist_ok=True)
    caminho_estado = Path(estado_path) if estado_path else pasta_csv / "estado_reservas.json"
    estado = _ler_estado(caminho_estado)

    chamadas = [(slot, strategy) for slot in slots for strategy in STRATEGIES]
    random.Random(seed).shuffle(chamadas)

    caminho_csv = pasta_csv / f"{data_brt}_BRT.csv"
    arquivo_novo = not caminho_csv.exists()
    observacoes = {slot.slot_id: (slot, []) for slot in slots if slot.tipo == "produto"}

    with open(caminho_csv, "a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS_EXECUCAO + COLUNAS_METRICAS)
        if arquivo_novo:
            escritor.writeheader()

        for posicao, (slot, strategy) in enumerate(chamadas, start=1):
            if posicao > 1:
                sleep(ESPERA_ENTRE_CHAMADAS_S)
            url, usou_reserva = resolve_url(slot, estado)
            ts_chamada = now()
            metricas, tentativas, erro, bloqueada, psi = _medir(slot, url, strategy, api_key, session, sleep)

            if psi is not None:
                destino = pasta_json / f"{slot.slot_id}_{strategy}.json"
                destino.write_text(json.dumps(psi, ensure_ascii=False), encoding="utf-8")
            if erro is None and not usou_reserva and slot.slot_id in observacoes:
                observacoes[slot.slot_id][1].append({**metricas, "bloqueada": bloqueada})

            linha = {
                "run_id": run_id, "gatilho": gatilho, "cron": cron,
                "ts_inicio_utc": inicio.isoformat(), "ts_utc": ts_chamada.isoformat(),
                "data_brt": data_brt, "dia_semana": dia_semana, "janela": janela, "posicao": posicao,
                "slot_id": slot.slot_id, "tipo": slot.tipo, "strategy": strategy, "url_usada": url,
                "usou_reserva": usou_reserva, "tentativas": tentativas, "erro": erro, "bloqueada": bloqueada,
                **metricas,
            }
            if "a11y_reprovadas_ids" in metricas:
                linha["a11y_reprovadas_ids"] = ";".join(metricas["a11y_reprovadas_ids"])
            escritor.writerow(linha)
            arquivo.flush()  # preserva as linhas já medidas se a execução for interrompida

    atualizar_estado(estado, observacoes)
    caminho_estado.parent.mkdir(parents=True, exist_ok=True)
    caminho_estado.write_text(json.dumps(estado, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(caminho_csv)


def _execucao_falhou_inteira(caminho_csv: str) -> bool:
    """Verdadeiro se todas as linhas da última execução têm erro (ex.: chave inválida)."""
    with open(caminho_csv, encoding="utf-8", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    ultima = [linha for linha in linhas if linha["run_id"] == linhas[-1]["run_id"]]
    return all(linha["erro"] for linha in ultima)


def main() -> int:
    parser = argparse.ArgumentParser(description="Coleta as métricas das URLs do estudo pela API da PSI.")
    parser.add_argument("--urls", default="config/urls.csv")
    parser.add_argument("--out", default="data/raw")
    parser.add_argument("--json", default="out/json")
    parser.add_argument("--estado", default="data/estado_reservas.json")
    args = parser.parse_args()

    api_key = os.environ.get("PSI_API_KEY")
    if not api_key:
        print("Defina a variável de ambiente PSI_API_KEY.", file=sys.stderr)
        return 2

    caminho = run(
        args.urls, args.out, args.json, api_key, estado_path=args.estado,
        gatilho=os.environ.get("GATILHO", "local"), cron=os.environ.get("CRON", ""),
    )
    print(f"CSV gravado em {caminho}")
    if _execucao_falhou_inteira(caminho):
        print("Todas as chamadas desta execução falharam.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
