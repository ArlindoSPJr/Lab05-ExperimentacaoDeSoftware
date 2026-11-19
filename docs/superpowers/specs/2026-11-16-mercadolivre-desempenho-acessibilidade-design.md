# Lab05 — Desempenho e acessibilidade do site do Mercado Livre (design)

Data: 2026-11-16 · Revisão 2 (incorpora a revisão independente de conformidade com o enunciado) · Base: `Lab05Medicao.pdf`

## 1. Intenção

Medir, de fora e como um usuário comum, o **desempenho** e a **acessibilidade** do site do Mercado Livre (mercadolivre.com.br) e responder às duas perguntas do Lab05:

- **O que o estudo mostrou?** Como o tempo de carregamento e as barreiras de acessibilidade variam com o tipo de página, o perfil de dispositivo e o horário, e se a medição sintética reflete os usuários reais.
- **O que isso significa para quem usa?** Quanto tempo os usuários (principalmente no celular) passam esperando, e quantas pessoas com deficiência podem encontrar barreiras, estimado com números públicos e com fonte.

## 2. Objetivos, não objetivos e antiobjetivos

**Objetivos**
- Ter um estudo quase-experimental com 3 fatores controlados (desenho fatorial 3 × 2 × 2), coleta automatizada e dados versionados.
- Combinar **três caminhos** do PDF (§2b):
  - *medir o serviço de fora*: medição sintética do Lighthouse via PageSpeed Insights;
  - *avaliar a qualidade do produto*: ISO/IEC 25010, eficiência de desempenho e acessibilidade/WCAG;
  - *analisar dados de operação*: **dados de campo** de usuários reais do Chrome (CrUX).
- Dividir o trabalho em **ondas sequenciais**: em cada sprint, A faz a onda 1, entrega para B (onda 2), que entrega para C (onda 3).

**Não objetivos**
- Comparar o ML com concorrentes por teste de hipótese. No máximo, concorrentes podem aparecer como referência descritiva na seção de impacto.
- Medir o app nativo, o checkout ou as páginas logadas.

**Antiobjetivos** (o trabalho fracassa se acontecer, mesmo que "funcione")
- Fazer qualquer coisa parecida com teste de carga, passar de 1 requisição por segundo ou desrespeitar o `robots.txt` e os termos de uso.
- Coletar ou versionar dados pessoais, inclusive em capturas de tela.
- Afirmar algo sobre todos os usuários do ML com base em medições sintéticas, sem discutir a validade externa.

## 3. Restrições (do PDF)

- O objeto de estudo é o **site em operação**. O GitHub e o GitHub Actions são só instrumentos de coleta, nunca objeto de pesquisa (§2a e §10).
- O grupo precisa provar com fontes datadas os 3 critérios: real, em operação e alto impacto. Ver o §5.1. **Nenhum número foi assumido neste documento.**
- Nenhum outro grupo pode estudar o mesmo software. **Confirmado: nenhum outro grupo escolheu o Mercado Livre.**
- Entregas: S01, S02, S03 e Final, com 5 pontos cada. A apresentação é de 10 min, **em 04/12**.
- O PDF pede o link do repositório e do **GitHub Projects** (§7). O Kanban é criado na S01.

## 4. Abordagens consideradas

| Decisão | Opções avaliadas | Escolha do grupo | Motivo |
|---|---|---|---|
| Tema | (1) Páginas de status de SaaS; (2) Desempenho e acessibilidade de e-commerce; (3) Node.js 20×22×24 local | **(2), com o Mercado Livre** | Preferência do grupo |
| Comparação | (A) Só o ML, variando fatores; (B) ML × concorrentes | **(A)** | Mantém um único software, controla os fatores e reduz o risco de colisão com outro grupo |
| Coleta | (1) PageSpeed Insights API + GitHub Actions; (2) Lighthouse local; (3) Lighthouse no GitHub Actions | **(1)** | Automatizada, versiona os dados sozinha e traz o CrUX (usuários reais) |

