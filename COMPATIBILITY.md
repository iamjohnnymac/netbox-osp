# Compatibility matrix

Per-release NetBox / Python / Postgres compatibility for `netbox-osp`.

Tested combinations are exercised in CI on every PR
(`.github/workflows/test.yml`). "Supported" means the release runs
green against the listed combination; combinations outside the table
may work but are not guaranteed.

| netbox-osp | NetBox       | Python         | Postgres     | Redis | Notes                                  |
|------------|--------------|----------------|--------------|-------|----------------------------------------|
| 0.1.x      | 4.6.x        | 3.12 · 3.13    | 17           | 7     | First functional release.              |
| 0.0.1      | n/a          | n/a            | n/a          | n/a   | Name-reservation placeholder; not in CI. |

## NetBox version policy

- The `max_version` in `PluginConfig` (`netbox_osp/__init__.py`) is the
  authoritative upper bound. Currently `4.6.99`; the band widens via a
  0.1.x patch once we've validated against a new NetBox minor.
- We target the current and previous NetBox **minor** version once a new
  minor is published (e.g. when 4.7 ships, the band widens to cover both).
- We do **not** backport fixes to dropped minors.
- Pre-release NetBox versions (4.x betas / RCs) are tested ad-hoc but
  not part of the support guarantee.

## Python version policy

- The minimum is whatever NetBox itself requires for its lowest
  supported version (Python 3.12 for NetBox 4.6).
- We add the newest stable Python the first CI run after its release.
- We drop a Python version one minor release after NetBox drops it.

## Database / cache

- Postgres versions tracking NetBox's documented supported range.
- Redis 7+. We do not use Redis-specific features beyond what NetBox
  itself requires.
- **PostGIS is not required.** Geometry is stored as GeoJSON in `JSONField`
  columns; plant-boundary validation uses a pure-Python ray-casting
  algorithm so the plugin runs on any NetBox-supported database.

## Upgrade path

- Within a minor version (`0.1.x` → `0.1.y`): straight `pip install -U
  netbox-osp` followed by `migrate` + `collectstatic`. No data loss.
- Across minor versions (`0.1.x` → `0.2.x`): consult the
  [CHANGELOG](CHANGELOG.md) "Breaking changes" section for the target
  release before upgrading.

## Reporting a compatibility issue

Open an issue at <https://github.com/iamjohnnymac/netbox-osp/issues>
with:

- `netbox-osp` version (`pip show netbox-osp`)
- NetBox version + branch
- Python version (`python --version`)
- Postgres version
- The failing migration / view / API call and full traceback
