param([switch]$DryRun)
$ErrorActionPreference = 'Stop'

function Test-OmnicutProcess {
    param($Process, $Processes, [string]$ProjectRoot, [int]$Port)
    $rootPattern = [regex]::Escape($ProjectRoot.TrimEnd('\', '/')) + '[\\/]'
    $visited = @{}
    $candidate = $Process
    while ($null -ne $candidate -and -not $visited.ContainsKey([int]$candidate.ProcessId)) {
        $visited[[int]$candidate.ProcessId] = $true
        $command = [string]$candidate.CommandLine
        $owned = $command -match $rootPattern
        # Windows venv Python may delegate to its base interpreter. The
        # wrapper's executable identifies this workspace even when its
        # command line uses relative paths; never accept another script/venv.
        $projectPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
        $relativeBackend = $command -match '\s["'']?(?:\.[\\/])?scripts[\\/]api_server\.py["'']?(?:\s|$)'
        if ($Port -eq 8000 -and $relativeBackend -and
            [string]$candidate.ExecutablePath -ieq $projectPython) {
            $owned = $true
        }
        $service = switch ($Port) {
            8000 { $command -match 'scripts[\\/]api_server\.py' }
            5173 { $command -match 'frontend([\\/]|\")' -and $command -match '(vite|npm run dev)' }
            3002 { $command -match '_HyperFrames_Studio' -and $command -match 'hyperframes.*preview' }
            default { $false }
        }
        if ($owned -and $service) { return $true }
        $parent = $Processes[[int]$candidate.ParentProcessId]
        if ($null -ne $parent -and $parent.CreationDate -gt $candidate.CreationDate) { return $false }
        $candidate = $parent
    }
    return $false
}

function Start-Omnicut {
    param([string]$ProjectRoot, [switch]$InspectOnly)
    $root = (Resolve-Path -LiteralPath $ProjectRoot).Path
    $python = Join-Path $root '.venv\Scripts\python.exe'
    $frontend = Join-Path $root 'frontend'
    $studio = Join-Path $root '03_Projects\_HyperFrames_Studio'
    foreach ($required in @($python, $frontend, $studio)) {
        if (-not (Test-Path -LiteralPath $required)) { throw "Missing launcher input: $required" }
    }
    $processes = @{}
    foreach ($process in Get-CimInstance Win32_Process) { $processes[[int]$process.ProcessId] = $process }
    $listeners = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in @(8000, 5173, 3002) })
    $owned = @{}
    $existingStudio = $false
    # Complete validation before stopping ANY process. An unrelated listener
    # blocks startup and remains untouched, including processes on other ports.
    foreach ($listener in $listeners) {
        $process = $processes[[int]$listener.OwningProcess]
        if ($null -eq $process -or -not (Test-OmnicutProcess $process $processes $root $listener.LocalPort)) {
            # Studio is auxiliary. Keep an independently opened HyperFrames
            # preview alive; this does not grant ownership or permission to
            # stop it. Unknown services on any port still block startup.
            if ($listener.LocalPort -eq 3002 -and $null -ne $process -and
                [string]$process.Name -ieq 'node.exe' -and
                [string]$process.CommandLine -match 'hyperframes(?:\.mjs|[\\/].*?)?[^\r\n]*\s+preview(?:\s|$)') {
                $existingStudio = $true
                continue
            }
            throw "Port $($listener.LocalPort) belongs to another or unverified process $($listener.OwningProcess). Close it manually or choose another port."
        }
        $owned[[int]$listener.OwningProcess] = $true
    }
    if ($InspectOnly) { return @{ root = $root; owned_processes = @($owned.Keys); ports = @(8000, 5173, 3002); existing_studio_preserved = $existingStudio } }
    foreach ($processId in $owned.Keys) { Stop-Process -Id $processId -Force }
    $env:FASTAPI_RELOAD = 'false'
    Start-Process -FilePath $python -ArgumentList ('"' + (Join-Path $root 'scripts\api_server.py') + '"') -WorkingDirectory $root -WindowStyle Hidden
    Start-Process -FilePath 'cmd.exe' -ArgumentList ('/d /c "cd /d "' + $frontend + '" && npm run dev -- --strictPort"') -WorkingDirectory $frontend -WindowStyle Hidden
    if ($existingStudio) {
        Write-Host 'Keeping the existing HyperFrames preview on port 3002; its workspace is managed by the session that opened it.'
    } else {
        Start-Process -FilePath 'cmd.exe' -ArgumentList ('/d /c "cd /d "' + $studio + '" && npx --yes hyperframes@0.8.143 preview --port=3002"') -WorkingDirectory $studio -WindowStyle Hidden
    }
    Write-Host 'Starting OmniCut: https://localhost:5173 | API: http://localhost:8000 | HyperFrames: http://localhost:3002'
    Start-Process 'https://localhost:5173'
}

if ($MyInvocation.InvocationName -ne '.') {
    try { Start-Omnicut -ProjectRoot (Split-Path -Parent $PSScriptRoot) -InspectOnly:$DryRun }
    catch { Write-Error $_; exit 1 }
}
