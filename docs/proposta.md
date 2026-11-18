# Proposta metodológica — Desempenho e acessibilidade do site do Mercado Livre

Lab05 — Experimento em Software Real · Sprint conjunta S01+S02 · Ciclo 1 · Onda 1 (integrante A) · Issue #4

Versão: v1, escrita em 17/11/2026, **antes do início da coleta** (18/11/2026, 20h07 BRT).
Base: design do estudo (`docs/superpowers/specs/2026-11-16-mercadolivre-desempenho-acessibilidade-design.md`, §5.2–§5.7).

> **Decisões fixadas antes da coleta (não mudam depois de ver os dados)**
>
> 1. **Métricas primárias:** LCP, TTFB e nº de auditorias de acessibilidade reprovadas. Todas as outras métricas são **descritivas** e não entram em teste de hipótese.
> 2. **Perfil de H2 e H4:** o teste primário usa o perfil **móvel** do Lighthouse. O desktop é relatado só como análise de sensibilidade.
> 3. **Testes bilaterais** em todas as hipóteses (H1–H5), inclusive em H1 e H3, cuja hipótese de pesquisa tem uma direção esperada.
> 4. **Correção de Holm** sobre os 5 testes primários, com α = 0,05. Os post-hoc também são corrigidos.
> 5. **Unidade de análise:** a URL em H2/H4 (n = 6 por tipo); a medição com efeitos aleatórios de URL e dia em H1/H3; o par por URL em H5.
> 6. **Janelas de horário:** pico = execuções das 20h07 e 22h07 BRT; madrugada = execuções das 03h07 e 05h07 BRT (justificativa em [Horário de pico](#horário-de-pico)).

## Pergunta de pesquisa

> O desempenho e a acessibilidade do site do Mercado Livre variam conforme o tipo de página, o perfil de dispositivo e o horário de acesso? E a medição sintética reflete a experiência dos usuários reais?

A pergunta tem duas partes:
- a primeira trata do efeito de três fatores controlados pelo grupo (tipo de página, perfil e horário), respondida por H1–H4;
- a segunda trata da validade da própria medição (sintética × campo), respondida por H5.

## GQM (template de Basili)

**Objetivo (Goal):**

| Elemento do template | Preenchimento |
|---|---|
| Analisar | o site do Mercado Livre (mercadolivre.com.br) |
| com o propósito de | caracterizar e comparar |
| com respeito a | desempenho de carregamento e acessibilidade |
| do ponto de vista | do usuário final |
| no contexto de | páginas públicas (categoria, busca, produto e home) medidas com perfis móvel e desktop em horários de pico e de baixa demanda (madrugada) |

**Perguntas (Questions) e métricas (Metrics):**

| Pergunta | Métricas | Papel |
|---|---|---|
| Q1. O perfil de dispositivo afeta o carregamento? | **LCP** (primária); FCP, Speed Index, TBT (descritivas) | H1 |
| Q2. O tipo de página afeta desempenho e peso? | **LCP** (primária); peso total (bytes) e nº de requisições (descritivas) | H2 (LCP). Bytes e requisições são só descritivas |
| Q3. O horário de pico piora a resposta do servidor? | **TTFB** (auditoria `server-response-time`, primária); LCP (descritiva nesta pergunta) | H3 |
| Q4. Quantas barreiras de acessibilidade existem e onde? | **Nº de auditorias de acessibilidade reprovadas** (primária), também detalhado por tipo de auditoria (contraste, rótulos, `alt` etc.); nota de acessibilidade (descritiva) | H4 |
| Q5. A medição sintética reflete a experiência dos usuários reais? | LCP sintético (mediana por URL, perfil móvel) × p75 de LCP do CrUX; categoria CrUX (FAST/AVERAGE/SLOW). O INP do CrUX é só descritivo, porque o Lighthouse não mede INP (o TBT é apenas um proxy) | H5 |

As **métricas primárias** (LCP, TTFB e nº de auditorias reprovadas) foram **fixadas antes da coleta**. As notas de 0 a 100 do Lighthouse não são primárias, de propósito: ver [Armadilhas de medição](#armadilhas-de-medição).

## Entidades, atributos e escalas

| Métrica | Entidade | Atributo | Direta / derivada | Escala | Estatísticas permitidas |
|---|---|---|---|---|---|
| TTFB | Recurso (infraestrutura do ML) | Externo: tempo de resposta do servidor | Direta (observada no carregamento) | Razão | Todas (média geométrica, razões, testes paramétricos ou não paramétricos) |
| LCP, FCP, Speed Index, TBT | Produto (página web) | Externo: tempo percebido | **Derivada**: o PSI simula o throttling (Lantern) a partir de um carregamento | Razão | Todas, analisadas em escala log |
| Peso total, nº de requisições | Produto (página web) | Interno: tamanho | Direta | Razão | Todas |
| Nº de auditorias de acessibilidade reprovadas | Produto (página web) | Externo: acessibilidade (barreiras detectáveis automaticamente) | Direta (contagem) | Razão (discreta) | Mediana, contagens, testes não paramétricos |
| Nota de desempenho e de acessibilidade (0–100) | Produto | Externo, agregado | **Derivada**: soma ponderada de curvas log-normais | Tratada como **ordinal** | Mediana, percentis, testes de postos. **Não usar médias** |
| Categoria CrUX (FAST/AVERAGE/SLOW) | Produto em uso | Externo: experiência do usuário | Derivada (p75 de campo) | Ordinal | Moda, proporções, kappa |
| p75 de LCP do CrUX | Produto em uso | Externo | Derivada (agregação de 28 dias) | Razão | Comparação pareada |

Consequências da escala para a análise:
- os tempos (razão) são analisados em log e os efeitos são relatados como **razões** (ex.: "1,15× mais lento");
- a contagem de auditorias reprovadas é discreta e quase constante entre repetições, por isso usa testes de postos sobre o valor agregado por URL;
- as notas e a categoria CrUX são ordinais e só aceitam mediana, percentis, proporções e testes de postos ou de concordância.

### Mapeamento na ISO/IEC 25010

**Versão usada: ISO/IEC 25010:2023** (2ª edição, que substitui a de 2011). Fonte: página oficial da norma na ISO, <https://www.iso.org/standard/78176.html>, e prévia oficial do prefácio em <https://webstore.ansi.org/preview-pages/ISO/preview_ISO+IEC+25010-2023.pdf> (acesso em 17/11/2026).

| Característica (2023) | Subcaracterística | Métricas do estudo |
|---|---|---|
| Eficiência de desempenho (*performance efficiency*) | Comportamento temporal (*time behaviour*) | TTFB, LCP, FCP, Speed Index, TBT |
| Eficiência de desempenho | Utilização de recursos (*resource utilization*) | Peso total (bytes), nº de requisições |
| Capacidade de interação (*interaction capability*, que substitui "usabilidade" da versão 2011) | Inclusividade (*inclusivity*) e assistência ao usuário (*user assistance*) | Nº de auditorias de acessibilidade reprovadas, por tipo; nota de acessibilidade |

Na versão 2011, a acessibilidade era subcaracterística de *usabilidade*. A versão 2023 divide a acessibilidade em *inclusividade* e *assistência ao usuário*, dentro de *capacidade de interação*. A correspondência é registrada aqui para quem conhece só a versão 2011.

### SLI/SLO de referência

- **SLO:** LCP ≤ 2,5 s no p75, que é o limiar "bom" dos Core Web Vitals. Fonte: web.dev, "Largest Contentful Paint (LCP)", <https://web.dev/articles/lcp> (acesso em 17/11/2026).
- **SLI:** a fração das medições de cada combinação tipo × perfil × horário que cumpre LCP ≤ 2,5 s.
- O uso é **descritivo** e não entra em teste de hipótese. Ele adapta ao site do ML a ideia de medir a operação (Lab03), já que não há acesso aos deploys para calcular métricas DORA.

## Classificação nas 7 categorias de pesquisa (v1)

> **Pendência para o integrante A:** conferir esta tabela com o material da **Aula 8**. Ela foi montada a partir do §5.5 do design, sem acesso ao material da aula. Confirmar os nomes exatos das categorias e das opções de cada uma, e ajustar a classificação se a aula usar outra nomenclatura.

| Categoria | Classificação | Justificativa |
|---|---|---|
| Natureza | Aplicada | Gera conhecimento sobre um software em produção, com impacto direto para os usuários e para a empresa. Não busca teoria geral |
| Objetivos | Descritiva e explicativa | Descritiva porque caracteriza desempenho e acessibilidade (Q1–Q4). Explicativa porque testa se tipo de página, perfil e horário explicam a variação (H1–H4) |
| Abordagem | Quantitativa | Todas as métricas são numéricas e a análise usa estatística descritiva e testes de hipótese |
| Procedimentos | Quase-experimento de campo, com análise de dados de operação (CrUX) | Os fatores e níveis são escolhidos pelo grupo, mas os objetos (URLs) são escolhidos por critério, sem randomização, e o sistema não é controlado. O CrUX traz dados de operação de usuários reais |
| Tempo | Longitudinal curto | Medidas repetidas 4 vezes por dia durante 7 dias (18/11 a 25/11/2026) |
| Controle | Parcial | O grupo controla as URLs, os horários, o perfil e a ordem das chamadas (sorteada). Não controla o ML (deploys, promoções) nem a infraestrutura do PSI |
| Nível de evidência | Moderado | Ganha força com o desenho fatorial, as repetições e a triangulação com o CrUX. Perde com a falta de randomização, o período atípico (semana anterior à Black Friday) e a medição sintética |

## Objetos, fatores e variáveis

**Objetos.** A unidade experimental para o fator tipo de página é a **URL**: 6 URLs por tipo, escolhidas por critério explícito e registradas em `config/urls.csv` (item #A-4 do arquivo de issues).

| Tipo | Critério de seleção (6 URLs) |
|---|---|
| Categoria | As 6 categorias de maior destaque no menu principal do ML |
| Busca | 1 termo genérico por categoria escolhida, sem filtros |
| Produto | O 1º item de "Mais vendidos" de cada categoria, mais 1 URL reserva por produto, registrada antes da coleta |
| Home (referência) | Apenas `https://www.mercadolivre.com.br/`. Não entra nos testes de tipo de página |

**Fatores e níveis** (fatorial 3 × 2 × 2, mais a home como referência descritiva):

| Fator | Níveis |
|---|---|
| Tipo de página | categoria, busca, produto |
| Perfil de dispositivo | perfil **móvel** do Lighthouse (4G lento simulado + CPU 4× mais lenta) × perfil **desktop** (parâmetro `strategy` da PSI) |
| Horário | pico (20h07 e 22h07 BRT) × madrugada (03h07 e 05h07 BRT) |

**Variáveis:**
- **Dependentes:** LCP, TTFB e nº de auditorias de acessibilidade reprovadas (primárias); FCP, Speed Index, TBT, bytes, requisições e notas (descritivas).
- **Independentes:** tipo de página, perfil e horário.
- **Controladas e registradas em cada linha:** `lighthouseVersion`, configuração de throttling, `finalUrl`, status HTTP, título da página, horário real da execução, posição da URL na ordem sorteada e dia da semana.

**Volume:** 19 URLs × 2 perfis = 38 chamadas por execução, sequenciais, com ≥ 2 s entre elas (abaixo do limite ético de 1 requisição por segundo). São 4 execuções por dia durante 7 dias, o que dá 1.064 medições. Cada combinação tipo × perfil × horário tem 84 medições, mas **n = 6 unidades independentes** (as URLs) para o fator tipo.

## Horário de pico

**Decisão:** o nível "pico" do fator horário usa execuções às **20h07 e 22h07 BRT**, e o nível de baixa demanda usa **03h07 e 05h07 BRT**. Na classificação das execuções, a janela de pico vai de 18h a 23h59 e a de madrugada de 00h a 07h59 (BRT), calculadas pelo horário de início de cada execução.

**Fonte principal: tráfego agregado do IX.br (NIC.br).**
- Página: "Tráfego total (Todos IX.br)", <https://ix.br/agregado/>, com o gráfico diário em <https://old.ix.br/images/pix/agregado_bps1-daily1.png> e o semanal em <https://old.ix.br/images/pix/agregado_bps1-weekly1.png>. Acesso em **17/11/2026, por volta das 21h58** (página com "Última Atualização: 2026-11-17 21:00").
- O IX.br é o conjunto de pontos de troca de tráfego (PTTs) mantido pelo NIC.br, por onde passa o tráfego entre provedores de acesso e de conteúdo no Brasil.
- **O que o gráfico diário mostrou na data de acesso** (leitura visual, valores aproximados, exceto os números impressos no gráfico):
  - o **pico diário** fica entre 20h e 22h, com o máximo por volta das 21h. O máximo das últimas 24 h impresso no gráfico é **53,21 Tbps** no total, e o valor atual (por volta das 21h) é **50,93 Tbps**;
  - o **vale** fica por volta das 04h, em cerca de 10–11 Tbps (leitura visual), ou seja, perto de 1/5 do pico;
  - a média impressa das últimas 24 h é **32,72 Tbps**.
- **O gráfico semanal** (11/11 a 17/11/2026) mostra o mesmo padrão em todos os dias: um pico por noite, com máximo da semana de **53,10 Tbps** e média de **31,37 Tbps** (valores impressos), e um vale de madrugada em todos os dias.
- **Conclusão para o estudo:** 20h07 e 22h07 caem na faixa de maior tráfego do dia, e 03h07 e 05h07 caem perto do vale. Isso sustenta a escolha dos dois níveis.

**Fonte complementar: hábito de compra online.**
- A pesquisa *E-commerce Trends 2026* (Octadesk com Opinion Box, mais de 2.000 respondentes, margem de erro de 2,2 p.p.) informa que **56%** dos consumidores preferem comprar à noite ou de madrugada. Fontes: Meio & Mensagem, "IA já impacta consumo e maioria compra à noite", 08/08/2025, <https://www.meioemensagem.com.br/marketing/ia-ja-impacta-consumo-e-maioria-compra-a-noite>; Forbes Brasil, 30/07/2025, <https://forbes.com.br/forbes-money/2025/07/mais-da-metade-dos-brasileiros-compra-online-durante-a-noite-ou-de-madrugada/> (acesso em 17/11/2026).
- Essa pesquisa **não** informa a hora exata, só o período ("noite ou madrugada"). Ela reforça que a noite é um período de uso relevante para e-commerce, mas não basta sozinha para fixar 20h–22h.

**Limitações da justificativa:**
- O tráfego do IX.br é **troca entre redes** (provedores de acesso e de conteúdo), não o tráfego dos usuários finais nem o do Mercado Livre. Ele é usado como indicador do uso residencial de internet no Brasil, e não do uso do ML.
- **Não encontramos** dado público do próprio Mercado Livre sobre o horário de maior acesso ao site. Também não encontramos um dado de compras online por hora cheia (20h, 21h, 22h). Buscas feitas em 17/11/2026: notícias e apresentações do IX.br/NIC.br (forum.ix.br, datacenterdynamics.com, convergenciadigital.com.br) e pesquisas de e-commerce (Octadesk, Visa, Nuvemshop, Tray). A notícia da DatacenterDynamics sobre o recorde de 10 Tbps de 2020 não pôde ser lida (HTTP 403).
- Os gráficos do IX.br são **dinâmicos** (janela móvel de 24 h e de 7 dias). Os números acima são os da data de acesso.
- O eixo do gráfico não informa o fuso. Ele foi interpretado como horário de Brasília porque a hora da "Última Atualização" (21:00) bate com o horário local (BRT) do acesso e com a borda direita do gráfico.

> **Pendência para o integrante A:** salvar uma cópia dos dois gráficos do IX.br (ex.: `docs/img/ixbr-diario-2026-11-17.png` e `docs/img/ixbr-semanal-2026-11-17.png`), já que as imagens publicadas mudam a cada atualização. Esta tarefa só podia criar `docs/proposta.md`, por isso as imagens não foram versionadas.

## Hipóteses

Todas as hipóteses abaixo foram **fixadas antes da coleta**. Todos os testes são **bilaterais** e passam pela **correção de Holm** sobre os 5 testes primários (α = 0,05).

| | Hipótese de pesquisa (H1) | H0 | Métrica (primária) | Unidade de análise | Perfil usado | Teste (a priori) |
|---|---|---|---|---|---|---|
| H1 | O LCP no perfil móvel do Lighthouse é diferente do LCP no perfil desktop (direção esperada: maior no móvel) | Não há diferença de LCP entre os perfis | LCP | Medição, com efeitos aleatórios de URL e dia | Móvel × desktop (é o próprio fator) | Modelo linear misto em log, efeito como razão com IC 95% |
| H2 | O LCP difere entre categoria, busca e produto | Não há diferença de LCP entre os tipos | LCP | **URL** (mediana por URL, n = 6 por tipo) | **Móvel** (desktop como sensibilidade) | Kruskal-Wallis, ε², post-hoc de Dunn |
| H3 | O TTFB no pico é diferente do TTFB na madrugada (direção esperada: maior no pico) | Não há diferença de TTFB entre pico e madrugada | TTFB | Medição, com efeitos aleatórios de URL e dia | Ambos (o perfil entra como fator no modelo) | Modelo linear misto em log, efeito como razão com IC 95% |
| H4 | O nº de auditorias de acessibilidade reprovadas difere entre os tipos | Não há diferença no nº de reprovadas entre os tipos | Nº de auditorias reprovadas | **URL** (valor modal por URL, n = 6 por tipo) | **Móvel** (desktop como sensibilidade) | Kruskal-Wallis, ε², post-hoc de Dunn |
| H5 | O LCP sintético difere do p75 de LCP do CrUX (análise de concordância) | Não há diferença sistemática entre o LCP sintético e o p75 do CrUX | LCP | Par por URL (só as URLs com dados no CrUX) | Móvel | Wilcoxon pareado, Spearman, Bland-Altman e kappa de Cohen nas categorias |

Notas:
- **Bilateralidade:** H1 e H3 têm uma direção esperada, mas o teste é bilateral para não descartar um resultado no sentido oposto (ex.: madrugada mais lenta por janelas de manutenção).
- **H1 é parcialmente verdadeira por construção**, porque o perfil móvel aplica throttling. O interesse está no **tamanho** da diferença e na interação com tipo e horário, não só no p-valor. Isso é tratado como ameaça de construto.
- **H2 e H4 usam a URL como unidade** porque as repetições da mesma URL não são amostras independentes (a acessibilidade quase não muda entre repetições). Usar as 84 medições como amostras seria pseudorreplicação.
- **H5:** as URLs sem dados no CrUX são listadas, e o valor da origem é usado só como referência.
- A home fica fora de todos os testes e entra só na descritiva.

## Armadilhas de medição

| Armadilha | Como aparece neste estudo | O que o estudo faz |
|---|---|---|
| **Lei de Goodhart** ("quando uma medida vira meta, deixa de ser uma boa medida") | A nota do Lighthouse (0–100) é uma meta comum em equipes de front-end. Ela pode ser melhorada com otimizações voltadas ao teste (ex.: adiar scripts só durante a janela medida ou otimizar só o elemento LCP) sem melhorar a experiência como um todo | As notas **não** são métricas primárias. As primárias são grandezas brutas (ms e contagens) e são trianguladas com o CrUX (usuários reais) em H5 |
| **Lei de Campbell** (quanto mais um indicador quantitativo é usado para decisões, mais ele fica sujeito a pressões que o corrompem e distorcem o processo que ele deveria monitorar) | Se a nota de acessibilidade guia decisões de produto, a equipe pode corrigir só o que a ferramenta automática detecta (ex.: preencher `alt` com texto genérico) e deixar barreiras reais que a ferramenta não vê. Também vale para o grupo: escolher URLs "boas" para o resultado distorceria o estudo | Contagem das auditorias reprovadas **por tipo**, e não só a nota. Critério de seleção das URLs fixado e registrado antes da coleta, com reservas pré-registradas |
| **Falácia de McNamara** (considerar só o que é fácil de medir e ignorar o resto) | As auditorias automáticas cobrem só uma parte do WCAG. O que não é medido (uso com leitor de tela real, navegação por teclado em fluxos completos, compreensão do conteúdo, celulares reais em redes brasileiras) poderia ser tratado como inexistente | Declarar no documento que **nota de acessibilidade ≠ conformidade com o WCAG** e que "perfil móvel" é throttling simulado, não um celular real. Listar isso em "o que não é possível afirmar" |

## Regras de validação

_A preencher na issue #17 (#A-6, ciclo 2): regras de descarte e de sinalização no formato condição → ação._

## Extensão da coleta

_A preencher na issue #19 (#A-8, ciclo 2): decisão de desligar a coleta após 25/11 às 05h07 ou de seguir até 28/11 só para análise exploratória._
