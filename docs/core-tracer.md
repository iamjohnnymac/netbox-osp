# Visual core tracer

The core tracer renders an end-to-end fibre path as a clickable graph,
covering every hop from a device interface through patch cords,
cassette pass-throughs, MPO/MTP trunks, splices, and OSP strands to the
device interface at the other end.

It's the answer to "where does fibre core 5 actually go?" — one click,
no clipboard juggling.

## How to access

The tracer entry point appears in three places:

1. **Strand detail** — `/plugins/osp/strands/<id>/`. The "Trace this
   core" button sits below the attribute panel.
2. **`dcim.FrontPort` detail** — `/dcim/front-ports/<id>/`. Injected as
   a right-page panel via a `PluginTemplateExtension`.
3. **`dcim.Interface` detail** — `/dcim/interfaces/<id>/`. Injected
   the same way.

All three buttons link to the same canonical view:
`/plugins/osp/strands/<strand_id>/trace/`. The FrontPort / Interface
entry points first resolve the closest associated Strand (via the
`Strand.cable_link` bridge or the `a_termination` / `b_termination`
GenericForeignKey) and then redirect.

If no Strand can be reached from a FrontPort / Interface, the redirect
view returns a friendly 404 explaining the gap.

## What you see

The tracer page has three regions:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Core trace                                       [← Back to strand] │
│ CORE-OSP-001 strand 5 (tube 1) on cable CORE-OSP-001               │
├─────────────────────────────────────────────────────────────────────┤
│ 2.23 / 8.00 dB used (27.8%) [OK]                                    │
├─────────────────────────────────────────────────────────────────────┤
│ ┌──────────┐  ┌──────┐  ┌──────────┐  ┌──────┐  ┌──────────┐        │
│ │router1   │→ │patch │→ │P1:Fr-23  │→ │cass. │→ │P1:Re-2/12│ → ...  │
│ │:Gi0/1    │  │cord  │  │↔ P1:Re-* │  │      │  │trunk fib5│        │
│ └──────────┘  └──────┘  └──────────┘  └──────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────────────┘
```

Each box is a **hop**. Click any box to navigate to that object's
detail page in NetBox.

The summary band above the graph shows total loss, target budget,
percentage used, and a colour-coded **band**:

- `ok`  — pct ≤ 80% (green)
- `warn` — pct ≤ 100% (amber)
- `fail` — pct > 100% (red)

The band uses the strand's parent `FibreLink.target_loss_budget_db` if
the strand is bound to a `FibreLink`. Otherwise it falls back to
`PLUGINS_CONFIG["netbox_osp"]["default_loss_budget_db"]` (default 8.0
dB).

## Hop kinds

| Kind         | What it represents                                            | Loss formula                                                |
|--------------|---------------------------------------------------------------|-------------------------------------------------------------|
| `interface`  | A `dcim.Interface` at either end of the path                  | 0 dB (connector loss is accounted for on the patch cord)    |
| `cable`      | A native `dcim.Cable` (patch cord, jumper, intra-rack run)    | length × `default_attenuation_db_per_km` / 1000             |
| `cassette`   | A `FrontPort ↔ RearPort` pass-through inside a cassette       | `default_cassette_loss_db` (default 0.5 dB)                 |
| `trunk`      | A `FibreTrunk` aggregator (the trunk itself, not its strands) | 0 dB (child strands carry the loss)                         |
| `splice`     | A `Splice` row in a `SpliceTray` inside a `SpliceClosure`     | `splice.loss_db` (default 0.10 dB)                          |
| `osp_strand` | A `Strand` inside an `OspCable`                               | length_m × `attenuation_db_per_km` / 1000                   |

## Configuration

The tracer reads four optional values from `PLUGINS_CONFIG["netbox_osp"]`:

```python
PLUGINS_CONFIG = {
    "netbox_osp": {
        # Cable / strand attenuation defaults (existing).
        "default_attenuation_db_per_km": 0.22,   # OS2 1550 nm
        "default_splice_loss_db": 0.10,          # fusion splice
        # New in v0.2.0 for the core tracer:
        "default_cassette_loss_db": 0.5,         # MPO cassette pass-through
        "default_patch_cord_loss_db": 0.1,       # patch cord with no length
        "default_loss_budget_db": 8.0,           # fallback link budget
    },
}
```

Any value omitted falls back to the documented default above.

## REST API

The trace endpoint is public so other plugins / external tooling can
render their own visualisations:

```
GET /api/plugins/osp/cores/<strand_id>/trace/
```

Returns:

```json
{
  "strand_id": 123,
  "hops": [
    {"kind": "interface", "label": "router1:Gi0/1", "url": "/dcim/interfaces/55/", "loss_db": 0.0},
    {"kind": "cable", "label": "router1:Gi0/1 → P1:Front-23", "url": "/dcim/cables/87/", "length_m": 2, "loss_db": 0.0},
    {"kind": "cassette", "label": "P1: Front-23 ↔ Rear-2/12", "url": "/dcim/devices/12/", "loss_db": 0.5},
    {"kind": "osp_strand", "label": "CORE-OSP-001 strand 5 (tube 1)", "url": "/plugins/osp/strands/22/", "length_m": 3500, "loss_db": 0.77}
  ],
  "total_loss_db": 1.27,
  "target_loss_budget_db": 8.0,
  "loss_pct": 15.9,
  "band": "ok",
  "incomplete": false
}
```

When `incomplete` is `true`, the hop list ends earlier than expected
because at least one strand termination is unbound. The UI surfaces a
small amber badge in the summary band.

## Traversal algorithm

The tracer is strand-rooted — it always anchors at a `Strand` and grows
outward in both directions, switching between two traversal modes:

1. **DCIM-side** — uses NetBox core's `PathEndpoint.trace()` (returns
   `list[(a_terms, cables, b_terms)]`) to walk patch cords + cassette
   pass-throughs from a FrontPort until it reaches a real
   `PathEndpoint` (an `Interface`, typically).
2. **OSP-side** — walks the splice graph by following `Splice` rows
   that reference the current strand, hopping to the splice's "other"
   strand each time. Cycles are detected via a visited-set.

For the interface-rooted entry points, the redirect view does one DCIM
walk to find the first Strand-claiming FrontPort and then jumps to the
canonical strand-rooted view.

## Implementation notes

- The graph is rendered client-side with **dagre-d3 v0.6.4** — vendored
  as `/static/netbox_osp/js/dagre-d3.min.js`. The bundle includes its
  own d3 v5, so the tracer has zero runtime dependencies on the NetBox
  core JS.
- The renderer degrades gracefully: if the JS bundle fails to load,
  the page shows the JSON response in a fallback panel so operators
  can still see the path.
- The endpoint runs purely against the existing data model — there are
  **no new migrations**.
