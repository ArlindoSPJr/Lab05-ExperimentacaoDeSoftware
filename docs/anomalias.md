# Anomalias e checagens diárias da coleta (#T-0)

Uma linha por dia de checagem, por volta das 09h BRT. O registro cobre a janela anterior: as execuções das 20h07, 22h07, 03h07 e 05h07.

| Data da checagem | Responsável | Execuções na janela anterior | Linhas por `run_id` | `bloqueada`/`erro` | Situação |
|---|---|---|---|---|---|
| 19/11/2026 | B (Arthur) | 2 de 4 (`20261119T040444Z`, `20261119T083531Z`) | 38 e 38 | 0% / 0% | **Falha:** ver anomalia 1 |

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
