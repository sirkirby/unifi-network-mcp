"""unifi-api CLI."""

from __future__ import annotations

from pathlib import Path

import typer
import uvicorn

from unifi_api.config import load_config
from unifi_api.logging import configure_logging
from unifi_api.server import create_app


app = typer.Typer(no_args_is_help=True, help="UniFi rich HTTP API service.")
keys_app = typer.Typer(no_args_is_help=True, help="Manage API keys.")
db_app = typer.Typer(no_args_is_help=True, help="Database operations.")
app.add_typer(keys_app, name="keys")
app.add_typer(db_app, name="db")


_DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"


@app.command()
def serve(
    host: str | None = typer.Option(None, help="Override config http.host"),
    port: int | None = typer.Option(None, help="Override config http.port"),
    config_path: Path = typer.Option(_DEFAULT_CONFIG_PATH, help="Path to config.yaml"),
) -> None:
    """Start the HTTP server."""
    cfg = load_config(config_path)
    configure_logging(cfg.logging.level)
    app_instance = create_app(cfg)
    uvicorn.run(app_instance, host=host or cfg.http.host, port=port or cfg.http.port, log_config=None)


@app.command()
def migrate(
    config_path: Path = typer.Option(_DEFAULT_CONFIG_PATH, help="Path to config.yaml"),
) -> None:
    """Run alembic migrations to head. Bootstraps an admin key on first run."""
    import asyncio
    import os
    import subprocess
    import uuid
    from datetime import datetime, timezone

    from sqlalchemy import select

    from unifi_api.auth.api_key import generate_key, hash_key
    from unifi_api.db.engine import create_engine
    from unifi_api.db.models import ApiKey
    from unifi_api.db.session import get_sessionmaker

    cfg = load_config(config_path)
    db_key = os.environ.get("UNIFI_API_DB_KEY")
    if not db_key:
        typer.echo("UNIFI_API_DB_KEY environment variable is required", err=True)
        raise typer.Exit(code=2)

    env = dict(os.environ)
    env["UNIFI_API_DB_PATH"] = cfg.db.path
    alembic_cwd = Path(__file__).parent.parent.parent  # apps/api
    result = subprocess.run(["alembic", "upgrade", "head"], env=env, cwd=alembic_cwd, check=False)
    if result.returncode != 0:
        raise typer.Exit(code=result.returncode)

    # Bootstrap admin key if api_keys is empty
    async def _maybe_bootstrap() -> str | None:
        engine = create_engine(cfg.db.path)
        sm = get_sessionmaker(engine)
        try:
            async with sm() as session:
                existing = (await session.execute(select(ApiKey))).first()
                if existing is not None:
                    return None
                material = generate_key()
                session.add(
                    ApiKey(
                        id=str(uuid.uuid4()),
                        prefix=material.prefix,
                        hash=hash_key(material.plaintext),
                        scopes="admin",
                        name="bootstrap-admin",
                        created_at=datetime.now(timezone.utc),
                    )
                )
                await session.commit()
            return material.plaintext
        finally:
            await engine.dispose()

    plaintext = asyncio.run(_maybe_bootstrap())
    if plaintext:
        typer.echo("=" * 60)
        typer.echo("Initial admin API key (shown once, save it now):")
        typer.echo(plaintext)
        typer.echo("=" * 60)


@keys_app.command("create")
def keys_create(
    name: str = typer.Argument(..., help="Human-readable name for the key"),
    scopes: str = typer.Option("read", help="Comma-separated scopes: read,write,admin"),
) -> None:
    """Create a new API key. Prints the plaintext exactly once."""
    typer.echo("(implemented in a later phase)")
    raise typer.Exit(code=0)


@keys_app.command("list")
def keys_list() -> None:
    """List API keys (prefix + scopes only; never plaintext)."""
    typer.echo("(implemented in a later phase)")
    raise typer.Exit(code=0)


@keys_app.command("revoke")
def keys_revoke(prefix: str = typer.Argument(..., help="Prefix of the key to revoke")) -> None:
    """Revoke an API key by prefix."""
    typer.echo("(implemented in a later phase)")
    raise typer.Exit(code=0)


@db_app.command("backup")
def db_backup(out_path: Path = typer.Argument(..., help="Backup destination")) -> None:
    """Encrypted backup."""
    typer.echo("(implemented in a later phase)")
    raise typer.Exit(code=0)


@db_app.command("rekey")
def db_rekey(new_key: str = typer.Argument(..., help="New passphrase")) -> None:
    """Rotate the column encryption key."""
    typer.echo("(implemented in a later phase)")
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