## 5. Desenho do estudo

### 5.1 Evidências dos 3 critérios (preencher na S01, onda 1)

| Critério | Evidência a buscar | Número | Fonte (link) | Data de acesso |
|---|---|---|---|---|
| Real | Site oficial, página institucional, documentação para desenvolvedores (developers.mercadolivre.com.br) | — | | |
| Em operação | Relatório trimestral de RI mais recente (investor.mercadolibre.com), comunicados recentes, presença de dados no CrUX (tráfego ativo nos últimos 28 dias) | — | | |
| Alto impacto | Compradores únicos e GMV **recortados para o Brasil** (os relatórios de RI cobrem a América Latina inteira), audiência mensal do domínio (ranking público acessível) e downloads do app | — | | |

### 5.2 Pergunta de pesquisa

> O desempenho e a acessibilidade do site do Mercado Livre variam conforme o tipo de página, o perfil de dispositivo e o horário de acesso? E a medição sintética reflete a experiência dos usuários reais?

### 5.3 GQM (template de Basili)

**Objetivo:** analisar *o site do Mercado Livre*, com o propósito de *caracterizar e comparar*, com respeito a *desempenho de carregamento e acessibilidade*, do ponto de vista *do usuário final*, no contexto de *páginas públicas medidas com perfis móvel e desktop em horários de pico e de baixa demanda*.

| Pergunta | Métricas | Papel |
|---|---|---|
| Q1. O perfil de dispositivo afeta o carregamento? | **LCP** (primária), FCP, Speed Index, TBT | H1 |
| Q2. O tipo de página afeta desempenho e peso? | **LCP** (primária); peso total (bytes) e nº de requisições | H2 (LCP); bytes e requisições são **descritivas** |
| Q3. O horário de pico piora a resposta do servidor? | **TTFB** (server-response-time, primária); LCP | H3 |
| Q4. Quantas barreiras de acessibilidade existem e onde? | **Nº de auditorias de acessibilidade reprovadas** (primária), por tipo de auditoria (contraste, rótulos, alt etc.); nota de acessibilidade (descritiva) | H4 |
| Q5. A medição sintética reflete a experiência dos usuários reais? | LCP sintético (mediana por URL) × p75 de LCP do CrUX; categoria CrUX (FAST/AVERAGE/SLOW). O INP do CrUX entra só como descritivo, porque o Lighthouse não mede INP (o TBT é só um proxy) | H5 |

As **métricas primárias** (LCP, TTFB e nº de auditorias reprovadas) foram fixadas antes da coleta. As demais são descritivas e não entram em teste de hipótese.

### 5.4 Entidades, atributos e escalas

| Métrica | Entidade | Atributo | Direta / derivada | Escala | Estatísticas permitidas |
|---|---|---|---|---|---|
| TTFB | Recurso (infraestrutura do ML) | Externo: tempo de resposta do servidor | Direta (observada no carregamento) | Razão | Todas (média geométrica, razões, testes paramétricos ou não) |
| LCP, FCP, Speed Index, TBT | Produto (página web) | Externo: tempo percebido | **Derivada**: o PSI simula o throttling (Lantern) a partir de um carregamento | Razão | Todas, analisadas em log |
| Peso total, nº de requisições | Produto (página web) | Interno: tamanho | Direta | Razão | Todas |
| Nº de auditorias de acessibilidade reprovadas | Produto (página web) | Externo: acessibilidade (barreiras detectáveis) | Direta (contagem) | Razão (discreta) | Mediana, contagens, testes não paramétricos |
| Nota de desempenho e de acessibilidade (0–100) | Produto | Externo, agregado | **Derivada**: soma ponderada de curvas log-normais | Tratada como **ordinal** | Mediana, percentis, testes de postos. Não usar médias |
| Categoria CrUX (FAST/AVERAGE/SLOW) | Produto em uso | Externo: experiência do usuário | Derivada (p75 de campo) | Ordinal | Moda, proporções, kappa |
| p75 de LCP do CrUX | Produto em uso | Externo | Derivada (agregação de 28 dias) | Razão | Comparação pareada |

