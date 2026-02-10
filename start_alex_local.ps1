# Launch Alex Local server

$ErrorActionPreference = "Stop"

# Launch Alex Local server
Set-Location $PSScriptRoot

# Launch Alex Local server
.\.venv\Scripts\Activate.ps1

# Launch Alex Local server
Start-Sleep -Seconds 2

# Launch Alex Local server
Start-Process "http://127.0.0.1:8000"

# Launch Alex Local server
uvicorn app:app --reload --host 127.0.0.1 --port 8000
