# Anomalias e checagens diárias da coleta (#T-0)

Uma linha por dia de checagem, por volta das 09h BRT. O registro cobre a janela anterior: as execuções das 20h07, 22h07, 03h07 e 05h07.

| Data da checagem | Responsável | Execuções na janela anterior | Linhas por `run_id` | `bloqueada`/`erro` | Situação |
|---|---|---|---|---|---|
| 19/11/2026 | B (Arthur) | 2 de 4 (`20261119T040444Z`, `20261119T083531Z`) | 38 e 38 | 0% / 0% | **Falha:** ver anomalia 1 |
| 20/11/2026 (registrada em 23/11) | C (Camila) | 1 de 4 (`20261120T082545Z`) | 38 | 0% / 0% | **Falha:** ver anomalia 2 |
| 21/11/2026 (registrada em 23/11) | C (Camila) | 4 de 4 (`20261120T230733Z`, `20261121T010740Z`, `20261121T060734Z`, `20261121T080732Z`) | 38, 38, 38 e 38 | 0% / 2,6% (1 linha de `20261121T010740Z`: `cat-3`, móvel, erro 400) | OK (erro abaixo de 10%) |
| 24/11/2026 (registrada em 25/11) | B (Arthur) | 4 de 4 (`20261123T230738Z`, `20261124T010733Z`, `20261124T060733Z`, `20261124T080734Z`) | 38, 38, 38 e 38 | 0% / 0% | OK |
| 25/11/2026 (registrada em 25/11) | B (Arthur) | 4 de 4 (`20261124T230737Z`, `20261125T010735Z`, `20261125T060731Z`, `20261125T080734Z`) | 38, 38, 38 e 38 | 0% / 0% | OK. Fim da coleta principal. Depois dela houve 1 execução fora do calendário: ver anomalia 3 |

## Anomalia 1: `schedule` do GitHub atrasado e descartado (noite de 18→19/11/2026)

**O que aconteceu:**

| Cron (UTC) | Previsto (BRT) | Início real (BRT) | Atraso | Janela gravada | Run do Actions |
|---|---|---|---|---|---|
| `7 23 * * *` | 18/11 20h07 | 19/11 01h04 | 4h57 | `madrugada` (deveria ser `pico`) | 44455744318 |
| `7 1 * * *` | 18/11 22h07 | 19/11 05h35 | 7h28 | `madrugada` (deveria ser `pico`) | 44488836343 |
| `7 6 * * *` | 19/11 03h07 | não executou | — | — | — |
| `7 8 * * *` | 19/11 05h07 | não executou | — | — | — |

As duas execuções que rodaram estão completas: 38 linhas cada, sem bloqueio e sem erro.

**Tratamento dos dados:** as duas execuções ficam no dataset com a janela pelo horário real (`madrugada`), porque é quando a medição de fato aconteceu. A coluna `cron` guarda o horário nominal, e por ela dá para identificá-las. Na análise, elas contam como as 2 execuções de madrugada de 19/11, e a noite de 18/11 fica sem execução de pico. A coleta principal passa a ter, no máximo, 12 execuções de pico e 14 de madrugada (26 em vez de 28).

