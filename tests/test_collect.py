"""Testes do coletor (issues #8 e #9). Nenhum teste acessa a rede."""
from __future__ import annotations

import copy
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import collect
from collect import (
    UrlSlot,
    atualizar_estado,
    call_psi,
    detect_block,
    extract_metrics,
    janela_brt,
    load_urls,
    resolve_url,
    run,
    strip_screenshots,
)

FIXTURES = Path(__file__).parent / "fixtures"
URLS_REAIS = Path(__file__).parent.parent / "config" / "urls.csv"


def fixture(nome: str) -> dict:
    return json.loads((FIXTURES / nome).read_text(encoding="utf-8"))


def utc(texto: str) -> datetime:
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))


def slot(tipo="produto", host="www.mercadolivre.com.br", url="https://www.mercadolivre.com.br/x/p/MLB1",
         reserva="https://www.mercadolivre.com.br/y/p/MLB2", mlb_id="MLB1", slot_id="pro-1") -> UrlSlot:
    return UrlSlot(slot_id, tipo, url, reserva, host, mlb_id)


class Resposta:
    def __init__(self, status_code, corpo=None):
        self.status_code = status_code
        self._corpo = corpo if corpo is not None else {}

    def json(self):
        return self._corpo


class SessaoRoteirizada:
    """Devolve as respostas na ordem dada e guarda os parâmetros recebidos."""

    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.chamadas = []

    def get(self, url, params=None, timeout=None):
        self.chamadas.append({"url": url, "params": params, "timeout": timeout})
        item = self.respostas.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class PsiFalsa:
    """Responde a toda chamada com a fixture, ajustando a URL final para a pedida."""

    def __init__(self):
        self.base = fixture("psi_home_mobile.json")
        self.pedidas = []

    def get(self, url, params=None, timeout=None):
        pedida = dict(params)["url"]
        self.pedidas.append((pedida, dict(params)["strategy"]))
        psi = copy.deepcopy(self.base)
        lhr = psi["lighthouseResult"]
        lhr["mainDocumentUrl"] = lhr["finalDisplayedUrl"] = pedida
        lhr["audits"]["network-requests"]["details"]["items"][0]["url"] = pedida
        return Resposta(200, psi)


def relogio(inicio: str, passo_s: int = 30):
    atual = {"t": utc(inicio)}

    def agora():
        valor = atual["t"]
        atual["t"] = valor + timedelta(seconds=passo_s)
        return valor

    return agora


def ler_csv(caminho) -> list[dict]:
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


# --- Issue #8: extração, janela BRT e leitura das URLs ---


def test_extract_metrics_home():
    m = extract_metrics(fixture("psi_home_mobile.json"))
    assert m["lcp_ms"] > 0 and m["ttfb_ms"] > 0
    assert 0 <= m["a11y_score"] <= 1
    assert m["a11y_reprovadas"] == len(m["a11y_reprovadas_ids"])
    assert m["lighthouse_version"]
    assert m["status_http"] == 200


def test_extract_metrics_sem_crux():
    m = extract_metrics(fixture("psi_sem_crux.json"))
    assert m["crux_lcp_p75_ms"] is None
    assert m["crux_origin_fallback"] is True
    assert m["crux_origin_lcp_p75_ms"] > 0


def test_extract_metrics_origin_fallback():
    m = extract_metrics(fixture("psi_origin_fallback.json"))
    assert m["crux_lcp_p75_ms"] is None
    assert m["crux_origin_fallback"] is True


@pytest.mark.parametrize(
    "instante, esperado",
    [
        ("2026-11-18T23:07Z", ("2026-11-18", "pico")),
        ("2026-11-19T01:50Z", ("2026-11-18", "pico")),
        ("2026-11-19T06:07Z", ("2026-11-19", "madrugada")),
        ("2026-11-19T15:00Z", ("2026-11-19", "fora")),
    ],
)
def test_janela_brt(instante, esperado):
    assert janela_brt(utc(instante)) == esperado


