# Agendador externo da coleta (issue #10)

## Por que existe

Na primeira noite da coleta (18→19/11/2026), o `schedule` do GitHub Actions falhou de duas formas:

- atrasou em 5 a 7 h os dois disparos de pico (20h07 e 22h07 BRT), que começaram às 01h04 e às 05h35 e foram gravados como `madrugada`;
- não executou os disparos de 03h07 e 05h07.

O GitHub avisa que o `schedule` pode atrasar ou ser descartado quando há carga alta. Como a janela de cada execução é calculada pelo **horário real de início** (é o horário da medição que importa para as hipóteses), um atraso desses tira a execução da janela. Sem execuções no pico não dá para testar H1, H2 e H5. O registro completo está em [`anomalias.md`](anomalias.md).

A partir de 19/11, quem dispara a coleta no horário certo é o **cron-job.org**, um serviço gratuito de cron por HTTP. Ele chama a API `workflow_dispatch` do GitHub. O `schedule` saiu do workflow para não gerar execuções atrasadas, fora da janela e duplicadas.

## Como o workflow distingue os disparos

| Disparo | `agendado` | `gatilho` no CSV | Destino | Entra na análise? |
|---|---|---|---|---|
| cron-job.org | `true` | `agendador` | `data/raw/` | Sim |
| Manual pela aba Actions ou `gh workflow run` | `false` (padrão) | `workflow_dispatch` | `data/raw/testes/` | Não |
| `schedule` antigo (só em 19/11) | — | `schedule` | `data/raw/` | Sim, com a janela pelo horário real |

Com `agendado=true`, o workflow só aceita um dos 4 crons do desenho (`7 23 * * *`, `7 1 * * *`, `7 6 * * *` e `7 8 * * *`). Qualquer outro valor faz a execução falhar sem medir, e isso abre a issue de alerta.

## Configuração (uma vez)

### 1. Token com permissão mínima (quem cria: o dono do repositório, ArlindoSPJr)

O token *fine-grained* só pode ser criado pelo dono do repositório. Em https://github.com/settings/personal-access-tokens/new:

- **Token name:** `lab05-agendador`
- **Expiration:** 30 dias, o que cobre até o fim da coleta e a eventual extensão até 28/11
- **Repository access:** *Only select repositories* → `Lab05-ExperimentacaoDeSoftware`
- **Permissions → Repository → Actions:** *Read and write*. Nenhuma outra permissão.

Esse token só consegue disparar e ler workflows deste repositório. Ele não lê código nem escreve no repositório. Mesmo assim, ele fica guardado num serviço de terceiros, então **revogue o token quando a coleta terminar** (#B-8).

### 2. Quatro tarefas no cron-job.org

Crie a conta em https://cron-job.org. Depois crie 4 tarefas iguais, que só mudam no horário e no campo `cron` do corpo:

- **URL:** `https://api.github.com/repos/ArlindoSPJr/Lab05-ExperimentacaoDeSoftware/actions/workflows/collect.yml/dispatches`
- **Método:** `POST`
- **Cabeçalhos:**
  - `Accept: application/vnd.github+json`
  - `Authorization: Bearer <token do passo 1>`
  - `X-GitHub-Api-Version: 2022-11-28`
  - `Content-Type: application/json`
- **Fuso horário da tarefa:** `America/Sao_Paulo`
- **Notificações:** ativar o e-mail em caso de falha

| Tarefa | Horário (BRT, todo dia) | Corpo (JSON) |
|---|---|---|
| `lab05-pico-1` | 20:07 | `{"ref":"main","inputs":{"agendado":"true","cron":"7 23 * * *"}}` |
| `lab05-pico-2` | 22:07 | `{"ref":"main","inputs":{"agendado":"true","cron":"7 1 * * *"}}` |
| `lab05-madrugada-1` | 03:07 | `{"ref":"main","inputs":{"agendado":"true","cron":"7 6 * * *"}}` |
| `lab05-madrugada-2` | 05:07 | `{"ref":"main","inputs":{"agendado":"true","cron":"7 8 * * *"}}` |

O campo `cron` continua no formato UTC antigo para que a coluna `cron` do CSV fique comparável com as execuções de 19/11.

**Não use o botão "Test run" dessas tarefas:** ele dispararia uma coleta válida fora do horário. Para testar, use o comando da seção abaixo.

### 3. Teste do caminho completo

Teste com o mesmo token, mas com `agendado=false`. Assim a resposta vai para `data/raw/testes/` e não entra na análise:

```bash
curl -i -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  https://api.github.com/repos/ArlindoSPJr/Lab05-ExperimentacaoDeSoftware/actions/workflows/collect.yml/dispatches \
  -d '{"ref":"main","inputs":{"agendado":"false","cron":""}}'
```

A resposta esperada é `HTTP 204`, e uma execução `workflow_dispatch` aparece na aba Actions.

## Fim da coleta

Conforme a decisão do #A-8, antes de 25/11 às 20h07 é preciso **desativar as 4 tarefas** no cron-job.org, ou trocá-las para a coleta exploratória (#B-12). Depois disso, **revogue o token**.

## Limites que continuam valendo

- A cadência não mudou: 4 execuções por noite, 38 chamadas cada, com ≥ 2 s entre chamadas (`docs/etica.md`).
- O cron-job.org também pode falhar. Por isso a checagem diária do #T-0 confere se as 4 execuções da noite aparecem no Actions.
- A fila do GitHub ainda pode atrasar o início em alguns minutos depois do disparo. Isso não muda a janela, porque o disparo mais apertado (22h07) ainda tem 1h52 até o fim da janela de pico.
