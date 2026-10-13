# Creates a one-click desktop shortcut for the Downloads Organizer.
# NOTE: keep this file ASCII-only. Windows PowerShell 5.1 reads .ps1 files
# using the ANSI code page unless they carry a UTF-8 BOM, so Turkish
# characters in this file would be corrupted.

$ErrorActionPreference = 'Stop'
$proje = Split-Path -Parent $MyInvocation.MyCommand.Path
$betik = Join-Path $proje 'indirilenler_duzenleyici.py'
$ikon = Join-Path $proje 'ikon.ico'

if (-not (Test-Path -LiteralPath $betik)) {
    Write-Host "Uygulama bulunamadi: $betik" -ForegroundColor Red
    exit 1
}

# Gercek yorumlayici yolunu bul. Get-Command, WindowsApps'taki "App Execution
# Alias" takma adini dondurur; kisayolun gercek dosyayi hedeflemesi icin
# yorumlayicinin kendisine sorulur.
$python = & python -c "import sys; print(sys.executable)" 2>$null
$python = $python | Select-Object -First 1
if (-not $python -or -not (Test-Path -LiteralPath $python)) {
    Write-Host "Python bulunamadi. Once Python 3.8+ kurun." -ForegroundColor Red
    exit 1
}
$pythonDir = Split-Path -Parent $python
$pythonw = Join-Path $pythonDir 'pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonw)) { $pythonw = $python }

$kisayol = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Indirilenler Duzenleyici.lnk'
$kabuk = New-Object -ComObject WScript.Shell
$k = $kabuk.CreateShortcut($kisayol)
$k.TargetPath = $pythonw
$k.Arguments = '"' + $betik + '"'
$k.WorkingDirectory = $proje
if (Test-Path -LiteralPath $ikon) {
    $k.IconLocation = $ikon
} else {
    # ikon yoksa sistemin klasör ikonunu kullan
    $k.IconLocation = Join-Path $env:SystemRoot 'System32\imageres.dll,3'
    Write-Host "Uyari: ikon.ico bulunamadi, sistem ikonu kullanildi." -ForegroundColor Yellow
}
$k.Description = 'Indirilenler klasorunu turlerine gore duzenler'
$k.Save()

Write-Host "Kisayol olusturuldu: $kisayol" -ForegroundColor Green
Write-Host "  Hedef: $pythonw"
Write-Host "  Betik: $betik"
