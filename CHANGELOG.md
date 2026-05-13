# Changelog

All notable changes to `netbox-osp` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Per-release NetBox / Python compatibility lives in
[COMPATIBILITY.md](COMPATIBILITY.md).

## [Unreleased]

## [0.1.0] — 2026-05-13

First functional release. Covers the full OSP fibre data model, the
interactive plant map with online + offline base layers, REST + GraphQL
APIs, bulk-import / bulk-edit, plant-boundary validation, and per-Location
GPS markers.

### Added

- **Data model** — `OspCable`, `Tube`, `Strand`, `SpliceClosure`,
  `SpliceTray`, `Splice`, `FibreLink`, `FibreLinkStrand`, `LocationGeo`
  with TIA-598-C auto-colours, capacity / utilisation accounting, and the
  `fibre_count == tube_count × fibres_per_tube` invariant enforced in
  `clean()`.
- **Fibre-link loss budget** — strand attenuation × length + per-splice
  loss + per-connector loss, with ok / warn / fail band against a
  configurable target. SVG gauge bar rendered on the FibreLink detail
  page.
- **Network map** — full-screen Leaflet at `/plugins/osp/map/`, filterable
  by status, with 7 online base layers (OSM, HOT OSM, CartoDB Positron /
  Dark Matter, OpenTopoMap, CyclOSM, Esri World Imagery) plus a bundled
  offline MBTiles bundle. Auto-falls back to offline after three tile
  errors within five seconds. User's explicit choice persists across
  reloads via `localStorage`.
- **GeoJSON cable-route editor** — leaflet-geoman drag-to-edit with the
  same base-layer machinery as the main map.
- **Plant-boundary trace tool** — operator drags vertices to draw the
  plant outline; exports a `[lon, lat]` coordinate list for the
  `plant_boundary` setting.
- **Optional plant-boundary validation** — set `PLUGINS_CONFIG['netbox_osp']
  ['plant_boundary']` and `OspCable.clean()` rejects any cable whose
  `route` falls outside the polygon. Pure-Python ray-casting; no PostGIS
  required.
- **Per-Location GPS markers (`LocationGeo`)** — 1:1 side-table on
  `dcim.Location` adding `latitude` / `longitude` / `elevation_m` /
  `marker_color`. Rendered as `L.circleMarker` overlay on the map and
  injected as a panel on the `dcim.Location` detail page.
- **Bulk-import / bulk-edit forms** for `Tube`, `Strand`, `Splice`,
  `SpliceTray`, `SpliceClosure`, and `LocationGeo` — closes a ~300-click
  data-entry gap for a 288-strand cable.
- **GraphQL types** for all nine plugin models via `strawberry-django`,
  registered with NetBox's `/graphql/` endpoint.
- **REST API** under `/api/plugins/osp/...` with full CRUD on every
  model, filter-sets aligned with the UI list views.
- **Offline-first tile proxy** at `/plugins/osp/tiles/<z>/<x>/<y>.<ext>`
  serving PNG / JPEG / WebP tiles from one or more MBTiles files, with
  per-tile `ETag` + `304 Not Modified` and transparent-PNG fallback for
  missing tiles.
- **Permission-matrix tests** — auto-generated coverage of GET / list /
  create / edit / delete and their bulk variants for the SpliceClosure
  view set (canary; remaining seven models follow a known pattern).
- **MkDocs Material docs site** at <https://iamjohnnymac.github.io/netbox-osp/>.

### Infrastructure

- Public GitHub repo with PyPI Trusted Publishing via OIDC (no API
  tokens).
- CI matrix: Python 3.12 / 3.13 × NetBox 4.6 on Postgres 17 + Redis 7.
- `mkdocs.yml` + GitHub Pages auto-deploy on every `main` push.
- `.pre-commit-config.yaml` with `ruff` (lint + format), configured to
  match the NetBox plugin ecosystem.
- Apache-2.0 license.

### Known limitations

- GraphQL schema registers cleanly but `osp_<model>_list` query fields
  don't surface in the merged global `Query` yet — being debugged
  against a live `/graphql/` endpoint. REST API is fully functional in
  the meantime.
- Permission-matrix tests cover the SpliceClosure canary; the remaining
  primary-object view sets will be added in a focused follow-up. REST
  `APIViewTestCase` permission tests are deferred until CI wires
  `API_TOKEN_PEPPERS`.

## [0.0.1] — 2026-05-13

- PyPI name-reservation placeholder. Not functional.

[Unreleased]: https://github.com/iamjohnnymac/netbox-osp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/iamjohnnymac/netbox-osp/releases/tag/v0.1.0
[0.0.1]: https://github.com/iamjohnnymac/netbox-osp/releases/tag/v0.0.1