**Mapeamento na ISO/IEC 25010:**
- Eficiência de desempenho → *comportamento temporal* (TTFB, LCP etc.) e *utilização de recursos* (bytes, requisições).
- Acessibilidade → característica *usabilidade* na versão 2011, ou *inclusividade/acessibilidade* (dentro de *capacidade de interação*) na versão 2023. Citar a versão usada.

**SLI/SLO:** o limiar "bom" dos Core Web Vitals (LCP ≤ 2,5 s no p75) é usado como SLO de referência. O SLI é a fração das medições de cada combinação que cumpre o limiar. Esse uso é descritivo e não entra em teste.

### 5.5 Classificação nas 7 categorias de pesquisa (v1, para A conferir com a Aula 8)

| Categoria | Classificação | Justificativa |
|---|---|---|
| Natureza | Aplicada | Gera conhecimento sobre um software em produção, com impacto direto para usuários e para a empresa |
| Objetivos | Descritiva e explicativa | Caracteriza desempenho e acessibilidade (Q1–Q4) e testa se os fatores explicam a variação (H1–H4) |
| Abordagem | Quantitativa | Métricas numéricas e testes estatísticos |
| Procedimentos | Quase-experimento de campo, com análise de dados de operação (CrUX) | Os fatores são escolhidos pelo grupo, mas não há randomização dos objetos (as URLs são escolhidas por critério) e o sistema não é controlado |
| Tempo | Longitudinal curto | Medidas repetidas ao longo de 7 dias |
| Controle | Parcial | O grupo controla as URLs, os horários, o perfil e a ordem das chamadas. Não controla o ML (deploys, promoções) nem a infraestrutura do PSI |
| Nível de evidência | Moderado | Ganha força com o desenho fatorial, as repetições e a triangulação com o CrUX. Perde com a ausência de randomização, o período atípico (Black Friday) e a medição sintética. Ver o §5.10 |

### 5.6 Objetos, fatores e variáveis

**Objetos e seleção das URLs.** Para tipo de página, a unidade experimental é a **URL**. Por isso são **6 URLs por tipo**, escolhidas por critério explícito e registradas em `config/urls.csv` com o critério usado.

| Tipo | Critério de seleção (6 URLs) | Host |
|---|---|---|
| Categoria | As 6 categorias de maior destaque no menu principal do ML (registrar captura do menu e data) | www.mercadolivre.com.br |
| Busca | 1 termo genérico por categoria escolhida (ex.: "celular", "notebook"), sem filtros | lista.mercadolivre.com.br |
| Produto | O 1º item da lista "Mais vendidos" de cada uma das 6 categorias, mais **1 URL reserva** por produto, também registrada antes da coleta | www.mercadolivre.com.br / produto.mercadolivre.com.br |
| Home (referência) | Apenas `https://www.mercadolivre.com.br/` | www.mercadolivre.com.br |

A home só tem uma URL possível, por isso **não entra nos testes de tipo de página**. Ela é medida como referência descritiva.

**Fatores e níveis** (fatorial 3 × 2 × 2 + home)

| Fator | Níveis |
|---|---|
| Tipo de página | categoria, busca, produto |
| Perfil de dispositivo | perfil **móvel** do Lighthouse (4G lento simulado + CPU 4× mais lenta) × perfil **desktop** (parâmetro `strategy` da PSI) |
| Horário | pico (20h07 e 22h07 BRT) × madrugada (03h07 e 05h07 BRT) |

A justificativa de "pico" como horário de maior uso residencial noturno precisa de **fonte** (ex.: relatório de tráfego de internet no Brasil), a cargo de A na S01. Os crons ficam em :07 para evitar a fila do GitHub Actions na hora cheia.