def test_load_urls(tmp_path):
    arquivo = tmp_path / "urls.csv"
    arquivo.write_text(
        "slot_id,tipo,url,url_reserva,host,mlb_id,criterio,data_selecao\n"
        "cat-1,categoria,https://a.com/c,,a.com,,crit,2026-11-17\n"
        "pro-1,produto,https://a.com/p,https://a.com/r,a.com,MLB1,crit,2026-11-18\n",
        encoding="utf-8",
    )
    slots = load_urls(str(arquivo))
    assert len(slots) == 2
    assert slots[0].url_reserva is None and slots[0].mlb_id is None
    assert slots[1].url_reserva == "https://a.com/r"


def test_ttfb_registra_a_alternativa_sem_server_response_time():
    psi = fixture("psi_home_mobile.json")
    audits = psi["lighthouseResult"]["audits"]
    del audits["server-response-time"]
    audits["metrics"] = {"details": {"items": [{"timeToFirstByte": 602}]}}
    m = extract_metrics(psi)
    assert m["ttfb_ms"] == 602
    assert m["ttfb_origem"] == "metrics"


# --- Issue #9: chamada, bloqueio, reservas e execução ---


def test_call_psi_retry_e_falha():
    sessao = SessaoRoteirizada([Resposta(429), Resposta(429), Resposta(429)])
    assert call_psi("https://a.com", "mobile", "k", sessao, sleep=lambda _: None) == (None, 3, "429")


def test_call_psi_retry_sucesso():
    sessao = SessaoRoteirizada([Resposta(500), Resposta(200, {"ok": True})])
    psi, tentativas, erro = call_psi("https://a.com", "mobile", "k", sessao, sleep=lambda _: None)
    assert psi == {"ok": True} and tentativas == 2 and erro is None


def test_call_psi_parametros():
    sessao = SessaoRoteirizada([Resposta(200, {})])
    call_psi("https://a.com", "desktop", "k", sessao, sleep=lambda _: None)
    params = sessao.chamadas[0]["params"]
    assert ("category", "PERFORMANCE") in params and ("category", "ACCESSIBILITY") in params
    assert ("strategy", "desktop") in params
    assert sessao.chamadas[0]["timeout"] == 120


def test_call_psi_erro_de_rede_nao_vaza_a_chave():
    falha = ConnectionError("https://www.googleapis.com/x?key=SEGREDO")
    sessao = SessaoRoteirizada([falha, falha, falha])
    psi, tentativas, erro = call_psi("https://a.com", "mobile", "SEGREDO", sessao, sleep=lambda _: None)
    assert psi is None and tentativas == 3
    assert "SEGREDO" not in erro


@pytest.mark.parametrize(
    "metricas",
    [
        {"final_url": "https://www.mercadolivre.com.br/login"},
        {"final_url": "https://www.mercadolivre.com.br/captcha/wall"},
        {"final_url": "https://www.mercadolivre.com.br/gz/account-verification?go=x"},
        {"final_url": "https://www.mercadolivre.com.br/x/p/MLB1", "titulo": "Captcha"},
        {"final_url": "https://www.mercadolivre.com.br/x/p/MLB1", "titulo": "Segurança — Mercado Livre"},
        {"final_url": "https://www.mercadolivre.com.br/x/p/MLB1", "status_http": 403},
        {"final_url": "https://outro-site.com/x"},
    ],
)
def test_detect_block_verdadeiro(metricas):
    assert detect_block({"status_http": 200, "titulo": "", **metricas}, slot()) is True


@pytest.mark.parametrize(
    "metricas, alvo",
    [
        (
            {"final_url": "https://www.mercadolivre.com.br/x/p/MLB1"},
            slot(host="produto.mercadolivre.com.br", url="https://produto.mercadolivre.com.br/MLB-1"),
        ),
        ({"final_url": "https://www.mercadolivre.com.br/x/p/MLB1"}, slot()),
        ({"final_url": "https://www.mercadolivre.com.br/x/p/MLB1", "titulo": "Bota de segurança"}, slot()),
    ],
)
def test_detect_block_falso(metricas, alvo):
    assert detect_block({"status_http": 200, "titulo": "", **metricas}, alvo) is False


def test_strip_screenshots():
    psi = {
        "lighthouseResult": {
            "fullPageScreenshot": {"screenshot": {"data": "x"}},
            "audits": {
                "final-screenshot": {},
                "screenshot-thumbnails": {},
                "full-page-screenshot": {},
                "speed-index": {"numericValue": 1},
            },
        }
    }
    limpo = strip_screenshots(psi)
    assert list(limpo["lighthouseResult"]["audits"]) == ["speed-index"]
    assert "fullPageScreenshot" not in limpo["lighthouseResult"]


