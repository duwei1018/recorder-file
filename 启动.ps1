# 启动.ps1 — 双击运行
$PythonExe = "py -3.12"
$ScriptDir = "C:\Users\Administrator\recorder-file"

Set-Location $ScriptDir

Write-Host "[Recorder-File]" -ForegroundColor Cyan
Write-Host ""
Write-Host "1  Process all new files"
Write-Host "2  Force reprocess all files"
Write-Host "3  Process a single file"
Write-Host "4  Resume from Step 2 (dialogue formatting)"
Write-Host "5  Resume from Step 3 (summary extraction)"
Write-Host ""
$c = (Read-Host "Select").Trim()

switch ($c) {
    "1" { Invoke-Expression "$PythonExe main.py" }
    "2" { Invoke-Expression "$PythonExe main.py --force" }
    "3" {
        $f = (Read-Host "File path").Trim().Trim('"')
        Invoke-Expression "$PythonExe main.py --file `"$f`""
    }
    "4" { Invoke-Expression "$PythonExe main.py --step 2 --force" }
    "5" { Invoke-Expression "$PythonExe main.py --step 3 --force" }
    default { Invoke-Expression "$PythonExe main.py" }
}

Write-Host ""
Write-Host "Done. Log: C:\Users\Administrator\recorder-file\agent.log" -ForegroundColor Green
pause
