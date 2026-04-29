"""Manager factory tests — caching + invalidation."""

import json
from datetime import datetime, timezone
from pathlib import Path
import uuid

import pytest

from unifi_api.db.crypto import ColumnCipher, derive_key
from unifi_api.db.engine import create_engine
from unifi_api.db.models import Base, Controller
from unifi_api.db.session import get_sessionmaker
from unifi_api.services.managers import (
    ManagerFactory,
    UnknownProduct,
)


async def _seed(tmp_path: Path, products: list[str] = ["network"]):
    engine = create_engine(tmp_path / "state.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = get_sessionmaker(engine)
    cipher = ColumnCipher(derive_key("k"))
    cid = str(uuid.uuid4())
    creds = cipher.encrypt(json.dumps({"username": "u", "password": "p", "api_token": None}).encode())
    async with sm() as session:
        session.add(Controller(
            id=cid, name="N", base_url="https://10.0.0.1",
            product_kinds=",".join(products),
            credentials_blob=creds,
            verify_tls=False, is_default=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ))
        await session.commit()
    return engine, sm, cipher, cid


@pytest.mark.asyncio
async def test_factory_caches_connection_manager(tmp_path: Path) -> None:
    engine, sm, cipher, cid = await _seed(tmp_path)
    factory = ManagerFactory(sm, cipher)
    async with sm() as session:
        cm1 = await factory.get_connection_manager(session, cid, "network")
        cm2 = await factory.get_connection_manager(session, cid, "network")
    assert cm1 is cm2
    await engine.dispose()


@pytest.mark.asyncio
async def test_invalidate_drops_cached_instance(tmp_path: Path) -> None:
    engine, sm, cipher, cid = await _seed(tmp_path)
    factory = ManagerFactory(sm, cipher)
    async with sm() as session:
        cm1 = await factory.get_connection_manager(session, cid, "network")
    await factory.invalidate_controller(cid)
    async with sm() as session:
        cm2 = await factory.get_connection_manager(session, cid, "network")
    assert cm1 is not cm2
    await engine.dispose()


@pytest.mark.asyncio
async def test_unknown_product_raises(tmp_path: Path) -> None:
    engine, sm, cipher, cid = await _seed(tmp_path, products=["network"])
    factory = ManagerFactory(sm, cipher)
    async with sm() as session:
        with pytest.raises(UnknownProduct):
            await factory.get_connection_manager(session, cid, "drive")
    await engine.dispose()
