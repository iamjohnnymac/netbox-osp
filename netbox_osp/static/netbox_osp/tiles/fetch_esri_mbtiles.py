#!/usr/bin/env python3
"""Fetch Esri World Imagery tiles for an arbitrary bbox + zoom range and
pack them into a vanilla MBTiles 1.3 SQLite bundle.

Coverage (configure via env vars below):
    bbox    : OSP_BBOX_MIN_LON, OSP_BBOX_MAX_LON, OSP_BBOX_MIN_LAT, OSP_BBOX_MAX_LAT
    zooms   : OSP_ZOOM_MIN through OSP_ZOOM_MAX inclusive (defaults 10..16)
    output  : OSP_OUT_MBTILES (default `imagery.mbtiles` next to this script)
    source  : https://server.arcgisonline.com/ArcGIS/rest/services/
              World_Imagery/MapServer/tile/{z}/{y}/{x}   (note: /z/y/x order,
              tiles are 256x256 JPEG served as image/jpeg)

MBTiles row convention (TMS, origin bottom-left):
    tile_row = (2^z - 1) - y_xyz

Standalone: stdlib + requests only. Re-runnable: INSERT OR REPLACE on the
tiles table, and metadata is rebuilt each run.

Usage:
    OSP_BBOX_MIN_LON=-180 OSP_BBOX_MAX_LON=180 \\
    OSP_BBOX_MIN_LAT=-85  OSP_BBOX_MAX_LAT=85  \\
    OSP_ZOOM_MIN=2 OSP_ZOOM_MAX=5 \\
    python fetch_esri_mbtiles.py
"""
from __future__ import annotations

import math
import os
import sqlite3
import sys
import time
from pathlib import Path

import requests


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _required_env_float(name: str) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        sys.stderr.write(
            f"Environment variable {name} is required. See module docstring.\n"
        )
        raise SystemExit(2)
    return float(raw)


BBOX = {
    "lon_min": _required_env_float("OSP_BBOX_MIN_LON"),
    "lat_min": _required_env_float("OSP_BBOX_MIN_LAT"),
    "lon_max": _required_env_float("OSP_BBOX_MAX_LON"),
    "lat_max": _required_env_float("OSP_BBOX_MAX_LAT"),
}
ZOOM_MIN = int(os.environ.get("OSP_ZOOM_MIN", "10"))
ZOOM_MAX = int(os.environ.get("OSP_ZOOM_MAX", "16"))

TILE_URL_TMPL = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}"
)
USER_AGENT = "netbox-osp tile-fetcher"
REQUEST_DELAY_S = 0.1            # ~10 req/s
REQUEST_TIMEOUT_S = 30
MAX_RETRIES = 3                  # 3 retries on top of the initial attempt

OUT_PATH = Path(
    os.environ.get(
        "OSP_OUT_MBTILES",
        str(Path(__file__).resolve().parent / "imagery.mbtiles"),
    )
)

METADATA_ROWS = {
    "name": "Esri World Imagery (configured bbox)",
    "format": "jpg",
    "bounds": "{lon_min},{lat_min},{lon_max},{lat_max}".format(**BBOX),
    "minzoom": str(ZOOM_MIN),
    "maxzoom": str(ZOOM_MAX),
    "type": "baselayer",
    "version": "1.3",
    "attribution": (
        "Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics,"
        " and the GIS User Community"
    ),
}


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def xy_for(lon: float, lat: float, z: int) -> tuple[int, int]:
    """Slippy/XYZ tile indices for a lon/lat at zoom z. y increases southward."""
    n = 1 << z
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int(
        (1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi)
        / 2.0
        * n
    )
    return x, y


def tile_range_for_bbox(z: int) -> tuple[int, int, int, int]:
    """Return (x_min, x_max, y_min, y_max) inclusive covering BBOX at zoom z.

    Note: lat_max maps to the smaller (more northern) y, lat_min to the larger.
    """
    n = 1 << z
    x_min, y_min = xy_for(BBOX["lon_min"], BBOX["lat_max"], z)
    x_max, y_max = xy_for(BBOX["lon_max"], BBOX["lat_min"], z)
    x_min = max(0, min(n - 1, x_min))
    x_max = max(0, min(n - 1, x_max))
    y_min = max(0, min(n - 1, y_min))
    y_max = max(0, min(n - 1, y_max))
    if x_max < x_min:
        x_min, x_max = x_max, x_min
    if y_max < y_min:
        y_min, y_max = y_max, y_min
    return x_min, x_max, y_min, y_max


