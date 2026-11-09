<#
Registers Windows Task Scheduler jobs for unattended auto-post.
Prints what it WOULD do unless -Apply is passed (it changes system scheduler state).

  powershell -File tools\autopost_conductor\install_task.ps1                # preview
  powershell -File tools\autopost_conductor\install_task.ps1 -Apply         # register
  powershell -File tools\autopost_conductor\install_task.ps1 -Remove -Apply # unregister
#>
param([switch]$Apply, [switch]$Remove, [string]$PostAt = '09:00', [string]$HealthAt = '08:30', [int]$Limit = 10)
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$bat = Join-Path $root 'tools\start_autopost.bat'
$jobs = @(
  @{ Name = 'OmniCut-Autopost-Health'; At = $HealthAt; Args = '--health' },
  @{ Name = 'OmniCut-Autopost-Run';    At = $PostAt;   Args = "--limit $Limit" }
)
foreach ($job in $jobs) {
  if ($Remove) {
    Write-Host "remove task $($job.Name)"
    if ($Apply) { schtasks /Delete /TN $job.Name /F | Out-Null }
    continue
  }
  $cmd = "`"$bat`" $($job.Args)"
  Write-Host "task $($job.Name): daily $($job.At) -> $cmd"
  if ($Apply) { schtasks /Create /TN $job.Name /TR $cmd /SC DAILY /ST $job.At /RL LIMITED /F | Out-Null }
}
if (-not $Apply) { Write-Host '(preview only - re-run with -Apply to register)' }
