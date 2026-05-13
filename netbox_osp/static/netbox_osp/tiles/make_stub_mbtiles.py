"""Create a stub MBTiles 1.3 file for the netbox-osp plugin.

This produces a minimal-but-valid MBTiles SQLite database so the tile-proxy
code path can be exercised without shipping the full basemap. The output is
named `basemap.mbtiles` and lives next to this script.

MBTiles 1.3 schema (https://github.com/mapbox/mbtiles-spec/blob/master/1.3/spec.md)
--------------------------------------------------------------------------
Required tables:
  metadata(name TEXT, value TEXT)          -- key/value descriptive fields
  tiles(zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB)

Required metadata rows in this stub:
  name      = "stub"
  format    = "png"
  bounds    = "-180,-90,180,90"
  minzoom   = "0"
  maxzoom   = "0"
  type      = "baselayer"
  version   = "1"

Tile contents:
  One row at (zoom_level=0, tile_column=0, tile_row=0) holding a 1x1
  transparent PNG (the same blank PNG bytes used by the plugin's tile_proxy
  fallback). The tile_row uses the TMS convention (row 0 at the bottom).

Run:
  python make_stub_mbtiles.py
"""

import os
import sqlite3
import sys

# 67-byte 1x1 transparent PNG — identical to the tile_proxy fallback bytes.
BLANK_PNG_1X1 = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
    0x89, 0x00, 0x00, 0x00, 0x0D, 0x49, 0x44, 0x41,
    0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
    0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
    0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
    0x42, 0x60, 0x82,
])

METADATA = [
    ("name", "stub"),
    ("format", "png"),
    ("bounds", "-180,-90,180,90"),
    ("minzoom", "0"),
    ("maxzoom", "0"),
    ("type", "baselayer"),
    ("version", "1"),
]


def build(target_path: str) -> None:
    if os.path.exists(target_path):
        os.remove(target_path)

    conn = sqlite3.connect(target_path)
    try:
        cur = conn.cursor()
        # Schema
        cur.execute(
            "CREATE TABLE metadata (name TEXT, value TEXT)"
        )
        cur.execute(
            "CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER, "
            "tile_row INTEGER, tile_data BLOB)"
        )
        # Uniqueness constraints recommended by spec
        cur.execute(
            "CREATE UNIQUE INDEX name ON metadata (name)"
        )
        cur.execute(
            "CREATE UNIQUE INDEX tile_index ON tiles "
            "(zoom_level, tile_column, tile_row)"
        )
        # Metadata rows
        cur.executemany(
            "INSERT INTO metadata (name, value) VALUES (?, ?)",
            METADATA,
        )
        # Single tile at z=0/x=0/y=0
        cur.execute(
            "INSERT INTO tiles (zoom_level, tile_column, tile_row, tile_data) "
            "VALUES (?, ?, ?, ?)",
            (0, 0, 0, BLANK_PNG_1X1),
        )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "basemap.mbtiles")
    build(out)
    size = os.path.getsize(out)
    print(f"Wrote {out} ({size} bytes)", file=sys.stdout)
