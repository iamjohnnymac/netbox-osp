# Tile bundling

`netbox_osp/static/netbox_osp/tiles/basemap.mbtiles` is a vendored
[MBTiles](https://github.com/mapbox/mbtiles-spec) file used by the
tile proxy view. It contains pre-rendered raster tiles for the
relevant area at the relevant zoom levels so the map works on an
air-gapped OT network with no upstream internet.

## Source data

Pull a fresh OpenStreetMap PBF extract from
[Geofabrik](https://download.geofabrik.de) covering your area of
interest. Clip it to a smaller bounding box before rendering — see
the env vars below.

## Render with tilemaker

[`tilemaker`](https://github.com/systemed/tilemaker) is a single-pass
renderer that emits raster MBTiles directly from a `.osm.pbf`.

### Environment variables

The render script honours these env vars (defaults shown):

| Var | Default | Purpose |
|-----|---------|---------|
| `OSP_BBOX_MIN_LON` | _required_ | Western edge of clip area |
| `OSP_BBOX_MAX_LON` | _required_ | Eastern edge of clip area |
| `OSP_BBOX_MIN_LAT` | _required_ | Southern edge of clip area |
| `OSP_BBOX_MAX_LAT` | _required_ | Northern edge of clip area |
| `OSP_ZOOM_MIN` | `6` | Lowest zoom kept |
| `OSP_ZOOM_MAX` | `16` | Highest zoom kept (16 is sufficient at site scale) |
| `OSP_OSM_PBF` | _required_ | Input file (`.osm.pbf` from Geofabrik) |
| `OSP_OUT_MBTILES` | `basemap.mbtiles` | Output file |

### One-liner

```bash
tilemaker \
  --input "${OSP_OSM_PBF:-my-area-latest.osm.pbf}" \
  --output "${OSP_OUT_MBTILES:-basemap.mbtiles}" \
  --bbox "${OSP_BBOX_MIN_LON:-2.2},${OSP_BBOX_MIN_LAT:-48.7},${OSP_BBOX_MAX_LON:-2.5},${OSP_BBOX_MAX_LAT:-48.9}" \
  --process resources/process-openmaptiles.lua \
  --config resources/config-openmaptiles.json \
  --store /tmp/tilemaker-store
```

The example bbox above is the Paris metro for illustration only — replace it
with the four `OSP_BBOX_*` env vars covering your own area before rendering.

Drop the resulting `basemap.mbtiles` at
`netbox_osp/static/netbox_osp/tiles/basemap.mbtiles` and re-run
`python manage.py collectstatic`.

## Layered overlays

The tile proxy also serves `*.mbtiles` files placed under
`<MEDIA_ROOT>/osp_tiles/` and prefers them over the bundled basemap.
Use this for site-scale orthophotos or detailed survey overlays
without rebuilding the basemap.