**Variáveis**
- Dependentes: LCP, TTFB e nº de auditorias de acessibilidade reprovadas (primárias); FCP, Speed Index, TBT, bytes, requisições e notas (descritivas).
- Independentes: tipo, perfil e horário.
- Controladas e registradas em cada linha: `lighthouseVersion`, configuração de throttling, `finalUrl`, status HTTP, título da página, horário real da execução, posição da URL na ordem sorteada, dia da semana.

**Volume.**
- Cada execução faz 19 URLs × 2 perfis = 38 chamadas, sequenciais, com ≥ 2 s entre elas e **ordem sorteada a cada execução**.
- São 4 execuções por dia durante 7 dias (18/11 20h07 → 25/11 05h07), o que dá **1.064 medições**.
- Cada combinação tipo × perfil × horário tem 6 URLs × 2 execuções × 7 dias = 84 medições, mas **n = 6 unidades independentes** (as URLs) para o fator tipo.

### 5.7 Hipóteses

| | Hipótese (H1) | H0 | Métrica | Unidade de análise |
|---|---|---|---|---|
| H1 | O LCP no perfil móvel do Lighthouse é maior que no perfil desktop | Não há diferença | LCP | Medição, com efeitos aleatórios de URL e dia |
| H2 | O LCP difere entre categoria, busca e produto | Não há diferença | LCP | **URL** (mediana por URL, n = 6 por tipo) |
| H3 | O TTFB é maior no pico do que na madrugada | Não há diferença | TTFB | Medição, com efeitos aleatórios de URL e dia |
| H4 | O nº de auditorias de acessibilidade reprovadas difere entre os tipos | Não há diferença | Nº de reprovadas | **URL** (valor modal por URL, n = 6 por tipo) |
| H5 | O LCP sintético móvel concorda com o p75 de LCP do CrUX | — (análise de concordância) | LCP | Par por URL (só as URLs com CrUX) |

H1 é parcialmente verdadeira por construção, porque o perfil móvel aplica throttling. O interesse está no **tamanho** da diferença por tipo de página e na interação com o horário, e não só no p-valor. Isso é discutido como ameaça de construto.

### 5.8 Análise estatística (escolhida a priori, sem "teste de normalidade → escolher teste")

- **Descritiva:** mediana, IQR, percentis 75 e 90, e boxplots por combinação, sempre por URL e no agregado. Também a fração de medições que cumpre o SLO.
- **H1 e H3, com interações:** modelo linear de efeitos mistos
  `log(métrica) ~ perfil * horário * tipo + (1 | URL) + (1 | dia)`.
  Os fatores usam codificação de soma (Sum), então o efeito principal de cada fator é estimado **na média dos outros fatores**, e não numa célula de referência. O efeito é relatado como **razão** (ex.: "o pico é 1,15× mais lento"), com IC de 95%. Alternativa robusta, se mais de 5% dos resíduos padronizados passarem de ±3 (critério fixado antes de olhar os p): modelo misto sobre postos alinhados (ART).
- **H2 e H4:** Kruskal-Wallis sobre os valores **agregados por URL** (n = 6 por tipo), com tamanho de efeito **ε²** e post-hoc de Dunn. A acessibilidade é praticamente constante entre as repetições de uma URL, então as repetições não contam como amostras. O teste primário usa o perfil **móvel**, e o desktop é relatado como sensibilidade. A home fica fora dos testes.
- **H5:** para cada URL com CrUX, compara a mediana sintética móvel com o p75 do CrUX:
  - Wilcoxon pareado e Spearman;
  - gráfico de Bland-Altman;
  - concordância de categoria (FAST/AVERAGE/SLOW) com kappa de Cohen.

  As URLs sem CrUX são listadas, e o valor da origem é usado só como referência.
- **Comparações múltiplas:** correção de **Holm** sobre os 5 testes primários (α = 0,05). Os post-hoc também são corrigidos. Todos os testes são **bilaterais**.
- **Tamanhos de efeito:** razão (modelo misto), Cliff's delta ou r (2 níveis) e ε² (Kruskal-Wallis).
- **Poder (Lab04):** a coleta tem duração fixa por causa do cronograma e da Black Friday, então a simulação **não define o nº de dias**. Ela estima o **efeito mínimo detectável** com n = 6 URLs por tipo e 7 dias, e esse número entra na discussão de validade de conclusão.

