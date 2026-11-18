"""Gera as 3 fixtures de teste do coletor (issue #7).

Uso, feito por um integrante (agentes de IA não abrem páginas do ML, ver docs/etica.md §5):

    PSI_API_KEY=... python scripts/gerar_fixtures.py     # chama a PSI 1 vez na home (mobile)
    python scripts/gerar_fixtures.py --derivar-apenas    # só recria as 2 fixtures derivadas
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect import call_psi, extract_metrics, strip_screenshots  # noqa: E402

HOME = "https://www.mercadolivre.com.br/"
PASTA = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def salvar(nome: str, dados: dict) -> None:
    (PASTA / nome).write_text(json.dumps(dados, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"gravado: tests/fixtures/{nome}")


def derivar(base: dict) -> None:
    """Cria as variantes sem CrUX da URL e com fallback de origem."""
    sem_crux = copy.deepcopy(base)
    sem_crux.pop("loadingExperience", None)
    salvar("psi_sem_crux.json", sem_crux)

    fallback = copy.deepcopy(base)
    fallback.setdefault("loadingExperience", {})["origin_fallback"] = True
    salvar("psi_origin_fallback.json", fallback)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--derivar-apenas", action="store_true", help="não chama a PSI")
    args = parser.parse_args()

    if args.derivar_apenas:
        base = strip_screenshots(json.loads((PASTA / "psi_home_mobile.json").read_text(encoding="utf-8")))
        salvar("psi_home_mobile.json", base)
        derivar(base)
        return 0

    chave = os.environ.get("PSI_API_KEY")
    if not chave:
        print("Defina a variável de ambiente PSI_API_KEY.", file=sys.stderr)
        return 2

    psi, tentativas, erro = call_psi(HOME, "mobile", chave, requests.Session())
    if psi is None:
        print(f"A PSI falhou após {tentativas} tentativas: {erro}", file=sys.stderr)
        return 1

    base = strip_screenshots(psi)
    salvar("psi_home_mobile.json", base)
    derivar(base)

    # Confere na resposta real os campos de que as hipóteses dependem.
    metricas = extract_metrics(base)
    for campo in ("lighthouse_version", "final_url", "status_http", "lcp_ms", "ttfb_ms", "ttfb_origem",
                  "total_bytes", "a11y_reprovadas", "crux_lcp_p75_ms"):
        print(f"{campo}: {metricas[campo]}")
    if metricas["lcp_ms"] is None or metricas["ttfb_ms"] is None:
        print("ATENÇÃO: LCP ou TTFB ausente. Não ligue a coleta antes de corrigir.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
