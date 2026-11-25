# Ameaças à validade (v1) e calendário promocional da coleta

Lab05 — Experimento em Software Real · Sprint conjunta S01+S02 · Ciclo 2 · Onda 1 (integrante A) · Issue #18

Base: design do estudo, §5.10 ([`superpowers/specs/2026-11-16-mercadolivre-desempenho-acessibilidade-design.md`](superpowers/specs/2026-11-16-mercadolivre-desempenho-acessibilidade-design.md#510-ameaças-à-validade)), e proposta metodológica ([`proposta.md`](proposta.md)).

Versão: **v1**, escrita em 25/11/2026, depois do fim da coleta principal (18/11 20h07 → 25/11 05h07 BRT) e antes da análise completa. A versão final é a da issue #26.

## 1. Ameaças à validade

A tabela parte das 12 linhas do design §5.10 e as atualiza com o que aconteceu na coleta e no piloto. A coluna **Origem** diz se a linha veio do design sem mudança (**design**), se veio do design e foi atualizada (**atualizada**) ou se é nova nesta versão (**nova**), com o arquivo interno que sustenta a mudança.

Números da coleta usados abaixo, contados em `data/raw/*.csv` em 25/11/2026: **23 execuções** (10 de pico e 13 de madrugada), **874 linhas**, nenhuma bloqueada, nenhuma com URL reserva, 1 com erro e todas as válidas com Lighthouse 13.6.0.

### Conclusão

| Ameaça | Mitigação | Origem |
|---|---|---|
| **Baixo poder em H2 e H4.** Com 6 URLs por tipo, a simulação só detecta, com poder ≥ 0,8, uma razão de **1,75** no LCP (H2) e de **1,50** nas reprovadas (H4) entre o tipo mais alto e o mais baixo. Em H3, o desenho detecta um pico **12% mais lento** (r = 1,12) | Relatar tamanho de efeito (ε², razões) e IC, não só o p-valor. Um H2 ou H4 não significativo **não** mostra que os tipos são iguais, só que a diferença é menor do que o desenho vê. Relatar o desktop como sensibilidade | atualizada: [`../analysis/out/poder/relatorio.md`](../analysis/out/poder/relatorio.md), [`entrega-s1s2.md`](entrega-s1s2.md) |
| Pseudorreplicação (repetições da mesma URL tratadas como amostras) | Agregar por URL (H2/H4) e efeitos aleatórios de URL e dia (H1/H3) | design |
| Comparações múltiplas | Holm sobre os 5 testes primários; métricas primárias definidas a priori ([`proposta.md`](proposta.md)) | design |
| **Perda de execuções e desbalanceamento.** O volume previsto era de 28 execuções; o possível é de **23** (10 de pico e 13 de madrugada). As noites de 18/11 e 19/11 ficaram sem pico (anomalia 1, em [`anomalias.md`](anomalias.md); anomalia 2, em [`entrega-s1s2.md`](entrega-s1s2.md)). A simulação de poder supôs 7 dias com 2 execuções por janela, então o poder real de H3 tende a ser um pouco menor que o simulado | O modelo misto aceita células desbalanceadas; relatar o n de cada célula; não imputar execuções. As execuções atrasadas ficam na janela do horário real. Desde 20/11 os disparos vêm do agendador externo com porteiro, e a coleta ficou completa | **nova**: [`anomalias.md`](anomalias.md), [`entrega-s1s2.md`](entrega-s1s2.md), [`agendador.md`](agendador.md) |
| **LCP em dois níveis nas categorias (móvel).** No piloto, o LCP das categorias no celular caiu perto de 3 s ou perto de 10 s, e 2 de 6 URLs trocaram de nível entre execuções. A distribuição não é log-normal nesse grupo, o que afeta os resíduos do modelo misto (H1) e deixa o poder real de H2 abaixo do simulado | H2 já usa a mediana por URL e Kruskal-Wallis (não paramétrico). Para H1/H3 vale o critério fixado antes dos p-valores: se mais de 5% dos resíduos padronizados passarem de ±3, reajustar com ART. As linhas são válidas e não são descartadas | **nova**: [`../analysis/out/piloto/relatorio.md`](../analysis/out/piloto/relatorio.md), [`entrega-s1s2.md`](entrega-s1s2.md) |
| **Parâmetros de variância instáveis.** As variâncias que alimentaram a simulação vêm de só 2 execuções por URL, e a variância entre dias, de poucos dias | Ler o efeito mínimo detectável como ordem de grandeza, não como valor preciso. Na #26, comparar as variâncias do piloto com as da coleta completa e dizer se o efeito mínimo muda de ordem | **nova**: [`../analysis/out/poder/relatorio.md`](../analysis/out/poder/relatorio.md) |

### Interna

| Ameaça | Mitigação | Origem |
|---|---|---|
| **Black Friday (27/11/2026).** A coleta principal (18/11 20h07 → 25/11 05h07) caiu inteira na temporada de "esquenta". As fontes da [§2](#2-calendário-promocional-do-mercado-livre-durante-a-coleta) relatam novos lotes de cupons do ML quase todo dia, de 21/11 a 25/11, o que pode trazer banners e tráfego atípicos | Declarar; registrar o calendário promocional (§2); efeito aleatório de dia no modelo misto. A coleta foi **desligada após 25/11 às 05h07**, sem análise exploratória da Black Friday (decisão da #19), então 26–28/11 não entram em nenhum conjunto | atualizada: §2 deste documento |
| **Pico e madrugada cobrem dias diferentes.** Por causa das perdas (anomalia 1, em [`anomalias.md`](anomalias.md); anomalia 2, em [`entrega-s1s2.md`](entrega-s1s2.md)), a madrugada tem execuções de 19/11 a 25/11, e o pico só de 20/11 a 24/11. Se o site muda ao longo da semana (por exemplo, mais promoções perto da Black Friday), parte dessa mudança pode aparecer como efeito de horário em H3 | O efeito aleatório de dia absorve parte da diferença entre os dias. Sugestão para a #26, a decidir pelo grupo: relatar H3 também só com os dias que têm as duas janelas, como sensibilidade fora do Holm | **nova**: [`anomalias.md`](anomalias.md), [`entrega-s1s2.md`](entrega-s1s2.md) |
| O ML muda o site durante a coleta (deploys, produto esgotado) | Registro de anomalias, URLs reservas e efeito aleatório de dia. Até 25/11, **nenhuma** linha precisou de URL reserva | atualizada: `data/raw/*.csv`, [`anomalias.md`](anomalias.md) |
| Mudança de versão do Lighthouse/PSI durante a coleta | Gravar `lighthouseVersion`; analisar com e sem os dias afetados. Até 25/11, todas as linhas válidas usaram o **Lighthouse 13.6.0**, então a ameaça não se concretizou | atualizada: `data/raw/*.csv`, [`dados.md`](dados.md) |
| **Atraso ou perda de execuções do cron do Actions; efeito de ordem das URLs.** A ameaça se concretizou: na noite de 18→19/11, o `schedule` atrasou as duas execuções de pico (4h57 e 7h28), que caíram na madrugada, e não disparou as duas de madrugada (anomalia 1). Na noite de 19→20/11, só a execução das 05h07 foi medida (anomalia 2, registrada só em [`entrega-s1s2.md`](entrega-s1s2.md)) | Crons em :07; horário real gravado; janela pelo horário real; ordem sorteada; validação de cobertura. Desde 19/11, várias tentativas por horário e um porteiro que mede só a primeira dentro de 60 min; desde 20/11, disparos pelo agendador externo | atualizada: [`anomalias.md`](anomalias.md), [`agendador.md`](agendador.md), [`entrega-s1s2.md`](entrega-s1s2.md) |
| **Falha pontual da PSI.** 1 das 874 linhas (`cat-3`, móvel, pico de 20/11) terminou com erro 400 depois de 3 tentativas | O filtro mínimo (`analysis/stats.py`, `filtro_minimo`) remove a linha antes dos testes; relatar a taxa de falha (0,1%). Com uma linha só, o viés é desprezível, mas a falha fica registrada | **nova**: `data/raw/2026-11-20_BRT.csv` |

### Construto

| Ameaça | Mitigação | Origem |
|---|---|---|
| **"Perfil móvel" é limitação simulada, não um celular real; o LCP do PSI é simulado (Lantern) e atenua a variação por horário.** A PSI fixa 4G lento simulado (150 ms de RTT, 1.638,4 kb/s) e CPU **1,2×**, e não os 4× previstos no design. O teste roda num servidor da América do Norte | Chamar o fator de *perfil*; usar o TTFB (observado) como métrica de H3; triangular com o CrUX (H5). Descrever o perfil com os valores informados pela PSI | atualizada: [`dados.md`](dados.md), [`entrega-s1s2.md`](entrega-s1s2.md) |
| **O TTFB observado é pequeno e ruidoso.** No piloto, as medianas ficaram entre 9,5 e 30 ms, com coeficiente de variação de 31% (desktop) e 40% (móvel). Valores dessa ordem sugerem resposta de um ponto de borda (CDN) perto do servidor de teste, e não necessariamente a carga do servidor de origem no pico | Ler H3 como "TTFB visto do ponto de teste da PSI", não como carga do back-end do ML; modelo em log, que trata o efeito como razão; não extrapolar para o TTFB do usuário brasileiro | **nova**: [`../analysis/out/piloto/relatorio.md`](../analysis/out/piloto/relatorio.md) |
| **O LCP sintético pode não representar o usuário real.** Na análise do piloto (1 dia, 18 URLs), o LCP sintético móvel ficou em média 2.683 ms acima do p75 do CrUX, com Spearman ρ = −0,368 e kappa = −0,047 nas categorias do CrUX | H5 existe para medir isso. Usar o LCP sintético para **comparar** fatores, não como "o que o usuário vê"; usar o CrUX como referência de campo. Confirmar com a coleta completa antes de concluir | **nova**: [`../analysis/out/analise_piloto/relatorio.md`](../analysis/out/analise_piloto/relatorio.md) |
| A nota automatizada de acessibilidade cobre só uma parte do WCAG | Analisar as auditorias reprovadas por tipo; declarar que a nota ≠ conformidade WCAG | design |
| Armadilhas de medição: Goodhart (a nota Lighthouse vira meta e é "jogada"), **Campbell** (decisões guiadas pela nota distorcem o produto), McNamara (o que não é medido, como leitores de tela reais, é ignorado) | Discutir no documento; usar métricas brutas (ms, contagens) como primárias, não as notas | design |

### Externa

| Ameaça | Mitigação | Origem |
|---|---|---|
| **Local do teste da PSI.** O PSI roda em datacenters do Google. As 3 execuções manuais feitas do Brasil em 19/11 também informaram "Local do navegador: América do Norte", então disparar do Brasil não leva a medição para o Brasil | Não generalizar valores absolutos de TTFB ou LCP para o usuário brasileiro; usar só diferenças relativas (pico × madrugada, móvel × desktop); usar o CrUX para a experiência real. A mitigação prevista no design (comparar com execuções do Brasil) foi feita e mostrou que **não** resolve a ameaça | atualizada: [`dados.md`](dados.md) |
| 19 URLs não representam o catálogo; uma semana atípica não representa o ano. A semana da coleta teve lotes diários de cupons do esquenta (§2) | Critério explícito de seleção (as mais destacadas/vendidas); contraste com o CrUX (28 dias); limitar as conclusões a páginas populares do ML **na semana anterior à Black Friday de 2026** | atualizada: §2 deste documento |

**Resumo:** 19 linhas, com pelo menos uma por tipo: 6 de conclusão, 6 internas, 5 de construto e 2 externas. 7 são novas, 8 foram atualizadas e 4 continuam como no design. Todas têm mitigação.

## 2. Calendário promocional do Mercado Livre durante a coleta

**Por que importa.** A Black Friday é a principal ameaça interna: a coleta principal (18/11 20h07 → 25/11 05h07) cai na semana de "esquenta", com campanhas que podem mudar o conteúdo, o peso das páginas e o tráfego. Os dias 26–28/11 nunca entram no conjunto principal. Pela decisão registrada na #19, a coleta foi desligada após 25/11 às 05h07, sem análise exploratória da Black Friday, então o calendário de 24–28/11 serve só de contexto.

**Como ler.** A tabela foi montada sem abrir o site do ML, e nenhum agente pode abri-lo (o `robots.txt` bloqueia `ClaudeBot`/`Claude-User`, ver [`etica.md`](etica.md) §5). **Observado** quer dizer que a fonte citada relata que a campanha estava ativa naquele dia; a observação é da fonte, não do grupo. Todas as fontes são de terceiros (imprensa e sites de cupons) e foram acessadas em **25/11/2026**.

### Contexto da temporada (antes da coleta)

| Data | Evento/campanha | Fonte (link) | Data de acesso |
|---|---|---|---|
| 19–20/10/2026 | Em 20/10, ML e Mercado Pago já tinham iniciado as campanhas do 11.11 e da Black Friday 2026, com a mensagem revelada em 19/10 (E-Commerce Brasil); parcelamento em até 21× sem juros no cartão Mercado Pago desde 19/10 (Exame) | [E-Commerce Brasil, 20/10/2026](https://www.ecommercebrasil.com.br/noticias/mercado-livre-11-11-black-friday-descontos); [Exame, 28/10/2026](https://exame.com/invest/mercados/mercado-livre-tera-24x-sem-juros-e-mais-de-r-100-mi-em-cupons-na-black-friday-2026/) | 25/11/2026 |
| 11/11/2026 | 11.11; parcelamento em até 24× sem juros no cartão Mercado Pago "a partir de 11 de novembro"; anúncio de mais de R$ 100 milhões em cupons na Black Friday | [Exame, 28/10/2026](https://exame.com/invest/mercados/mercado-livre-tera-24x-sem-juros-e-mais-de-r-100-mi-em-cupons-na-black-friday-2026/); [Agência GBC, 30/10/2026](https://agenciagbc.com/2026/10/30/mercado-livre-vai-distribuir-r-100-milhoes-em-cupons-na-black-friday-veja-como-conseguir-descontos-e-parcelar-compras-em-ate-24-vezes/) | 25/11/2026 |
| 16/11/2026 | "A temporada da Black Friday 2026 no Mercado Livre já está no ar"; cupons "liberados em ondas ao longo de todo o mês de novembro" | [Seletronic, 16/11/2026 (atualizado 17/11)](https://seletronic.com.br/black-friday-mercado-livre-2026/) | 25/11/2026 |

### Durante a coleta e até a Black Friday

| Data | Evento/campanha | Tipo | Fonte (link) | Data de acesso |
|---|---|---|---|---|
| 18/11/2026 (qua) | Página de cupons "ativos da Black November e Black Friday 2026" publicada nesse dia (a página mostra 18/11 13h47 e, no momento do acesso, 25/11 15h25, sem rótulo; lido como publicação e atualização) | observado | [Seletronic, 18/11/2026 13h47](https://seletronic.com.br/cupom-mercado-livre-hoje-black-november-black-friday-2026/) | 25/11/2026 |
| 19/11/2026 (qui) | sem fonte encontrada | observado | — | — |
| 20/11/2026 (sex) | sem fonte encontrada | observado | — | — |
| 21/11/2026 (sáb) | Novo lote de cupons na Black Friday: R$ 200 OFF em tecnologia (`TECH2111`) e 15% OFF em casa (`CASA2111`) | observado | [Seletronic, 21/11/2026 13h57](https://seletronic.com.br/mercado-livre-novos-cupons-200-off-tecnologia-15-off-casa-black-friday/) | 25/11/2026 |
| 22/11/2026 (dom) | Três cupons para todo o site, de até R$ 230 OFF (`TODOSITE2211`, `SITETODO2211`, `TODO2211SITE`) | observado | [Seletronic, 22/11/2026 19h01](https://seletronic.com.br/mercado-livre-novos-cupons-ate-230-off-todo-site-black-friday/) | 25/11/2026 |
| 23/11/2026 (seg) | "Cupom Mercado Livre disponível hoje": 10% OFF em compras acima de R$ 199 (`OFERTAML`) | observado | [MKT Esportivo, 23/11/2026](https://www.mktesportivo.com/2026/11/cupom-mercado-livre-hoje-23-11-ate-100-reais-de-desconto-com-o-cupom-10-off/) | 25/11/2026 |
| 24/11/2026 (ter) | "Nova promoção nesta terça-feira (24), já na reta final para a Black Friday" (cupom de 10% OFF) | anunciado | [MKT Esportivo, 24/11/2026](https://www.mktesportivo.com/2026/11/cupom-mercado-livre-hoje-24-11-10-de-desconto-com-ate-200-reais-liberados/) | 25/11/2026 |
| 25/11/2026 (qua) | Seis cupons "no esquenta Black Friday" (`MELIAGORA`, `LIVREHOJE` e outros); cupom surpresa às 18h00, exclusivo para o cartão Mercado Pago (depois do fim da coleta, às 05h07) | anunciado | [MKT Esportivo, 25/11/2026](https://www.mktesportivo.com/2026/11/cupom-mercado-livre-hoje-25-11-6-codigos-libertados-no-esquenta-black-friday/); [Seletronic, 25/11/2026 16h15](https://seletronic.com.br/mercado-livre-cupom-surpresa-4-digitos-18h-25-11/) | 25/11/2026 |
| 26/11/2026 (qui) | sem fonte encontrada | anunciado | — | — |
| 27/11/2026 (sex) | **Black Friday** | anunciado | [Como Comprar, 29/10/2026](https://comocomprar.com.br/black-friday-mercado-livre-2026/); [Agência GBC, 30/10/2026](https://agenciagbc.com/2026/10/30/mercado-livre-vai-distribuir-r-100-milhoes-em-cupons-na-black-friday-veja-como-conseguir-descontos-e-parcelar-compras-em-ate-24-vezes/); [MKT Esportivo, 25/11/2026](https://www.mktesportivo.com/2026/11/cupom-mercado-livre-hoje-25-11-6-codigos-libertados-no-esquenta-black-friday/) | 25/11/2026 |
| 28/11/2026 (sáb) | sem fonte encontrada | anunciado | — | — |

**Observações sobre as fontes:**
- Em 24/11 e 25/11, as fontes relatam a campanha como ativa no próprio dia. As linhas ficam como **anunciado** porque essa é a regra fixada para 24–28/11 na issue #18.
- A Cyber Monday cai em 30/11/2026 ([Como Comprar](https://comocomprar.com.br/black-friday-mercado-livre-2026/)), fora do período desta tabela.
- O fim da campanha de 2026 não tinha sido divulgado até 29/10/2026 ([Como Comprar](https://comocomprar.com.br/black-friday-mercado-livre-2026/)). Nenhuma fonte lida informa a data final.
- As fontes divergem no parcelamento máximo (18×, 21× ou 24×), conforme a data da matéria. A tabela segue a Exame, que separa as duas fases (21× desde 19/10, 24× a partir de 11/11).
- Os cupons são de sites agregadores, que reproduzem códigos do app. Eles mostram que havia campanha ativa, mas não dizem se banners ou conteúdo mudaram nas 19 URLs medidas.

### Pendências para um integrante humano

- **19/11 e 20/11:** nenhuma fonte de terceiros com data foi encontrada. Um integrante pode procurar uma fonte datada (imprensa, perfil oficial do ML replicado na imprensa) ou registrar o que lembrar ter visto no site, com data.
- **26/11 e 28/11:** nenhum evento específico foi encontrado. Como a coleta já estava desligada, esses dias pesam pouco; basta confirmar se houve campanha anunciada.
- **Banners nas URLs medidas (opcional):** se o grupo quiser saber se as 19 URLs mostravam banners da Black Friday durante a coleta, só um integrante humano pode conferir no site. Os agentes não podem abrir `mercadolivre.com.br`.