def test_slot_usa_reserva():
    estado = {"pro-1": {"indisponivel": True}, "cat-1": {"indisponivel": True}}
    produto = slot()
    categoria = slot(tipo="categoria", slot_id="cat-1", reserva=None, mlb_id=None)
    assert resolve_url(produto, estado) == (produto.url_reserva, True)
    assert resolve_url(categoria, estado) == (categoria.url, False)


def test_reserva_so_apos_duas_execucoes_seguidas():
    produto = slot()
    estado = {}
    sumiu = [{"status_http": 404, "final_url": "https://www.mercadolivre.com.br/x", "bloqueada": True}]
    ok = [{"status_http": 200, "final_url": "https://www.mercadolivre.com.br/x/p/MLB1", "bloqueada": False}]

    atualizar_estado(estado, {produto.slot_id: (produto, sumiu)})
    assert estado["pro-1"]["indisponivel"] is False
    atualizar_estado(estado, {produto.slot_id: (produto, ok)})
    assert estado["pro-1"]["falhas_seguidas"] == 0
    atualizar_estado(estado, {produto.slot_id: (produto, sumiu)})
    atualizar_estado(estado, {produto.slot_id: (produto, sumiu)})
    assert estado["pro-1"]["indisponivel"] is True


def test_captcha_nao_conta_como_produto_esgotado():
    produto = slot()
    estado = {}
    captcha = [{"status_http": 200, "final_url": "https://www.mercadolivre.com.br/captcha/wall", "bloqueada": True}]
    atualizar_estado(estado, {produto.slot_id: (produto, captcha)})
    atualizar_estado(estado, {produto.slot_id: (produto, captcha)})
    assert estado["pro-1"]["indisponivel"] is False


def test_run_ordem_cobertura_e_janela(tmp_path):
    esperas = []
    kwargs = dict(api_key="k", sleep=esperas.append, gatilho="schedule", cron="7 23 * * *")

    def executar(seed, pasta):
        sessao = PsiFalsa()
        caminho = run(
            str(URLS_REAIS), str(pasta), str(tmp_path / "json"), seed=seed, session=sessao,
            now=relogio("2026-11-19T02:55:00Z"), estado_path=str(tmp_path / "estado.json"), **kwargs,
        )
        return caminho, sessao.pedidas

    caminho, ordem_1 = executar(1, tmp_path / "a")
    linhas = ler_csv(caminho)
    assert len(linhas) == 38
    assert len(esperas) == 37 and all(e >= 2 for e in esperas)
    assert {l["janela"] for l in linhas} == {"pico"}
    assert {l["data_brt"] for l in linhas} == {"2026-11-18"}
    assert Path(caminho).name == "2026-11-18_BRT.csv"

    _, ordem_2 = executar(2, tmp_path / "b")
    assert ordem_1 != ordem_2

    caminho_2, _ = executar(1, tmp_path / "a")
    assert caminho_2 == caminho
    assert len(ler_csv(caminho)) == 76
    texto = Path(caminho).read_text(encoding="utf-8")
    assert texto.count("run_id,gatilho") == 1


def test_run_grava_json_sem_capturas(tmp_path):
    sessao = PsiFalsa()
    sessao.base["lighthouseResult"]["audits"]["final-screenshot"] = {"details": {"data": "x"}}
    run(
        str(URLS_REAIS), str(tmp_path / "csv"), str(tmp_path / "json"), "k", seed=1, session=sessao,
        sleep=lambda _: None, now=relogio("2026-11-18T23:07:00Z"), estado_path=str(tmp_path / "e.json"),
    )
    arquivos = list((tmp_path / "json").rglob("*.json"))
    assert len(arquivos) == 38
    assert all("final-screenshot" not in a.read_text(encoding="utf-8") for a in arquivos)


def test_modulo_nao_acessa_hosts_do_ml_diretamente():
    """O coletor só fala com a API da PSI (comentário da onda 1 na issue #9)."""
    assert collect.PSI_ENDPOINT.startswith("https://www.googleapis.com/")
