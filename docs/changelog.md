# Changelog

All notable changes to `netbox-osp` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased — `0.1.0.dev0`

### Added

- Multi-base-layer map switcher: 7 online providers + 1 offline MBTiles
  bundle, with auto-fallback when public tile servers are unreachable.
- Cable / Tube / Strand models with TIA-598-C auto-colours.
- Splice closure / tray / splice models with per-splice measured loss.
- Fibre-link loss-budget computation (strand × attenuation + splices +
  connectors), with ok / warn / fail band.
- Full-screen Leaflet plant map filterable by site / status / type.
- GeoJSON route editor for cables (leaflet-geoman).
- Plant-boundary trace tool — operator drags vertices, exports coords.
- Apache-2.0 license, README, MkDocs Material docs site.

### Infrastructure

- Public GitHub repo with `release.yml` workflow using PyPI Trusted
  Publishing via OIDC (no API tokens).
- `test.yml` matrix: Python 3.12/3.13 × NetBox 4.5/4.6.
- `docs.yml` deploying MkDocs Material to GitHub Pages.
- `.pre-commit-config.yaml` with ruff (lint + format).

## `0.0.1` — 2026-05-13

- Initial PyPI name reservation. Placeholder release; not functional.
