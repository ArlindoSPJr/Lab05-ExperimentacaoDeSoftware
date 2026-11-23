# Entrega Lab05 S01 + S02 — Desempenho e acessibilidade do site do Mercado Livre

## Plano de coleta e análise e resultados do piloto

### Desenho fatorial

O estudo mede o site do Mercado Livre de fora, pela API do PageSpeed Insights (PSI), em execuções agendadas no GitHub Actions. O desenho é um **fatorial 3 × 2 × 2**, com a home como referência descritiva:

| Fator | Níveis | Unidade experimental |
|---|---|---|
| Tipo de página | categoria, busca, produto (6 URLs cada) | **URL** |
| Perfil de dispositivo | móvel × desktop (parâmetro `strategy` da PSI) | medição |
| Horário | pico (20h07 e 22h07 BRT) × madrugada (03h07 e 05h07 BRT) | medição |
| Home (referência) | `https://www.mercadolivre.com.br/`, fora dos testes | — |

- **Perfil móvel:** a limitação de rede e CPU é fixada pela PSI: 4G lento simulado (150 ms de RTT, 1.638,4 kb/s) e CPU 1,2×, segundo o relatório da PSI de 19/11/2026 ([`dados.md`](dados.md)). É um celular emulado num servidor da América do Norte, e não um usuário real no Brasil.
- **Janelas:** a execução entra na janela pelo horário real de início: pico de 18h a 23h59 e madrugada de 00h a 07h59 (BRT). Execuções fora dessas faixas são descartadas. A escolha do pico se apoia no tráfego agregado do IX.br ([`proposta.md`](proposta.md)).
- **Execução:** cada execução faz 19 URLs × 2 perfis = 38 chamadas sequenciais, em **ordem sorteada**, com pelo menos 2 s entre elas (limite ético de 1 requisição por segundo).
- **Volume previsto:** 4 execuções por dia durante 7 dias (18/11 20h07 → 25/11 05h07), ou seja, 28 execuções e **1.064 medições**. Cada combinação tipo × perfil × horário tem 84 medições, mas só **6 unidades independentes** (as URLs) para o fator tipo.
- **Ajuste depois da primeira noite:** o `schedule` do GitHub atrasou as duas execuções de pico de 18/11 e não disparou as duas de madrugada (anomalia 1, [`anomalias.md`](anomalias.md)). A noite de 18/11 ficou sem pico, e o máximo possível passou a 26 execuções (12 de pico e 14 de madrugada), ou 988 medições. Desde 19/11, cada horário tem várias tentativas, e um porteiro deixa medir só a primeira dentro de 60 min do horário nominal ([`agendador.md`](agendador.md)). Até a manhã de 23/11, foram 15 execuções, todas com 38 linhas.

### Plano de análise

As escolhas foram fixadas antes da coleta (design §5.8). Antes de qualquer teste, o filtro mínimo (`analysis/stats.py`, `filtro_minimo`) mantém só as linhas de disparos agendados, sem bloqueio, sem erro e dentro de uma das duas janelas.

| Hipótese | Métrica | Unidade de análise | Perfil | Teste | Tamanho de efeito |
|---|---|---|---|---|---|
| H1: o LCP difere entre os perfis | LCP | medição, com efeitos aleatórios de URL e de dia | os dois | modelo linear misto em log | razão móvel/desktop com IC 95% |
| H2: o LCP difere entre os tipos | LCP | URL (mediana) | móvel; desktop como sensibilidade | Kruskal-Wallis + Dunn | ε² |
| H3: o TTFB difere entre pico e madrugada | TTFB observado | medição, com efeitos aleatórios de URL e de dia | os dois | modelo linear misto em log | razão pico/madrugada com IC 95% |
| H4: o nº de auditorias reprovadas difere entre os tipos | nº de reprovadas | URL (moda) | móvel; desktop como sensibilidade | Kruskal-Wallis + Dunn | ε² |
| H5: o LCP sintético concorda com o p75 do CrUX | LCP | par por URL | móvel | Wilcoxon pareado, Spearman, Bland-Altman | kappa nas categorias do CrUX |

- O modelo misto é `log(métrica) ~ perfil * horário * tipo`, com codificação de soma, de modo que o efeito de cada fator é estimado na média dos outros.
- Todos os testes são bilaterais, com **correção de Holm** sobre os 5 testes primários (α = 0,05).
- **Alternativa robusta:** se mais de 5% dos resíduos padronizados do modelo misto passarem de ±3, o modelo é ajustado de novo sobre postos alinhados (ART). Esse critério foi fixado antes de olhar os p-valores.
- **Descritiva:** mediana, IQR, p75 e p90 por combinação, por URL e no agregado, com a fração de medições que cumpre o SLO de LCP ≤ 2,5 s.
- **Scripts:** `analysis/stats.py` (funções estatísticas, com testes em `tests/test_stats.py`) e `analysis/analise.py`, que roda tudo com `python analysis/analise.py --input data/raw`.

