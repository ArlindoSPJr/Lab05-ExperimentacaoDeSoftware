# Disparo da coleta (issue #10)

## Por que existe

Na primeira noite da coleta (18→19/11/2026), o `schedule` do GitHub Actions falhou de duas formas:

- atrasou em 5 a 7 h os dois disparos de pico (20h07 e 22h07 BRT), que começaram às 01h04 e às 05h35 e foram gravados como `madrugada`;
- não executou os disparos de 03h07 e 05h07.

O GitHub avisa que o `schedule` pode atrasar ou ser descartado quando há carga alta. Como a janela de cada execução é calculada pelo **horário real de início** (é o horário da medição que importa para as hipóteses), um atraso desses tira a execução da janela. Sem execuções no pico não dá para testar H1, H2 e H5. O registro completo está em [`anomalias.md`](anomalias.md).

## Como funciona agora (desde 19/11): várias tentativas e um porteiro

Em vez de depender de **um** disparo por horário, o workflow recebe **várias tentativas** por horário e mede só uma:

1. **`schedule` a cada 10 min na primeira hora de cada horário.** São 6 tentativas por horário: 20h07–20h57, 22h07–22h57, 03h07–03h57 e 05h07–05h57 BRT. Tudo roda nos servidores do GitHub, sem PC ligado e sem token. O repositório é público, então os minutos do Actions são gratuitos.
2. **O porteiro** (`scripts/porteiro.py`, testado em `tests/test_porteiro.py`) roda no início de cada tentativa. Ele deixa medir só se as duas condições valem:
   - o instante está entre 5 min antes e 60 min depois de um dos 4 horários nominais;
   - esse horário ainda não tem, no CSV do dia, uma execução de coleta sem erro que começou dentro dessa mesma tolerância.

   Caso contrário, a tentativa sai em poucos segundos **sem chamar a PSI**. A cadência ética continua sendo de 1 coleta por horário.
3. **Uma tentativa atrasada demais é descartada.** Assim, um atraso como o de 18→19/11 não grava mais uma medição na janela errada.
4. **Se uma coleta falha inteira** (todas as linhas com erro), a próxima tentativa do mesmo horário mede de novo.

A coluna `cron` do CSV continua com o horário nominal do desenho (`7 23 * * *`, `7 1 * * *`, `7 6 * * *` e `7 8 * * *`), e não com a expressão de 10 em 10 min. Quem preenche esse valor é o porteiro.

**Limite:** se o GitHub atrasar **todas** as 6 tentativas de um horário em mais de 1 h, ou descartar todas, aquele horário fica sem medição. A checagem diária do #T-0 registra isso em `anomalias.md`. Para reduzir esse risco, dá para somar disparos externos (abaixo), e o porteiro evita medição duplicada.

## Como o workflow distingue os disparos

| Disparo | `gatilho` no CSV | Passa pelo porteiro? | Destino | Entra na análise? |
|---|---|---|---|---|
| `schedule` (a cada 10 min) | `schedule` | Sim | `data/raw/` | Sim |
| Agendador externo opcional (`agendado=true`) | `agendador` | Sim | `data/raw/` | Sim |
| Manual pela aba Actions ou `gh workflow run` (`agendado=false`) | `workflow_dispatch` | Não | `data/raw/testes/` | Não |

## Disparos externos opcionais (redundância)

Nenhum deles é obrigatório. Eles só somam tentativas ao `schedule`.

### Agendador de Tarefas do Windows

- `scripts/agendar_windows.ps1` cria 4 tarefas diárias às 20h07, 22h07, 03h07 e 05h07. Com `-Remover`, ele as apaga.
- Cada tarefa roda `scripts/disparar_coleta.ps1`, que chama `gh workflow run collect.yml -f agendado=true` com o login do `gh` do integrante.
- Se o PC acordar mais de 30 min atrasado, o disparo é ignorado.
- O log fica em `%LOCALAPPDATA%\lab05\disparos.log`.
- **O PC não precisa ficar ligado:** se ele estiver desligado, o `schedule` cobre o horário.
- Está instalado no PC do Arthur desde 19/11. O teste com `-Teste` gerou a execução 44534155362, gravada em `data/raw/testes/`.

### cron-job.org

O cron-job.org é um serviço gratuito de cron por HTTP, que dispara no minuto exato. Ele exige um token do dono do repositório guardado num serviço de terceiros. A configuração está a seguir.

## Configuração do cron-job.org (opcional)

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

O campo `cron` do corpo é ignorado, porque o porteiro deduz o horário pelo instante do disparo. Ele continua no corpo só para facilitar a leitura.

O botão "Test run" dessas tarefas é inofensivo fora do horário, porque o porteiro descarta o disparo. Dentro da tolerância de um horário ainda não medido, porém, ele faria uma coleta válida.

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

Conforme a decisão do #A-8, antes de 25/11 às 20h07 é preciso **desativar os disparos**, ou trocá-los para a coleta exploratória (#B-12):

- no GitHub, rodar `gh workflow disable collect.yml` (ou tirar o bloco `schedule` do workflow);
- no Windows, rodar `powershell -File scripts\agendar_windows.ps1 -Remover`;
- no cron-job.org, se tiver sido usado, desativar as 4 tarefas e **revogar o token**.

**Estado em 26/11/2026 (#B-8):** o workflow está desabilitado (`disabled_manually`) e as tarefas do Windows foram removidas. Os JSONs estão na release [`coleta-principal`](https://github.com/ArlindoSPJr/Lab05-ExperimentacaoDeSoftware/releases/tag/coleta-principal) (ver [`dados.md`](dados.md#jsons-brutos-release-coleta-principal-b-8)). Ainda falta desativar as tarefas e revogar o token do cron-job.org.

## Limites que continuam valendo

- A cadência não mudou: 4 execuções por noite, 38 chamadas cada, com ≥ 2 s entre chamadas (`docs/etica.md`).
- Todo disparo pode falhar, tanto o `schedule` quanto os externos. Por isso a checagem diária do #T-0 confere se cada um dos 4 horários da noite tem uma execução com 38 linhas.
- O porteiro aceita até 60 min de atraso, e mesmo assim a medição continua na janela certa: o horário mais apertado (22h07) termina a tolerância às 23h07, ainda dentro do pico.
- O início real da medição varia em até 1 h entre as noites. Isso é uma ameaça interna pequena e fica registrado pela coluna `ts_inicio_utc`.
