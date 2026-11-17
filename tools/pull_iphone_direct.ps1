param(
    [string]$TargetFolder = "00_Inbox\iPhone_Clips",
    [string[]]$Clips = @(),      # Example: -Clips @('IMG_8212', 'IMG_8213') or @('8212', '8213')
    [int]$Recent = 10,           # Default recent count if no clips specified
    [int]$From = 0,              # Optional start number e.g. -From 8206
    [int]$To = 0                 # Optional end number e.g. -To 8216
)

$destDir = Join-Path (Get-Location) $TargetFolder
if (-not (Test-Path $destDir)) {
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  OmniCut Pro - iPhone Direct High-Speed  " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Destination: $destDir"

$shell = New-Object -ComObject Shell.Application
$computer = $shell.Namespace(17)
$iphone = $computer.Items() | Where-Object { $_.Name -like '*iPhone*' -or $_.Name -like '*Apple*' }

if (-not $iphone) {
    Write-Host "[!] ไม่พบ iPhone! กรุณาเสียบสาย USB และปลดล็อกหน้าจอ (Passcode/FaceID)" -ForegroundColor Red
    exit 1
}

Write-Host "[✓] เชื่อมต่อสำเร็จ: $($iphone.Name)" -ForegroundColor Green
$devFolder = $iphone.GetFolder
$storage = $devFolder.Items() | Where-Object { $_.Name -eq 'Internal Storage' }

if (-not $storage) {
    Write-Host "[!] ไม่สามารถเข้าถึงพื้นที่จัดเก็บได้ กรุณาปลดล็อกหน้าจอ iPhone" -ForegroundColor Red
    exit 1
}

$storageFolder = $storage.GetFolder
$folders = @($storageFolder.Items()) | Sort-Object Name -Descending
$newestFolder = $folders | Where-Object { $_.Name -match '^\d{6}_[a-z]' } | Select-Object -First 1

if (-not $newestFolder) {
    Write-Host "[!] ไม่พบโฟลเดอร์ DCIM ใน iPhone" -ForegroundColor Red
    exit 1
}

Write-Host "[✓] ค้นหาโฟลเดอร์ล่าสุด: $($newestFolder.Name)" -ForegroundColor Green
$dcimFolder = $newestFolder.GetFolder
$destFolderObj = $shell.Namespace($destDir)

$items = @($dcimFolder.Items())
$vids = @()
foreach ($it in $items) {
    $type = $dcimFolder.GetDetailsOf($it, 1)
    if ($type -like '*MOV*' -or $type -like '*video*' -or $type -like '*movie*' -or $type -like '*mp4*') {
        $name = $dcimFolder.GetDetailsOf($it, 0)
        $size = $dcimFolder.GetDetailsOf($it, 2)
        $date = $dcimFolder.GetDetailsOf($it, 3)
        $vids += [PSCustomObject]@{
            Item = $it
            Name = $name
            Size = $size
            Date = $date
        }
    }
}

# Filtering logic
$selectedVids = @()
if ($Clips.Count -gt 0) {
    $cleanClips = $Clips | ForEach-Object { if ($_ -match '^\d+$') { "IMG_$_" } else { $_ } }
    $selectedVids = $vids | Where-Object { $cleanClips -contains $_.Name }
} elseif ($From -gt 0 -and $To -gt 0) {
    $selectedVids = $vids | Where-Object {
        if ($_.Name -match '^IMG_(\d+)$') {
            $num = [int]$matches[1]
            return ($num -ge $From -and $num -le $To)
        }
        return $false
    }
} else {
    $selectedVids = $vids | Sort-Object Name -Descending | Select-Object -First $Recent
}

Write-Host "พบคลิปเป้าหมาย $($selectedVids.Count) ไฟล์ เริ่มดึงข้อมูลตรงผ่านสาย..." -ForegroundColor Yellow

$copied = 0
foreach ($v in ($selectedVids | Sort-Object Name)) {
    $destFile = Join-Path $destDir "$($v.Name).MOV"
    if (Test-Path $destFile) {
        Write-Host "  [-] มีอยู่แล้ว (ข้าม): $($v.Name).MOV" -ForegroundColor DarkGray
    } else {
        Write-Host "  [+] กำลังดึง: $($v.Name).MOV ($($v.Size))..." -ForegroundColor Cyan
        $destFolderObj.CopyHere($v.Item, 16 + 4)
        Write-Host "      ✓ เสร็จสิ้น!" -ForegroundColor Green
        $copied++
    }
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "ดึงคลิปเสร็จสิ้น! บันทึกลง $TargetFolder เรียบร้อย ($copied ไฟล์ใหม่)" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
