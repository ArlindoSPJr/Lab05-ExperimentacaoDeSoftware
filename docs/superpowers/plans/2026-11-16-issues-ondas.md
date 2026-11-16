# Lab05 Mercado Livre — Issues por onda e sprint

> **Para quem executar:** cada issue vira um cartão no GitHub Projects. Issues de código seguem TDD (teste primeiro) e usam checkboxes (`- [ ]`) para acompanhamento.

**Objetivo:** dividir todo o trabalho do design aprovado em issues atribuídas aos papéis A, B e C, em ondas sequenciais (A → B → C) por sprint.

**Arquitetura:**
- Coleta: script Python chamando a PageSpeed Insights API, agendado no GitHub Actions, com CSVs versionados.
- Validação: script que consolida o dataset.
- Análise: script Python com modelo misto, Kruskal-Wallis por URL e concordância com o CrUX.
- Documentação: Markdown em `docs/`.

**Stack:** Python 3.12, `requests`, `pandas`, `scipy`, `statsmodels`, `scikit-posthocs`, `matplotlib`, `pytest`; GitHub Actions; GitHub Projects.

**Spec:** `docs/superpowers/specs/2026-11-16-mercadolivre-desempenho-acessibilidade-design.md`. As referências "§x" apontam para ela.

## Restrições globais (valem para todas as issues)

- O objeto de estudo é o site em operação. GitHub e Actions são só instrumentos.
- **Máx. 1 req/s.** Na prática, ≥ 2 s entre chamadas e 38 chamadas por execução.
- Respeitar o `robots.txt` de cada host e os termos de uso do ML e da PSI. **Nada de login, nada de dados pessoais**, e as capturas de tela são removidas do JSON.
- Coleta principal: **18/11 20h07 → 25/11 05h07 BRT**. Os crons em UTC são `7 23 * * *`, `7 1 * * *`, `7 6 * * *` e `7 8 * * *`.
- **19 URLs**: 6 de categoria, 6 de busca, 6 de produto (+ 6 reservas) e a home como referência. Com 2 perfis (`mobile`, `desktop`), são 38 chamadas por execução e **1.064 medições** no total.
- **Métricas primárias:** LCP (H1, H2, H5), TTFB (H3) e nº de auditorias de acessibilidade reprovadas (H4). Correção de **Holm** com α = 0,05.
- Os dias 26–28/11 (Black Friday, 27/11) **nunca** entram no conjunto principal.
- A chave da API fica só no secret `PSI_API_KEY`.
- Entrega conjunta S01 + S02 em **26/11**. Apresentação em **04/12** e ensaio em **03/12**.

## Pontos de atenção (falhas prováveis sem teste explícito)

