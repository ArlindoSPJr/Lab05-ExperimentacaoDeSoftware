# Lab05 — Desempenho e acessibilidade do site do Mercado Livre (design)

Data: 2026-11-16 · Base: `Lab05Medicao.pdf`

## 1. Intenção

Medir, de fora e como um usuário comum, o **desempenho** e a **acessibilidade** do site do Mercado Livre (mercadolivre.com.br) e responder às duas perguntas do Lab05:

- **O que o estudo mostrou?** Como o tempo de carregamento e as violações de acessibilidade variam com o tipo de página, o dispositivo e o horário.
- **O que isso significa para quem usa?** Quanto tempo os usuários (principalmente no celular) passam esperando, e quantos são afetados por barreiras de acessibilidade, usando números públicos de audiência.

## 2. Objetivos, não objetivos e antiobjetivos

**Objetivos**
- Ter um estudo quase-experimental com 3 fatores controlados, coleta automatizada e dados versionados.
- Combinar dois caminhos do PDF: *medir o serviço de fora* (medição sintética do Lighthouse) e *avaliar a qualidade do produto* (ISO/IEC 25010: eficiência de desempenho e acessibilidade/WCAG), mais o contraste com **dados de campo** de usuários reais do Chrome (CrUX), o que acrescenta o caminho *analisar dados de operação*.
- Dividir o trabalho em **ondas sequenciais**: em cada sprint, A faz a onda 1, entrega para B (onda 2), que entrega para C (onda 3).

**Não objetivos**
- Comparar o ML com concorrentes por teste de hipótese. No máximo, concorrentes podem aparecer como referência na seção de impacto.
- Medir o app nativo do ML, o checkout ou as páginas logadas.

**Antiobjetivos** (o trabalho fracassa se acontecer, mesmo que "funcione")
- Fazer qualquer coisa parecida com teste de carga, passar de 1 requisição por segundo ou desrespeitar o `robots.txt`.
- Coletar dados pessoais ou usar a conta de alguém.
- Afirmar algo sobre todos os usuários do ML com base em medições sintéticas, sem discutir a validade externa.

## 3. Restrições (do PDF)

- O objeto de estudo é o software em operação. Nada de mineração de repositório.
- O grupo precisa provar com fontes datadas que o ML é real, está em operação e tem alto impacto. **Os números ainda precisam ser levantados com fonte; nenhum foi assumido neste documento.**
- Nenhum outro grupo pode estudar o mesmo software. **Confirmar com o professor na S01.**
- Entregas: S01, S02, S03 e Final, com 5 pontos cada. A apresentação final tem 10 minutos.

## 4. Abordagens consideradas

| Decisão | Opções avaliadas | Escolha do grupo | Motivo |
|---|---|---|---|
| Tema | (1) Páginas de status de SaaS; (2) Desempenho e acessibilidade de e-commerce; (3) Node.js 20×22×24 local | **(2), com o Mercado Livre** | Preferência do grupo |
| Comparação | (A) Só o ML, variando fatores; (B) ML × concorrentes | **(A)** | Mantém um único software, controla os fatores e reduz o risco de colisão com outro grupo |
| Coleta | (1) PageSpeed Insights API + GitHub Actions; (2) Lighthouse local; (3) Lighthouse no GitHub Actions | **(1)** | Automatizada, versiona os dados sozinha e traz o CrUX (usuários reais) como segundo caminho |

## 5. Desenho do estudo

### 5.1 Pergunta de pesquisa

> O desempenho e a acessibilidade do site do Mercado Livre variam conforme o tipo de página, o dispositivo e o horário de acesso? E a medição sintética reflete a experiência dos usuários reais?

### 5.2 GQM (template de Basili)

**Objetivo:** analisar *o site do Mercado Livre*, com o propósito de *caracterizar e comparar*, com respeito a *desempenho de carregamento e acessibilidade*, do ponto de vista *do usuário final*, no contexto de *páginas públicas acessadas por celular e desktop em horários de pico e de baixa demanda*.

| Pergunta | Métricas |
|---|---|
| Q1. O dispositivo afeta o tempo de carregamento? | LCP, FCP, Speed Index, TBT, nota de desempenho |
| Q2. O tipo de página afeta desempenho e peso? | As de Q1 + peso total (bytes) e número de requisições |
| Q3. O horário de pico piora o desempenho? | LCP, TTFB (resposta do servidor), nota de desempenho |
| Q4. Quantas barreiras de acessibilidade existem e onde? | Nota de acessibilidade, nº de auditorias de acessibilidade reprovadas por tipo (contraste, rótulos, alt etc.) |
| Q5. A medição sintética reflete a experiência dos usuários reais? | LCP sintético (Lighthouse) × p75 de LCP/INP/CLS dos dados de campo do CrUX (por URL quando houver, senão por origem), categoria CrUX (FAST/AVERAGE/SLOW). Obs.: o CrUX é uma média móvel de 28 dias por URL e dispositivo, então só varia por dispositivo (não por horário) e pode faltar em URLs com pouco tráfego. Serve como validação complementar. |

