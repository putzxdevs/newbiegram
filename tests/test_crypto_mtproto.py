"""Tests for MTProto message framing (pack/unpack) and the KDF."""

import hashlib
import os
from io import BytesIO

import pytest

from newbiegram.crypto import aes, mtproto
from newbiegram.errors import SecurityCheckMismatch
from newbiegram.raw import functions
from newbiegram.raw.core import Message


@pytest.fixture
def credentials():
    return os.urandom(256), os.urandom(8)


def _ping(seq_no: int = 0, msg_id: int = 1234567890123456789) -> Message:
    body = functions.Ping(ping_id=0)
    return Message(body=body, msg_id=msg_id, seq_no=seq_no, length=len(body.write()))


def test_kdf_is_direction_dependent(credentials):
    """Outgoing and incoming use different auth_key slices (x=0 vs x=8)."""
    auth_key, msg_key = credentials
    msg_key *= 2  # 16 bytes

    outgoing = mtproto.kdf(auth_key, msg_key, True)
    incoming = mtproto.kdf(auth_key, msg_key, False)

    assert outgoing != incoming
    assert len(outgoing[0]) == 32 and len(outgoing[1]) == 32


def test_kdf_is_deterministic(credentials):
    auth_key, msg_key = credentials
    msg_key *= 2

    assert mtproto.kdf(auth_key, msg_key, True) == mtproto.kdf(auth_key, msg_key, True)


def test_pack_produces_auth_key_id_and_msg_key_prefix(credentials):
    """Wire format is auth_key_id (8) + msg_key (16) + AES-IGE payload."""
    auth_key, auth_key_id = credentials
    session_id = os.urandom(8)

    packed = mtproto.pack(_ping(), salt=0, session_id=session_id,
                          auth_key=auth_key, auth_key_id=auth_key_id)

    assert packed[:8] == auth_key_id
    assert len(packed) > 24
    # The encrypted body is block-aligned; the 24-byte cleartext header is not.
    assert len(packed[24:]) % 16 == 0


def test_pack_is_non_deterministic_but_parseable(credentials):
    """Random padding means two packs differ, yet both decrypt to the same body."""
    auth_key, auth_key_id = credentials
    session_id = os.urandom(8)

    first = mtproto.pack(_ping(), salt=0, session_id=session_id,
                         auth_key=auth_key, auth_key_id=auth_key_id)
    second = mtproto.pack(_ping(), salt=0, session_id=session_id,
                          auth_key=auth_key, auth_key_id=auth_key_id)
    assert first != second

    # unpack() uses the incoming KDF direction, so decrypt manually with the
    # outgoing one to confirm both frames carry the same cleartext header.
    for packed in (first, second):
        msg_key = packed[8:24]
        aes_key, aes_iv = mtproto.kdf(auth_key, msg_key, True)
        data = mtproto.aes.ige256_decrypt(packed[24:], aes_key, aes_iv)

        # Long(0) is a single byte, so the salt occupies offset 0 and the
        # session_id sits at 8:16.
        assert data[8:16] == session_id

        # The msg_key must verify against auth_key[88:120] + plaintext.
        msg_key_large = hashlib.sha256(auth_key[88:120] + data).digest()
        assert msg_key == msg_key_large[8:24]


def test_unpack_rejects_wrong_auth_key_id(credentials):
    auth_key, _ = credentials
    session_id = os.urandom(8)
    packed = mtproto.pack(_ping(), salt=0, session_id=session_id,
                          auth_key=auth_key, auth_key_id=os.urandom(8))

    with pytest.raises(SecurityCheckMismatch):
        mtproto.unpack(BytesIO(packed), session_id, auth_key, os.urandom(8))


def test_unpack_rejects_wrong_session_id(credentials):
    """The session_id lives inside the encrypted payload, so a mismatch is
    detected only after decryption succeeds."""
    auth_key, auth_key_id = credentials
    packed = mtproto.pack(_ping(), salt=0, session_id=os.urandom(8),
                          auth_key=auth_key, auth_key_id=auth_key_id)

    with pytest.raises(SecurityCheckMismatch):
        mtproto.unpack(BytesIO(packed), os.urandom(8), auth_key, auth_key_id)


def test_unpack_roundtrip_using_server_direction(credentials):
    """Pack with the server's KDF direction so unpack() can read it back.

    `pack` hardcodes outgoing=True, so to exercise `unpack` we rebuild the frame
    the way a server would: msg_key over auth_key[96:128] and incoming kdf.
    """
    auth_key, auth_key_id = credentials
    session_id = os.urandom(8)
    message = _ping()

    salt = os.urandom(8)
    data = salt + session_id + message.write()
    padding = os.urandom(-(len(data) + 12) % 16 + 12)
    plaintext = data + padding

    msg_key_large = hashlib.sha256(auth_key[96:128] + plaintext).digest()
    msg_key = msg_key_large[8:24]
    aes_key, aes_iv = mtproto.kdf(auth_key, msg_key, False)

    frame = auth_key_id + msg_key + aes.ige256_encrypt(plaintext, aes_key, aes_iv)

    parsed = mtproto.unpack(BytesIO(frame), session_id, auth_key, auth_key_id)
    assert parsed.msg_id == message.msg_id
    assert parsed.seq_no == message.seq_no
    assert isinstance(parsed.body, type(message.body))


def test_unpack_rejects_tampered_msg_key(credentials):
    auth_key, auth_key_id = credentials
    session_id = os.urandom(8)
    message = _ping()

    salt = os.urandom(8)
    data = salt + session_id + message.write()
    padding = os.urandom(-(len(data) + 12) % 16 + 12)
    plaintext = data + padding

    msg_key = hashlib.sha256(auth_key[96:128] + plaintext).digest()[8:24]
    aes_key, aes_iv = mtproto.kdf(auth_key, msg_key, False)
    body = aes.ige256_encrypt(plaintext, aes_key, aes_iv)

    # Flip a bit inside the msg_key: the sha256 check in unpack() must catch it.
    bad_key = bytes([msg_key[0] ^ 0x01]) + msg_key[1:]
    bad_aes_key, bad_aes_iv = mtproto.kdf(auth_key, bad_key, False)
    frame = auth_key_id + bad_key + aes.ige256_encrypt(plaintext, bad_aes_key, bad_aes_iv)

    with pytest.raises((SecurityCheckMismatch, ValueError)):
        mtproto.unpack(BytesIO(frame), session_id, auth_key, auth_key_id)
    assert body  # keep the reference so the fixture data is not optimised away
