"""Reach Forge Printer: read and write Halo: Reach map variants (.mvar).

Phase 1 of docs/REACH_FORGE_PRINTER_PLAN.md. Nothing in the bot imports this.
"""

from .bitstream import BitReader, BitWriter
from .mvar import (
    Author,
    ContentHeader,
    ForgeObject,
    FormatError,
    LabelTable,
    MapVariant,
    MvarFile,
    Quota,
    build_chdr,
    read_chdr,
    stream_hash,
)

__all__ = [
    "Author",
    "BitReader",
    "BitWriter",
    "ContentHeader",
    "ForgeObject",
    "FormatError",
    "LabelTable",
    "MapVariant",
    "MvarFile",
    "Quota",
    "build_chdr",
    "read_chdr",
    "stream_hash",
]
