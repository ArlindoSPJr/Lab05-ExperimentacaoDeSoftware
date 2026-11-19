<#
Cria (ou recria) as 4 tarefas do Agendador de Tarefas do Windows que disparam a
coleta (issue #10, ver docs/agendador.md).

As tarefas rodam com o usuário logado (a tela pode estar bloqueada) e tentam
acordar o PC da suspensão. Não rodam com o PC desligado.

Uso:    powershell -File scripts\agendar_windows.ps1
Remover: powershell -File scripts\agendar_windows.ps1 -Remover
#>
param([switch]$Remover)

$ErrorActionPreference = "Stop"
$script = Join-Path $PSScriptRoot "disparar_coleta.ps1"
$tarefas = [ordered]@{
    "Lab05 coleta pico-1 (20h07)"      = @{ Hora = "20:07"; Cron = "7 23 * * *" }
    "Lab05 coleta pico-2 (22h07)"      = @{ Hora = "22:07"; Cron = "7 1 * * *" }
    "Lab05 coleta madrugada-1 (03h07)" = @{ Hora = "03:07"; Cron = "7 6 * * *" }
    "Lab05 coleta madrugada-2 (05h07)" = @{ Hora = "05:07"; Cron = "7 8 * * *" }
}

foreach ($nome in $tarefas.Keys) {
    Unregister-ScheduledTask -TaskName $nome -Confirm:$false -ErrorAction SilentlyContinue
    if ($Remover) { continue }
    $t = $tarefas[$nome]
    $acao = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`" -Cron `"$($t.Cron)`""
    $gatilho = New-ScheduledTaskTrigger -Daily -At $t.Hora
    # A tarefa não é recuperada depois: um disparo atrasado cairia na janela errada.
    $config = New-ScheduledTaskSettingsSet -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
    Register-ScheduledTask -TaskName $nome -Action $acao -Trigger $gatilho -Settings $config `
        -Description "Dispara o workflow collect.yml com agendado=true (Lab05, issue #10)" | Out-Null
}

Get-ScheduledTask -TaskName "Lab05 coleta*" | ForEach-Object {
    "{0} -> próxima: {1}" -f $_.TaskName, (Get-ScheduledTaskInfo $_).NextRunTime
}
