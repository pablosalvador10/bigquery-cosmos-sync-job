"""Entrypoint so ``python -m bq_cosmos_sync ...`` works."""

from bq_cosmos_sync.cli import app

if __name__ == "__main__":
    app()
