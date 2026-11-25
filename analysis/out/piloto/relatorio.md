# Descritiva do piloto incorporado (#C-1)

Gerado por `analysis/piloto.py` a partir de `data/raw/*.csv` (sem `data/raw/testes/`).
Piloto: execuções `schedule`/`agendador` iniciadas entre 18/11 20h07 e 19/11 06h07 BRT.

## Cobertura

**76/152 linhas** (2 de 4 execuções). Linhas por janela: madrugada: 76.

| cron | previsto_brt | run_id | janela_gravada | linhas | bloqueadas | com_erro | com_reserva | mais_de_1_tentativa |
|---|---|---|---|---|---|---|---|---|
| 7 23 * * * | 18/11 20h07 | 20261119T040444Z | madrugada | 38 | 0 | 0 | 0 | 0 |
| 7 1 * * * | 18/11 22h07 | 20261119T083531Z | madrugada | 38 | 0 | 0 | 0 | 2 |
| 7 6 * * * | 19/11 03h07 |  |  | 0 | 0 | 0 | 0 | 0 |
| 7 8 * * * | 19/11 05h07 |  |  | 0 | 0 | 0 | 0 | 0 |

As execuções que faltam são as da anomalia 1 (`docs/anomalias.md`): o `schedule` do GitHub atrasou as duas primeiras, que caíram na madrugada, e não disparou as duas últimas.

## Bloqueios, erros e reservas

| Indicador | Taxa |
|---|---|
| Linhas bloqueadas | 0,0% |
| Linhas com erro | 0,0% |
| Linhas com URL reserva | 0,0% |
| Linhas com mais de 1 tentativa | 2,6% |

Origem do TTFB: {'server-response-time': 76}.

## Descritiva por tipo × perfil × janela

Mediana e IQR. LCP e TTFB em ms; `a11y_reprovadas` em número de auditorias. Os valores completos (n, Q1, Q3) estão em `descritiva.csv`.

| tipo | strategy | janela | lcp_ms mediana | lcp_ms iqr | ttfb_ms mediana | ttfb_ms iqr | a11y_reprovadas mediana | a11y_reprovadas iqr |
|---|---|---|---|---|---|---|---|---|
| busca | desktop | madrugada | 1.220,3 | 525,9 | 28,0 | 8,2 | 4,0 | 0,0 |
| busca | mobile | madrugada | 4.398,5 | 1.041,4 | 25,5 | 8,5 | 4,0 | 1,0 |
| categoria | desktop | madrugada | 926,3 | 93,1 | 9,5 | 9,5 | 2,5 | 1,0 |
| categoria | mobile | madrugada | 6.678,7 | 6.925,1 | 12,0 | 7,0 | 2,0 | 0,0 |
| home | desktop | madrugada | 1.152,0 | 70,0 | 14,0 | 8,0 | 3,0 | 0,0 |
| home | mobile | madrugada | 6.604,1 | 798,8 | 25,0 | 8,0 | 3,0 | 0,0 |
| produto | desktop | madrugada | 1.140,0 | 129,2 | 30,0 | 22,2 | 5,0 | 0,2 |
| produto | mobile | madrugada | 4.597,5 | 1.022,5 | 27,0 | 16,8 | 4,0 | 2,0 |

## Variância entre execuções da mesma URL

Coeficiente de variação (desvio ÷ média) entre as execuções de cada URL, por perfil:

| metrica | strategy | urls | cv_mediano | cv_max |
|---|---|---|---|---|
| lcp_ms | desktop | 19 | 0,085 | 0,374 |
| lcp_ms | mobile | 19 | 0,093 | 0,756 |
| ttfb_ms | desktop | 19 | 0,307 | 0,950 |
| ttfb_ms | mobile | 19 | 0,404 | 0,676 |

URLs com maior variação de LCP:

| slot_id | tipo | strategy | media | desvio | cv |
|---|---|---|---|---|---|
| cat-3 | categoria | mobile | 6.490,595 | 4.905,589 | 0,756 |
| cat-4 | categoria | mobile | 6.619,522 | 4.742,590 | 0,716 |
| bus-2 | busca | desktop | 1.341,197 | 501,736 | 0,374 |
| bus-4 | busca | desktop | 1.296,749 | 380,013 | 0,293 |
| pro-6 | produto | desktop | 1.446,502 | 389,618 | 0,269 |

Auditorias de acessibilidade reprovadas: 3 de 38 combinações URL × perfil mudaram de uma execução para a outra.

### LCP em dois níveis nas categorias (celular)

O LCP das páginas de categoria no perfil móvel não varia de forma contínua: ele cai em dois níveis. 6 de 12 medições ficaram acima de 8.000 ms (mediana 10.098 ms), e as outras 6 ficaram perto de 3.098 ms. O FCP acompanha o mesmo salto (mediana 4.279 ms contra 2.431 ms), enquanto o peso da página e o número de requisições quase não mudam. 2 das 6 URLs trocaram de nível entre uma execução e a outra.

As linhas têm status 200, não estão bloqueadas e mostram a página certa, então **não há motivo para descartá-las**. Parece um comportamento real da página, mas a causa não foi investigada. Na análise, isso pesa a favor da mediana e de testes não paramétricos, e contra supor uma distribuição log-normal para o LCP das categorias. A #C-3 precisa considerar essa mistura ao simular.

### Decomposição da variância em log (insumo da #C-3)

| metrica | strategy | n_urls | execucoes_por_url | var_entre_urls_log | var_entre_execucoes_log | dp_entre_urls_log | dp_entre_execucoes_log | fracao_entre_execucoes |
|---|---|---|---|---|---|---|---|---|
| lcp_ms | desktop | 19 | 2,0000 | 0,0230 | 0,0222 | 0,1518 | 0,1490 | 0,4905 |
| lcp_ms | mobile | 19 | 2,0000 | 0,0605 | 0,0844 | 0,2459 | 0,2906 | 0,5827 |
| ttfb_ms | desktop | 19 | 2,0000 | 0,3134 | 0,3334 | 0,5598 | 0,5774 | 0,5154 |
| ttfb_ms | mobile | 19 | 2,0000 | 0,1439 | 0,2050 | 0,3793 | 0,4527 | 0,5876 |

`dp_entre_urls_log` e `dp_entre_execucoes_log` são os desvios-padrão, na escala log, do efeito aleatório de URL e do resíduo. A simulação de poder (#C-3) usa esses valores. Os detalhes de cada URL estão em `variancia_por_url.csv`.

## Limitações

- **Só 2 execuções por URL.** A variância entre execuções de cada URL vem de 2 valores, então é uma estimativa muito instável. Ela serve como ordem de grandeza, não como parâmetro preciso.
- **Não há execução de pico no piloto.** A descritiva cobre só a madrugada. A #C-3 precisa supor que a variância do pico é igual à da madrugada, ou reestimá-la com as noites coletadas a partir de 20/11.
- **Não há variação entre dias** (é uma noite só), então o efeito aleatório de `data_brt` do modelo misto não pode ser estimado com o piloto.
- Nenhuma linha precisou ser descartada.
