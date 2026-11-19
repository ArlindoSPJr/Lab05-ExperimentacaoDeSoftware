<#
Dispara uma coleta agendada do workflow collect.yml (issue #10).

É chamado pelo Agendador de Tarefas do Windows nos 4 horários da coleta. O
agendamento é criado por scripts/agendar_windows.ps1. Usa o login do gh do
próprio usuário, sem nenhum token guardado aqui.

Se o PC acordar ou ligar com atraso, o disparo é ignorado quando estiver mais de
30 min atrasado. Uma medição fora do horário seria gravada na janela errada.
Cada disparo fica registrado em %LOCALAPPDATA%\lab05\disparos.log.

Uso: powershell -File scripts\disparar_coleta.ps1 -Cron "7 23 * * *" [-Teste]
#>
param(
    [Parameter(Mandatory = $true)][string]$Cron,
    [switch]$Teste
)

$ErrorActionPreference = "Stop"
$gh = "C:\Program Files\GitHub CLI\gh.exe"
$repo = "ArlindoSPJr/Lab05-ExperimentacaoDeSoftware"
$logDir = Join-Path $env:LOCALAPPDATA "lab05"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir "disparos.log"

function Write-Log([string]$msg) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [$Cron] $msg" | Out-File -FilePath $log -Append -Encoding utf8
}

# Horário nominal (BRT) de cada cron UTC do desenho.
$nominal = @{ "7 23 * * *" = "20:07"; "7 1 * * *" = "22:07"; "7 6 * * *" = "03:07"; "7 8 * * *" = "05:07" }
if (-not $nominal.ContainsKey($Cron)) { Write-Log "cron inválido, nada disparado"; exit 1 }

if (-not $Teste) {
    $alvo = [datetime]::ParseExact($nominal[$Cron], "HH:mm", $null)
    $atraso = ((Get-Date) - $alvo).TotalMinutes
    if ($atraso -lt -5 -or $atraso -gt 30) {
        Write-Log ("ignorado: {0:N0} min do horário nominal {1}" -f $atraso, $nominal[$Cron])
        exit 0
    }
}

$agendado = if ($Teste) { "false" } else { "true" }
try {
    & $gh workflow run collect.yml --repo $repo --ref main -f "agendado=$agendado" -f "cron=$Cron" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "gh saiu com código $LASTEXITCODE" }
    Write-Log "disparado (agendado=$agendado)"
} catch {
    Write-Log "FALHA ao disparar: $_"
    exit 1
}
