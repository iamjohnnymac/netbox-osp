# netbox-osp

Outside-plant (OSP) fibre management for NetBox: cables, tubes, strands,
splice closures, fibre links with loss-budget calculation, and a
full-screen network map backed by offline MBTiles.

## Quick install

Add the plugin to `local_requirements.txt` (or your equivalent
`plugin_requirements.txt`):

```
netbox-osp
```

Then enable it in `configuration/plugins.py`:

```python
PLUGINS = [
    "netbox_osp",
]

PLUGINS_CONFIG = {
    "netbox_osp": {
        "default_attenuation_db_per_km": 0.22,
        "default_splice_loss_db": 0.10,
        "default_connector_loss_db": 0.30,
        # Default map view. Override with the lat/lon of your area.
        "map_default_center": [0.0, 0.0],
        "map_default_zoom": 2,
    },
}
```

Apply migrations and collect static assets:

```bash
python manage.py migrate
python manage.py collectstatic --no-input
```

NetBox 4.5.x or 4.6.x is required.

## Features

- **OSP Cable / Tube / Strand** — model multi-tube armoured fibre cables
  with TIA-598-C colour-coded tubes and strands.
- **Splice Closure / Tray / Splice** — track field splices with per-splice
  loss and OTDR trace links.
- **Fibre Link with loss budget** — chain strands through splices to form
  an end-to-end logical link with computed strand / splice / connector
  loss, budget percentage, and status band (ok / warn / fail).
- **Network Map** — full-screen Leaflet map showing sites, OSP cables,
  and splice closures filterable by status. Uses leaflet-geoman for
  the cable route editor.
- **Offline tiles** — MBTiles-based tile proxy so the map works on an
  air-gapped OT network. See `docs/tile-bundling.md`.

## Data model

| Model | Purpose |
|-------|---------|
| `OspCable` | A physical fibre cable run between two sites. Stores type, attenuation, GeoJSON route, length. |
| `Tube` | A buffer tube inside an `OspCable`. Unique on `(cable, number)`. |
| `Strand` | A single fibre strand. Optional bridge to `dcim.Cable` via `Strand.cable_link` for legacy strand-as-cable workflows. |
| `SpliceClosure` | A physical splice enclosure (dome, pedestal, etc.) sited at a location with optional GeoJSON point. |
| `SpliceTray` | A tray inside a closure. Holds individual splices. |
| `Splice` | A fusion or mechanical splice joining two strands. |
| `FibreLink` | A logical end-to-end link composed of one or more strands joined by splices, with a configurable loss budget. |
| `FibreLinkStrand` | Through-table assigning strands to a `FibreLink` in ordered hops. |

See [docs/data-model.md](docs/data-model.md) for the full ER overview.

## API endpoints

All endpoints sit under `/api/plugins/osp/`:

| Path | Methods | Notes |
|------|---------|-------|
| `/api/plugins/osp/cables/` | GET / POST / PATCH / DELETE | List + CRUD `OspCable` |
| `/api/plugins/osp/tubes/` | GET / POST / PATCH / DELETE | List + CRUD `Tube` |
| `/api/plugins/osp/strands/` | GET / POST / PATCH / DELETE | List + CRUD `Strand` |
| `/api/plugins/osp/closures/` | GET / POST / PATCH / DELETE | List + CRUD `SpliceClosure` |
| `/api/plugins/osp/trays/` | GET / POST / PATCH / DELETE | List + CRUD `SpliceTray` |
| `/api/plugins/osp/splices/` | GET / POST / PATCH / DELETE | List + CRUD `Splice` |
| `/api/plugins/osp/links/` | GET / POST / PATCH / DELETE | List + CRUD `FibreLink` |

Plus the UI endpoints:

| Path | Purpose |
|------|---------|
| `/plugins/osp/map/` | Full-screen network map (HTML) |
| `/plugins/osp/map/data/` | Map GeoJSON FeatureCollection (filterable) |
| `/plugins/osp/tiles/<z>/<x>/<y>.<ext>` | Tile proxy backed by MBTiles |

## Map tiles

The map uses Leaflet plus a Django view that serves PNG/JPEG/WebP tiles
out of one or more MBTiles files:

1. `<MEDIA_ROOT>/osp_tiles/*.mbtiles` — user-supplied high-resolution
   overlays (search first).
2. `netbox_osp/static/netbox_osp/tiles/basemap.mbtiles` — bundled basemap.

To regenerate the bundled basemap from an OSM extract, see
[docs/tile-bundling.md](docs/tile-bundling.md).

## License

Apache-2.0. See `LICENSE` for the full text.
