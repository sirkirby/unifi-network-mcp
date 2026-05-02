"""CLI tests."""

import subprocess


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["uv", "run", "--package", "unifi-api-server", "unifi-api-server", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_help_lists_subcommands() -> None:
    r = _run("--help")
    assert r.returncode == 0
    out = r.stdout + r.stderr
    assert "serve" in out
    assert "migrate" in out
    assert "keys" in out


def test_keys_help() -> None:
    r = _run("keys", "--help")
    assert r.returncode == 0
    out = r.stdout + r.stderr
    assert "create" in out
    assert "list" in out
    assert "revoke" in out


def test_serve_help() -> None:
    r = _run("serve", "--help")
    assert r.returncode == 0