### 5.9 Coleta (instrumentação)

- **`scripts/collect.py`** (Python) faz uma chamada por URL e perfil:
  - lê `config/urls.csv`, **sorteia a ordem** das URLs e chama `https://www.googleapis.com/pagespeedonline/v5/runPagespeed` com `category=performance&category=accessibility` para cada `strategy`;
  - em caso de erro, **tenta de novo dentro da própria execução** (até 2 vezes, com espera) e registra o nº de tentativas;
  - grava uma linha por chamada em `data/raw/AAAA-MM-DD_BRT.csv`. O arquivo é nomeado pela data **BRT da janela**: as execuções de 20h07 e 22h07 de uma noite ficam no mesmo arquivo. A data e a janela (18h–23h59 = pico, 00h–07h59 = madrugada) são calculadas uma vez por execução, a partir do horário de início, em modo de acréscimo.
- **Detecção de bloqueio:** compara `finalUrl`, status e título com o esperado. Captcha, redirecionamento para login ou página de erro marcam a linha como `bloqueada`.
- **JSON bruto:** antes de compactar, **remove as auditorias com imagem** (`final-screenshot`, `screenshot-thumbnails`, `full-page-screenshot`), o que tira possíveis nomes de pessoas e reduz o tamanho.
  - O JSON é publicado como **artifact do GitHub Actions**, sem commit no git.
  - No fim da coleta, B junta todos os JSONs num `.zip` anexado a uma *release*.
  - Só os CSVs entram no repositório.
- **Segredo:** a chave fica no secret `PSI_API_KEY` do GitHub e nunca no código.
- **`.github/workflows/collect.yml`:** quatro crons em UTC (`7 23 * * *`, `7 1 * * *`, `7 6 * * *`, `7 8 * * *`) e `workflow_dispatch`. Faz commit dos CSVs no fim. O horário real de cada execução é gravado. Disparos manuais gravam em `data/raw/testes/` e cada linha registra o `gatilho` (`schedule` ou `workflow_dispatch`); só `schedule` entra na análise.
  - **Revisão de 19/11/2026:** o `schedule` do GitHub atrasou e descartou disparos na 1ª noite (`docs/anomalias.md`). Os mesmos 4 horários passaram a ser disparados por um agendador externo (cron-job.org) via `workflow_dispatch` com `agendado=true`, gravado como `gatilho=agendador` (`docs/agendador.md`). Entram na análise `agendador` e `schedule`.
- **`scripts/validate.py`:** confere cobertura (38 linhas por execução), faltas, linhas bloqueadas, mudanças de `lighthouseVersion` e anomalias. Gera `data/processed/dataset.csv` e `docs/anomalias.md`.
- **Política de substituição de URL:** se um produto esgotar ou sair do ar, o `collect.py` passa a usar a URL reserva pré-registrada **no mesmo slot**. A troca é marcada como anomalia, e a análise usa o slot como unidade. URLs de categoria e busca não são trocadas.
- **Ética:**
  - registrar (com data) o `robots.txt` de **cada host** usado (www., lista., produto.) e os termos de uso do ML e da PSI API;
  - tipos de página proibidos pelo `robots.txt` são excluídos do estudo;
  - o volume fica em 38 chamadas a cada ~2 h, muito abaixo de 1 req/s;
  - nenhum login e nenhum dado pessoal.

### 5.10 Ameaças à validade

