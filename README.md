# netbox-osp

<div align="center">

<img src="https://raw.githubusercontent.com/iamjohnnymac/netbox-osp/main/icon.svg" alt="netbox-osp" width="96" height="96" />

**Outside-plant fibre management for NetBox — cables, splice closures, loss budgets,
and an offline-capable plant map.**

[![PyPI version](https://img.shields.io/pypi/v/netbox-osp.svg)](https://pypi.org/project/netbox-osp/)
[![Python versions](https://img.shields.io/pypi/pyversions/netbox-osp.svg)](https://pypi.org/project/netbox-osp/)
[![NetBox 4.6](https://img.shields.io/badge/NetBox-4.6-orange)](https://github.com/netbox-community/netbox)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Tests](https://github.com/iamjohnnymac/netbox-osp/actions/workflows/test.yml/badge.svg)](https://github.com/iamjohnnymac/netbox-osp/actions/workflows/test.yml)
[![Docs](https://img.shields.io/badge/docs-mkdocs--material-blue)](https://iamjohnnymac.github.io/netbox-osp/)
[![Demo walkthrough](https://img.shields.io/badge/demo-walkthrough-purple)](https://iamjohnnymac.github.io/netbox-osp/demo/)

</div>

Outside-plant (OSP) fibre management for NetBox. `netbox-osp` extends NetBox's `dcim` models
with a full OSP data model — cables, buffer tubes, strands, splice closures, trays, and end-to-end
fibre links — and pairs it with a full-screen interactive plant map. The plugin is offline-first
(no PostGIS, no upstream tile servers required), applies TIA-598-C colour ordering automatically,
and computes a per-link loss budget so operators can see at a glance whether a span meets its
attenuation target.

## Screenshots

<div align="center">

<img src="https://raw.githubusercontent.com/iamjohnnymac/netbox-osp/main/docs/screenshots/network_map.png" alt="Full-screen network map with cables, splice closures, and Location GPS markers" width="800" />

<sub><em>Full-screen Leaflet plant map at <code>/plugins/osp/map/</code> — OSP cables, splice closures, Sites, and per-Location markers all filterable.</em></sub>

<img src="https://raw.githubusercontent.com/iamjohnnymac/netbox-osp/main/docs/screenshots/mtp_harness_deploy.png" alt="One-click MTP harness deploy form" width="800" />

<sub><em>One form submit atomically deploys a parent FibreTrunk + N cassette devices + N cables + N TrunkBreakout rows.</em></sub>

<img src="https://raw.githubusercontent.com/iamjohnnymac/netbox-osp/main/docs/screenshots/core_tracer.png" alt="Visual core tracer end-to-end fibre path with per-hop loss" width="800" />

<sub><em>Click "Trace this core" on any Strand / FrontPort / Interface. Each hop is clickable; loss budget banded ok/warn/fail above the graph.</em></sub>

</div>

## Features

- **OSP cable / tube / strand data model** — multi-tube armoured cables with TIA-598-C
  colour-coded tubes and strands. The `fibre_count == tube_count * fibres_per_tube`
  invariant is enforced in `clean()`.
- **Splice closures, trays, and splices** — model dome / inline / pedestal / handhole /
  wall-mount / aerial closures, with measured per-splice loss and OTDR trace links.
- **Fibre-link loss budget** — chain strands through splices into an end-to-end logical
  link. The plugin computes strand attenuation × length + per-splice + per-connector loss,
  renders an SVG gauge, and bands the result as **ok / warn / fail** against a configurable
  target budget.
- **Full-screen Leaflet map** with seven online base layers (OSM, HOT OSM, CartoDB Positron
  and Dark Matter, OpenTopoMap, CyclOSM, Esri World Imagery) plus a bundled offline MBTiles
  layer. The map auto-falls-back to offline after three tile errors in five seconds and
  remembers the operator's explicit choice across reloads.
- **GeoJSON cable-route editor** — leaflet-geoman drag-to-edit on cables and closures,
  sharing the same base-layer machinery as the main map.
- **Plant-boundary validation** — set a closed polygon in `PLUGINS_CONFIG` and
  `OspCable.clean()` rejects any cable whose route falls outside it. Pure-Python
  ray-casting, no PostGIS dependency.
- **Per-Location GPS markers** — `LocationGeo` is a 1:1 side-table on `dcim.Location`
  that adds latitude / longitude / elevation / marker colour, rendered as overlays on
  the network map and as a panel on the Location detail page.
- **REST + GraphQL APIs** — full CRUD on every model under `/api/plugins/osp/...` plus
  read-only GraphQL types via `strawberry-django` at NetBox's shared `/graphql/` endpoint.
- **Bulk import / bulk edit** for tubes, strands, splices, trays, closures, and
  LocationGeo — closes the ~300-click data-entry gap on a 288-strand cable.
- **NetBox 4.6+** with a CI matrix covering Python 3.12 and 3.13 on Postgres 17 + Redis 7.

## Compatibility

| netbox-osp | NetBox | Python      | Postgres | Redis | Notes                     |
|------------|--------|-------------|----------|-------|---------------------------|
| 0.1.x      | 4.6.x  | 3.12 · 3.13 | 17       | 7     | First functional release. |

PostGIS is **not** required — geometry is stored as GeoJSON in `JSONField` columns and
plant-boundary validation uses pure-Python ray-casting. See [COMPATIBILITY.md](COMPATIBILITY.md)
for the full support policy, NetBox / Python / Postgres version policies, and upgrade-path
guidance.

## Install

### From PyPI

The recommended path for production installs:

```bash
pip install netbox-osp
```

Enable the plugin in NetBox's `configuration/plugins.py`:

```python
PLUGINS = [
    "netbox_osp",
]
```

Apply migrations and collect static assets:

```bash
python manage.py migrate
python manage.py collectstatic --no-input
```

Restart NetBox and the RQ workers.

### From source (development)

```bash
git clone https://github.com/iamjohnnymac/netbox-osp.git
cd netbox-osp
pip install -e .
```

Then follow the same `PLUGINS` / migrate / collectstatic steps above.

### With netbox-docker

Add the plugin to `plugin_requirements.txt`:

```text
netbox-osp
```

Enable it in `configuration/plugins.py`:

```python
PLUGINS = [
    "netbox_osp",
]

PLUGINS_CONFIG = {
    "netbox_osp": {
        "default_attenuation_db_per_km": 0.22,
        "default_splice_loss_db": 0.10,
        "default_connector_loss_db": 0.30,
        "map_default_center": [0.0, 0.0],
        "map_default_zoom": 2,
    },
}
```

Rebuild and restart the `netbox` and `netbox-worker` containers.

See [docs/install.md](docs/install.md) for the complete walk-through.

## Configuration

All settings live under `PLUGINS_CONFIG["netbox_osp"]`:

```python
PLUGINS_CONFIG = {
    "netbox_osp": {
        # Fallback attenuation when an OspCable has no explicit value.
        "default_attenuation_db_per_km": 0.22,

        # Fallback per-splice loss when a Splice has no explicit loss_db.
        "default_splice_loss_db": 0.10,

        # Per-connector loss applied at both ends of every FibreLink.
        "default_connector_loss_db": 0.30,

        # Default Leaflet view as [lat, lon]. Set to your area of interest.
        "map_default_center": [0.0, 0.0],

        # Default Leaflet zoom level. 13-16 is appropriate for site scale.
        "map_default_zoom": 2,

        # Optional closed polygon of [lon, lat] vertices (GeoJSON order).
        # If set, OspCable.clean() rejects any cable whose route falls
        # outside the polygon. Pure-Python ray-casting; no PostGIS needed.
        # "plant_boundary": [
        #     [10.000, 50.000],
        #     [10.010, 50.000],
        #     [10.010, 50.010],
        #     [10.000, 50.010],
        # ],
    },
}
```

| Key                             | Default      | Purpose                                                                 |
|---------------------------------|--------------|-------------------------------------------------------------------------|
| `default_attenuation_db_per_km` | `0.22`       | Fallback attenuation when an `OspCable` has no explicit value.          |
| `default_splice_loss_db`        | `0.10`       | Fallback per-splice loss when a `Splice` has no explicit `loss_db`.     |
| `default_connector_loss_db`     | `0.30`       | Per-connector loss applied at both ends of every `FibreLink`.           |
| `map_default_center`            | `[0.0, 0.0]` | `[lat, lon]` for the default map view.                                  |
| `map_default_zoom`              | `2`          | Default Leaflet zoom level (13–16 is appropriate for site scale).       |
| `plant_boundary`                | `None`       | Optional closed `[lon, lat]` polygon. Validates `OspCable.route`.       |

See [docs/configure.md](docs/configure.md) for deeper docs on plant-boundary validation,
per-Location GPS markers, and GraphQL.

## Ecosystem integrations

`netbox-osp` composes with the wider NetBox plugin ecosystem rather than reinventing it.
Each integration below is **optional** — the plugin runs fine without any of them.

- **[netbox-attachments](https://github.com/Kani999/netbox-attachments)** — attach OTDR
  `.sor` traces, splice photos, as-built drawings, and acceptance certificates to any
  OSP model. Install with `pip install netbox-osp[attachments] netbox-attachments` and
  add a `scope_filter` block to `PLUGINS_CONFIG`.

See [docs/integrations.md](docs/integrations.md) for the full configuration snippets,
use-case matrix, and verification steps.

## Data model

All geometry is stored as GeoJSON in WGS84 with `[lon, lat]` order (RFC 7946). Conversion
to Leaflet's `[lat, lon]` happens at the JS boundary only.

```
dcim.Site                                       dcim.Manufacturer
  |  |                                                |
  |  +--< OspCable >-----------< Tube >-----< Strand --+
  |          (route GeoJSON)         |          |
  |                                  +--------- |
  |                                             +--> dcim.Cable
  |                                             |    (Strand.cable_link, optional)
  |                                             |
  +--< SpliceClosure >--< SpliceTray >--< Splice >--+
            (Point)                       (strand_a, strand_b)

  FibreLink >--< FibreLinkStrand >--< Strand
        (loss budget, status)         (ordered hops)
```

| Model              | Purpose                                                                                                            |
|--------------------|--------------------------------------------------------------------------------------------------------------------|
| `OspCable`         | A physical fibre cable run between two sites. Stores type, attenuation, GeoJSON route, and length.                 |
| `Tube`             | A buffer tube inside an `OspCable`. Unique on `(cable, number)`.                                                   |
| `Strand`           | A single fibre strand. Optional bridge to `dcim.Cable` via `Strand.cable_link` for legacy strand-as-cable flows.   |
| `SpliceClosure`    | A physical splice enclosure (dome, pedestal, etc.) sited at a location with optional GeoJSON point.                |
| `SpliceTray`       | A tray inside a closure. Holds individual splices.                                                                 |
| `Splice`           | A fusion or mechanical splice joining two strands. Stores measured `loss_db` and an optional OTDR trace URL.       |
| `FibreLink`        | A logical end-to-end link composed of one or more strands joined by splices, with a configurable loss budget.      |
| `FibreLinkStrand`  | Through-table assigning strands to a `FibreLink` in ordered hops.                                                  |
| `LocationGeo`      | 1:1 side-table on `dcim.Location` adding latitude / longitude / elevation / marker colour for per-Location pins.   |

See [docs/data-model.md](docs/data-model.md) for the field-by-field reference.

## API

### REST

All endpoints sit under `/api/plugins/osp/`. Standard NetBox auth (`Authorization: Token <key>`)
and filtering / pagination apply.

| Path                                | Methods                     | Notes                       |
|-------------------------------------|-----------------------------|-----------------------------|
| `/api/plugins/osp/cables/`          | GET / POST / PATCH / DELETE | List + CRUD `OspCable`      |
| `/api/plugins/osp/tubes/`           | GET / POST / PATCH / DELETE | List + CRUD `Tube`          |
| `/api/plugins/osp/strands/`         | GET / POST / PATCH / DELETE | List + CRUD `Strand`        |
| `/api/plugins/osp/closures/`        | GET / POST / PATCH / DELETE | List + CRUD `SpliceClosure` |
| `/api/plugins/osp/trays/`           | GET / POST / PATCH / DELETE | List + CRUD `SpliceTray`    |
| `/api/plugins/osp/splices/`         | GET / POST / PATCH / DELETE | List + CRUD `Splice`        |
| `/api/plugins/osp/links/`           | GET / POST / PATCH / DELETE | List + CRUD `FibreLink`     |
| `/api/plugins/osp/location-geos/`   | GET / POST / PATCH / DELETE | List + CRUD `LocationGeo`   |

### GraphQL

Types are registered with NetBox's shared `/graphql/` endpoint and authenticate with the same
API token as REST.

```graphql
{
  osp_cable_list {
    id
    cid
    status
    fibre_count
    length_m
  }
}
```

The schema is read-only — use REST for writes.

### UI endpoints

| Path                                       | Purpose                                  |
|--------------------------------------------|------------------------------------------|
| `/plugins/osp/map/`                        | Full-screen network map (HTML)           |
| `/plugins/osp/map/data/`                   | Map GeoJSON FeatureCollection (filterable) |
| `/plugins/osp/tiles/<z>/<x>/<y>.<ext>`     | Tile proxy backed by MBTiles             |

## Map tiles

The plant map uses Leaflet with seven public online base layers plus a bundled offline MBTiles
layer, and auto-falls-back to offline after three tile-load failures in five seconds. To replace
the bundled stub with your own area's imagery, drop one or more `.mbtiles` files under
`<MEDIA_ROOT>/osp_tiles/` — they take precedence over the bundled basemap. See
[docs/tile-bundling.md](docs/tile-bundling.md) for the `tilemaker`-based build workflow.

## Development

```bash
git clone https://github.com/iamjohnnymac/netbox-osp.git
cd netbox-osp
pip install -e ".[test,docs]"
pre-commit install
```

Run the lint + format check and the test suite:

```bash
pre-commit run --all-files
python -m coverage run -m pytest
```

Ruff (lint + format) is configured in `pyproject.toml` to match the wider NetBox plugin
ecosystem; the pre-commit hook runs it on every commit.

## Roadmap

- **Short-term** — extend the permission-matrix tests to the remaining seven primary-object view
  sets, finish debugging the GraphQL `osp_<model>_list` field surfacing against a live `/graphql/`
  endpoint.
- **Medium-term** — OTDR trace upload, DWDM channel allocation on `FibreLink`, QGIS-friendly
  export of cable routes.
- **Long-term** — optional PostGIS backend for users who want native spatial indexes, and
  submission to the NetBox Labs Plugin Certification Program.

Issue tracker for the live picture: <https://github.com/iamjohnnymac/netbox-osp/issues>.

## Contributing

PRs welcome. Please run `pre-commit run --all-files` and ensure the test suite passes before
pushing, and keep new code aligned with the ruff config in `pyproject.toml`. Substantive
changes should add or update tests under `netbox_osp/tests/`. A formal `CONTRIBUTING.md` will
land alongside the first cert-program submission.

## Support

- **Bug reports** — <https://github.com/iamjohnnymac/netbox-osp/issues>
- **Questions and discussion** — <https://github.com/iamjohnnymac/netbox-osp/discussions>
- **Chat** — `#netbox-plugins` on [NetDev Slack](https://netdev.chat/)

## License

Apache-2.0. See [LICENSE](LICENSE) for the full text. Icon CC BY 4.0.
