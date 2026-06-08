import pytest
from agentlens.store.sqlite import SQLiteStore


@pytest.fixture
async def store(tmp_path):
    db_path = tmp_path / "test.db"
    s = SQLiteStore(f"sqlite+aiosqlite:///{db_path}")
    await s.init()
    yield s
    await s.close()