| Tipo | Ameaça | Mitigação |
|---|---|---|
| Conclusão | Poucas unidades independentes (6 URLs por tipo) dão baixo poder em H2/H4 | Simulação do efeito mínimo detectável (Lab04); relatar tamanho de efeito e IC, não só p-valor |
| Conclusão | Pseudorreplicação (repetições da mesma URL tratadas como amostras) | Agregar por URL (H2/H4) e efeitos aleatórios de URL e dia (H1/H3) |
| Conclusão | Comparações múltiplas | Holm sobre os testes primários; métricas primárias definidas a priori |
| Interna | **Black Friday (27/11/2026):** a coleta (18–25/11) cai na semana de "esquenta", com banners, campanhas e tráfego atípicos | Declarar; registrar o calendário promocional do ML durante a coleta; **não** juntar 26–28/11 ao conjunto principal (se coletados, viram análise exploratória separada) |
| Interna | O ML muda o site durante a coleta (deploys, produto esgotado) | Registro de anomalias, URLs reservas e efeito aleatório de dia |
| Interna | Mudança de versão do Lighthouse/PSI durante a coleta | Gravar `lighthouseVersion`; analisar com e sem os dias afetados |
| Interna | Atraso ou perda de execuções do cron do Actions; efeito de ordem das URLs | Crons em :07; horário real gravado; ordem sorteada; validação de cobertura |
| Construto | "Perfil móvel" é throttling simulado, não um celular real; o LCP do PSI é simulado (Lantern) e atenua a variação por horário | Chamar o fator de *perfil*; usar o TTFB (observado) como métrica de H3; triangular com o CrUX (H5) |
| Construto | A nota automatizada de acessibilidade cobre só uma parte do WCAG | Analisar as auditorias reprovadas por tipo; declarar que a nota ≠ conformidade WCAG |
| Construto | Armadilhas de medição: Goodhart (a nota Lighthouse vira meta e é "jogada"), **Campbell** (decisões guiadas pela nota distorcem o produto), McNamara (o que não é medido, como leitores de tela reais, é ignorado) | Discutir no documento; usar métricas brutas (ms, contagens) como primárias, não as notas |
| Externa | O PSI executa em datacenters do Google escolhidos pela origem da requisição. Um runner do GitHub tende a ficar nos EUA, o que infla o TTFB para um site brasileiro | No piloto, comparar algumas execuções manuais no PSI web feitas do Brasil; registrar; não generalizar valores absolutos de TTFB, só diferenças relativas pico × madrugada |
| Externa | 19 URLs não representam o catálogo; uma semana atípica não representa o ano | Critério explícito de seleção (as mais destacadas/vendidas); contraste com o CrUX (28 dias); limitar as conclusões a páginas populares nesse período |

### 5.11 Impacto e o que não é possível afirmar

**Estimativas** (todas com link e data de acesso):
- **Espera:** diferença medida (ex.: segundos a mais no perfil móvel ou no pico) × audiência mensal do ML **no Brasil** × parcela de acessos móveis = horas de espera por mês. Se só houver dado de audiência latino-americana, recortar para o Brasil com a proporção que o próprio relatório de RI informar, ou declarar a limitação.
- **Acessibilidade:** prevalência de pessoas com deficiência no Brasil (IBGE, PNAD Contínua) × audiência = ordem de grandeza de pessoas potencialmente expostas às barreiras encontradas, por tipo de barreira (ex.: contraste afeta baixa visão).
- **Referência (opcional, sem teste):** algumas medições pontuais de concorrentes, só para contextualizar.

**O que não é possível afirmar:**
- a experiência real em redes móveis brasileiras (a medição é sintética, de datacenter);
- nada sobre páginas logadas, checkout ou o app nativo;
- causalidade de deploys ou de decisões de engenharia do ML;
- generalização para outras semanas, em especial fora do período da Black Friday;
- que a nota automática de acessibilidade equivale à conformidade com o WCAG;
- valores absolutos de TTFB como os vistos por usuários no Brasil.

### 5.12 Reaproveitamento dos laboratórios anteriores

