<#
Registers Windows Task Scheduler jobs for unattended auto-post.
Prints what it WOULD do unless -Apply is passed (it changes system scheduler state).

  powershell -File tools\autopost_conductor\install_task.ps1                # preview
  powershell -File tools\autopost_conductor\install_task.ps1 -Apply         # register
  powershell -File tools\autopost_conductor\install_task.ps1 -HybridIntervalMinutes 5 -AllChannels -Apply
  powershell -File tools\autopost_conductor\install_task.ps1 -Remove -Apply # unregister
#>
param(
  [switch]$Apply,
  [switch]$Remove,
  [string]$PostAt = '09:00',
  [string]$HealthAt = '08:30',
  [int]$Limit = 10,
  [ValidateSet('schedule', 'draft', 'due_now', 'hybrid')]
  [string]$Mode = 'schedule',
  [string]$Channel = 'main',
  [switch]$AllChannels,
  [int]$HybridIntervalMinutes = 0
)
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$bat = Join-Path $root 'tools\start_autopost.bat'
$channelFlag = if ($AllChannels) { '--all-channels' } else { "--channel $Channel" }
$jobs = @(
  @{ Name = 'OmniCut-Autopost-Health'; Schedule = "/SC DAILY /ST $HealthAt"; Args = '--health' },
  @{ Name = 'OmniCut-Autopost-Run';    Schedule = "/SC DAILY /ST $PostAt";   Args = "--mode $Mode $channelFlag --limit $Limit" }
)
if ($HybridIntervalMinutes -gt 0) {
  $jobs += @{ Name = 'OmniCut-Autopost-Hybrid'; Schedule = "/SC MINUTE /MO $HybridIntervalMinutes"; Args = "--mode hybrid $channelFlag --limit $Limit" }
} elseif ($Remove) {
  $jobs += @{ Name = 'OmniCut-Autopost-Hybrid'; Schedule = ''; Args = '' }
}
foreach ($job in $jobs) {
  if ($Remove) {
    Write-Host "remove task $($job.Name)"
    if ($Apply) { schtasks /Delete /TN $job.Name /F 2>$null | Out-Null }
    continue
  }
  $cmd = "`"$bat`" $($job.Args)"
  Write-Host "task $($job.Name): $($job.Schedule) -> $cmd"
  if ($Apply) {
    $schedArgs = $job.Schedule -split '\s+'
    & schtasks /Create /TN $job.Name /TR $cmd @schedArgs /RL LIMITED /F | Out-Null
  }
}
if (-not $Apply) { Write-Host '(preview only - re-run with -Apply to register)' }
