# Configure

All settings live under `PLUGINS_CONFIG["netbox_osp"]` in your NetBox
`configuration/plugins.py` (or equivalent).

## Settings

| Key | Default | Purpose |
|-----|---------|---------|
| `default_attenuation_db_per_km` | `0.22` | Fallback attenuation when an `OspCable` has no explicit `attenuation_db_per_km` set. Used in fibre-link loss-budget calculation. |
| `default_splice_loss_db` | `0.10` | Fallback per-splice loss when a `Splice` row has no explicit `loss_db`. |
| `default_connector_loss_db` | `0.30` | Per-connector loss applied at each end of every `FibreLink`. |
| `map_default_center` | `[0.0, 0.0]` | `[lat, lon]` for the default map view. Set this to the lat/lon of your area of interest. |
| `map_default_zoom` | `2` | Default Leaflet zoom level. `13`–`16` is appropriate for site-scale viewing. |

## Base map tiles

The map ships with eight base layers. Seven are public online tile servers
(OpenStreetMap, Humanitarian OSM, CartoDB Positron / Dark Matter, OpenTopoMap,
CyclOSM, Esri World Imagery). The eighth is the bundled offline MBTiles served
by the plugin's tile proxy at `/plugins/osp/tiles/<z>/<x>/<y>.<ext>`.

If three tile-load failures occur within five seconds on an online layer, the
map auto-falls-back to the offline layer and shows a toast with a **Retry
online** button. The user's explicit choice persists across reloads via
`localStorage`.

To replace the bundled offline tiles with your own area's imagery, drop one
or more `.mbtiles` files at `<MEDIA_ROOT>/osp_tiles/` — they take precedence
over the bundled stub. See [tile bundling](tile-bundling.md) for the build
workflow.