| Lab | O que é reaproveitado | O que é novo |
|---|---|---|
| Lab01 | Coleta automatizada por API; Kanban no GitHub Projects | Agendamento no Actions; objeto em operação (site), não repositório |
| Lab02 | Desenho com tratamentos e fatores | Fatorial 3×2×2 com medidas repetidas; objetos (URLs) em vez de participantes |
| Lab03 | Conceitos DORA. Como não há acesso aos deploys do ML, DORA não se aplica diretamente; a ideia de medir a operação é adaptada como **SLI/SLO** (Core Web Vitals) | SLO de LCP ≤ 2,5 s; taxa de execuções com bloqueio ou falha da coleta |
| Lab04 | Escolha do teste, simulação de poder e erro tipo I, dashboard | Simulação aplicada ao efeito mínimo detectável; o dashboard pode ser o formato do documento final |

## 6. Estrutura do repositório

```
config/urls.csv            # 19 URLs + reservas, com tipo, slot e critério de seleção
scripts/collect.py         # coleta via PSI API (ordem sorteada, retry, detecção de bloqueio)
scripts/validate.py        # cobertura, anomalias, dataset consolidado
.github/workflows/collect.yml
data/raw/                  # CSVs por janela BRT (versionados)
data/processed/            # dataset consolidado e validado
analysis/                  # notebooks/scripts de análise, gráficos e simulação de poder
docs/                      # proposta, evidências, ética, anomalias, relatórios, documento final
```

O JSON bruto fica em artifacts do Actions e numa release, fora do git.

## 7. Divisão em ondas (A → B → C a cada sprint)

Cada onda termina com um **artefato de passagem** que o próximo integrante usa sem precisar de quem saiu. Papéis fixos: **A = Planejamento e Método**, **B = Instrumentação e Operação**, **C = Análise e Impacto**. Todas as tarefas ficam como cartões no **GitHub Projects**.

A coleta (GitHub Actions) roda sozinha em segundo plano a partir da onda 2 da S01, então ela continua mesmo durante as ondas de A e C. Enquanto ela roda (18/11–25/11), o dono da onda corrente faz uma checagem diária de 5 minutos: C de 19 a 21/11, A de 22 a 23/11 e B de 24 a 25/11. Qualquer falha é comunicada a B no mesmo dia.

**Cronograma da disciplina:** S01 13/11–19/11 · S02 20/11–26/11 (20/11 é feriado) · S03 27/11–03/12 · **apresentação do grupo em 04/12**.

**Entrega conjunta S01 + S02:** por causa do feriado e da extensão do trabalho, o grupo junta as duas entregas numa só, em **26/11**. A sprint conjunta (16/11–26/11) tem dois ciclos A → B → C: o ciclo 1 prepara e liga a coleta, e o ciclo 2 valida e analisa. A coleta não muda de data, porque o fim dela é limitado pela Black Friday.

**Datas críticas**
- Workflow **ligado até 18/11 às 20h07**.
- **Piloto incorporado:** 18/11 20h07 → 19/11 05h07. Essas execuções fazem parte do conjunto principal, a menos que o piloto revele problemas, caso em que as execuções afetadas são descartadas e registradas.
- Fim da coleta principal: **25/11 às 05h07**.
- A coleta é **desligada em 25/11 após a última execução**, ou segue até 28/11 só para a análise exploratória da Black Friday, separada. Decisão de A na S02.

### Sprint conjunta S01 + S02 — Proposta, coleta e análise (16/11–26/11, entrega única em 26/11)

**Ciclo 1 — Preparação e início da coleta (16/11–21/11)**

| Onda | Quem | Tarefas | Passa adiante |
|---|---|---|---|
| 1 (16–17/11) | A | Criar o GitHub Projects. Tabela de evidências dos 3 critérios (§5.1). Pergunta, GQM, entidades/atributos/escalas, 7 categorias v1 e hipóteses (revisar §5.3–§5.7). Fonte para o horário de pico. Escolher as 19 URLs + reservas pelos critérios do §5.6. Registrar o `robots.txt` de cada host e os termos de uso | `docs/proposta.md`, `docs/evidencias.md`, `docs/etica.md`, `config/urls.csv` |
| 2 (17–18/11) | B | Chave da PSI + secret. `collect.py` (ordem sorteada, retry, detecção de bloqueio, remoção de imagens, artifact). Workflow **ligado até 18/11 20h07**. Disparos manuais de teste. Comparar algumas execuções no PSI web feitas do Brasil | Workflow ativo + `docs/dados.md` (dicionário de dados) |
| 3 (19–21/11, inclui o feriado) | C | Descritiva do piloto incorporado (18/11 20h07 → 19/11 05h07). Checagem de bloqueios e variância. Simulação do efeito mínimo detectável (Lab04). Esqueleto do script de análise (modelo misto, Kruskal-Wallis, H5) rodando sobre o piloto. Seção "plano de coleta e análise + resultados do piloto" do documento de entrega | `analysis/piloto` + script de análise pronto para o dataset completo |