1. **CrUX ausente** para uma URL (`loadingExperience` vazio ou sem `metrics`): a linha deve ser gravada com campos CrUX vazios e `crux_origin_fallback` preenchido. A coleta não pode quebrar. Teste: `test_extract_metrics_sem_crux` (#B-2).
2. **Captcha, login ou redirecionamento**, quando `finalUrl` tem host diferente do esperado ou o título contém "captcha" ou "Entrar": a linha é marcada `bloqueada=True` e não entra na análise. Teste: `test_detect_block_redirect` (#B-3).
3. **PSI retorna 429 ou 500**: até 2 novas tentativas com espera. Se todas falharem, a linha é gravada com `erro` e `tentativas=3`, e a execução continua. Teste: `test_call_psi_retry_e_falha` (#B-3).
4. **Cron atrasado** (ex.: a execução das 22h07 rodando às 22h50): a janela é definida pela hora BRT real (18h–23h59 = `pico`, 00h–07h59 = `madrugada`, demais = `fora`). Linhas `fora` são anomalia. Teste: `test_janela_brt` (#B-2).
5. **Produto esgotado**, com URL 404 ou redirecionada: o slot passa para a URL reserva, com `usou_reserva=True`, e a troca é registrada. Teste: `test_slot_usa_reserva` (#B-3).

---

# Sprint conjunta S01 + S02 (16/11–26/11, entrega única em 26/11)

## Ciclo 1 — Preparação e início da coleta

### Onda 1 — A (16–17/11)

#### #A-1 Confirmar tema e entrega conjunta com o professor
- [ ] Confirmar que nenhum outro grupo escolheu o Mercado Livre.
- [ ] Confirmar a entrega conjunta S01 + S02 em 26/11.
- [ ] Registrar as respostas (data e meio) em `docs/proposta.md`.

**Aceite:** as duas confirmações estão registradas. Se alguma for negada, avisar B e C antes de 17/11 e replanejar.

#### #A-2 Criar o GitHub Projects (Kanban)
- [ ] Criar o Project ligado ao repositório, com as colunas Backlog / Em andamento / Revisão / Concluído.
- [ ] Criar uma issue no GitHub para cada item deste arquivo, com label `A`/`B`/`C`, `sprint-1-2`/`sprint-3` e `onda-1`/`onda-2`/`onda-3`.
- [ ] Colocar o link do Project no `README.md` (o PDF exige o link, §7).

**Aceite:** o link está no README e todas as issues estão no Kanban.

#### #A-3 Evidências dos 3 critérios (§5.1)
- [ ] Criar `docs/evidencias.md` com a tabela Critério | Evidência | Número | Fonte (link) | Data de acesso.
- [ ] **Real:** site oficial e documentação para desenvolvedores.
- [ ] **Em operação:** relatório trimestral de RI mais recente, comunicado recente e presença de dados no CrUX.
- [ ] **Alto impacto:** compradores únicos e GMV **recortados para o Brasil**, audiência mensal do domínio e downloads do app.

**Aceite:** todo número tem link e data de acesso, e nenhum valor é inventado.

#### #A-4 Proposta metodológica (§5.2–§5.7)
- [ ] Criar `docs/proposta.md` com a pergunta de pesquisa, o GQM (objetivo no template de Basili e Q1–Q5 com métricas e papel), a tabela de entidades/atributos/escalas, o mapeamento ISO/IEC 25010 (citando a versão) e o SLO de LCP ≤ 2,5 s.
- [ ] Incluir as **7 categorias v1**, conferidas com o material da Aula 8 e com justificativa para cada uma.
- [ ] Incluir as hipóteses H1–H5, com H0, métrica e unidade de análise.
- [ ] Incluir as armadilhas Goodhart, Campbell e McNamara aplicadas ao estudo.

**Aceite:** todas as seções do §5.2 ao §5.7 estão presentes, e as métricas primárias estão marcadas como fixadas antes da coleta.

#### #A-5 Seleção das URLs (§5.6)
- [ ] Criar `config/urls.csv` com as colunas `slot_id,tipo,url,url_reserva,host,criterio,data_selecao`.
- [ ] Categoria: as 6 de maior destaque no menu, com a captura do menu salva em `docs/img/menu-AAAA-MM-DD.png`.
- [ ] Busca: 1 termo genérico por categoria, sem filtros (host `lista.mercadolivre.com.br`).
- [ ] Produto: o 1º "Mais vendido" de cada categoria + 1 reserva por produto.
- [ ] Home: `https://www.mercadolivre.com.br/`, tipo `home`, sem reserva.
- [ ] Justificar o horário de pico (20h–22h) com uma fonte e registrar em `docs/proposta.md`.

**Aceite:** o arquivo tem 19 linhas, os 6 produtos têm `url_reserva` preenchida e todas as URLs abrem sem login.

#### #A-6 Ética (§5.9)
- [ ] Criar `docs/etica.md` com o `robots.txt` de `www.`, `lista.` e `produto.` (conteúdo relevante e data) e com os termos de uso do ML e da PSI API.
- [ ] Checar se alguma URL do `urls.csv` é proibida pelo `robots.txt`. Se for, trocar ou excluir o tipo e registrar.
- [ ] Registrar as regras: ≤ 1 req/s, sem login, sem dados pessoais, capturas removidas.

**Aceite:** existe um registro datado por host e nenhuma URL proibida no `urls.csv`.

**Passagem A → B:** `docs/proposta.md`, `docs/evidencias.md`, `docs/etica.md` e `config/urls.csv` com commit no `main` até 17/11.

### Onda 2 — B (17–18/11) — prazo crítico: workflow ligado até 18/11 20h07

#### #B-1 Setup do repositório e da chave
**Arquivos:** `requirements.txt`, `.gitignore`, `pyproject.toml` (configuração do pytest), `tests/`
- [ ] `requirements.txt` com `requests`, `pandas`, `scipy`, `statsmodels`, `scikit-posthocs`, `matplotlib` e `pytest`.
- [ ] Criar a chave da PSI API no Google Cloud e salvar no secret `PSI_API_KEY` do repositório.
- [ ] Fazer uma chamada manual na URL da home e salvar a resposta, **sem capturas de tela**, em `tests/fixtures/psi_home_mobile.json`.
- [ ] Criar também uma fixture sem CrUX: cópia com `loadingExperience` removido (`tests/fixtures/psi_sem_crux.json`).

**Aceite:** `pytest` roda (mesmo sem testes), as fixtures existem e não têm `final-screenshot`.

#### #B-2 Extração de métricas e janela BRT
**Arquivos:** criar `scripts/collect.py` e `tests/test_collect.py`.

**Interfaces produzidas:**
- `UrlSlot` (dataclass): `slot_id: str, tipo: str, url: str, url_reserva: str | None, host: str`
- `load_urls(path: str) -> list[UrlSlot]`
- `extract_metrics(psi: dict) -> dict`, com as chaves `lcp_ms, fcp_ms, speed_index_ms, tbt_ms, ttfb_ms, total_bytes, n_requests, perf_score, a11y_score, a11y_reprovadas, a11y_reprovadas_ids, lighthouse_version, final_url, titulo, throttling, crux_lcp_p75_ms, crux_lcp_categoria, crux_inp_p75_ms, crux_cls_p75, crux_origin_fallback`
- `janela_brt(ts_utc: datetime) -> tuple[str, str]`, que devolve (`data_brt` "AAAA-MM-DD", janela `pico|madrugada|fora`)

Origem dos campos:
- `lighthouseResult.audits['largest-contentful-paint'|'first-contentful-paint'|'speed-index'|'total-blocking-time'|'server-response-time'|'total-byte-weight'].numericValue`
- `n_requests` = número de itens em `audits['network-requests'].details.items`
- Auditorias reprovadas = itens de `categories.accessibility.auditRefs` cujo audit tem `score == 0`
- CrUX em `loadingExperience.metrics`; fallback em `originLoadingExperience`

- [ ] **Teste 1:** `test_extract_metrics_home`. Com a fixture `psi_home_mobile.json`, `lcp_ms > 0`, `ttfb_ms > 0`, `0 <= a11y_score <= 1`, `a11y_reprovadas == len(a11y_reprovadas_ids)` e `lighthouse_version` não vazio.
- [ ] **Teste 2:** `test_extract_metrics_sem_crux`. Com a fixture `psi_sem_crux.json`, `crux_lcp_p75_ms is None` e sem exceção.
- [ ] **Teste 3:** `test_janela_brt`.
  - `2026-11-18T23:07Z` → `("2026-11-18","pico")`
  - `2026-11-19T01:50Z` → `("2026-11-18","pico")` (22h50 BRT)
  - `2026-11-19T06:07Z` → `("2026-11-19","madrugada")`
  - `2026-11-19T15:00Z` → `("2026-11-19","fora")`
- [ ] **Teste 4:** `test_load_urls`. Um CSV de exemplo com 2 linhas gera 2 `UrlSlot`, e `url_reserva` vazio vira `None`.
- [ ] Rodar `pytest tests/test_collect.py -v` e ver falhar.
- [ ] Implementar. Para BRT, usar UTC−3 fixo (o Brasil não tem horário de verão).
- [ ] Rodar de novo e ver passar. Fazer commit.

#### #B-3 Execução robusta da coleta
**Arquivos:** modificar `scripts/collect.py` e `tests/test_collect.py`.

**Interfaces produzidas:**
- `call_psi(url: str, strategy: str, api_key: str, session, max_retries: int = 2, espera_s: float = 5) -> tuple[dict | None, int, str | None]`, que devolve (json, tentativas, erro)
- `detect_block(metrics: dict, expected_host: str) -> bool`
- `strip_screenshots(psi: dict) -> dict`, que remove `final-screenshot`, `screenshot-thumbnails` e `full-page-screenshot`
- `resolve_url(slot: UrlSlot, estado_reservas: dict) -> tuple[str, bool]`, que devolve (url, usou_reserva)
- `run(urls_path: str, out_dir: str, json_dir: str, api_key: str, seed: int | None = None) -> str`, que devolve o caminho do CSV gravado

Cada linha do CSV contém `run_id, ts_utc, data_brt, janela, posicao, slot_id, tipo, strategy, url_usada, usou_reserva, tentativas, erro, bloqueada` + as chaves de `extract_metrics`.

- [ ] **Teste 1:** `test_call_psi_retry_e_falha`. Com uma sessão falsa que devolve 429 três vezes, o resultado é `(None, 3, "429")`.
- [ ] **Teste 2:** `test_call_psi_retry_sucesso`. Com 500 e depois 200, o resultado é `tentativas == 2`.
- [ ] **Teste 3:** `test_detect_block_redirect`. `final_url` em `www.mercadolivre.com.br/login` → `True`. Título contendo "captcha" → `True`. URL igual → `False`.
- [ ] **Teste 4:** `test_strip_screenshots`. As 3 chaves somem e as demais auditorias continuam.
- [ ] **Teste 5:** `test_slot_usa_reserva`. Um produto marcado como indisponível em `estado_reservas` devolve `(url_reserva, True)`.
- [ ] **Teste 6:** `test_run_ordem_e_cobertura`. Com a PSI simulada e `seed=1`, o CSV tem 38 linhas, o espaçamento simulado é ≥ 2 s e a ordem difere com `seed=2`.
- [ ] Ver falhar, implementar, ver passar e fazer commit.

**Regras:**
- O produto vai para a reserva quando a URL original retorna 404, redireciona para fora da página do produto ou aparece como esgotada.
- O estado das reservas fica em `data/estado_reservas.json`, também commitado, para que a troca persista entre execuções.

#### #B-4 Workflow agendado
**Arquivo:** `.github/workflows/collect.yml`
- [ ] Gatilhos: `schedule` com os 4 crons das restrições globais e `workflow_dispatch`.
- [ ] Passos: setup do Python 3.12, `pip install -r requirements.txt`, `python scripts/collect.py` com `PSI_API_KEY` vindo do secret.
- [ ] Publicar `out/json/` com `actions/upload-artifact`, retenção de 90 dias.
- [ ] Fazer commit de `data/raw/` e `data/estado_reservas.json` com `git pull --rebase` antes do push, para evitar conflito entre execuções.
- [ ] Dar `permissions: contents: write` e `concurrency` para impedir duas execuções simultâneas.
- [ ] Disparar manualmente 1 vez e conferir o CSV com 38 linhas e o artifact publicado.
- [ ] Deixar o workflow no `main` **até 18/11 20h07**.

**Aceite:** a execução manual dá verde, e a primeira execução agendada (18/11 23h07 UTC) aparece na aba Actions.

#### #B-5 Dicionário de dados e checagem de localização
- [ ] Criar `docs/dados.md` com cada coluna do CSV: nome, unidade, origem no JSON e escala (segundo o §5.4).
- [ ] Fazer 3 execuções manuais no PSI web, a partir do Brasil, com a home mobile. Registrar o TTFB e o LCP e comparar com uma execução do Actions, para medir a ameaça externa de localização (§5.10).

**Aceite:** todas as colunas estão documentadas e a comparação está registrada.

**Passagem B → C:** workflow ativo, `docs/dados.md` pronto e primeiras execuções em `data/raw/`.

### Onda 3 — C (19–21/11, inclui o feriado)

#### #C-1 Descritiva do piloto incorporado
**Arquivos:** `analysis/piloto.py` e `analysis/out/piloto/`
- [ ] Carregar as execuções de 18/11 20h07 → 19/11 05h07.
- [ ] Calcular a cobertura (esperado 4 × 38 = 152 linhas), os bloqueios, os erros e o uso de reservas.
- [ ] Calcular mediana e IQR de LCP, TTFB e reprovadas por tipo × perfil × janela, e a variância entre execuções da mesma URL.
- [ ] Se houver um problema que exija descarte, comunicar a B e registrar em `docs/anomalias.md`.

**Aceite:** existe um relatório curto com cobertura, bloqueios e variâncias.

#### #C-2 Biblioteca de análise com testes
**Arquivos:** criar `analysis/stats.py` e `tests/test_stats.py`.

**Interfaces produzidas:**
- `por_url(df, metrica: str, agg: str = "median") -> DataFrame`, uma linha por `slot_id × strategy`
- `kruskal_por_tipo(df_url, metrica: str) -> dict`, com as chaves `H, p, eps2, dunn` (DataFrame com p de Holm)
- `modelo_misto(df, metrica: str) -> dict`, com as chaves `coef` (razões exp(β)), `ic95` e `p`. A fórmula é `np.log(metrica) ~ strategy * janela * tipo`, com efeitos aleatórios cruzados de `slot_id` e `data_brt` via `statsmodels` `mixedlm` (`groups` constante + `vc_formula`).
- `concordancia_crux(df) -> dict`, com as chaves `n_pares, wilcoxon_p, spearman_rho, bland_altman` (média e limites) e `kappa`
- `holm(pvals: dict[str, float]) -> dict[str, float]`
- `cliffs_delta(x, y) -> float`

- [ ] `test_holm`: `{"a":0.01,"b":0.04,"c":0.03}` → `{"a":0.03,"b":0.06,"c":0.06}`.
- [ ] `test_cliffs_delta`: `x=[1,2,3]` e `y=[4,5,6]` → `-1.0`.
- [ ] `test_kruskal_eps2`: 3 grupos sintéticos claramente separados (6 por grupo) → `p < 0.05` e `0 < eps2 <= 1`.
- [ ] `test_por_url_mediana`: um slot com valores `[1,2,100]` → `2`.
- [ ] `test_modelo_misto_recupera_efeito`: dados sintéticos com o perfil móvel 2× mais lento → `coef["strategy[T.mobile]"]` entre 1,8 e 2,2.
- [ ] Ver falhar, implementar, ver passar e fazer commit.

#### #C-3 Simulação do efeito mínimo detectável (Lab04)
**Arquivo:** `analysis/poder.py`
- [ ] Usar a variância do piloto (#C-1). Simular 1.000 datasets com n = 6 URLs por tipo, 7 dias e 2 execuções por janela, variando o efeito.
- [ ] Encontrar o menor efeito com poder ≥ 0,8 para H2 (Kruskal-Wallis por URL) e para H3 (modelo misto).
- [ ] Simular o erro tipo I com efeito 0 e verificar se fica ≈ 0,05.

**Aceite:** existe uma tabela com o efeito mínimo detectável de H2 e H3 e o erro tipo I observado.

#### #C-4 Script de análise completo rodando sobre o piloto
**Arquivo:** `analysis/analise.py`, com entrada `data/processed/dataset.csv` (ou os CSVs brutos, no piloto) e saída em `analysis/out/`.
- [ ] Gerar a descritiva por combinação e o SLI de LCP ≤ 2,5 s.
- [ ] Rodar H1 e H3 com `modelo_misto`, H2 e H4 com `kruskal_por_tipo` sobre `por_url` (H4 usando a moda), e H5 com `concordancia_crux`.
- [ ] Aplicar `holm` sobre os 5 p primários.
- [ ] Gerar boxplots por combinação e o gráfico de Bland-Altman.
- [ ] Rodar sobre o piloto sem erro, mesmo com poucos dados.

**Aceite:** `python analysis/analise.py --input data/raw` gera `analysis/out/` sem exceção.

#### #C-5 Seção "Plano de coleta e análise + piloto"
- [ ] Criar `docs/entrega-s1s2.md` com esta seção: o desenho, os resultados do piloto e o efeito mínimo detectável.

**Passagem C → A:** `analysis/` pronto e `docs/entrega-s1s2.md` iniciado.

## Ciclo 2 — Validação e análise

### Onda 1 — A (22–23/11)

#### #A-7 Revisão do plano à luz do piloto
- [ ] Definir critérios de validação e regras de descarte: linha `bloqueada`, linha com `erro`, janela `fora` e mudança de `lighthouse_version`.
- [ ] Mudar só o que não quebra o desenho.
- [ ] Registrar em `docs/proposta.md`, seção "Regras de validação".

#### #A-8 Ameaças à validade v1 e calendário da Black Friday
- [ ] Criar `docs/ameacas.md` com a tabela do §5.10, os 4 tipos e uma mitigação para cada ameaça.
- [ ] Registrar o calendário promocional do ML de 18 a 28/11: banners, campanhas e datas observadas, com fonte.

#### #A-9 Decidir a extensão da coleta até 28/11
- [ ] Decidir se a coleta **desliga após 25/11 05h07** ou segue até 28/11 só para uma análise exploratória separada.
- [ ] Registrar a decisão em `docs/proposta.md` e avisar B.

#### #A-10 Seções da proposta no documento de entrega
- [ ] Levar evidências, pergunta, GQM, entidades/escalas, 7 categorias v1, hipóteses e ética para `docs/entrega-s1s2.md`.

**Passagem A → B:** regras de validação e decisão sobre a extensão.

### Onda 2 — B (24/11 – manhã de 25/11)

#### #B-6 Monitoramento e anomalias
- [ ] Conferir diariamente a aba Actions e os e-mails de falha.
- [ ] Registrar cada anomalia em `docs/anomalias.md`: data, run_id, tipo e ação tomada.

#### #B-7 Validação e dataset consolidado
**Arquivos:** criar `scripts/validate.py` e `tests/test_validate.py`.

**Interface:** `validate(raw_dir: str, inicio: str = "2026-11-18T23:07Z", fim: str = "2026-11-25T08:07Z") -> tuple[DataFrame, list[dict]]`, que devolve o dataset e as anomalias. Grava `data/processed/dataset.csv` e acrescenta ao `docs/anomalias.md`.

- [ ] `test_validate_cobertura`: uma execução com 37 linhas gera a anomalia `cobertura_incompleta`.
- [ ] `test_validate_exclui_bloqueadas_e_fora`: linhas `bloqueada` ou com janela `fora` não entram no dataset e são contadas como anomalias.
- [ ] `test_validate_recorta_periodo`: linhas de 26/11 não entram.
- [ ] `test_validate_versao_lighthouse`: duas versões diferentes geram a anomalia `mudanca_versao`.
- [ ] Ver falhar, implementar, ver passar e fazer commit.
- [ ] **Na manhã de 25/11**, depois da execução das 05h07, rodar `python scripts/validate.py` e fazer commit do `dataset.csv`.

**Aceite:** o dataset tem ≈ 1.064 linhas menos as anomalias, com as anomalias documentadas.

#### #B-8 Release dos JSONs e fim da coleta
- [ ] Baixar os artifacts e juntar num `json-brutos.zip`. Criar a release `coleta-principal` com ele.
- [ ] Aplicar a decisão do #A-9: desabilitar o workflow ou mantê-lo até 28/11 gravando em `data/raw/exploratoria/`.

**Passagem B → C:** `data/processed/dataset.csv` e `docs/anomalias.md` até a manhã de 25/11.

### Onda 3 — C (tarde de 25/11 – 26/11)

#### #C-6 Análise completa
- [ ] Rodar `python analysis/analise.py --input data/processed/dataset.csv`.
- [ ] Revisar os resíduos do modelo misto. Se forem ruins, usar ART-ANOVA como alternativa e registrar.
- [ ] Gerar uma tabela com H1–H5: estatística, p, p de Holm e tamanho de efeito com IC.

#### #C-7 Montar e entregar a entrega única S01 + S02
- [ ] Completar `docs/entrega-s1s2.md` com resultados, ameaças v1 e anomalias.
- [ ] Revisar se cobre o que o PDF pede para a S01 (proposta, evidências, pergunta, caminho, 7 categorias v1, plano, piloto) e para a S02 (coleta completa, dados validados e versionados, análise, ameaças).
- [ ] Entregar em 26/11.

---

# Sprint S03 — Impacto, conclusões e entrega final (27/11–03/12)

Documento final: `docs/documento-final.md`. Cada onda escreve a sua parte já na versão final.

### Onda 1 — A (27–28/11)

#### #A-11 7 categorias e ameaças finais
- [ ] Revisar as 7 categorias com justificativa, considerando os resultados.
- [ ] Finalizar `docs/ameacas.md`.
- [ ] Levar as duas coisas para o documento final.

#### #A-12 Método, conclusões e limitações
- [ ] Escrever as seções de método (desenho, GQM, escalas, ética), conclusões e limitações no documento final.

**Passagem A → B:** as seções de A estão fechadas no documento final.

### Onda 2 — B (29–30/11)

#### #B-9 Fontes de impacto
- [ ] Criar `docs/impacto-fontes.md` com a audiência mensal do ML no Brasil, a % de acessos móveis e a prevalência de pessoas com deficiência (IBGE, PNAD Contínua), com link e data de acesso.

#### #B-10 Resultados e reaproveitamento dos Labs
- [ ] Escrever a seção de resultados no documento final, a partir de `analysis/out/`.
- [ ] Escrever a tabela de reaproveitamento dos Labs 01–04 (§5.12).

#### #B-11 README de reprodutibilidade
- [ ] Documentar no `README.md` como rodar a coleta, a validação, a análise e os testes; onde estão os dados e a release; e o link do Project.

#### #B-12 Exploração da Black Friday (somente se o #A-9 decidiu estender)
- [ ] Descrever os dados de 26–28/11, separados do conjunto principal e sem teste de hipótese.

**Passagem B → C:** as seções de resultados e de reaproveitamento estão prontas, junto com `docs/impacto-fontes.md`.

### Onda 3 — C (01–03/12)

#### #C-8 Impacto e "o que não é possível afirmar"
- [ ] Calcular as horas de espera por mês (efeito × audiência BR × % móvel).
- [ ] Estimar a ordem de grandeza de pessoas potencialmente expostas às barreiras, por tipo de barreira.
- [ ] Listar o que não é possível afirmar (§5.11).

#### #C-9 Fechar o documento final
- [ ] Conferir os 8 itens sugeridos na §8 do PDF.
- [ ] Revisar a consistência dos números e gerar o PDF (ou dashboard) final.

#### #C-10 Apresentação de 10 minutos
- [ ] Montar os slides cobrindo: software e números; pergunta e caminho; 7 categorias; conceitos; reaproveitamento; resultados; ameaças; impacto e limites.

### Todos — 03/12

#### #T-1 Ensaio
- [ ] Ensaio cronometrado (≤ 10 min).
- [ ] Rodada de perguntas cruzadas: cada um explica uma parte que não fez.

**Apresentação: 04/12.**
