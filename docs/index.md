# netbox-osp

Outside-plant (OSP) fibre management for [NetBox](https://github.com/netbox-community/netbox):

- **OSP cables** with TIA-598-C colour-coded buffer tubes and strands
- **Splice closures** with trays + individual splices, per-splice measured loss
- **Fibre links** that chain strands through splices and compute a loss budget
  (strand × attenuation + splices + connectors) with a status band
- **Network map** — full-screen Leaflet, online + offline base layers, auto-fallback
  to a bundled MBTiles bundle when public tile servers are unreachable
- **GeoJSON route editor** for cables, drag-to-edit for closures

## Quick links

- [Demo walkthrough](demo.md) — 8-step tour of the plugin running on the live demo
- [Install](install.md)
- [Configure](configure.md)
- [Data model](data-model.md)
- [Tile bundling](tile-bundling.md)
- [Compatibility](compatibility.md)
- [Changelog](changelog.md)
- [GitHub](https://github.com/iamjohnnymac/netbox-osp) · [PyPI](https://pypi.org/project/netbox-osp/)

## Status

**Alpha** — the v0.1.0 release is in active development. The 0.0.1 release on
PyPI is a name-reservation placeholder.

## License

Apache-2.0.
