# Changelog

All notable changes to `netbox-osp` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Per-release NetBox / Python compatibility lives in
[COMPATIBILITY.md](COMPATIBILITY.md).

## [Unreleased]

### Added

- **netbox-attachments integration** — documented `scope_filter`
  configuration for [netbox-attachments](https://github.com/Kani999/netbox-attachments)
  covering all 10 OSP models (`OspCable`, `Tube`, `Strand`, `Splice`,
  `SpliceClosure`, `SpliceTray`, `FibreLink`, `FibreTrunk`,
  `TrunkBreakout`, `LocationGeo`). Operators can now attach OTDR
  `.sor` traces, splice photos, as-built PDFs, and acceptance-test
  certificates to any OSP record. Install with `pip install
  netbox-osp[attachments] netbox-attachments`. Zero plugin code — pure
  composition via the upstream `scope_filter` setting. See
  `docs/integrations.md`. Sets up the file-storage layer that the
  upcoming v0.3.5 OTDR moat work will read `.sor` files from.

## [0.2.2] — 2026-05-18

### Docs

- README screenshots now use absolute `raw.githubusercontent.com` URLs
  so they render inline on the PyPI project page (relative `docs/`
  paths in the previous releases pointed at files PyPI doesn't bundle).
- Added an 8-step **demo walkthrough** at `/demo/` on the docs site
  with 10 screenshots captured live from the public demo, covering
  the OSP model, splice closures, loss-budget gauge, MTP harness
  deploy form, visual core tracer, and the plant map.
- README gains a "demo walkthrough" badge linking to the new page.
- No code changes — `pip install -U netbox-osp` is metadata-only.

## [0.2.1] — 2026-05-14

### Fixed

- Visual core tracer (introduced in 0.2.0) rendered an empty Path graph
  because `dagre-d3.min.js` declares an external `d3` dependency rather
  than inlining it. The loss-budget band and hop legend rendered fine
  but the graph itself stayed blank with "Renderer JS not loaded".
  Vendored `d3.v5.min.js` alongside the dagre-d3 bundle and added the
  `<script>` tag in `strand_tracer.html` ahead of dagre-d3.

## [0.2.0] — 2026-05-13

Five-PR cycle adding inter-rack fibre infrastructure: MPO/MTP trunks
with breakouts to cassettes, one-click harness deploy, cassette
device-type catalogue, and an end-to-end visual core tracer.

### Added

- **`FibreTrunk` model** — parent for multi-fibre rack-to-rack physical
  trunks (MPO/MTP 12/24/72-fibre, Ribbon 144-fibre, loose-tube indoor
  runs). Carries `cid`, `trunk_type`, `fibre_count`, `manufacturer`,
  `length_m`, `status` (reuses `OspStatusChoices`), GeoJSON `route` with
  `show_on_map` opt-out, `description`, `comments`, `tenant`, `tags`.
  DB-level `CheckConstraint` on `fibre_count > 0` plus a form-friendly
  validation surfacing the same on the `fibre_count` field. New
  `TrunkTypeChoices` palette (`mpo-12`, `mpo-24`, `mpo-72`,
  `ribbon-144`, `loose-tube-n`, `other`) with a per-type
  `DEFAULT_FIBRE_COUNT` mapping ready for a follow-up auto-fill.
- **REST CRUD** under `/api/plugins/osp/trunks/` (full serializer,
  viewset, filter-set, router registration).
- **GraphQL** — `osp_fibre_trunk` and `osp_fibre_trunk_list` queries
  via the new `FibreTrunkType` / `FibreTrunkFilter`.
- **Admin chrome** — list / add / edit / delete / bulk-edit /
  bulk-delete / bulk-import / changelog views, table with status +
  trunk-type colour columns, filter form, sidebar entry under a new
  "Trunks" group with Add + Import buttons, search-index registration.
- **Tests** — `tests/test_fibretrunk.py` covering `__str__`, defaults,
  `clean()` (fibre_count guard and GeoJSON shape), tagging, REST CRUD
  with auth, and GraphQL module-level exposure.
- **`TrunkBreakout` through-table** bridging `FibreTrunk` to NetBox's
  native `dcim.Cable`. Captures the trunk-with-breakouts pattern:
  operators express "24F MTP trunk → 12F breakout to rack A + 12F
  breakout to rack B" as one cohesive entity with the trunk identity
  preserved across child cables. Fields: `trunk` FK
  (CASCADE), `cable` FK (PROTECT), `fibre_range_start` / `fibre_range_end`
  (1-indexed `PositiveSmallIntegerField`), `description`, `tags`.
  `CheckConstraint`s enforce `start >= 1` and `end >= start`; two
  `unique_together` (`trunk, cable` and `trunk, fibre_range_start`)
  catch double-allocation. `clean()` rejects ranges that exceed parent
  `fibre_count` or overlap a sibling breakout — all field-keyed.
- **`FibreTrunk.clean()`** now enforces sum of child-breakout ranges ≤
  `fibre_count` (the PR-A `# TODO(PR-B)` marker is wired up).
- **`FibreTrunk.fibres_used` / `fibres_remaining` / `fibres_utilization_pct`**
  computed properties feed the admin table's utilisation column.
- **"Import from cables" wizard** at
  `/plugins/osp/trunks/<trunk_id>/import-cables/` — multi-select unbound
  `dcim.Cable`s and assign fibre ranges atomically. All-or-nothing via
  `transaction.atomic()`; surfaces both `ValidationError` and
  `IntegrityError` race-loser collisions as form errors.
- **REST + GraphQL** for `TrunkBreakout`: CRUD at
  `/api/plugins/osp/trunk-breakouts/`, GraphQL `osp_trunk_breakout` and
  `osp_trunk_breakout_list` queries via `FibreTrunkBreakoutType` /
  `FibreTrunkBreakoutFilter`.
- **Admin chrome for `TrunkBreakout`** — list / add / edit / delete /
  bulk-edit / bulk-delete / bulk-import / changelog views, table with
  parent-trunk + cable + range columns, filter form, "Trunk Breakouts"
  sidebar entry under the existing Trunks group, search-index
  registration.
- **CSV bulk import** — `trunk_cid,cable_label,fibre_range_start,fibre_range_end`
  with friendly errors on ambiguous / missing cable labels.
- **Tests** — `tests/test_trunkbreakout.py` (31 cases) covering model
  `clean()` field-keyed errors, `unique_together` enforcement,
  `FibreTrunk` utilisation arithmetic, REST CRUD with auth, GraphQL
  surface, and the import-cables wizard view (GET, POST happy path,
  POST validation failure). Import-form tests added to
  `tests/test_imports.py`.
- **MTP harness one-click deploy form** at
  `/plugins/osp/trunks/deploy-harness/` — a single form submit creates
  the parent `FibreTrunk` + N cassette `dcim.Device`s + N
  `dcim.Cable`s linking the source patch-panel RearPort to each new
  cassette's RearPort + N `TrunkBreakout` rows binding the cables to
  the trunk at chosen fibre ranges. Atomic — the whole batch rolls
  back if any row fails validation. Two-step preview/confirm flow uses
  `django.core.signing.dumps` (base64-encoded, HTML-safe) to
  round-trip the cleaned form state safely between the preview and
  confirm POST steps with a 600s expiry. Sidebar entry under the
  existing "Trunks" group plus a green button on the FibreTrunk detail
  page next to "Add Breakout" / "Import from Cables". New plugin
  setting `default_cable_type` (default `"smf"`). Exception ladder
  mirrors PR B's import wizard: `ValidationError` → form-keyed errors,
  `IntegrityError` → race-condition message, `AbortRequest` →
  cable-path-impossible message. Tests in `tests/test_mtp_harness.py`
  cover GET auth, N=2 / N=3 happy paths, overlap rollback,
  missing-rack rollback, fibre-sum overflow, duplicate-rack rejection,
  preview-then-confirm round-trip, and permission denial.
- **Bundled cassette catalogue** — five `DeviceType` JSON templates at
  `netbox_osp/device_types/cassettes/` covering the standard MPO/MTP
  fibre-cassette and LC patch-panel shapes that pair with the MTP
  harness deploy form: `mpo-12f-lc-cassette` (1× MPO-12 rear → 12× LC),
  `mpo-24f-lc-cassette` (1× MPO-24 rear → 24× LC),
  `mpo-12f-mpo-cassette` (MPO pass-through), `lgx-lc-12f-panel`
  (1U LGX), `ru1-lc-24f-panel` (1U 24F with 2× MPO-12 rears). JSON
  follows the `netbox-community/devicetype-library` schema (hyphenated
  `rear-ports` / `front-ports` keys), so the same files import via the
  upstream loader too.
- **`load_osp_cassettes` management command** — `python manage.py
  load_osp_cassettes` seeds all five cassettes into the live DB.
  Idempotent (slug-keyed `update_or_create`), wraps each cassette in
  one `transaction.atomic()`, materialises `RearPortTemplate` +
  `FrontPortTemplate` + `PortTemplateMapping` rows with `front`-to-
  `rear` pin maps preserved. Ships a `--dry-run` flag for safe
  inspection.
- **Cassette tests** — `tests/test_cassettes.py` covering JSON
  validity, required-key presence, cross-reference integrity (every
  `rear_port` referent exists, every `rear_port_position` is within
  bounds), management-command happy-path + idempotency contract, a
  spot check on the MPO-12F-LC port-template materialisation, and a
  forbidden-token guard so operator-site names never bake into the
  generic catalogue.

- **Visual core tracer** (PR E) — click "Trace this core" on a `Strand`,
  `dcim.FrontPort`, or `dcim.Interface` detail page to render an
  end-to-end fibre path as a clickable dagre-d3 graph. Each hop —
  interface, patch cord, cassette pass-through, MPO/MTP trunk, splice,
  OSP strand — shows inline loss + length; the summary band above the
  graph shows total dB used against the strand's parent FibreLink
  budget (or a configurable default), colour-coded `ok` / `warn` /
  `fail`. New JSON endpoint at `GET
  /api/plugins/osp/cores/<strand_id>/trace/` returns the hop list for
  external tooling. dagre-d3 v0.6.4 (~700 KB minified) ships vendored
  in `static/netbox_osp/js/dagre-d3.min.js`. Three new
  `PluginTemplateExtension` subclasses inject the trace button onto
  `dcim.Interface`, `dcim.FrontPort`, and netbox-osp `Strand` detail
  pages. New optional config keys under `PLUGINS_CONFIG["netbox_osp"]`:
  `default_cassette_loss_db` (0.5), `default_patch_cord_loss_db` (0.1),
  `default_loss_budget_db` (8.0). Zero new migrations — the tracer is
  read-only over the existing data model. Tests in
  `tests/test_core_tracer.py` cover the JSON endpoint, the
  full-page HTML view, splice-chain walking, loss-math summation, the
  "incomplete" flag, and the trace-button template integration.

### Notes for upcoming v0.2 PRs

- **PR E** — visual core tracer.

The `0.2.0` release tag fires once all five v0.2 PRs land. This entry
documents PRs A, B, C, D, and E. All five v0.2 features
landed; v0.2.0 is ready to tag.

## [0.1.1] — 2026-05-13

### Fixed

- Corrected author / maintainer name in package metadata, `PluginConfig`,
  `mkdocs.yml` copyright, and the icon SVG copyright comment from
  "John McKenzie" to "John McKean". 0.1.0 shipped with the wrong
  spelling and PyPI does not permit re-uploading a published version,
  so this metadata-only patch ships the correction.

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

[Unreleased]: https://github.com/iamjohnnymac/netbox-osp/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/iamjohnnymac/netbox-osp/releases/tag/v0.2.2
[0.2.1]: https://github.com/iamjohnnymac/netbox-osp/releases/tag/v0.2.1
[0.2.0]: https://github.com/iamjohnnymac/netbox-osp/releases/tag/v0.2.0
[0.1.1]: https://github.com/iamjohnnymac/netbox-osp/releases/tag/v0.1.1
[0.1.0]: https://github.com/iamjohnnymac/netbox-osp/releases/tag/v0.1.0
[0.0.1]: https://github.com/iamjohnnymac/netbox-osp/releases/tag/v0.0.1
