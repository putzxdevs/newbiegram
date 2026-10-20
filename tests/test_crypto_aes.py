"""Tests for the AES backends in newbiegram.crypto.aes.

`newbiegram.crypto.aes` resolves to either tgcrypto or the pure-Python pyaes
fallback, so every test here exercises whichever backend is installed. Install
the `fast` extra to cover tgcrypto as well.
"""

import os

from newbiegram.crypto import aes


def test_ige_roundtrip_is_length_preserving():
    """IGE operates on whole 16-byte blocks; MTProto always pads input to a
    multiple of 16, so that is the only shape callers ever pass in."""
    for size in (16, 32, 48, 256):
        data = os.urandom(size)
        key = os.urandom(32)
        iv = os.urandom(32)

        encrypted = aes.ige256_encrypt(data, key, iv)
        assert len(encrypted) == size
        assert aes.ige256_decrypt(encrypted, key, iv) == data


def test_ige_roundtrip_trailing_partial_block():
    """Complete 16-byte blocks round-trip; a trailing partial block is
    zero-padded on the right, because IGE has no padding semantics of its own.

    Regression test for the `xor()` operand-width bug: the short final chunk was
    xored against a full 16-byte AES output using the *chunk* width, which raised
    OverflowError. MTProto never hits this path (it pads to a 16-byte multiple
    and carries the real length in a prefix), but the function must not explode.
    """
    data = b"A" * 48 + b"BCDE"  # 52 bytes -> final chunk is 4 bytes
    key = os.urandom(32)
    iv = os.urandom(32)

    encrypted = aes.ige256_encrypt(data, key, iv)
    assert len(encrypted) == 64  # rounded up to the next block boundary

    decrypted = aes.ige256_decrypt(encrypted, key, iv)
    assert len(decrypted) == 64
    assert decrypted[:48] == data[:48]
    # The partial chunk is right-aligned inside its 16-byte block.
    assert decrypted[48:] == b"\x00" * 12 + b"BCDE"


def test_ige_is_deterministic():
    data = os.urandom(32)
    key = os.urandom(32)
    iv = os.urandom(32)

    assert aes.ige256_encrypt(data, key, iv) == aes.ige256_encrypt(data, key, iv)


def test_ige_changes_output_when_key_changes():
    data = os.urandom(32)
    iv = os.urandom(32)

    assert aes.ige256_encrypt(data, os.urandom(32), iv) != aes.ige256_encrypt(
        data, os.urandom(32), iv
    )


def test_xor_handles_uneven_operands():
    """xor() must take its width from the longer operand, not the first one.

    The final IGE block can be shorter than 16 bytes while the AES output it is
    combined with is not, so `len(a)` alone is not a safe width.
    """
    # Wide first operand: output keeps the full width.
    assert aes.xor(b"\xff" * 16, b"\x00" * 8) == b"\xff" * 16

    # Narrow first operand: the short side is right-aligned and zero-extended,
    # so the leading 8 bytes of the wide operand pass through unchanged.
    assert aes.xor(b"\x0f" * 8, b"\x00" * 16) == b"\x00" * 8 + b"\x0f" * 8
    assert aes.xor(b"\xff" * 8, b"\xff" * 16) == b"\xff" * 8 + b"\x00" * 8


def test_xor_zero_extends_short_operands():
    """Both operands are read as big-endian integers, so a short operand is
    right-aligned against the wider one and the result has the wider length."""
    # Wide first operand: the narrow operand covers the low-order (trailing) bytes.
    assert aes.xor(b"\x00" * 8 + b"\xff" * 8, b"\xff" * 8) == b"\x00" * 16
    assert aes.xor(b"\x12" * 16, b"\x34" * 8) == b"\x12" * 8 + b"\x26" * 8

    # Narrow first operand: the wide operand's high half passes through unchanged.
    assert aes.xor(b"\x0f" * 8, b"\x00" * 16) == b"\x00" * 8 + b"\x0f" * 8
    assert aes.xor(b"\xff" * 8, b"\xff" * 16) == b"\xff" * 8 + b"\x00" * 8


def test_xor_is_involutive_for_equal_lengths():
    a = os.urandom(16)
    b = os.urandom(16)
    assert aes.xor(aes.xor(a, b), b) == a


def test_ctr_is_symmetric_and_advances_the_counter():
    """ctr256_* mutates the caller's counter state in place.

    `state` selects a byte offset within the AES-encrypted counter block and `iv`
    is the big-endian counter that is incremented on wrap, so a multi-block
    stream only round-trips if both are threaded through every call.
    """
    data = os.urandom(64)
    key = os.urandom(32)
    iv = bytearray(os.urandom(16))
    state = bytearray(16)
    iv_before = bytes(iv)

    encrypted = b"".join(
        aes.ctr256_encrypt(data[i : i + 16], key, iv, state) for i in range(0, len(data), 16)
    )
    assert bytes(iv) != iv_before, "counter must advance across blocks"

    # Decryption must start from the counter position used *before* encryption,
    # which is why real callers snapshot the state rather than reusing it.
    iv_dec = bytearray(iv_before)
    state_dec = bytearray(16)
    decrypted = b"".join(
        aes.ctr256_decrypt(encrypted[i : i + 16], key, iv_dec, state_dec)
        for i in range(0, len(encrypted), 16)
    )
    assert decrypted == data
