from netbox.plugins import PluginConfig


class NetBoxOspConfig(PluginConfig):
    name = "netbox_osp"
    verbose_name = "NetBox OSP"
    description = "Outside-plant fibre management — cables, splice closures, fibre links with loss budgets, and an offline-capable Leaflet plant map."
    version = "0.1.0.dev0"
    author = "John McKenzie"
    author_email = "33052970+iamjohnnymac@users.noreply.github.com"
    base_url = "osp"
    min_version = "4.6.0"
    max_version = "4.6.99"

    default_settings = {
        "default_attenuation_db_per_km": 0.22,
        "default_splice_loss_db": 0.10,
        "default_connector_loss_db": 0.30,
        # World view by default. Override with the lat/lon of your area.
        "map_default_center": [0.0, 0.0],
        "map_default_zoom": 2,
    }


config = NetBoxOspConfig