# ---------------------------------------------------------------------------
# SQLite / MBTiles helpers
# ---------------------------------------------------------------------------

def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            name  TEXT,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS tiles (
            zoom_level  INTEGER,
            tile_column INTEGER,
            tile_row    INTEGER,
            tile_data   BLOB,
            PRIMARY KEY (zoom_level, tile_column, tile_row)
        );
        """
    )


def reset_metadata(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM metadata")
    conn.executemany(
        "INSERT INTO metadata (name, value) VALUES (?, ?)",
        list(METADATA_ROWS.items()),
    )


# ---------------------------------------------------------------------------
# HTTP fetch with retry/backoff
# ---------------------------------------------------------------------------

def fetch_tile(session: requests.Session, z: int, x: int, y_xyz: int) -> bytes | None:
    """Return tile bytes or None if it cannot be fetched after retries."""
    url = TILE_URL_TMPL.format(z=z, y=y_xyz, x=x)
    backoff = 0.5
    last_err: str | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            r = session.get(url, timeout=REQUEST_TIMEOUT_S)
            if 200 <= r.status_code < 300 and r.content:
                return r.content
            last_err = f"HTTP {r.status_code} ({len(r.content)} bytes)"
        except requests.RequestException as exc:
            last_err = repr(exc)
        if attempt < MAX_RETRIES:
            time.sleep(backoff)
            backoff *= 2
    sys.stdout.write(
        f"\n  SKIP z={z} x={x} y={y_xyz}: {last_err}\n"
    )
    sys.stdout.flush()
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pre_exists = OUT_PATH.is_file()
    print(f"Output : {OUT_PATH}")
    print(f"Bbox   : {BBOX}")
    print(f"Zooms  : {ZOOM_MIN}..{ZOOM_MAX}")
    print(f"Re-run : {'yes (insert or replace)' if pre_exists else 'no (fresh file)'}\n")

    conn = sqlite3.connect(OUT_PATH)
    try:
        ensure_schema(conn)
        reset_metadata(conn)
        conn.commit()

        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})

        per_zoom_counts: dict[int, int] = {}
        per_zoom_failures: dict[int, int] = {}
        total_requested = 0
        total_written = 0

        for z in range(ZOOM_MIN, ZOOM_MAX + 1):
            x_min, x_max, y_min, y_max = tile_range_for_bbox(z)
            nx = x_max - x_min + 1
            ny = y_max - y_min + 1
            count = nx * ny
            total_requested += count
            print(
                f"[z={z}] x={x_min}..{x_max} y={y_min}..{y_max} "
                f"— fetching {count} tiles"
            )
            written_this_zoom = 0
            failed_this_zoom = 0
            for y_xyz in range(y_min, y_max + 1):
                for x in range(x_min, x_max + 1):
                    blob = fetch_tile(session, z, x, y_xyz)
                    if blob is None:
                        failed_this_zoom += 1
                        sys.stdout.write("x")
                    else:
                        tms_y = (1 << z) - 1 - y_xyz
                        conn.execute(
                            "INSERT OR REPLACE INTO tiles "
                            "(zoom_level, tile_column, tile_row, tile_data) "
                            "VALUES (?, ?, ?, ?)",
                            (z, x, tms_y, blob),
                        )
                        written_this_zoom += 1
                        sys.stdout.write(".")
                    sys.stdout.flush()
                    time.sleep(REQUEST_DELAY_S)
                # Commit per row so a Ctrl-C doesn't lose much progress.
                conn.commit()
            sys.stdout.write("\n")
            sys.stdout.flush()
            per_zoom_counts[z] = written_this_zoom
            per_zoom_failures[z] = failed_this_zoom
            total_written += written_this_zoom
            print(
                f"  -> z={z}: wrote {written_this_zoom}/{count} "
                f"(failed {failed_this_zoom})"
            )

        conn.commit()
    finally:
        conn.close()

    size_bytes = OUT_PATH.stat().st_size
    size_mb = size_bytes / (1024 * 1024)

    print("\n=== Summary ===")
    print(f"Total requested : {total_requested}")
    print(f"Total written   : {total_written}")
    print("Per zoom (written / failed):")
    for z in range(ZOOM_MIN, ZOOM_MAX + 1):
        print(
            f"  z={z}: {per_zoom_counts.get(z, 0)} written, "
            f"{per_zoom_failures.get(z, 0)} failed"
        )
    print(f"\nDONE — wrote {OUT_PATH} ({size_mb:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