**Correção (19/11/2026, #10):** o `schedule` do GitHub passou a disparar a cada 10 min na primeira hora de cada horário, e o porteiro (`scripts/porteiro.py`) deixa medir só a primeira tentativa até 60 min depois do horário nominal, sem duplicar. Disparos externos opcionais (`agendado=true`, gravados como `gatilho=agendador`) passam pelo mesmo porteiro. Detalhes em [`agendador.md`](agendador.md). A primeira noite com o esquema novo é a de 19→20/11.

**Ameaça à validade:** é uma ameaça de **conclusão e interna**, por causa da perda de uma noite de pico e do desbalanceamento. Ela entra na revisão do #A-7.

## Anomalia 2: noite de 19→20/11/2026 com 3 de 4 execuções perdidas

Registrada em 23/11/2026 por C (Camila), na revisão das checagens de 20 e 21/11 (#T-0).

**O que aconteceu:** na primeira noite com o esquema de tentativas e porteiro (`agendador.md`), o `schedule` do GitHub disparou só duas vezes, em vez de 6 tentativas por horário.

| Horário nominal (BRT) | Disparo real (BRT) | Run do Actions | Resultado |
|---|---|---|---|
| 19/11 20h07 | nenhum | — | sem medição |
| 19/11 22h07 | nenhum | — | sem medição |
| 20/11 03h07 | 20/11 00h55 | 44670943637 | o porteiro não mediu: `coletar=False (fora da tolerância de todos os horários)` |
| 20/11 05h07 | 20/11 05h25 | 44702392944 | medida: `20261120T082545Z`, 38 linhas, sem bloqueio e sem erro |

O disparo das 00h55 não serve para nenhum horário: fica 2h48 depois das 22h07 e 2h12 antes das 03h07, fora da tolerância de 60 min. O porteiro funcionou como previsto e evitou gravar uma medição na janela errada. A partir da noite de 20→21/11, as execuções passaram a vir do agendador externo (`gatilho=agendador`), e a coleta ficou completa.

**Tratamento dos dados:** nada a descartar. A única execução da noite fica no dataset como a madrugada de 20/11.

**Efeito no desenho:** somando as anomalias 1 e 2, a coleta principal tem, no máximo, **23 execuções** (10 de pico e 13 de madrugada), ou 874 linhas, em vez das 28 previstas. As noites de 18/11 e 19/11 ficam sem pico.

**Ameaça à validade:** **conclusão e interna**, pela perda de mais uma noite de pico e pelo desbalanceamento entre as janelas (10 × 13). Entra na revisão do #A-7. A simulação de poder (#C-3) supôs 7 dias com 2 execuções por janela, então o poder real de H3 tende a ser um pouco menor que o simulado.

## Anomalia 3: execução depois do fim da coleta (25/11/2026 20h07)

Registrada em 25/11/2026 por B (Arthur), no #B-6 e no #B-8.

**O que aconteceu:** a decisão do #A-8 ([`proposta.md`](proposta.md#extensão-da-coleta)) desliga a coleta após a execução de 25/11 05h07. O workflow, porém, continuou ativo, e o agendador externo disparou às 20h07. A execução `20261125T230736Z` (run do Actions 45718812938, `gatilho=agendador`, `cron=7 23 * * *`, `janela=pico`, `data_brt=2026-11-25`) gravou 38 linhas em [`data/raw/2026-11-25_BRT.csv`](../data/raw/2026-11-25_BRT.csv), sem bloqueio e sem erro.

**Tratamento dos dados:** as 38 linhas ficam no CSV bruto, que não é editado, mas **não entram no dataset**. O `scripts/validate.py` recorta a coleta pelo `ts_inicio_utc` em [18/11 18h00, 25/11 08h00) BRT, e essa execução começou depois do fim. A análise deve ler `data/processed/dataset.csv`, e não `data/raw/` direto: com `--input data/raw`, o `analise.py` incluiria essa execução como um pico de 25/11.

**Contenção (25/11/2026 ~21h20, commit `50f9c46`):** o token do git do integrante não tem o escopo `workflow`, então não deu para tirar o `schedule` do `collect.yml`. O porteiro (`scripts/porteiro.py`) passou a devolver `coletar=false` a partir de 25/11 06h10 BRT (`FIM_DA_COLETA`), e o teste `test_decidir_nao_coleta_depois_do_fim` cobre isso. Como o workflow sempre faz checkout do `main` antes de rodar o porteiro, os disparos de `schedule` e do agendador externo saem sem chamar a PSI desde a tentativa das 22h07. Falta **desabilitar o workflow na aba Actions** e revogar o token do cron-job.org (#B-8).

**Ameaça à validade:** nenhuma para o conjunto principal, que não usa essas linhas. É um registro de ética: foram 38 carregamentos a mais no site de terceiros, dentro do limite de 1 req/s.

## Campanhas e banners em 24–25/11/2026 (#B-6)

Nenhum agente pode abrir o `mercadolivre.com.br`, porque o `robots.txt` bloqueia `ClaudeBot`/`Claude-User` ([`etica.md`](etica.md) §5). Então os banners **não foram vistos** pelo grupo nas 19 URLs. O registro junta as fontes de terceiros do calendário do #A-7 e um sinal indireto dos próprios dados.

| Data | Campanha relatada | Fonte |
|---|---|---|
| 24/11/2026 (ter) | Cupom de 10% OFF, "já na reta final para a Black Friday" | [MKT Esportivo, 24/11/2026](https://www.mktesportivo.com/2026/11/cupom-mercado-livre-hoje-24-11-10-de-desconto-com-ate-200-reais-liberados/), acesso em 25/11/2026 (ver [`ameacas.md`](ameacas.md) §2) |
| 25/11/2026 (qua) | Seis cupons "no esquenta Black Friday"; cupom surpresa às 18h00 (depois do fim da coleta) | [MKT Esportivo, 25/11/2026](https://www.mktesportivo.com/2026/11/cupom-mercado-livre-hoje-25-11-6-codigos-libertados-no-esquenta-black-friday/); [Seletronic, 25/11/2026](https://seletronic.com.br/mercado-livre-cupom-surpresa-4-digitos-18h-25-11/), acesso em 25/11/2026 |

**Sinal indireto nos dados** (`data/processed/dataset.csv`, perfil móvel, todas as URLs; mediana por `data_brt`):

| `data_brt` | Peso total (KiB) | Nº de requisições | LCP (ms) |
|---|---|---|---|
| 19/11 | 2.191 | 124,0 | 4.611 |
| 20/11 | 2.023 | 124,0 | 4.571 |
| 21/11 | 1.883 | 113,5 | 4.378 |
| 22/11 | 1.979 | 114,5 | 4.256 |
| 23/11 | 1.920 | 112,5 | 4.265 |
| 24/11 | 2.129 | 115,5 | 4.418 |
| 25/11 | 2.138 | 135,5 | 4.572 |

Em 24–25/11 o peso das páginas voltou a subir, e em 25/11 (só as 2 execuções de madrugada) a mediana de requisições foi a mais alta da coleta. Isso é compatível com conteúdo de campanha, mas **não prova** que havia banners: o número de dias é pequeno, não há teste, e 19/11 e 25/11 só têm execuções de madrugada. O campo `titulo` veio vazio em todas as linhas, então não ajuda a identificar a campanha. O efeito aleatório de dia no modelo misto absorve parte dessa variação (ameaça interna "Black Friday" em [`ameacas.md`](ameacas.md)).

<!-- validate.py: início -->
## Validação da coleta principal (`scripts/validate.py`, #B-7)

Seção gerada por `python scripts/validate.py`. Recorte por `ts_inicio_utc` em [2026-11-18T21:00Z, 2026-11-25T11:00Z). Regras D1–D4 e S1–S2 de [`proposta.md`](proposta.md#regras-de-validação).

**Reconciliação:** 873 no dataset + 1 excluídas + 0 faltantes + 38 × 5 ausentes = 1064 (esperado 1064: fecha). Dataset final: 873 linhas de 23 execuções. Linhas no recorte fora do calendário: 0.

| Tipo | Ação | `run_id` | `data_brt` | Detalhe |
|---|---|---|---|---|
| `execucao_ausente` | registrar |  | 2026-11-18 | nenhuma execução de pico para o cron '7 1 * * *' |
| `execucao_ausente` | registrar |  | 2026-11-18 | nenhuma execução de pico para o cron '7 23 * * *' |
| `execucao_ausente` | registrar |  | 2026-11-19 | nenhuma execução de pico para o cron '7 1 * * *' |
| `execucao_ausente` | registrar |  | 2026-11-19 | nenhuma execução de pico para o cron '7 23 * * *' |
| `execucao_remanejada` | sinalizar | `20261119T040444Z` | 2026-11-19 | cron nominal '7 23 * * *' mediu na janela 'madrugada'; conta como '7 6 * * *' |
| `execucao_remanejada` | sinalizar | `20261119T083531Z` | 2026-11-19 | cron nominal '7 1 * * *' mediu na janela 'madrugada'; conta como '7 8 * * *' |
| `descartada_erro` | descartar (D2) | `20261121T010740Z` | 2026-11-20 | cat-3 mobile: 400 |
| `execucao_ausente` | registrar |  | 2026-11-20 | nenhuma execução de madrugada para o cron '7 6 * * *' |
<!-- validate.py: fim -->
