# Activate venv if exists, otherwise assume global
$venvPath = ".\.venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    Write-Host "Activating virtual environment..."
    & $venvPath
}

# Run Streamlit
Write-Host "Starting Streamlit Dashboard..."
python -m streamlit run app.py
