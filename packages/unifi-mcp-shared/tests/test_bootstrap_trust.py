"""Regression coverage for explicit startup configuration."""

import logging
import os

import pytest
from unifi_mcp_shared import bootstrap


@pytest.fixture
def bundled_config(tmp_path, monkeypatch):
    """Use a synthetic package resource; never consult operator configuration."""
    for key in list(os.environ):
        if key.startswith("UNIFI_") or key == "CONFIG_PATH":
            monkeypatch.delenv(key)
    monkeypatch.setattr(bootstrap, "_TRUSTED_VARS", None)
    bundle = tmp_path / "bundled"
    bundle.mkdir()
    (bundle / "config.yaml").write_text(
        'unifi:\n  host: ${oc.env:UNIFI_HOST,""}\n'
        '  username: ""\n  password: ""\n  api_key: ""\n'
        "  port: 443\n  verify_ssl: true\n"
    )
    monkeypatch.setattr(bootstrap.importlib.resources, "files", lambda _: bundle)
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    return project


def load():
    return bootstrap.load_server_config(
        package_name="synthetic.config", env_prefix="NETWORK", logger=logging.getLogger("test")
    )


def test_implicit_yaml_cannot_supply_host_to_process_credentials(bundled_config, monkeypatch):
    (bundled_config / "config").mkdir()
    (bundled_config / "config/config.yaml").write_text("unifi:\n  host: attacker.invalid\n")
    monkeypatch.setenv("UNIFI_PASSWORD", "synthetic-password")
    bootstrap.load_process_env()
    cfg = load()
    assert cfg.unifi.host == ""
    assert cfg.unifi.password == "synthetic-password"
    with pytest.raises(SystemExit) as error:
        bootstrap.assert_credentials_configured(
            cfg, plugin_name="test", env_prefix="NETWORK", logger=logging.getLogger("test")
        )
    assert error.value.code == 5


def test_dotenv_cannot_reach_yaml_interpolation(bundled_config):
    # No process HOST override: the bundled oc.env resolver is the only reader.
    (bundled_config / ".env").write_text("UNIFI_HOST=attacker.invalid\n")
    bootstrap.load_process_env()
    assert load().unifi.host == ""
    assert "UNIFI_HOST" not in os.environ


def test_no_automatic_dotenv_discovery(bundled_config, monkeypatch):
    import dotenv

    def unexpected(*args, **kwargs):
        pytest.fail("bootstrap must not discover or load any dotenv file")

    monkeypatch.setattr(dotenv, "load_dotenv", unexpected)
    monkeypatch.setattr(dotenv, "find_dotenv", unexpected)
    bootstrap.load_process_env()
    bootstrap.load_process_env()


def test_explicit_absolute_yaml_and_env_precedence(bundled_config, monkeypatch):
    trusted = bundled_config.parent / "trusted.yaml"
    trusted.write_text(
        "unifi:\n  host: controller.invalid\n  port: 8443\n"
        '  username: ""\n  password: ""\n  api_key: ""\n  verify_ssl: true\n'
    )
    monkeypatch.setenv("CONFIG_PATH", str(trusted))
    monkeypatch.setenv("UNIFI_PASSWORD", "synthetic-password")
    bootstrap.load_process_env()
    cfg = load()
    assert cfg.unifi.host == "controller.invalid"
    assert cfg.unifi.password == "synthetic-password"
    assert cfg.unifi.port == 8443
    monkeypatch.setenv("UNIFI_HOST", "shared.invalid")
    monkeypatch.setenv("UNIFI_NETWORK_HOST", "specific.invalid")
    assert load().unifi.host == "specific.invalid"


@pytest.mark.parametrize("path", ["config/config.yaml", "./config.yaml", "../config.yaml"])
def test_relative_config_path_refuses_startup(bundled_config, monkeypatch, path, caplog):
    monkeypatch.setenv("CONFIG_PATH", path)
    with pytest.raises(SystemExit) as error:
        load()
    assert error.value.code == 2
    assert "absolute path" in caplog.text


def test_missing_explicit_config_fails_closed(bundled_config, monkeypatch):
    monkeypatch.setenv("CONFIG_PATH", str(bundled_config / "missing.yaml"))
    with pytest.raises(SystemExit) as error:
        load()
    assert error.value.code == 2
