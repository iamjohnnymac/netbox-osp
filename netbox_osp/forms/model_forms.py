from netbox.forms import NetBoxModelForm
from utilities.forms.fields import (
    CommentField, DynamicModelChoiceField, JSONField,
)

from dcim.models import Cable, Location, Manufacturer, Site
from tenancy.models import Tenant

from ..models import (
    FibreLink, FibreTrunk, LocationGeo, OspCable, Splice, SpliceClosure,
    SpliceTray, Strand, TrunkBreakout, Tube,
)


class OspCableForm(NetBoxModelForm):
    site_a = DynamicModelChoiceField(queryset=Site.objects.all(), required=True, label="Site A")
    site_b = DynamicModelChoiceField(queryset=Site.objects.all(), required=True, label="Site B")
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    manufacturer = DynamicModelChoiceField(queryset=Manufacturer.objects.all(), required=False)
    route = JSONField(
        required=False,
        help_text="GeoJSON LineString. Use the map editor below or paste directly.",
    )
    comments = CommentField()

    class Meta:
        model = OspCable
        fields = (
            "cid", "type", "status", "install_method",
            "fibre_count", "tube_count", "fibres_per_tube",
            "length_m", "attenuation_db_per_km",
            "site_a", "site_b", "tenant", "manufacturer", "part_number",
            "installed_date", "route", "description", "comments", "tags",
        )


class TubeForm(NetBoxModelForm):
    cable = DynamicModelChoiceField(queryset=OspCable.objects.all(), required=True)

    class Meta:
        model = Tube
        fields = ("cable", "number", "color", "description", "tags")


class StrandForm(NetBoxModelForm):
    cable = DynamicModelChoiceField(queryset=OspCable.objects.all(), required=True)
    tube = DynamicModelChoiceField(queryset=Tube.objects.all(), required=False)
    cable_link = DynamicModelChoiceField(queryset=Cable.objects.all(), required=False, label="dcim.Cable link")

    class Meta:
        model = Strand
        fields = (
            "cable", "tube", "position", "color", "status",
            "cable_link", "description", "tags",
        )


class SpliceClosureForm(NetBoxModelForm):
    site = DynamicModelChoiceField(queryset=Site.objects.all(), required=False)
    location = DynamicModelChoiceField(queryset=Location.objects.all(), required=False)
    manufacturer = DynamicModelChoiceField(queryset=Manufacturer.objects.all(), required=False)
    location_point = JSONField(
        required=False,
        help_text='GeoJSON Point. e.g. {"type":"Point","coordinates":[2.349,48.864]}',
    )
    comments = CommentField()

    class Meta:
        model = SpliceClosure
        fields = (
            "name", "closure_type", "manufacturer", "model", "capacity_splices",
            "site", "location", "status", "installed_date",
            "location_point", "elevation_m", "description", "comments", "tags",
        )


class SpliceTrayForm(NetBoxModelForm):
    closure = DynamicModelChoiceField(queryset=SpliceClosure.objects.all(), required=True)

    class Meta:
        model = SpliceTray
        fields = ("closure", "number", "capacity", "description", "tags")


class SpliceForm(NetBoxModelForm):
    tray = DynamicModelChoiceField(queryset=SpliceTray.objects.all(), required=True)
    strand_a = DynamicModelChoiceField(queryset=Strand.objects.all(), required=True)
    strand_b = DynamicModelChoiceField(queryset=Strand.objects.all(), required=True)

    class Meta:
        model = Splice
        fields = (
            "tray", "position", "splice_type", "loss_db",
            "strand_a", "strand_b", "spliced_date", "spliced_by",
            "otdr_trace_url", "description", "tags",
        )


class FibreLinkForm(NetBoxModelForm):
    comments = CommentField()

    class Meta:
        model = FibreLink
        fields = (
            "name", "status", "connector_loss_db", "connectors_per_end",
            "target_loss_budget_db", "description", "comments", "tags",
        )


class LocationGeoForm(NetBoxModelForm):
    location = DynamicModelChoiceField(
        queryset=Location.objects.all(), required=True,
        help_text="The Location this GPS record belongs to.",
    )

    class Meta:
        model = LocationGeo
        fields = (
            "location", "latitude", "longitude", "elevation_m",
            "marker_color", "description", "tags",
        )


class FibreTrunkForm(NetBoxModelForm):
    manufacturer = DynamicModelChoiceField(queryset=Manufacturer.objects.all(), required=False)
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    route = JSONField(
        required=False,
        help_text="GeoJSON LineString. Leave blank for intra-plant trunks.",
    )
    comments = CommentField()

    class Meta:
        model = FibreTrunk
        fields = (
            "cid", "trunk_type", "polarity", "fibre_count", "manufacturer", "length_m",
            "status", "route", "show_on_map", "tenant",
            "description", "comments", "tags",
        )


class TrunkBreakoutForm(NetBoxModelForm):
    trunk = DynamicModelChoiceField(queryset=FibreTrunk.objects.all(), required=True)
    cable = DynamicModelChoiceField(
        queryset=Cable.objects.all(),
        required=True,
        label="dcim.Cable",
        help_text="Native NetBox cable carrying this fibre range.",
    )

    class Meta:
        model = TrunkBreakout
        fields = (
            "trunk", "cable",
            "fibre_range_start", "fibre_range_end",
            "description", "tags",
        )
