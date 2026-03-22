"""Entry point for ``python -m unifi_relay_sidecar``."""

from __future__ import annotations

import asyncio
import logging
import sys

from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )
    from unifi_relay_sidecar.config import load_config
    from unifi_relay_sidecar.main import RelaySidecar

    try:
        config = load_config()
    except ValueError as e:
        logging.error("Configuration error: %s", e)
        sys.exit(1)

    sidecar = RelaySidecar(config)
    try:
        asyncio.run(sidecar.run())
    except KeyboardInterrupt:
        logging.info("Shutting down...")


if __name__ == "__main__":
    main()
