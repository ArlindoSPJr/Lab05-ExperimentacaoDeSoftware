# Lab05 Mercado Livre — Issues por onda e sprint

> **Para quem executar:** cada issue vira um cartão no GitHub Projects. Issues de código seguem TDD (teste primeiro) e usam checkboxes (`- [ ]`) para acompanhamento.

**Objetivo:** dividir todo o trabalho do design aprovado em issues atribuídas aos papéis A, B e C, em ondas sequenciais (A → B → C) por sprint.

**Arquitetura:**
- Coleta: script Python chamando a PageSpeed Insights API, agendado no GitHub Actions, com CSVs versionados.
- Validação: script que consolida o dataset.
- Análise: script Python com modelo misto, Kruskal-Wallis por URL e concordância com o CrUX.
- Documentação: Markdown em `docs/`.

**Stack:** Python 3.12, `requests`, `pandas`, `numpy`, `scipy`, `statsmodels`, `scikit-posthocs`, `matplotlib`, `pytest`; GitHub Actions; GitHub Projects.

**Spec:** `docs/superpowers/specs/2026-11-16-mercadolivre-desempenho-acessibilidade-design.md`. As referências "§x" apontam para ela.

**Revisão:** versão 2. Incorpora as 29 correções da revisão independente de rastreabilidade.

## Restrições globais (valem para todas as issues)

- O objeto de estudo é o site em operação. GitHub e Actions são só instrumentos. Tema confirmado: nenhum outro grupo escolheu o ML.
- **Máx. 1 req/s.** Na prática, ≥ 2 s entre chamadas e 38 chamadas por execução.
- Respeitar o `robots.txt` de cada host e os termos de uso do ML e da PSI. **Nada de login, nada de dados pessoais.** As capturas de tela são removidas do JSON.
- Coleta principal: **18/11 20h07 → 25/11 05h07 BRT**.
  - Crons em UTC: `7 23 * * *`, `7 1 * * *`, `7 6 * * *` e `7 8 * * *`.
  - São 28 execuções agendadas: 7 noites × 2 e 7 madrugadas × 2.
- **19 URLs**: 6 de categoria, 6 de busca, 6 de produto (+ 6 reservas) e a home como referência. Com 2 perfis (`mobile`, `desktop`), são 38 chamadas por execução e **1.064 medições** no total.
- **Janelas BRT** (decisão de método): 18h–23h59 = `pico`; 00h–07h59 = `madrugada`; demais = `fora`. A janela e a `data_brt` são calculadas **uma vez por execução**, a partir do horário de início.
- **Métricas primárias:** LCP (H1, H2, H5), TTFB (H3) e nº de auditorias de acessibilidade reprovadas (H4).
  - H2 e H4 usam o perfil **móvel**, e a home fica fora dos testes.
  - Correção de **Holm** sobre os 5 p primários, com α = 0,05. Testes **bilaterais**.
- Os dias 26–28/11 (Black Friday, 27/11) **nunca** entram no conjunto principal.
- Só execuções com `gatilho == 'schedule'` entram na análise. Os disparos manuais gravam em `data/raw/testes/`.
- A chave da API fica só no secret `PSI_API_KEY`.
- As notas da PSI vêm na escala 0–1 (o §5.4 fala em 0–100). A escala fica declarada no dicionário de dados.
- Entrega conjunta S01 + S02 em **26/11**. Apresentação em **04/12** e ensaio em **03/12**.

## Pontos de atenção (falhas prováveis sem teste explícito)

