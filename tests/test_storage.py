"""Tests for the built-in SQLite storage backend."""

import pytest

from newbiegram import raw
from newbiegram.storage import SQLiteStorage


@pytest.fixture
async def storage():
    store = SQLiteStorage(name="test", use_memory=True)
    await store.open()
    try:
        yield store
    finally:
        await store.close()


def test_open_and_close_in_memory(storage):
    """`use_memory=True` must keep the database off disk entirely."""
    assert storage.conn is not None
    assert storage.database == ":memory:"


async def test_close_clears_connection(storage):
    conn = storage.conn
    await storage.close()
    assert storage.conn is None
    assert conn is not None  # close() released our reference, it did not create one


async def test_dc_id_roundtrip(storage):
    await storage.dc_id(2)
    assert await storage.dc_id() == 2


async def test_peers_roundtrip(storage):
    await storage.update_peers([(123, -456, "user", "alice", None)])

    peer = await storage.get_peer_by_id(123)
    assert isinstance(peer, raw.types.InputPeerUser)
    assert peer.user_id == 123
    assert peer.access_hash == -456

    by_username = await storage.get_peer_by_username("alice")
    assert isinstance(by_username, raw.types.InputPeerUser)
    assert by_username.user_id == 123


async def test_update_peers_upserts_by_id(storage):
    """`update_peers` uses REPLACE, so the same id overwrites rather than duplicates."""
    await storage.update_peers([(1, -1, "user", "bob", None)])
    await storage.update_peers([(1, -99, "user", "bob", None)])

    peer = await storage.get_peer_by_id(1)
    assert peer.access_hash == -99


async def test_chat_peer_roundtrip(storage):
    # Groups are stored under the negated id and mapped back to chat_id.
    await storage.update_peers([(-30, 0, "group", None, None)])

    peer = await storage.get_peer_by_id(-30)
    assert isinstance(peer, raw.types.InputPeerChat)
    assert peer.chat_id == 30


async def test_get_peer_by_id_missing_raises(storage):
    """Lookups raise KeyError rather than returning None, so callers must catch it."""
    with pytest.raises(KeyError):
        await storage.get_peer_by_id(999999)


async def test_get_peer_by_username_missing_raises(storage):
    with pytest.raises(KeyError):
        await storage.get_peer_by_username("nobody")


async def test_last_update_on_is_refreshed_by_trigger(storage):
    """A trigger keeps `last_update_on` at "now" on every write.

    That is why the username cache can never go stale through normal use: the
    timestamp is refreshed by the database, not left to the caller.
    """
    await storage.update_peers([(5, -5, "user", "fresh", None)])

    await storage.conn.execute(
        "UPDATE peers SET last_update_on = last_update_on - ? WHERE username = 'fresh'",
        (SQLiteStorage.USERNAME_TTL * 3,),
    )
    await storage.conn.commit()

    # Still resolvable, and the trigger reset the timestamp back to now.
    assert isinstance(await storage.get_peer_by_username("fresh"), raw.types.InputPeerUser)


async def test_get_peer_by_phone_number(storage):
    await storage.update_peers([(20, -20, "user", None, "+1000")])

    peer = await storage.get_peer_by_phone_number("+1000")
    assert peer.user_id == 20

    with pytest.raises(KeyError):
        await storage.get_peer_by_phone_number("+1999")


async def test_session_state_roundtrip(storage):
    await storage.auth_key(b"\x01" * 256)
    assert await storage.auth_key() == b"\x01" * 256

    await storage.user_id(42)
    assert await storage.user_id() == 42

    await storage.is_bot(True)
    # Booleans are persisted as SQLite INTEGERs.
    assert bool(await storage.is_bot()) is True

    await storage.test_mode(False)
    assert bool(await storage.test_mode()) is False


async def test_delete_is_safe(storage):
    await storage.delete()
    await storage.delete()


async def test_session_string_export_and_reimport():
    """A session must survive a full export/import cycle, since that is how
    StringSession hand-off works."""
    original = SQLiteStorage(name="source", use_memory=True)
    await original.open()
    await original.dc_id(4)
    await original.auth_key(b"\xab" * 256)
    await original.api_id(12345)
    await original.user_id(7)
    session_string = await original.export_session_string()
    await original.close()

    restored = SQLiteStorage(name="restored", session_string=session_string)
    await restored.open()
    try:
        assert await restored.dc_id() == 4
        assert await restored.auth_key() == b"\xab" * 256
        assert await restored.api_id() == 12345
        assert await restored.user_id() == 7
    finally:
        await restored.close()


async def test_file_backed_storage_persists(tmp_path):
    store = SQLiteStorage(name="persist", workdir=tmp_path)
    await store.open()
    await store.dc_id(3)
    await store.auth_key(b"\x11" * 256)
    await store.save()
    await store.close()

    assert (tmp_path / "persist.session").exists()

    reopened = SQLiteStorage(name="persist", workdir=tmp_path)
    await reopened.open()
    try:
        assert await reopened.dc_id() == 3
        assert await reopened.auth_key() == b"\x11" * 256
    finally:
        await reopened.close()


async def test_methods_are_safe_without_a_connection():
    """Every accessor must degrade gracefully before open()/after close()."""
    store = SQLiteStorage(name="unopened", use_memory=True)
    assert await store.dc_id() is None
    assert await store.get_peer_by_id(1) is None
    await store.update_peers([])
    await store.delete()
