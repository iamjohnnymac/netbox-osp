from netbox.plugins import PluginConfig


class NetBoxOspConfig(PluginConfig):
    name = "netbox_osp"
    verbose_name = "NetBox OSP"
    description = "Outside-plant fibre management — cables, splice closures, fibre links with loss budgets, and an offline-capable Leaflet plant map."
    version = "0.3.1"
    author = "John McKean"
    author_email = "33052970+iamjohnnymac@users.noreply.github.com"
    base_url = "osp"
    min_version = "4.6.0"
    max_version = "4.6.99"

    default_settings = {
        "default_attenuation_db_per_km": 0.22,
        "default_splice_loss_db": 0.10,
        "default_connector_loss_db": 0.30,
        # PR E — visual core tracer.
        # Per-cassette pass-through loss budget when a hop crosses a
        # FrontPort↔RearPort coupling. 0.5 dB is a reasonable industry
        # default; operators can tune per environment.
        "default_cassette_loss_db": 0.5,
        # Fallback loss for a patch cord whose length is unknown.
        "default_patch_cord_loss_db": 0.1,
        # Default link budget the tracer compares against when the strand
        # isn't bound to a FibreLink (and therefore lacks an explicit
        # target_loss_budget_db).
        "default_loss_budget_db": 8.0,
        # World view by default. Override with the lat/lon of your area.
        "map_default_center": [0.0, 0.0],
        "map_default_zoom": 2,
        # Default Cable.type chosen by the MTP harness one-click deploy
        # form. Override per-install if the plant is mostly multimode.
        "default_cable_type": "smf",
    }


config = NetBoxOspConfig
