# Data model

All geometry is stored as GeoJSON in WGS84 with `[lon, lat]` order
(RFC 7946). Conversion to Leaflet's `[lat, lon]` happens at the JS
boundary only.

## Relationships

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

## Models

### `OspCable`
A physical fibre cable run between two `dcim.Site`s.
Key fields: `cid`, `type`, `status`, `install_method`, `fibre_count`,
`tube_count`, `fibres_per_tube`, `length_m`, `attenuation_db_per_km`,
`site_a`, `site_b`, `tenant`, `manufacturer`, `route` (GeoJSON
LineString), `route_length_m` (auto-computed on save).
Constraint: `fibre_count == tube_count * fibres_per_tube`.

### `Tube`
A buffer tube inside an `OspCable`. Unique on `(cable, number)`. Colour
defaults to TIA-598-C order if unset.

### `Strand`
A single fibre strand. Unique on `(cable, position)`. Colour and tube
auto-assigned from `position`. The optional `cable_link` FK to
`dcim.Cable` bridges to the legacy strand-as-cable model so existing
patch-panel termination data still works.
Termination is via generic FKs (`a_termination`, `b_termination`) to
patch-panel front-ports.

### `SpliceClosure`
A physical splice enclosure (dome / inline / pedestal / handhole /
wall-mount / aerial). Located at a `dcim.Site` + optional `dcim.Location`
and a GeoJSON `location_point`. Tracks `capacity_splices` for utilisation.

### `SpliceTray`
A tray inside a closure. Unique on `(closure, number)`. Holds splices.

### `Splice`
A fusion or mechanical splice joining `strand_a` and `strand_b`.
Constraint: `strand_a != strand_b` (no self-splice). Stores
`loss_db`, `spliced_date`, `spliced_by`, `otdr_trace_url`.

### `FibreLink`
A logical end-to-end link with two generic-FK terminations
(`a_termination`, `b_termination`), one or more `strands` chained via
`FibreLinkStrand` hops, and a `target_loss_budget_db`.
Computed properties: `strand_loss_db`, `splice_loss_db`,
`connector_total_loss_db`, `total_loss_db`, `loss_budget_pct`,
`loss_budget_band` (ok / warn / fail).

### `FibreLinkStrand`
Through-table assigning a `Strand` to a `FibreLink` at a given
`position`. Unique on `(link, position)` and `(link, strand)`.

### `LocationGeo`
A 1:1 side-table on `dcim.Location` adding `latitude`, `longitude`,
`elevation_m`, and `marker_color`. NetBox core gives Sites lat/lon but
not Locations — this fills the gap so individual rooms, manholes, or
jetty poles can be pinned on the network map alongside Site markers.
`latitude` and `longitude` use `Decimal(max_digits=10, decimal_places=6)`
matching `Site.latitude` / `Site.longitude` precision; both are optional
but must be set together. `marker_color` picks from a short hue-separated
palette so different Location classes stay visually distinct.

### `FibreTrunk`
A multi-fibre physical trunk (MPO/MTP 12/24/72-fibre, Ribbon 144-fibre,
loose-tube indoor runs). Carries `cid`, `trunk_type`, `fibre_count`,
`manufacturer`, `length_m`, `status` (reuses `OspStatusChoices`), an
optional GeoJSON `route` with a `show_on_map` opt-out, `description`,
`comments`, `tenant`, `tags`. DB-level `CheckConstraint` on
`fibre_count > 0`. The forthcoming `TrunkBreakout` through-table (v0.2
PR B) bridges this parent to `dcim.Cable` so operators can express
"one 24F trunk → two 12F breakouts" as one logical entity.

### MTP harness one-click deploy

The harness-deploy form at `/plugins/osp/trunks/deploy-harness/`
orchestrates a complete inter-rack fibre deployment in one submit. The
operator provides trunk metadata, a source patch-panel RearPort, a
cassette `DeviceType`, and one row per destination rack (each with a
fibre range, cable length, and either a "create new cassette" or
"reuse existing device" choice). On confirm the view writes — inside
a single `transaction.atomic()` — one `FibreTrunk` parent row, N
`dcim.Device` cassettes, N `dcim.Cable`s connecting the source
RearPort to each destination's RearPort, and N `TrunkBreakout` rows
binding the cables to the trunk at the chosen fibre ranges. Any
validation failure (overlapping ranges, rack-position collision,
unavailable port) rolls back the entire batch. The flow contains no
new database models — it is pure orchestration over PR A's
`FibreTrunk`, PR B's `TrunkBreakout`, and core `dcim.Device` /
`dcim.Cable`.
