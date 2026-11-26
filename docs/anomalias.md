# Anomalias e checagens diárias da coleta (#T-0)

Uma linha por dia de checagem, por volta das 09h BRT. O registro cobre a janela anterior: as execuções das 20h07, 22h07, 03h07 e 05h07.

| Data da checagem | Responsável | Execuções na janela anterior | Linhas por `run_id` | `bloqueada`/`erro` | Situação |
|---|---|---|---|---|---|
| 19/11/2026 | B (Arthur) | 2 de 4 (`20261119T040444Z`, `20261119T083531Z`) | 38 e 38 | 0% / 0% | **Falha:** ver anomalia 1 |
| 20/11/2026 (registrada em 23/11) | C (Camila) | 1 de 4 (`20261120T082545Z`) | 38 | 0% / 0% | **Falha:** ver anomalia 2 |
| 21/11/2026 (registrada em 23/11) | C (Camila) | 4 de 4 (`20261120T230733Z`, `20261121T010740Z`, `20261121T060734Z`, `20261121T080732Z`) | 38, 38, 38 e 38 | 0% / 2,6% (1 linha de `20261121T010740Z`: `cat-3`, móvel, erro 400) | OK (erro abaixo de 10%) |

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
