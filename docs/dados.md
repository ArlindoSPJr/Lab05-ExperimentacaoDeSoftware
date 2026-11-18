# Dicionário de dados da coleta (issue #11)

Cada linha de `data/raw/AAAA-MM-DD_BRT.csv` é uma chamada à API do PageSpeed Insights (PSI) para uma URL e um perfil. Uma execução completa tem 38 linhas (19 URLs × 2 perfis). O arquivo é nomeado pela data BRT do início da execução.

- **Notas:** `perf_score` e `a11y_score` vêm na escala **0–1**, como a PSI devolve. O design (§5.4) cita 0–100, que é a mesma nota multiplicada por 100.
- **Campos vazios:** indicam valor ausente na resposta. Em linhas com `erro`, todas as métricas ficam vazias.
- **Disparos manuais:** ficam em `data/raw/testes/` e não entram na análise.
- **Abreviação:** `audits[x]` significa `lighthouseResult.audits['x']`, e `LHR` significa `lighthouseResult`.

## Identificação da execução

| Coluna | Unidade / formato | Origem | Escala |
|---|---|---|---|
| `run_id` | `AAAAMMDDTHHMMSSZ` | Horário de início da execução (UTC) | Nominal |
| `gatilho` | `schedule`, `workflow_dispatch` ou `local` | Variável `GATILHO` | Nominal |
| `cron` | Expressão cron | Variável `CRON` (vazia em disparos manuais) | Nominal |
| `ts_inicio_utc` | ISO 8601, UTC | Relógio do coletor, uma vez por execução | Intervalar |
| `ts_utc` | ISO 8601, UTC | Relógio do coletor, antes de cada chamada | Intervalar |
| `data_brt` | `AAAA-MM-DD` | `janela_brt(ts_inicio_utc)` | Intervalar |
| `dia_semana` | `seg` … `dom` | Calculado de `data_brt` | Nominal |
| `janela` | `pico` (18h–23h59), `madrugada` (00h–07h59) ou `fora` | `janela_brt(ts_inicio_utc)` | Nominal |
| `posicao` | 1 a 38 | Posição na ordem sorteada | Ordinal |

## Identificação da medição

| Coluna | Unidade / formato | Origem | Escala |
|---|---|---|---|
| `slot_id` | Texto | `config/urls.csv` | Nominal |
| `tipo` | `categoria`, `busca`, `produto` ou `home` | `config/urls.csv` | Nominal |
| `strategy` | `mobile` ou `desktop` | Parâmetro enviado à PSI | Nominal |
| `url_usada` | URL | `url` ou `url_reserva` de `config/urls.csv` | Nominal |
| `usou_reserva` | `True` / `False` | `data/estado_reservas.json` | Nominal |
| `tentativas` | Contagem (1 a 3) | Coletor | Razão |
| `erro` | Código HTTP, tipo de falha de rede ou `runtimeError.code` | Coletor / `LHR.runtimeError.code` | Nominal |
| `bloqueada` | `True` / `False` | `detect_block` (captcha, login, status ≠ 200 ou host inesperado) | Nominal |

## Métricas sintéticas (Lighthouse)

| Coluna | Unidade | Origem no JSON | Escala |
|---|---|---|---|
| `lcp_ms` | ms | `audits[largest-contentful-paint].numericValue` | Razão |
| `fcp_ms` | ms | `audits[first-contentful-paint].numericValue` | Razão |
| `speed_index_ms` | ms | `audits[speed-index].numericValue` | Razão |
| `tbt_ms` | ms | `audits[total-blocking-time].numericValue` | Razão |
| `ttfb_ms` | ms | Ver "Origem do TTFB" | Razão |
| `ttfb_origem` | Texto | Fonte usada para `ttfb_ms` | Nominal |
| `total_bytes` | bytes | `audits[total-byte-weight].numericValue` | Razão |
| `n_requests` | Contagem | Nº de itens em `audits[network-requests].details.items` | Razão |
| `perf_score` | 0–1 | `LHR.categories.performance.score` | Ordinal |
| `a11y_score` | 0–1 | `LHR.categories.accessibility.score` | Ordinal |
| `a11y_reprovadas` | Contagem | Itens de `categories.accessibility.auditRefs` cuja auditoria tem `score == 0` | Razão (discreta) |
| `a11y_reprovadas_ids` | IDs separados por `;` | Os mesmos itens de `a11y_reprovadas` | Nominal |

### Origem do TTFB

O coletor usa a primeira fonte disponível e grava qual foi em `ttfb_origem`:

1. `server-response-time`: `audits[server-response-time].numericValue`, valor observado no carregamento;
2. `metrics`: `audits[metrics].details.items[0].timeToFirstByte`, valor simulado, usado só se a primeira fonte faltar.

A análise de H3 deve usar apenas linhas com `ttfb_origem = server-response-time`, porque as duas fontes não são equivalentes.

O Lighthouse 13.6.0 não devolve o título da página na PSI, então `titulo` tende a ficar vazio. Nesse caso, o bloqueio é detectado pela URL final e pelo status HTTP.

## Controle da medição

| Coluna | Unidade / formato | Origem no JSON | Escala |
|---|---|---|---|
| `lighthouse_version` | Texto | `LHR.lighthouseVersion` | Nominal |
| `user_agent` | Texto | `LHR.userAgent` | Nominal |
| `final_url` | URL | `LHR.mainDocumentUrl`, `finalDisplayedUrl` ou `finalUrl` | Nominal |
| `status_http` | Código HTTP | `statusCode` do item de `network-requests` com a URL final, ou do 1º `Document` | Nominal |
| `titulo` | Texto | `LHR.title`, vazio se a PSI não devolver | Nominal |
| `throttling` | JSON | `LHR.configSettings.throttling` | Nominal |

## Dados de campo (CrUX)

Os campos `crux_lcp_*`, `crux_inp_*` e `crux_cls_*` só são preenchidos quando há dado da própria URL.

| Coluna | Unidade | Origem no JSON | Escala |
|---|---|---|---|
| `crux_lcp_p75_ms` | ms | `loadingExperience.metrics.LARGEST_CONTENTFUL_PAINT_MS.percentile` | Razão |
| `crux_lcp_categoria` | `FAST`, `AVERAGE` ou `SLOW` | `loadingExperience.metrics.LARGEST_CONTENTFUL_PAINT_MS.category` | Ordinal |
| `crux_inp_p75_ms` | ms | `loadingExperience.metrics.INTERACTION_TO_NEXT_PAINT.percentile` | Razão |
| `crux_cls_p75` | Adimensional | `loadingExperience.metrics.CUMULATIVE_LAYOUT_SHIFT_SCORE.percentile ÷ 100` | Razão |
| `crux_origin_fallback` | `True` / `False` | `True` quando não há dado da URL | Nominal |
| `crux_origin_lcp_p75_ms` | ms | `originLoadingExperience.metrics.LARGEST_CONTENTFUL_PAINT_MS.percentile` | Razão |

## Checagem de localização (ameaça externa, design §5.10)

**Pendente.** Depende de 3 execuções manuais feitas por um integrante em pagespeed.web.dev, a partir do Brasil, e da primeira execução do Actions.

| Execução | Origem | Data e hora (BRT) | TTFB (ms) | LCP (ms) |
|---|---|---|---|---|
| Manual 1 | PSI web, Brasil | | | |
| Manual 2 | PSI web, Brasil | | | |
| Manual 3 | PSI web, Brasil | | | |
| Actions | `run_id` a preencher | | | |
