# backup_code.ps1 — recorder-file code backup
# Destination: Desktop\Program Backup\
# Keeps the latest 7 timestamped snapshots + always updates one "recorder-file" (latest)

$SRC     = "C:\Users\Administrator\recorder-file"
$DST     = "C:\Users\Administrator\Desktop\程序备份"
$TS      = Get-Date -Format "yyyyMMdd_HHmmss"
$BACKUP  = Join-Path $DST "recorder-file-$TS"
$LATEST  = Join-Path $DST "recorder-file"
$LOGFILE = Join-Path $DST "backup_log.txt"

$excludeDirs  = @("__pycache__", ".git", "venv", "knowledge_db", "logs")
$excludeExts  = @("*.pyc", "*.pyo", "*.log", "*.db")

function Write-Log($msg) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
    Write-Host $line
    Add-Content -Path $LOGFILE -Value $line -Encoding UTF8
}

New-Item -ItemType Directory -Path $DST -Force | Out-Null

Write-Log "=== Backup started: $BACKUP ==="

$xdArgs = $excludeDirs | ForEach-Object { $_ }
$xfArgs = $excludeExts | ForEach-Object { $_ }

# Copy to timestamped directory
$rcArgs = @($SRC, $BACKUP, "/E", "/NP", "/NFL", "/NDL", "/NC", "/NS", "/NJS",
            "/XD") + $xdArgs + @("/XF") + $xfArgs
& robocopy @rcArgs | Out-Null
Write-Log "Timestamped backup done: $BACKUP"

# Update latest snapshot
if (Test-Path $LATEST) { Remove-Item $LATEST -Recurse -Force }
$rcArgs2 = @($SRC, $LATEST, "/E", "/NP", "/NFL", "/NDL", "/NC", "/NS", "/NJS",
             "/XD") + $xdArgs + @("/XF") + $xfArgs
& robocopy @rcArgs2 | Out-Null
Write-Log "Latest snapshot updated: $LATEST"

# Clean up old backups, keep only the latest 7
$old = Get-ChildItem -Path $DST -Directory -Filter "recorder-file-2*" |
       Sort-Object Name -Descending |
       Select-Object -Skip 7
foreach ($d in $old) {
    Remove-Item $d.FullName -Recurse -Force
    Write-Log "Removed old backup: $($d.Name)"
}

$kept = (Get-ChildItem -Path $DST -Directory -Filter "recorder-file-2*").Count
Write-Log "=== Backup complete, $kept timestamped snapshots retained ==="
