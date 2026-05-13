from netbox.forms import NetBoxModelImportForm
from ..models import OspCable


class OspCableImportForm(NetBoxModelImportForm):
    class Meta:
        model = OspCable
        fields = (
            "cid", "type", "status", "install_method",
            "fibre_count", "tube_count", "fibres_per_tube",
            "length_m", "attenuation_db_per_km",
            "site_a", "site_b", "tenant", "manufacturer", "part_number",
            "description",
        )