### 5.3 Fatores e níveis

| Fator | Níveis |
|---|---|
| Tipo de página | home, categoria, busca, produto. São **3 URLs públicas por tipo** (12 URLs no total), fixadas em `config/urls.csv`. Usar várias URLs por tipo evita que o resultado dependa de uma única página. |
| Dispositivo | `mobile` × `desktop` (parâmetro `strategy` da PSI API) |
| Horário | pico (20h e 22h BRT = 23h e 01h UTC) × madrugada (03h e 05h BRT = 06h e 08h UTC) |

Cada execução gera 12 URLs × 2 dispositivos = 24 chamadas, feitas em sequência com intervalo de ≥ 2 s. São **4 execuções por dia** (2 em cada janela de horário) durante **7 dias** (18/11 20h → 25/11 05h), o que dá 4 × 24 × 7 = **672 medições**. Cada combinação de fatores (ex.: produto + celular + pico) recebe 3 URLs × 2 execuções × 7 dias = 42 medições.

O cronograma (S02 começa em 20/11 e termina em 26/11) não comporta 14 dias de coleta. Por isso duas execuções por janela compensam metade dos dias, e os 7 dias ainda incluem um fim de semana. A simulação de poder com o piloto (S01, onda 3) confirma se 42 por combinação bastam. Se não bastarem, a coleta continua rodando até 28/11 e os dias extras entram na S03 como análise de robustez.
### 5.4 Hipóteses (versão inicial, a refinar na onda 1 da S01)

- H1: o LCP no celular é maior que no desktop.
- H2: o LCP difere entre os tipos de página.
- H3: o LCP e o TTFB são maiores no pico do que na madrugada.
- H4: o número de auditorias de acessibilidade reprovadas difere entre os tipos de página.
- H5: o LCP sintético (celular) difere do p75 de LCP dos dados de campo do CrUX.

Cada uma tem H0 correspondente de "não há diferença".

### 5.5 Escalas e análise