### Piloto incorporado

As primeiras execuções da coleta servem de piloto. Elas validam a coleta e dão a variância usada na simulação de poder. O piloto previsto eram as 4 execuções da noite de 18→19/11 (detalhes em `analysis/out/piloto/relatorio.md`, gerado por `analysis/piloto.py`).

**Cobertura: 76/152 linhas (2 de 4 execuções).**

| Horário nominal (BRT) | Execução | Início real (BRT) | Janela gravada | Linhas |
|---|---|---|---|---|
| 18/11 20h07 | `20261119T040444Z` | 19/11 01h04 | madrugada | 38/38 |
| 18/11 22h07 | `20261119T083531Z` | 19/11 05h35 | madrugada | 38/38 |
| 19/11 03h07 | não executou | — | — | 0/38 |
| 19/11 05h07 | não executou | — | — | 0/38 |
| **Total** | | | | **76/152** |

- **Bloqueios, erros e reservas:** nenhuma linha bloqueada, com erro ou com URL reserva. 2 linhas (2,6%) precisaram de uma segunda tentativa. Todo o TTFB veio da fonte observada (`server-response-time`). Nenhuma linha precisou ser descartada.
- **Medianas do piloto** (madrugada):

  | Tipo | LCP desktop | LCP móvel | TTFB móvel | Reprovadas (móvel) |
  |---|---|---|---|---|
  | Categoria | 926 ms | 6.679 ms | 12 ms | 2 |
  | Busca | 1.220 ms | 4.399 ms | 25,5 ms | 4 |
  | Produto | 1.140 ms | 4.598 ms | 27 ms | 4 |
  | Home | 1.152 ms | 6.604 ms | 25 ms | 3 |

- **Variância entre execuções da mesma URL:** o coeficiente de variação mediano do LCP foi de 9% no móvel e de 8,5% no desktop. O do TTFB foi de 40% e 31%, porque são valores pequenos (dezenas de ms). As auditorias reprovadas quase não mudam: só 3 das 38 combinações URL × perfil mudaram de uma execução para a outra.
- **LCP em dois níveis nas categorias (móvel):** o LCP das páginas de categoria no celular cai em dois níveis, perto de 3 s ou perto de 10 s, com o FCP acompanhando o salto e sem mudança no peso da página. Duas URLs trocaram de nível entre as duas execuções. As linhas são válidas e foram mantidas. Como a distribuição não é log-normal nesse grupo, isso reforça o uso da mediana por URL e de testes não paramétricos em H2.
- **O que mudou por causa do piloto:** a falha do `schedule` levou ao esquema de tentativas e porteiro descrito acima. O desenho, as métricas e os testes não mudaram.

### Efeito mínimo detectável

A duração da coleta é fixa, então a simulação de poder (reaproveitando o Lab04) não define o número de dias: ela estima o **menor efeito que o desenho detecta com poder ≥ 0,8**. Desenho simulado: 6 URLs por tipo, 7 dias, 2 execuções por janela, com a variância do piloto. Detalhes em `analysis/out/poder/relatorio.md`, gerado por `analysis/poder.py`.

O efeito é uma razão r: em H2 e H4, o tipo mais alto é r× o mais baixo; em H3, o TTFB do pico é r× o da madrugada.

| Hipótese | Datasets por nível | Menor r com poder ≥ 0,8 | Erro tipo I (r = 1,00) |
|---|---|---|---|
| H2: LCP entre os tipos (móvel) | 1.000 | **1,75** (> 1,30 na grade do plano) | 0,039 |
| H3: TTFB pico × madrugada | 200 | **1,12** | 0,060 |
| H4: reprovadas entre os tipos | 1.000 | **1,50** (> 1,30 na grade do plano) | 0,040 |

- O erro tipo I observado fica entre 0,03 e 0,07 nas três hipóteses, como esperado para α = 0,05.
- **H3 é sensível:** detecta um pico 12% mais lento, porque usa todas as medições no modelo misto.
- **H2 e H4 só detectam diferenças grandes entre os tipos:** 75% no LCP e 50% nas reprovadas. Com 6 URLs por tipo, a variação de uma URL para outra domina. Um resultado não significativo em H2 ou H4 **não** mostra que os tipos são iguais, só que a diferença, se existe, é menor do que o desenho consegue ver. Isso entra na ameaça à validade de conclusão.

### Limitações do piloto

- Só 2 execuções por URL: as variâncias são uma ordem de grandeza, não um valor preciso.
- Não há execução de pico nem variação entre dias no piloto. Na simulação, a variação entre dias veio dos dias coletados até 23/11.
- A simulação supõe um LCP log-normal e não reproduz os dois níveis do LCP das categorias. O poder real de H2 tende a ser menor que o simulado.
