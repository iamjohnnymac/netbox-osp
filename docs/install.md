# Install

## Requirements

- NetBox **4.6.x** (4.5 support is blocked by a `dcim` migration node that
  exists only in 4.6+; will be relaxed once the migration is regenerated
  against an earlier dcim baseline)
- Python **3.12** or newer

## From PyPI

Add the plugin to your `local_requirements.txt` (or `plugin_requirements.txt`
in netbox-docker setups):

```text
netbox-osp
```

Enable it in `configuration/plugins.py`:

```python
PLUGINS = [
    "netbox_osp",
]

PLUGINS_CONFIG = {
    "netbox_osp": {
        "default_attenuation_db_per_km": 0.22,
        "default_splice_loss_db": 0.10,
        "default_connector_loss_db": 0.30,
        # World view by default. Override with the lat/lon of your area.
        "map_default_center": [0.0, 0.0],
        "map_default_zoom": 2,
    },
}
```

Apply migrations and collect static assets:

```bash
python manage.py migrate
python manage.py collectstatic --no-input
```

Restart NetBox and the RQ workers.

## From source

```bash
git clone https://github.com/iamjohnnymac/netbox-osp.git
cd netbox-osp
pip install -e .
```

Then follow the same `PLUGINS` / migrate / collectstatic steps above.