- Tempos e bytes estão em escala de **razão**. As notas Lighthouse (0–100) são derivadas e devem ser tratadas com cuidado (discutir a escala). A categoria CrUX é **ordinal**. As contagens de violações são de razão (discretas).
- Análise: estatística descritiva (mediana, IQR, boxplots por fator). Teste de normalidade antes de escolher o teste. O mais provável são testes não paramétricos (Mann-Whitney/Wilcoxon para 2 níveis, Kruskal-Wallis + post-hoc para 4 tipos), com tamanho de efeito (Cliff's delta ou r). A escolha final fica com o integrante C, apoiada na simulação de poder e de erro tipo I do Lab04.
- Armadilhas de medição a discutir: as notas Lighthouse podem ser "jogadas" (Goodhart). A nota de acessibilidade automatizada cobre só parte do WCAG (McNamara: o que não é medido não some).

### 5.6 Coleta (instrumentação)

- `scripts/collect.py` (Python): lê `config/urls.csv`, chama `https://www.googleapis.com/pagespeedonline/v5/runPagespeed` com `category=performance&category=accessibility` e cada `strategy`, extrai as métricas e grava uma linha por chamada em `data/raw/YYYY-MM-DD.csv`. Também guarda o JSON bruto compactado, para auditoria.
- A chave da API fica no secret `PSI_API_KEY` do GitHub e nunca no código.
- `.github/workflows/collect.yml`: `schedule` com quatro crons (23:00, 01:00, 06:00 e 08:00 UTC) e `workflow_dispatch` para disparo manual. Ao final, faz commit dos CSVs. Observação: o cron do Actions pode atrasar alguns minutos, por isso o script grava o horário real da execução.
- Validação (`scripts/validate.py`): tenta de novo as chamadas com erro (até 2 vezes), marca linhas incompletas e verifica a cobertura esperada por dia.
- Ética: verificar e registrar o `robots.txt` do ML na S01. Volume muito abaixo de 1 req/s. Nenhum dado pessoal (só páginas públicas, sem login).

### 5.7 Ameaças à validade (ponto de partida)

- **Conclusão:** poucos dias geram baixo poder estatístico (mitigação: análise de poder com dados do piloto).
- **Interna:** o ML muda o site durante a coleta (deploys, banners de promoção, produto esgotado). Mitigação: registrar anomalias e manter o JSON bruto.
- **Construto:** a medição sintética não é a experiência real. Mitigação: contraste com o CrUX (H5).
- **Externa:** o Google mede de datacenters próprios e não de redes móveis brasileiras, e 12 URLs não representam todo o catálogo.

### 5.8 Impacto

Combinar o efeito medido (ex.: segundos a mais no celular) com números públicos e com fonte, como a audiência mensal do ML (SimilarWeb, relatórios de RI do Mercado Livre) e a parcela de acessos mobile, para estimar horas de espera por mês. A estimativa precisa deixar explícito o que **não** pode ser afirmado.

## 6. Estrutura do repositório

```
config/urls.csv            # URLs fixas por tipo de página
scripts/collect.py         # coleta via PSI API
scripts/validate.py        # validação e cobertura
.github/workflows/collect.yml
data/raw/                  # CSVs diários (versionados)
data/processed/            # dataset consolidado e validado
analysis/                  # notebooks/scripts de análise e gráficos
docs/                      # proposta, relatórios por sprint, documento final
```

## 7. Divisão em ondas (A → B → C a cada sprint)

Cada onda termina com um **artefato de passagem** que o próximo integrante usa sem precisar de quem saiu. Papéis fixos: **A = Planejamento e Método**, **B = Instrumentação e Operação**, **C = Análise e Impacto**.

A coleta (GitHub Actions) roda sozinha em segundo plano a partir da onda 2 da S01, então ela continua mesmo durante as ondas de A e C.

**Cronograma da disciplina:** S01 13/11–19/11 · S02 20/11–26/11 (20/11 é feriado) · S03 27/11–03/12 · apresentações em 04/12 e 11/12.

**Datas críticas:** o workflow precisa estar **ligado até 18/11 às 20h**. A coleta principal termina em **25/11 às 05h**.

### Sprint S01 — Proposta (13/11–19/11)

| Onda | Quem | Tarefas | Passa adiante |
|---|---|---|---|
| 1 (16–17/11) | A | Evidências dos 3 critérios (fontes + data de acesso); pergunta, GQM e hipóteses; 7 categorias v1; escolher as 12 URLs; plano de coleta e de análise; confirmar o tema com o professor | `docs/proposta.md`, `config/urls.csv` |
| 2 (17–18/11) | B | Chave da PSI API + secret; `collect.py`; workflow agendado e **ligado até 18/11 20h**; registro do `robots.txt`; **coleta piloto** (disparos manuais + primeiras execuções agendadas) | `data/raw/` do piloto + dicionário de dados (`docs/dados.md`) |
| 3 (19/11) | C | Descritiva do piloto; variância observada; simulação de poder (Lab04) para definir o nº de dias; montar a entrega da S01 | `analysis/piloto` + recomendação de nº de dias; entrega S01 |

### Sprint S02 — Coleta e análise (20/11–26/11)

| Onda | Quem | Tarefas | Passa adiante |
|---|---|---|---|
| 1 (20–21/11) | A | Ajustar o plano com base no piloto (nº de dias, URLs quebradas); critérios de validação; ameaças à validade v1 (4 tipos) | Plano revisado + `docs/ameacas.md` |
| 2 (22–24/11) | B | Acompanhar a coleta completa; `validate.py`; dataset consolidado em `data/processed/` (após 25/11 05h); registro de anomalias | Dataset validado e versionado |
| 3 (25–26/11) | C | Descritiva completa; testes de H1–H5; tamanhos de efeito; gráficos; montar a entrega da S02 | `analysis/` + relatório S02 |

### Sprint S03 — Impacto e conclusões (27/11–03/12)

| Onda | Quem | Tarefas | Passa adiante |
|---|---|---|---|
| 1 (27–28/11) | A | 7 categorias revisadas e justificadas; ameaças finalizadas; conclusões e limitações | Seções de método e conclusões |
| 2 (29–30/11) | B | Levantar números públicos de impacto com fonte (audiência, % mobile); README de reprodutibilidade; comparação de referência com concorrentes (opcional, sem teste) | `docs/impacto-fontes.md` + README |
| 3 (01–03/12) | C | Calcular o impacto; "o que não é possível afirmar"; rascunho do documento e da apresentação; montar a entrega da S03 | Rascunhos |

### Final — Documento e apresentação (apresentação em 04/12)

A apresentação é em 04/12, então não há sprint Final separada. As tarefas finais entram nas ondas da S03:

- **A (27–28/11):** além das tarefas acima, escreve as seções de método, categorias e validade **já na versão final** do documento.
- **B (29–30/11):** além das tarefas acima, escreve a seção de resultados e a de "o que foi reaproveitado dos Labs" na versão final.
- **C (01–03/12):** fecha o documento final e monta a apresentação de 10 min.
- **03/12 (todos):** ensaio da apresentação. Todos devem conseguir explicar qualquer parte.

## 8. Decisões tomadas por mim (Claude), a confirmar

- 3 URLs por tipo de página e 4 tipos de página.
- 4 execuções por dia (20h, 22h, 03h e 05h BRT) durante 7 dias, em vez de 2 execuções × 14 dias, por causa do cronograma.
- Python para os scripts e a análise.
- Formato final: relatório em Markdown/PDF no repositório + slides. O PDF deixa o formato livre, e o grupo pode trocar (por exemplo, dashboard).

## 9. Em aberto para o grupo

- Quem é A, B e C.
- (Resolvido) A apresentação é em 04/12, e a sprint Final foi incorporada à S03.
