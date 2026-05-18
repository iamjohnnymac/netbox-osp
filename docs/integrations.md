# Ecosystem integrations

`netbox-osp` is built to **compose** with the wider NetBox plugin ecosystem
rather than reinvent it. The OSP data model — cables, tubes, strands,
closures, trays, splices, links, trunks — is the source of truth; other
certified plugins handle attachments, QR codes, branching, conduits, and
so on. This page documents the integrations that work out-of-the-box and
the exact configuration to enable them.

All integrations on this page are **optional**. The plugin runs fine
without any of them installed.

---

## netbox-attachments

[**netbox-attachments**](https://github.com/Kani999/netbox-attachments)
adds an `Attachments` tab to any NetBox model — files, images, OTDR
`.sor` traces, splice photos, vendor data sheets, as-built drawings.

`netbox-osp` doesn't ship its own attachment system. Instead, configure
`netbox-attachments` to recognise every OSP model and you get
file-attach surfaces on cables, closures, trays, splices, and trunks
for free.

### Install

```bash
pip install netbox-osp[attachments]
```

The `[attachments]` extra pulls in a compatible `netbox-attachments`
release. You can also install it directly without the extra:

```bash
pip install netbox-attachments
```

Enable both plugins in `configuration/plugins.py`:

```python
PLUGINS = [
    "netbox_attachments",
    "netbox_osp",
]
```

Apply migrations, collect static assets, then restart NetBox and the
RQ workers:

```bash
python manage.py migrate
python manage.py collectstatic --no-input
```

### Configure `scope_filter`

Add this block to `PLUGINS_CONFIG` to enable attachments on every
OSP model:

```python
PLUGINS_CONFIG = {
    "netbox_attachments": {
        "applied_scope": "model",
        "scope_filter": [
            "netbox_osp.ospcable",
            "netbox_osp.tube",
            "netbox_osp.strand",
            "netbox_osp.splice",
            "netbox_osp.spliceclosure",
            "netbox_osp.splicetray",
            "netbox_osp.fibrelink",
            "netbox_osp.fibretrunk",
            "netbox_osp.trunkbreakout",
            "netbox_osp.locationgeo",
        ],
        "display_default": "right_page",
        "create_add_button": True,
    },
    "netbox_osp": {
        # ... your existing OSP config
    },
}
```

Model names are lowercase per netbox-attachments' convention. Drop any
models you don't want attachment surfaces on — `scope_filter` is opt-in
per model.

### What this unlocks

| Attach this | …to this model | Why |
|---|---|---|
| `.sor` OTDR trace | `OspCable`, `FibreLink` | Per-strand fault history, captured at install and after every cable cut. Pairs perfectly with the v0.3.5 OTDR moat work. |
| Splice photo | `SpliceClosure`, `SpliceTray`, `Splice` | "What did the inside of this closure look like when we left it?" Field-crew confidence + warranty evidence. |
| As-built PDF | `OspCable` | Route diagrams, pole-line attachments, conduit run drawings handed back from the contractor. |
| Test certificate | `FibreLink` | Acceptance-test certificates per IEEE 802.3 / TIA-568.3-D. Saves a click into the contractor's portal. |
| Vendor data sheet | `FibreTrunk`, `TrunkBreakout` | Cassette MPO pinout, harness colour code, manufacturer cable-build spec. |
| Cable schematic | `Tube`, `Strand` | Manufacturer tube-colour diagram or strand-position chart for unusual cable builds. |

### Verify the integration

1. Browse to any `SpliceClosure` detail page — e.g.
   `/plugins/osp/closures/<id>/`
2. The right-page area should now show an **Attachments** card
3. Click **Add attachment**, upload a placeholder file, confirm it
   appears in the list

If the Attachments card doesn't appear, check:

- The closure's app/model string (`netbox_osp.spliceclosure`) is in
  `scope_filter` exactly (lowercase)
- Both plugins are listed in `PLUGINS`
- `applied_scope: "model"` is set (the default is `"app"`, which
  enables attachments on **every** model in the app — usually fine,
  but `"model"` keeps the surface intentional)
- The NetBox process was restarted after editing `PLUGINS_CONFIG`

### Why this matters for v0.3.5

The next release cycle (v0.3.5) adds first-class OTDR `.sor` parsing,
KeyEvents tables, baseline / drift detection, and a geo-anchored fault
pin on the plant map. **The `.sor` files themselves will continue to
live in netbox-attachments** — we parse on upload, store the metadata
in our `OTDRTrace` model, and let netbox-attachments handle the raw
file storage. Installing netbox-attachments now means you're ready for
v0.3.5 with no further configuration.

---

## Field QR codes (SpliceClosure + SpliceTray)

`netbox-osp` ships built-in QR codes on `SpliceClosure` and
`SpliceTray` detail pages. The QR encodes the absolute URL of the
page — print it on the closure label, a field tech scans it with a
phone, and lands directly on the splice plan with attached photos
and loss budget. No login flow needed beyond NetBox's standard
session.

### Install

```bash
pip install netbox-osp[qrcode]
```

The `[qrcode]` extra pulls in the
[`qrcode`](https://pypi.org/project/qrcode/) Python library
(pure-Python SVG generation, no Pillow required). With the extra
installed, the QR panel renders automatically on
`/plugins/osp/closures/<id>/` and `/plugins/osp/trays/<id>/`.
Without it, the panel quietly hides — the rest of the plugin is
unaffected.

No `PLUGINS_CONFIG` changes are needed.

### Why not netbox-qrcode?

[`netbox-qrcode`](https://github.com/netbox-community/netbox-qrcode)
is the established plugin for QR codes on NetBox core models
(`dcim.device`, `dcim.cable`, etc.) and ships a rich label-design
system for print workflows. We considered wrapping it but its
template extensions hardcode the supported model list at the class
level, so plugin models like `netbox_osp.spliceclosure` can't be
added via configuration alone. Rather than fork or monkey-patch
upstream, we use the same underlying `qrcode` Python library
directly — same QR codes, no upstream coupling, ~50 LOC.

If you also use netbox-qrcode for `dcim.device` / `dcim.cable` /
etc. labels, both plugins coexist cleanly: netbox-qrcode owns its
models, `netbox-osp` owns ours.

### Verify the integration

1. Install the extra: `pip install netbox-osp[qrcode]` (in the
   NetBox virtualenv or container)
2. Restart NetBox and the RQ workers
3. Browse to any `SpliceClosure` detail page — e.g.
   `/plugins/osp/closures/<id>/`
4. The right-page area should show a **Field QR code** card with
   the SVG QR and the encoded URL below
5. Open your phone's camera, point it at the QR, confirm it opens
   the same detail page

If the QR card doesn't appear, check that `qrcode` is importable in
the NetBox Python environment (`python -c "import qrcode"`).
