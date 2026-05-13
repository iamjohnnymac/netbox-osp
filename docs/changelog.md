# Changelog

All notable changes to `netbox-osp` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Per-release NetBox / Python compatibility lives on the
[Compatibility](compatibility.md) page.

## Unreleased

### Added

- **`FibreTrunk` model** — parent for multi-fibre rack-to-rack physical
  trunks (MPO/MTP 12/24/72-fibre, Ribbon 144-fibre, loose-tube indoor
  runs). Carries `cid`, `trunk_type`, `fibre_count`, `manufacturer`,
  `length_m`, `status` (reuses `OspStatusChoices`), GeoJSON `route` with
  `show_on_map` opt-out, `description`, `comments`, `tenant`, `tags`.
  DB-level `CheckConstraint` on `fibre_count > 0` plus a form-friendly
  validation. New `TrunkTypeChoices` palette with a per-type
  `DEFAULT_FIBRE_COUNT` mapping for follow-up auto-fill.
- **REST CRUD** under `/api/plugins/osp/trunks/`.
- **GraphQL** — `osp_fibre_trunk` and `osp_fibre_trunk_list` queries.
- **Admin chrome** — list / add / edit / delete / bulk-edit /
  bulk-delete / bulk-import / changelog views, table, filter form,
  sidebar entry under a new "Trunks" group, search-index registration.
- **Tests** — `tests/test_fibretrunk.py` covering `__str__`, defaults,
  `clean()`, tagging, REST CRUD, and GraphQL module-level exposure.
- **`TrunkBreakout` through-table** bridging `FibreTrunk` to NetBox's
  native `dcim.Cable`. Captures the trunk-with-breakouts pattern:
  "24F MTP trunk → 12F breakout to rack A + 12F breakout to rack B" as
  one entity. `trunk` FK (CASCADE), `cable` FK (PROTECT),
  1-indexed `fibre_range_start` / `fibre_range_end`, two
  `unique_together` to prevent double-allocation, and field-keyed
  `clean()` rejecting overflow and sibling overlap.
- **`FibreTrunk.clean()`** now enforces sum-of-children ≤ `fibre_count`.
- **`FibreTrunk.fibres_used` / `fibres_remaining` / `fibres_utilization_pct`**
  computed properties.
- **"Import from cables" wizard** at
  `/plugins/osp/trunks/<trunk_id>/import-cables/` — atomic multi-select
  bind of unbound `dcim.Cable`s to fibre ranges.
- **REST + GraphQL** for `TrunkBreakout`.
- **CSV bulk import** keyed by `trunk_cid` + `cable_label`.
- **MTP harness one-click deploy form** at
  `/plugins/osp/trunks/deploy-harness/` — a single form submit creates
  the parent `FibreTrunk` + N cassette `dcim.Device`s + N
  `dcim.Cable`s + N `TrunkBreakout` rows atomically. Two-step
  preview/confirm flow uses `django.core.signing.dumps`
  (base64-encoded, HTML-safe) for the state token. Replaces ~30
  individual NetBox object writes with one form.
- **Bundled cassette catalogue** — five `DeviceType` JSON templates at
  `netbox_osp/device_types/cassettes/` covering the standard MPO/MTP
  fibre-cassette and LC patch-panel shapes that pair with the MTP
  harness deploy form: `mpo-12f-lc-cassette`, `mpo-24f-lc-cassette`,
  `mpo-12f-mpo-cassette`, `lgx-lc-12f-panel`, `ru1-lc-24f-panel`.
  Files follow the `netbox-community/devicetype-library` schema.
- **`load_osp_cassettes` management command** — seeds all five
  cassettes idempotently:

      python manage.py load_osp_cassettes

  Slug-keyed `update_or_create`, atomic per cassette, materialises
  `RearPortTemplate` + `FrontPortTemplate` + `PortTemplateMapping`
  rows. `--dry-run` flag for safe inspection.
- **Visual core tracer** (PR E) — click "Trace this core" on a `Strand`,
  `dcim.FrontPort`, or `dcim.Interface` detail page to render an
  end-to-end fibre path as a clickable dagre-d3 graph. Each hop —
  interface, patch cord, cassette pass-through, MPO/MTP trunk, splice,
  OSP strand — shows inline loss + length; the summary band above the
  graph shows total dB used against the strand's parent FibreLink
  budget (or a configurable default), colour-coded `ok` / `warn` /
  `fail`. New JSON endpoint at
  `GET /api/plugins/osp/cores/<strand_id>/trace/` returns the hop list
  for external tooling. dagre-d3 v0.6.4 (~700 KB minified) ships
  vendored in `static/netbox_osp/js/dagre-d3.min.js`. Three new
  `PluginTemplateExtension` subclasses inject the trace button onto
  `dcim.Interface`, `dcim.FrontPort`, and netbox-osp `Strand` detail
  pages. New optional config keys under `PLUGINS_CONFIG["netbox_osp"]`:
  `default_cassette_loss_db` (0.5), `default_patch_cord_loss_db` (0.1),
  `default_loss_budget_db` (8.0). Zero new migrations — the tracer is
  read-only over the existing data model.

The `0.2.0` release tag fires once all five v0.2 PRs land. This entry
documents PRs A, B, C, D, and E. All five v0.2 features
landed; v0.2.0 is ready to tag.

## 0.1.1 — 2026-05-13

### Fixed

- Corrected author / maintainer name in package metadata, `PluginConfig`,
  `mkdocs.yml` copyright, and the icon SVG copyright comment from
  "John McKenzie" to "John McKean". 0.1.0 shipped with the wrong
  spelling and PyPI does not permit re-uploading a published version,
  so this metadata-only patch ships the correction.

## 0.1.0 — 2026-05-13

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
  models will be added in a focused follow-up. REST `APIViewTestCase`
  permission tests are deferred until CI wires `API_TOKEN_PEPPERS`.

## 0.0.1 — 2026-05-13

- PyPI name-reservation placeholder. Not functional.