1. **CrUX ausente ou com fallback de origem** (`loadingExperience` vazio, sem `metrics` ou com `origin_fallback: true`):
   - os `crux_*` da URL ficam `None`;
   - `crux_origin_fallback=True` e `crux_origin_lcp_p75_ms` vêm de `originLoadingExperience`;
   - a coleta não quebra.
   - Testes: `test_extract_metrics_sem_crux` e `test_extract_metrics_origin_fallback` (#B-2).
2. **Bloqueio**: `detect_block` retorna `True` quando ocorre qualquer uma destas condições:
   - (a) `status_http` ≥ 400;
   - (b) o host de `final_url` não é `slot.host` nem está em `{www.mercadolivre.com.br, lista.mercadolivre.com.br, produto.mercadolivre.com.br}`;
   - (c) o caminho contém `login`, `/jms/` ou `lgz`;
   - (d) o `titulo` contém `captcha` ou `entrar`, sem diferenciar maiúsculas.

   Teste: `test_detect_block` (#B-3).
3. **PSI retorna 429 ou 500**: até 2 novas tentativas com espera. Se todas falharem, a linha é gravada com `erro` e `tentativas=3`, e a execução continua. Teste: `test_call_psi_retry_e_falha` (#B-3).
4. **Cron atrasado e virada de meia-noite**: uma execução das 22h07 que passe da meia-noite continua inteira em `pico` com a data D. Teste: `test_run_ordem_cobertura_e_janela` (#B-3).
5. **Produto esgotado**: 404/410 ou `final_url` sem o ID `MLB` do produto em 2 execuções seguidas faz o slot passar para a reserva a partir da execução seguinte. Teste: `test_slot_usa_reserva` (#B-3).

## Vigilância diária da coleta (transversal)

#### #T-0 Vigilância diária da coleta (18/11–25/11) — dono da onda corrente
Quem confere: C de 19 a 21/11, A de 22 a 23/11 e B de 24 a 25/11.
- [ ] Ativar as notificações de falha do Actions para os 3 integrantes (B, no #B-4).
- [ ] Todo dia, por volta das 09h BRT, o dono da onda corrente confere três coisas:
  - as 4 execuções agendadas da janela anterior aparecem no Actions;
  - o CSV foi commitado com 38 linhas por `run_id`;
  - a taxa de `bloqueada`/`erro` está ≤ 10%.
- [ ] Se houver falha, avisar B no mesmo dia e registrar em `docs/anomalias.md`.

**Aceite:** `docs/anomalias.md` tem uma linha "checagem OK/falha" por dia, de 19/11 a 25/11.

---

# Sprint conjunta S01 + S02 (16/11–26/11, entrega única em 26/11)

## Ciclo 1 — Preparação e início da coleta

### Onda 1 — A (16–17/11)

#### #A-1 GitHub Projects, papéis e decisões do grupo
- [ ] Criar o Project ligado ao repositório, com as colunas Backlog / Em andamento / Revisão / Concluído.
- [ ] Criar uma issue no GitHub para cada item deste arquivo, com labels `A`/`B`/`C`/`todos`, `sprint-1-2`/`sprint-3` e `onda-1`/`onda-2`/`onda-3`.
- [ ] Colocar o link do Project no `README.md` (o PDF exige o link, §7).
- [ ] Definir quem é A, B e C e registrar no README (§9 do design).
- [ ] Validar com o grupo as decisões do §8 do design e registrar "aprovado/alterado" em `docs/proposta.md`.

**Aceite:** o link e os papéis estão no README, todas as issues estão no Kanban e as decisões do §8 estão registradas.

#### #A-2 Evidências dos 3 critérios (§5.1)
- [ ] Criar `docs/evidencias.md` com a tabela Critério | Evidência | Número | Fonte (link) | Data de acesso.
- [ ] **Real:** site oficial e documentação para desenvolvedores.
- [ ] **Em operação:** relatório trimestral de RI mais recente e comunicado recente.
- [ ] **Em operação, CrUX:** verificar se há dados no CrUX pelo PSI web (pagespeed.web.dev, sem chave). Salvar uma captura da seção de usuários reais e anotar a data.
- [ ] **Alto impacto:** compradores únicos e GMV **recortados para o Brasil**, audiência mensal do domínio e downloads do app.

**Aceite:** todo número tem link e data de acesso, e nenhum valor é inventado.

#### #A-3 Proposta metodológica (§5.2–§5.7)
- [ ] Criar `docs/proposta.md` com:
  - a pergunta de pesquisa;
  - o GQM: objetivo no template de Basili e Q1–Q5 com métricas e papel;
  - a tabela de entidades, atributos e escalas;
  - o mapeamento ISO/IEC 25010, citando a versão;
  - o SLO de LCP ≤ 2,5 s.
- [ ] Incluir as **7 categorias v1**, conferidas com o material da Aula 8 e com justificativa para cada uma.
- [ ] Incluir as hipóteses H1–H5 com H0, métrica, unidade de análise e perfil usado (H2/H4 no móvel). Os testes são bilaterais.
- [ ] Incluir as armadilhas Goodhart, Campbell e McNamara aplicadas ao estudo.

**Aceite:** todas as seções do §5.2 ao §5.7 estão presentes. As métricas primárias, o perfil de H2/H4 e a bilateralidade estão marcados como fixados antes da coleta.

#### #A-4 Seleção das URLs (§5.6)
- [ ] Criar `config/urls.csv` com as colunas `slot_id,tipo,url,url_reserva,host,mlb_id,criterio,data_selecao`.
  - `host` é o host do **`finalUrl` observado** ao abrir a URL na seleção, e não o da URL digitada.
  - `mlb_id` é o ID do produto (só para produtos).
- [ ] **Categoria:** as 6 de maior destaque no menu. Salvar a captura do menu em `docs/img/menu-AAAA-MM-DD.png`, feita sem login e sem dados pessoais visíveis.
- [ ] **Busca:** 1 termo genérico por categoria, sem filtros (host `lista.mercadolivre.com.br`).
- [ ] **Produto:** o 1º "Mais vendido" de cada categoria + 1 reserva por produto.
- [ ] **Home:** `https://www.mercadolivre.com.br/`, tipo `home`, sem reserva.
- [ ] Justificar o horário de pico (20h–22h) com uma fonte e registrar em `docs/proposta.md`.

**Aceite:** o arquivo tem 19 linhas, os 6 produtos têm `url_reserva` e `mlb_id`, e todas as URLs abrem sem login.

#### #A-5 Ética (§5.9)
- [ ] Criar `docs/etica.md` com:
  - o `robots.txt` de `www.`, `lista.` e `produto.` (conteúdo relevante e data);
  - os termos de uso do ML e da PSI API.
- [ ] Checar se alguma URL do `urls.csv` é proibida pelo `robots.txt`. Se for, trocar ou excluir o tipo e registrar.
- [ ] Registrar as regras: ≤ 1 req/s, sem login, sem dados pessoais e capturas removidas.

**Aceite:** existe um registro datado por host e nenhuma URL proibida no `urls.csv`.

**Passagem A → B:** `docs/proposta.md`, `docs/evidencias.md`, `docs/etica.md` e `config/urls.csv` com commit no `main` até 17/11.

### Onda 2 — B (17–18/11) — prazo crítico: workflow ligado até 18/11 20h07

Esta é a onda mais carregada. **Só o #B-5 pode ir para 19/11** sem afetar o workflow.

#### #B-1 Setup do repositório e da chave
**Arquivos:** `requirements.txt`, `.gitignore`, `pyproject.toml` (configuração do pytest) e `tests/fixtures/`.
- [ ] `requirements.txt` com `requests`, `pandas`, `numpy`, `scipy`, `statsmodels`, `scikit-posthocs`, `matplotlib` e `pytest`.
- [ ] `.gitignore` com `out/`, `__pycache__/`, `.venv/`, `.env` e `*.zip`. Os JSONs brutos nunca são commitados (§5.9).
- [ ] Criar a chave da PSI API no Google Cloud e salvar no secret `PSI_API_KEY`.
- [ ] Fazer uma chamada manual na home (mobile, `category` PERFORMANCE + ACCESSIBILITY) e salvar a resposta, **sem as 3 auditorias de imagem**, em `tests/fixtures/psi_home_mobile.json`.
- [ ] Criar mais duas fixtures derivadas dela:
  - `psi_sem_crux.json`, sem `loadingExperience`;
  - `psi_origin_fallback.json`, com `loadingExperience.origin_fallback = true`.

**Aceite:** `pytest` roda, as 3 fixtures existem e nenhuma contém `final-screenshot`, `screenshot-thumbnails` ou `full-page-screenshot`.

#### #B-2 Extração de métricas e janela BRT
**Arquivos:** criar `scripts/collect.py` e `tests/test_collect.py`.

**Interfaces produzidas:**
- `UrlSlot` (dataclass): `slot_id: str, tipo: str, url: str, url_reserva: str | None, host: str, mlb_id: str | None`
- `load_urls(path: str) -> list[UrlSlot]`
- `extract_metrics(psi: dict) -> dict`, com as chaves `lcp_ms, fcp_ms, speed_index_ms, tbt_ms, ttfb_ms, total_bytes, n_requests, perf_score, a11y_score, a11y_reprovadas, a11y_reprovadas_ids, lighthouse_version, final_url, status_http, titulo, throttling, crux_lcp_p75_ms, crux_lcp_categoria, crux_inp_p75_ms, crux_cls_p75, crux_origin_fallback, crux_origin_lcp_p75_ms`
- `janela_brt(ts_utc: datetime) -> tuple[str, str]`, que devolve (`data_brt` "AAAA-MM-DD", janela `pico|madrugada|fora`)

**Origem dos campos:**
- Tempos e bytes: `lighthouseResult.audits['largest-contentful-paint'|'first-contentful-paint'|'speed-index'|'total-blocking-time'|'server-response-time'|'total-byte-weight'].numericValue`.
- `n_requests`: número de itens em `audits['network-requests'].details.items`.
- `status_http`: `statusCode` do item de `network-requests` cujo `url == finalUrl` (ou o 1º com `resourceType == 'Document'`). `None` se ausente.
- `titulo`: título final da página, se a PSI devolver. Senão, `""`.
- `throttling`: `json.dumps(lighthouseResult.configSettings.throttling)`.
- Auditorias reprovadas: itens de `categories.accessibility.auditRefs` cujo audit tem `score == 0`.
- CrUX da URL: vem de `loadingExperience.metrics` **só se** `loadingExperience` existir, tiver `metrics` e não tiver `origin_fallback == true`. Senão, os `crux_*` ficam `None`.
- `crux_origin_fallback: bool` (True quando não há dado da URL) e `crux_origin_lcp_p75_ms` vêm de `originLoadingExperience`.

**Testes:**
- [ ] **Teste 1:** `test_extract_metrics_home`. Com a fixture `psi_home_mobile.json`:
  - `lcp_ms > 0` e `ttfb_ms > 0`;
  - `0 <= a11y_score <= 1`;
  - `a11y_reprovadas == len(a11y_reprovadas_ids)`;
  - `lighthouse_version` não vazio;
  - `status_http == 200`.
- [ ] **Teste 2:** `test_extract_metrics_sem_crux`. Com `psi_sem_crux.json`, `crux_lcp_p75_ms is None`, `crux_origin_fallback is True`, `crux_origin_lcp_p75_ms > 0` e sem exceção.
- [ ] **Teste 3:** `test_extract_metrics_origin_fallback`. Com `psi_origin_fallback.json`, `crux_lcp_p75_ms is None` e `crux_origin_fallback is True`.
- [ ] **Teste 4:** `test_janela_brt`.
  - `2026-11-18T23:07Z` → `("2026-11-18","pico")`
  - `2026-11-19T01:50Z` → `("2026-11-18","pico")`
  - `2026-11-19T06:07Z` → `("2026-11-19","madrugada")`
  - `2026-11-19T15:00Z` → `("2026-11-19","fora")`
- [ ] **Teste 5:** `test_load_urls`. Um CSV de exemplo com 2 linhas gera 2 `UrlSlot`, e `url_reserva` vazio vira `None`.

**Passos:**
- [ ] Rodar `pytest tests/test_collect.py -v` e ver falhar.
- [ ] Implementar. Para BRT, usar UTC−3 fixo (o Brasil não tem horário de verão).
- [ ] Rodar de novo e ver passar. Fazer commit.

**Aceite:** `pytest tests/test_collect.py -v` passa com os 5 testes, e o commit está no `main`.

#### #B-3 Execução robusta da coleta
**Arquivos:** modificar `scripts/collect.py` e `tests/test_collect.py`.

**Interfaces produzidas:**
- `call_psi(url: str, strategy: str, api_key: str, session, max_retries: int = 2, espera_s: float = 5, sleep=time.sleep) -> tuple[dict | None, int, str | None]`, que devolve (json, tentativas, erro).
  - Parâmetros enviados como lista de tuplas: `[('url', url), ('strategy', strategy), ('category', 'PERFORMANCE'), ('category', 'ACCESSIBILITY'), ('key', api_key)]`.
  - `timeout=120`.
- `detect_block(metrics: dict, slot: UrlSlot) -> bool`, com a regra do ponto de atenção 2.
- `strip_screenshots(psi: dict) -> dict`, que remove `final-screenshot`, `screenshot-thumbnails` e `full-page-screenshot`.
- `resolve_url(slot: UrlSlot, estado_reservas: dict) -> tuple[str, bool]`, que devolve (url, usou_reserva).
- `run(urls_path, out_dir, json_dir, api_key, seed=None, session=None, sleep=time.sleep, now=lambda: datetime.now(timezone.utc), gatilho="local", cron="") -> str`, que devolve o caminho do CSV gravado.
- CLI: `python scripts/collect.py --urls config/urls.csv --out data/raw --json out/json`. Lê `PSI_API_KEY`, `GATILHO` e `CRON` do ambiente.

**Colunas do CSV:** `run_id, gatilho, cron, ts_inicio_utc, ts_utc, data_brt, dia_semana, janela, posicao, slot_id, tipo, strategy, url_usada, usou_reserva, tentativas, erro, bloqueada` + as chaves de `extract_metrics`.
- `data_brt`, `dia_semana` (`seg`…`dom`) e `janela` são calculadas **uma vez por execução**, com `janela_brt(ts_inicio_utc)`.
- `ts_utc` é o instante de cada chamada.

**Regras:**
- `run` grava em `{out_dir}/{data_brt}_BRT.csv`, **em modo de acréscimo**, com cabeçalho só se o arquivo for novo.
- **Reserva:** um produto vai para a reserva em dois casos:
  - a URL original tem `status_http` 404/410, ou um `final_url` sem o `mlb_id`, em **2 execuções seguidas**;
  - B marca o slot à mão em `data/estado_reservas.json` (esgotado visto no navegador).
- `run` atualiza `estado_reservas.json` no fim da execução. A reserva vale a partir da execução seguinte.
- Slots `categoria`, `busca` e `home` nunca trocam.

**Testes:**
- [ ] **Teste 1:** `test_call_psi_retry_e_falha`. Uma sessão falsa devolve 429 três vezes e `sleep` é falso. O resultado é `(None, 3, "429")`.
- [ ] **Teste 2:** `test_call_psi_retry_sucesso`. A sessão devolve 500 e depois 200. O resultado tem `tentativas == 2`.
- [ ] **Teste 3:** `test_call_psi_parametros`. A sessão falsa recebe as duas `category` e a `strategy`.
- [ ] **Teste 4:** `test_detect_block`. Devem retornar `True`:
  - `final_url` `https://www.mercadolivre.com.br/login`;
  - título contendo "Captcha";
  - `status_http=403`.

  Devem retornar `False`:
  - slot `produto.mercadolivre.com.br/MLB-1` com `final_url` `https://www.mercadolivre.com.br/x/p/MLB1`;
  - URL igual à esperada.
- [ ] **Teste 5:** `test_strip_screenshots`. As 3 chaves somem e as demais auditorias continuam.
- [ ] **Teste 6:** `test_slot_usa_reserva`.
  - Um produto marcado como indisponível em `estado_reservas` devolve `(url_reserva, True)`.
  - Um slot `categoria` marcado como indisponível devolve `(url, False)`.
- [ ] **Teste 7:** `test_run_ordem_cobertura_e_janela`. Com PSI falsa, `sleep` falso que registra as durações e `now` simulado começando em `2026-11-19T02:55Z` e avançando 30 s por chamada:
  - com `seed=1`, há 38 linhas e todas as esperas entre chamadas são ≥ 2 s;
  - a ordem difere com `seed=2`;
  - todas as linhas têm `janela == 'pico'` e `data_brt == '2026-11-18'`;
  - duas chamadas de `run` com a mesma `data_brt` geram **um** arquivo com 76 linhas e um cabeçalho.

**Passos:**
- [ ] Ver falhar, implementar, ver passar e fazer commit.

**Aceite:** `pytest tests/test_collect.py -v` passa com os 12 testes (#B-2 + #B-3), e o commit está no `main`.

#### #B-4 Workflow agendado
**Arquivo:** `.github/workflows/collect.yml`
- [ ] Gatilhos: `schedule` com os 4 crons das restrições globais e `workflow_dispatch`.
- [ ] Passos:
  - setup do Python 3.12;
  - `pip install -r requirements.txt`;
  - `python scripts/collect.py ...`, com `PSI_API_KEY` vindo do secret e `GATILHO: ${{ github.event_name }}` e `CRON: ${{ github.event.schedule }}` como variáveis de ambiente.
- [ ] Disparos manuais (`workflow_dispatch`) gravam com `--out data/raw/testes`.
- [ ] Publicar `out/json/` com `actions/upload-artifact`, retenção de 90 dias.
- [ ] Fazer commit de `data/raw/` e `data/estado_reservas.json` com `git pull --rebase` antes do push.
- [ ] Configurar `permissions: contents: write` e `concurrency`, para impedir duas execuções simultâneas.
- [ ] Ativar as notificações de falha do Actions para os 3 integrantes (apoio ao #T-0).
- [ ] Disparar manualmente 1 vez e conferir 38 linhas em `data/raw/testes/` e o artifact publicado.
- [ ] Deixar o workflow no `main` **até 18/11 20h07**.

**Aceite:** a execução manual dá verde, e a primeira execução agendada (18/11 23h07 UTC) aparece na aba Actions com `gatilho=schedule` no CSV.

#### #B-5 Dicionário de dados e checagem de localização (pode ir para 19/11)
- [ ] Criar `docs/dados.md` com cada coluna do CSV: nome, unidade, origem no JSON e escala (§5.4). Declarar que as notas vêm na escala 0–1.
- [ ] Fazer 3 execuções manuais no PSI web, a partir do Brasil, com a home mobile. Registrar o TTFB e o LCP e comparar com uma execução do Actions (ameaça externa de localização, §5.10).

**Aceite:** todas as colunas estão documentadas e a comparação está registrada.

**Passagem B → C:** workflow ativo, `docs/dados.md` pronto e primeiras execuções em `data/raw/`.

### Onda 3 — C (19–21/11, inclui o feriado)

#### #C-1 Descritiva do piloto incorporado
**Arquivos:** `analysis/piloto.py` e `analysis/out/piloto/`
- [ ] Carregar só as linhas com `gatilho == 'schedule'` de 18/11 20h07 a 19/11 05h07. Não ler `data/raw/testes/`.
- [ ] Calcular a cobertura (esperado 4 × 38 = 152 linhas), os bloqueios, os erros e o uso de reservas.
- [ ] Calcular mediana e IQR de LCP, TTFB e reprovadas por tipo × perfil × janela, e a variância entre execuções da mesma URL.
- [ ] Se houver um problema que exija descarte, comunicar a B e registrar em `docs/anomalias.md`.

**Aceite:** `analysis/out/piloto/` tem um relatório com cobertura (x/152), bloqueios e variâncias.

#### #C-2 Biblioteca de análise com testes
**Arquivos:** criar `analysis/stats.py` e `tests/test_stats.py`.

**Interfaces produzidas:**
- `filtro_minimo(df) -> DataFrame`: mantém `gatilho=='schedule' & ~bloqueada & erro.isna() & janela!='fora'`. Reusada pelo `validate.py` (#B-7).
- `por_url(df, metrica: str, agg: str = "median") -> DataFrame`: uma linha por `slot_id × strategy`. `agg='mode'` usa o menor valor modal em caso de empate.
- `kruskal_por_tipo(df_url, metrica: str) -> dict`, com as chaves `H, p, eps2, dunn` (DataFrame com p de Holm).
- `modelo_misto(df, metrica: str) -> dict`, com as chaves `razao_perfil, razao_pico, ic95_perfil, ic95_pico, p_perfil, p_pico`.
  - Fórmula: `np.log(<metrica>) ~ C(strategy, Sum) * C(janela, Sum) * C(tipo, Sum)`.
  - Efeitos aleatórios cruzados de `slot_id` e `data_brt` via `statsmodels` `mixedlm` (`groups` constante + `vc_formula`).
  - Com a codificação Sum, o efeito principal de cada fator de 2 níveis é estimado **na média dos outros fatores**.
  - `razao_perfil = exp(-2·β[C(strategy, Sum)[S.desktop]])` (mobile/desktop) e `razao_pico = exp(-2·β[C(janela, Sum)[S.madrugada]])` (pico/madrugada). O IC é transformado da mesma forma.
- `concordancia_crux(df) -> dict`, com as chaves `n_pares, wilcoxon_p, spearman_rho, bland_altman` (média e limites), `kappa` e `slots_sem_crux: list[str]`.
  - Usa só `strategy == 'mobile'` e os slots com `crux_lcp_p75_ms` não nulo.
  - O par é (mediana sintética por slot, p75 do CrUX).
  - A categoria sintética segue os limiares do CrUX: LCP ≤ 2500 ms = FAST, ≤ 4000 ms = AVERAGE, senão SLOW.
- `categoria_lcp(ms: float) -> str`
- `holm(pvals: dict[str, float]) -> dict[str, float]`
- `cliffs_delta(x, y) -> float`
- `art_alinhar(df, metrica: str, efeito: str) -> DataFrame`: postos alinhados para a alternativa robusta (#C-6).

**Testes:**
- [ ] `test_holm`: `{"a":0.01,"b":0.04,"c":0.03}` → `{"a":0.03,"b":0.06,"c":0.06}`.
- [ ] `test_cliffs_delta`: `x=[1,2,3]` e `y=[4,5,6]` → `-1.0`.
- [ ] `test_kruskal_eps2`: 3 grupos sintéticos claramente separados, com 6 por grupo → `p < 0.05` e `0 < eps2 <= 1`.
- [ ] `test_por_url_mediana`: um slot com `[1,2,100]` → `2`.
- [ ] `test_por_url_moda`: `[3,3,5]` → `3`; `[2,4]` → `2`.
- [ ] `test_filtro_minimo`: linhas `bloqueada`, com `erro`, com janela `fora` ou com `gatilho='workflow_dispatch'` são removidas.
- [ ] `test_modelo_misto_recupera_efeito`: dados sintéticos com o perfil móvel 2× mais lento em todas as células → `razao_perfil` entre 1,8 e 2,2.
- [ ] `test_concordancia_categoria`: `categoria_lcp(2400)=="FAST"`, `categoria_lcp(2600)=="AVERAGE"` e `categoria_lcp(4100)=="SLOW"`.
- [ ] `test_art_alinhar`: em dados sem efeito do fator, os postos alinhados têm a mesma mediana entre os níveis (tolerância de 1 posto).

**Passos:**
- [ ] Ver falhar, implementar, ver passar e fazer commit.

**Aceite:** `pytest tests/test_stats.py -v` passa com os 9 testes.

#### #C-3 Simulação do efeito mínimo detectável (Lab04)
**Arquivo:** `analysis/poder.py`
- [ ] Usar a variância do piloto (#C-1).
- [ ] Simular, numa grade de 6 níveis de efeito (razão de 1,00 a 1,30), com n = 6 URLs por tipo, 7 dias e 2 execuções por janela:
  - 1.000 datasets por nível para H2 e H4 (Kruskal-Wallis por URL);
  - **200** datasets por nível para H3 (modelo misto).
- [ ] Encontrar o menor efeito com poder ≥ 0,8 para H2, H3 e H4. Registrar o tempo de execução.
- [ ] Simular o erro tipo I com efeito 0.

**Aceite:** existe uma tabela com o efeito mínimo detectável de H2, H3 e H4, e o erro tipo I observado fica entre 0,03 e 0,07.

#### #C-4 Script de análise completo rodando sobre o piloto
**Arquivo:** `analysis/analise.py`
- **Entrada:** `--input` aceita um diretório (concatena `*.csv`, sem descer em subpastas) ou um arquivo.
- **Filtro:** na entrada bruta, aplica `stats.filtro_minimo`.
- **Saída:** `analysis/out/`.

- [ ] Descritiva (mediana, IQR, p75 e p90) por combinação, **por slot e no agregado**.
- [ ] SLI de LCP ≤ 2,5 s por combinação.
- [ ] Taxa de execuções com bloqueio ou falha.
- [ ] Excluir `tipo == 'home'` de todos os testes. Ela só entra na descritiva.
- [ ] Rodar os testes de hipótese:
  - **H1:** `modelo_misto(df, 'lcp_ms')['p_perfil']`.
  - **H3:** `modelo_misto(df, 'ttfb_ms')['p_pico']`.
  - **H2:** `kruskal_por_tipo(por_url(df[df.strategy=='mobile'], 'lcp_ms'), 'lcp_ms')`.
  - **H4:** `kruskal_por_tipo(por_url(df[df.strategy=='mobile'], 'a11y_reprovadas', agg='mode'), 'a11y_reprovadas')`.
  - **H5:** `concordancia_crux(df)`, entrando no Holm o `wilcoxon_p`.
  - Os mesmos testes no desktop entram como sensibilidade, **fora do Holm**.
- [ ] Aplicar `holm` sobre os 5 p primários. Os testes são bilaterais.
- [ ] Calcular o Cliff's delta de perfil e de horário sobre as medianas por slot, como efeito complementar.
- [ ] Gerar boxplots por combinação e o gráfico de Bland-Altman.
- [ ] Rodar sobre o piloto sem erro, mesmo com poucos dados.

**Aceite:** `python analysis/analise.py --input data/raw` gera `analysis/out/` sem exceção.

#### #C-5 Seção "Plano de coleta e análise + piloto"
- [ ] Criar `docs/entrega-s1s2.md` com essa seção:
  - o desenho fatorial;
  - a tabela de cobertura do piloto (x/152);
  - o efeito mínimo detectável.

**Aceite:** a seção existe e tem os 3 elementos.

**Passagem C → A:** `analysis/` pronto e `docs/entrega-s1s2.md` iniciado.

## Ciclo 2 — Validação e análise

### Onda 1 — A (22–23/11)

#### #A-6 Revisão do plano à luz do piloto
- [ ] Definir as regras de **descarte**: linha `bloqueada`, linha com `erro`, janela `fora` e `gatilho != 'schedule'`.
- [ ] Definir as regras de **sinalização sem descarte**: mudança de `lighthouse_version` e uso de reserva.
- [ ] Registrar as janelas BRT (18h–23h59 = pico, 00h–07h59 = madrugada) como decisão de método.
- [ ] Mudar só o que não quebra o desenho.

**Aceite:** `docs/proposta.md` tem a seção "Regras de validação", com cada regra no formato condição → ação (descartar ou sinalizar).

#### #A-7 Ameaças à validade v1 e calendário da Black Friday
- [ ] Criar `docs/ameacas.md` com a tabela do §5.10: os 4 tipos, com mitigação para cada ameaça.
- [ ] Registrar o calendário promocional do ML com fonte: de 18 a 23/11 o que foi **observado** e de 24 a 28/11 o que foi **anunciado**.

**Aceite:** há pelo menos uma ameaça por tipo, todas as linhas têm mitigação e o calendário tem fonte e data.

#### #A-8 Decidir a extensão da coleta até 28/11
- [ ] Decidir se a coleta **desliga após 25/11 05h07** ou segue até 28/11 só para uma análise exploratória separada.
- [ ] Registrar a decisão em `docs/proposta.md` e avisar B.

**Aceite:** a decisão está registrada com data, e B confirmou que recebeu.

#### #A-9 Seções da proposta no documento de entrega
- [ ] Levar para `docs/entrega-s1s2.md` 7 seções: evidências, pergunta, GQM, entidades e escalas, 7 categorias v1, hipóteses e ética.

**Aceite:** `docs/entrega-s1s2.md` contém as 7 seções.

**Passagem A → B:** regras de validação e decisão sobre a extensão.

### Onda 2 — B (24/11 – manhã de 25/11)

#### #B-6 Monitoramento e anomalias (24–25/11)
- [ ] Fazer a checagem do #T-0 em 24 e 25/11.
- [ ] Registrar cada anomalia em `docs/anomalias.md`: data, run_id, tipo e ação tomada.
- [ ] Anotar em `docs/anomalias.md` os banners e campanhas vistos em 24–25/11.

**Aceite:** `docs/anomalias.md` tem registros em 24 e em 25/11.

#### #B-7 Validação e dataset consolidado
**Arquivos:** criar `scripts/validate.py` e `tests/test_validate.py`.

**Interface:** `validate(raw_dir: str, inicio: str = "2026-11-18T21:00Z", fim: str = "2026-11-25T11:00Z") -> tuple[DataFrame, list[dict]]`, que devolve o dataset e as anomalias.
- O recorte usa o `ts_inicio_utc` da execução (`run_id`), em intervalo semiaberto [inicio, fim).
  - 21h00Z corresponde às 18h BRT de 18/11 (início da janela de pico).
  - 11h00Z corresponde às 08h BRT de 25/11 (fim da janela de madrugada).
- Reusa `analysis.stats.filtro_minimo` e não lê `data/raw/testes/` nem `data/raw/exploratoria/`.
- Grava `data/processed/dataset.csv` e acrescenta ao `docs/anomalias.md`.
- Imprime a reconciliação.

**Testes:**
- [ ] `test_validate_cobertura`: uma execução com 37 linhas gera a anomalia `cobertura_incompleta`.
- [ ] `test_validate_execucao_ausente`: o conjunto esperado tem 28 pares (`data_brt`, `cron`). Sem um deles, gera a anomalia `execucao_ausente`.
- [ ] `test_validate_exclui_bloqueadas_e_fora`: linhas `bloqueada` ou com janela `fora` não entram e são contadas como anomalias.
- [ ] `test_validate_exclui_erro`: linha com `erro` não vazio não entra.
- [ ] `test_validate_exclui_manual`: linhas com `gatilho != 'schedule'` não entram.
- [ ] `test_validate_inclui_ultima_execucao`:
  - uma execução iniciada em `2026-11-25T08:31Z`, com linhas até `08:58Z`, entra inteira;
  - uma iniciada em `2026-11-25T23:07Z` não entra.
- [ ] `test_validate_versao_lighthouse`: duas versões diferentes geram a anomalia `mudanca_versao` e as linhas **continuam** no dataset.

**Passos:**
- [ ] Ver falhar, implementar, ver passar e fazer commit.
- [ ] **Na manhã de 25/11**, depois de confirmar no Actions que a execução das 05h07 terminou e o CSV foi commitado:
  - rodar `python scripts/validate.py`;
  - fazer commit do `dataset.csv`.

**Aceite:** a reconciliação impressa fecha (`len(dataset) + linhas_excluidas + 38 × execucoes_ausentes == 1064`), e cada exclusão está em `docs/anomalias.md`.

#### #B-8 Release dos JSONs e fim da coleta
- [ ] Baixar os artifacts das 28 execuções agendadas e juntar num `json-brutos.zip`. Criar a release `coleta-principal` com ele.
- [ ] Aplicar a decisão do #A-8 **antes de 25/11 às 20h07**: desabilitar o workflow ou trocar o `--out` para `data/raw/exploratoria`.

**Aceite:** a release `coleta-principal` existe com as 28 execuções, e o workflow está desabilitado ou gravando em `data/raw/exploratoria/`.

**Passagem B → C:** `data/processed/dataset.csv` e `docs/anomalias.md` até a manhã de 25/11.

### Onda 3 — C (tarde de 25/11 – 26/11)

#### #C-6 Análise completa
- [ ] Rodar `python analysis/analise.py --input data/processed/dataset.csv`.
- [ ] Salvar o QQ-plot e o gráfico de resíduos × ajustados.
- [ ] Aplicar o critério fixado antes de olhar os p: se mais de 5% dos resíduos padronizados passarem de ±3, rodar a alternativa robusta (modelo misto sobre postos alinhados, com `stats.art_alinhar`). Registrar a decisão.
- [ ] Se houver `mudanca_versao`, rodar H1–H5 de novo sem as `data_brt` afetadas e relatar as duas versões lado a lado.
- [ ] Gerar a tabela H1–H5 com estatística, p, p de Holm e tamanho de efeito. As razões levam IC de 95%; ε² e Cliff's delta levam IC por bootstrap com 2.000 reamostragens.

**Aceite:** `analysis/out/tabela_hipoteses.csv` tem 5 linhas (H1–H5), com estatística, p, p de Holm, efeito e IC.

#### #C-7 Montar e entregar a entrega única S01 + S02
- [ ] Completar `docs/entrega-s1s2.md` com resultados, ameaças v1 e anomalias.
- [ ] Marcar o checklist do que o PDF pede:
  - **S01:** proposta, evidências, pergunta, caminho, 7 categorias v1, plano de coleta e análise, piloto;
  - **S02:** coleta completa, dados validados e versionados, análise, ameaças.
- [ ] Entregar em 26/11.

**Aceite:** a entrega foi feita em 26/11, e o checklist S01/S02 está marcado em `docs/entrega-s1s2.md`.

---

# Sprint S03 — Impacto, conclusões e entrega final (27/11–03/12)

Documento final: `docs/documento-final.md`. Cada onda escreve a sua parte já na versão final.

### Onda 1 — A (27–28/11)

#### #A-10 7 categorias e ameaças finais
- [ ] Revisar as 7 categorias com justificativa, considerando os resultados.
- [ ] Finalizar `docs/ameacas.md`.
- [ ] Completar o calendário promocional observado até 25/11 (ou 28/11, se a coleta foi estendida).
- [ ] Levar tudo para o documento final.

**Aceite:** as seções estão em `docs/documento-final.md`, e cada categoria tem justificativa ligada a um resultado.

#### #A-11 Método, limitações e conclusão "O que o estudo mostrou?"
- [ ] Escrever no documento final as seções de método (desenho, GQM, escalas, ética) e de limitações.
- [ ] Escrever a conclusão de **"O que o estudo mostrou?"**.

**Aceite:** as seções existem em `docs/documento-final.md`.

**Passagem A → B:** as seções de A estão fechadas no documento final.

### Onda 2 — B (29–30/11)

#### #B-9 Fontes de impacto
- [ ] Criar `docs/impacto-fontes.md` com link e data de acesso para:
  - a audiência mensal do ML no Brasil;
  - a % de acessos móveis;
  - a prevalência de pessoas com deficiência **por tipo** (visual, auditiva, motora, mental/intelectual), do IBGE (PNAD Contínua).
- [ ] Se só houver audiência da América Latina, registrar a proporção do Brasil informada pelo RI ou declarar a limitação.
- [ ] (Opcional) Fazer 1 medição pontual no PSI web de 2 concorrentes, só descritiva e sem teste (§2 e §5.11).

**Aceite:** cada número tem link e data de acesso.

#### #B-10 Resultados e reaproveitamento dos Labs
- [ ] Escrever a seção de resultados no documento final, a partir de `analysis/out/`.
- [ ] Escrever a tabela de reaproveitamento dos Labs 01–04 (§5.12).

**Aceite:** cada número da seção de resultados aponta para um arquivo em `analysis/out/`.

#### #B-11 README de reprodutibilidade
- [ ] Documentar no `README.md`:
  - como rodar a coleta, a validação, a análise e os testes;
  - onde estão os dados e a release;
  - o link do Project.

**Aceite:** um colega consegue, só com o README, rodar `pytest` e `python analysis/analise.py --input data/processed/dataset.csv` num clone limpo.

#### #B-12 Exploração da Black Friday (somente se o #A-8 decidiu estender)
- [ ] Descrever os dados de 26–28/11 (`data/raw/exploratoria/`), separados do conjunto principal e sem teste de hipótese.

**Aceite:** a seção exploratória existe e não tem p-valor, ou há o registro "não estendido".

**Passagem B → C:** as seções de resultados e de reaproveitamento estão prontas, junto com `docs/impacto-fontes.md`.

### Onda 3 — C (01–03/12)

#### #C-8 Impacto e conclusão "O que isso significa para quem usa?"
- [ ] Calcular as horas de espera por mês (efeito × audiência BR × % móvel).
- [ ] Montar a tabela auditoria reprovada → tipo de deficiência afetada (ex.: `color-contrast` → baixa visão; `image-alt`/`label` → usuários de leitor de tela).
- [ ] Estimar a ordem de grandeza de pessoas potencialmente expostas, por tipo de barreira.
- [ ] Listar os 6 itens do que não é possível afirmar (§5.11).
- [ ] Escrever a conclusão de **"O que isso significa para quem usa?"** no documento final.

**Aceite:** as horas/mês e as pessoas expostas aparecem com fórmula e fontes, a lista tem os 6 itens e a conclusão existe.

#### #C-9 Fechar o documento final
- [ ] Conferir os 8 itens da §8 do PDF:
  1. o software, com números;
  2. a pergunta e o caminho;
  3. as 7 categorias com justificativa;
  4. os conceitos da disciplina;
  5. o reaproveitamento dos Labs;
  6. os resultados com a análise adequada à escala;
  7. as ameaças dos 4 tipos;
  8. o impacto e o que não é possível afirmar.
- [ ] Revisar a consistência dos números e gerar o PDF (ou dashboard) final.

**Aceite:** o PDF final está gerado no repositório, e os números do documento batem com `analysis/out/`.

#### #C-10 Apresentação de 10 minutos
- [ ] Montar os slides cobrindo os 8 itens do #C-9.

**Aceite:** os slides cobrem os 8 tópicos.

### Todos — 03/12

#### #T-1 Ensaio
- [ ] Ensaio cronometrado.
- [ ] Rodada de perguntas cruzadas: cada um explica uma parte que não fez.

**Aceite:** o ensaio dura ≤ 10 min, e cada integrante explicou uma parte que não fez.

**Apresentação: 04/12.**