**Ciclo 2 — Validação e análise (22/11–26/11)**

| Onda | Quem | Tarefas | Passa adiante |
|---|---|---|---|
| 1 (22–23/11) | A | Revisar o plano à luz do piloto (só o que não quebra o desenho: critérios de validação e regras de descarte). Ameaças à validade v1 (§5.10). Registrar o calendário promocional da Black Friday. Decidir se a coleta segue até 28/11 (exploratória). Consolidar as seções de proposta (evidências, GQM, 7 categorias v1) no documento de entrega | Plano revisado + `docs/ameacas.md` + seções de proposta |
| 2 (24–25/11, manhã) | B | Acompanhar a coleta. `validate.py`. **Consolidar o dataset na manhã de 25/11**, após a execução das 05h07. Registro de anomalias. Release com os JSONs brutos | `data/processed/dataset.csv` + `docs/anomalias.md` |
| 3 (25/11 tarde – 26/11) | C | Rodar o script de análise (já pronto no ciclo 1) sobre o dataset completo: descritiva, modelo misto (H1/H3, com interações), Kruskal-Wallis por URL (H2/H4), concordância (H5), Holm, tamanhos de efeito e gráficos. **Montar e entregar a entrega única S01 + S02** | `analysis/` + entrega S01 + S02 |

### Sprint S03 — Impacto, conclusões e entrega final (27/11–03/12)

A apresentação é em 04/12, então a sprint Final está incorporada aqui. Cada onda escreve sua parte **já na versão final** do documento.

| Onda | Quem | Tarefas | Passa adiante |
|---|---|---|---|
| 1 (27–28/11) | A | 7 categorias revisadas e justificadas. Ameaças finalizadas. Limitações e conclusão "O que o estudo mostrou?". Seções finais de método, categorias e validade | Seções de método e conclusões |
| 2 (29–30/11) | B | Fontes de impacto (audiência BR, % móvel, IBGE/PNAD) em `docs/impacto-fontes.md`. Seção de resultados. Tabela de reaproveitamento dos Labs (§5.12). README de reprodutibilidade. Exploração da Black Friday, se houver | Seções de resultados e reaproveitamento + README |
| 3 (01–03/12) | C | Cálculo do impacto (espera e acessibilidade). Conclusão "O que isso significa para quem usa?". Lista de "o que não é possível afirmar". Fechar o documento final. Apresentação de 10 min | Documento final + apresentação |
| 03/12 | Todos | Ensaio. Todos devem conseguir explicar qualquer parte | — |

## 8. Decisões a validar pelo grupo

- 6 URLs por tipo (categoria, busca, produto) + home como referência, com os critérios de seleção do §5.6.
- 4 execuções por dia (20h07, 22h07, 03h07, 05h07 BRT) durante 7 dias.
- Métricas primárias LCP, TTFB e nº de auditorias reprovadas; modelo misto + Kruskal-Wallis por URL + Holm.
- JSON bruto fora do git (artifacts + release).
- Python para scripts e análise.
- Formato final: relatório em Markdown/PDF no repositório + slides. O PDF valoriza criatividade, então um dashboard (reaproveitando o Lab04) é uma alternativa.

## 9. Em aberto para o grupo

- Quem é A, B e C. Por enquanto o documento usa só os papéis.
