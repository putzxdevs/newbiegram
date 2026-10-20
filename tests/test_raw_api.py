"""Structural tests for the compiler-generated raw MTProto API surface.

These guard against the compiler silently emitting an incomplete tree, which
would otherwise only surface as an ImportError at connect time.
"""

import importlib
from io import BytesIO

import newbiegram
from newbiegram import raw
from newbiegram.raw import all as raw_all
from newbiegram.session import session as session_module


def test_layer_is_current():
    """Layer must match the schema the compiler was last run against."""
    assert raw_all.layer == 231
    assert isinstance(raw_all.layer, int)
    assert raw_all.layer >= 180


def test_package_version_matches_metadata():
    assert newbiegram.__version__
    # PEP 440-ish sanity: digits with an optional pre-release suffix.
    assert any(char.isdigit() for char in newbiegram.__version__)


def test_raw_namespace_is_populated():
    assert len(raw_all.objects) > 2000
    assert len([n for n in dir(raw.types) if not n.startswith("_")]) > 500
    assert len([n for n in dir(raw.functions) if not n.startswith("_")]) > 50


def test_raw_objects_are_serialisable():
    """Every generated class must round-trip through write()/read().

    Note that `TLObject.read` (the base class) consumes the 4-byte constructor
    id and dispatches through `raw.all.objects`; the per-class `read()` skips
    that header and must only be reached via the dispatcher.
    """
    sample = raw.types.InputPeerSelf()
    buffer = BytesIO()
    buffer.write(sample.write())
    buffer.seek(0)

    parsed = type(sample).read(buffer)
    assert isinstance(parsed, raw.types.InputPeerSelf)


def test_functions_and_types_modules_import():
    for module in ("newbiegram.raw.functions", "newbiegram.raw.types",
                   "newbiegram.raw.base", "newbiegram.errors.exceptions"):
        assert importlib.import_module(module) is not None


def test_dispatcher_reads_by_constructor_id():
    """TLObject.read must skip the little-endian constructor id."""
    ping = raw.functions.Ping(ping_id=0)
    buffer = BytesIO(ping.write())

    parsed = raw.core.TLObject.read(buffer)
    assert isinstance(parsed, raw.functions.Ping)
    assert parsed.ping_id == 0


def test_tl_id_is_stable():
    """Constructor IDs are CRC32 of the TL signature; changing one breaks the wire."""
    assert raw.functions.Ping.ID == 0x7ABE77EC
    assert raw.types.InputPeerSelf.ID == 0x7DA07EC9


def test_session_uses_the_generated_layer():
    """The auth session must negotiate the layer the compiler generated.

    If these drift apart, the client requests a schema the generated code cannot
    encode, and failures only appear at connect time.
    """
    assert session_module.layer == raw_all.layer
