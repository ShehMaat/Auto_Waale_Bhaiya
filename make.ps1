param (
    [Parameter(Mandatory=$true)]
    [ValidateSet("install", "dev", "test", "lint", "format", "typecheck", "db-up", "db-migrate", "services-up", "services-down")]
    [string]$Command
)

switch ($Command) {
    "install" {
        Write-Host "Installing dependencies..."
        uv sync
        Set-Location apps\web
        npm install
        Set-Location ..\..
    }
    "dev" {
        Write-Host "Starting API development server..."
        uv run uvicorn apps.api.app.main:app --reload
    }
    "test" {
        Write-Host "Running tests..."
        uv run pytest
    }
    "lint" {
        Write-Host "Running Ruff linter..."
        uv run ruff check .
    }
    "format" {
        Write-Host "Running Ruff formatter..."
        uv run ruff format .
    }
    "typecheck" {
        Write-Host "Running Mypy typechecker..."
        uv run mypy .
    }
    "db-up" {
        Write-Host "Starting Database..."
        docker compose up -d db
    }
    "db-migrate" {
        Write-Host "Running Database Migrations..."
        uv run alembic upgrade head
    }
    "services-up" {
        Write-Host "Starting all services..."
        docker compose up -d
    }
    "services-down" {
        Write-Host "Stopping all services..."
        docker compose down
    }
}
