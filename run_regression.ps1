$ErrorActionPreference = "Continue"

Write-Host "=== RUFF ==="
.venv\Scripts\ruff.exe check .

Write-Host "=== MYPY ==="
.venv\Scripts\mypy.exe .

Write-Host "=== ALEMBIC CHECK ==="
.venv\Scripts\alembic.exe check

Write-Host "=== ALEMBIC UPGRADE HEAD ==="
.venv\Scripts\alembic.exe upgrade head

Write-Host "=== PYTEST ==="
# exclude tests/production/test_actual_deployment.py because it tears down the DB!
.venv\Scripts\coverage.exe run -m pytest tests/ --ignore=tests/production/test_actual_deployment.py

Write-Host "=== COVERAGE ==="
.venv\Scripts\coverage.exe report
