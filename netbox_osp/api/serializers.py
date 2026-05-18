from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from netbox.api.serializers import NetBoxModelSerializer

from ..models import (
    FibreLink, FibreLinkStrand, FibreTrunk, LocationGeo, OspCable, Splice,
    SpliceClosure, SpliceTray, Strand, TrunkBreakout, Tube,
)
from ..models._geo import validate_linestring, validate_point


class OspCableSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_osp-api:ospcable-detail")
    effective_length_m = serializers.IntegerField(read_only=True)
    loss_db = serializers.DecimalField(max_digits=8, decimal_places=3, read_only=True)

    class Meta:
        model = OspCable
        fields = (
            "id", "url", "display", "cid", "type", "status", "install_method",
            "fibre_count", "tube_count", "fibres_per_tube",
            "length_m", "attenuation_db_per_km",
            "site_a", "site_b", "tenant", "manufacturer", "part_number",
            "installed_date", "route", "route_length_m", "effective_length_m",
            "loss_db", "description", "comments",
            "tags", "custom_fields", "created", "last_updated",
        )
        brief_fields = ("id", "url", "display", "cid", "status")

    def validate_route(self, value):
        if value is not None:
            validate_linestring(value)
        return value


class TubeSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_osp-api:tube-detail")

    class Meta:
        model = Tube
        fields = (
            "id", "url", "display", "cable", "number", "color",
            "description", "tags", "custom_fields", "created", "last_updated",
        )
        brief_fields = ("id", "url", "display", "number", "color")


class StrandSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_osp-api:strand-detail")

    class Meta:
        model = Strand
        fields = (
            "id", "url", "display", "cable", "tube", "position", "color",
            "status", "cable_link",
            "a_termination_type", "a_termination_id",
            "b_termination_type", "b_termination_id",
            "description", "tags", "custom_fields", "created", "last_updated",
        )
        brief_fields = ("id", "url", "display", "position", "color", "status")


class SpliceClosureSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_osp-api:spliceclosure-detail")
    used_splices = serializers.IntegerField(read_only=True)
    utilization_pct = serializers.FloatField(read_only=True)

    class Meta:
        model = SpliceClosure
        fields = (
            "id", "url", "display", "name", "closure_type", "manufacturer",
            "model", "capacity_splices", "site", "location", "status",
            "installed_date", "location_point", "elevation_m",
            "used_splices", "utilization_pct",
            "description", "comments",
            "tags", "custom_fields", "created", "last_updated",
        )
        brief_fields = ("id", "url", "display", "name", "status")

    def validate_location_point(self, value):
        if value is not None:
            validate_point(value)
        return value


class SpliceTraySerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_osp-api:splicetray-detail")
    used = serializers.IntegerField(read_only=True)

    class Meta:
        model = SpliceTray
        fields = (
            "id", "url", "display", "closure", "number", "capacity", "used",
            "description", "tags", "custom_fields", "created", "last_updated",
        )
        brief_fields = ("id", "url", "display", "number")


class SpliceSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_osp-api:splice-detail")

    class Meta:
        model = Splice
        fields = (
            "id", "url", "display", "tray", "position", "splice_type",
            "loss_db", "strand_a", "strand_b", "spliced_date", "spliced_by",
            "otdr_trace_url", "description",
            "tags", "custom_fields", "created", "last_updated",
        )
        brief_fields = ("id", "url", "display", "position", "splice_type")


class LocationGeoSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_osp-api:locationgeo-detail")
    has_coords = serializers.BooleanField(read_only=True)

    class Meta:
        model = LocationGeo
        fields = (
            "id", "url", "display", "location",
            "latitude", "longitude", "elevation_m",
            "marker_color", "description",
            "has_coords",
            "tags", "custom_fields", "created", "last_updated",
        )
        brief_fields = ("id", "url", "display", "location")


class FibreTrunkSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_osp-api:fibretrunk-detail")
    fibres_used = serializers.IntegerField(read_only=True)
    fibres_remaining = serializers.IntegerField(read_only=True)
    fibres_utilization_pct = serializers.FloatField(read_only=True)

    class Meta:
        model = FibreTrunk
        fields = (
            "id", "url", "display", "cid", "trunk_type", "polarity", "fibre_count",
            "manufacturer", "length_m", "status", "route", "show_on_map",
            "description", "comments", "tenant",
            "fibres_used", "fibres_remaining", "fibres_utilization_pct",
            "tags", "custom_fields", "created", "last_updated",
        )
        brief_fields = ("id", "url", "display", "cid", "status")

    def validate_route(self, value):
        if value is not None:
            validate_linestring(value)
        return value


class TrunkBreakoutSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_osp-api:trunkbreakout-detail")
    fibre_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = TrunkBreakout
        fields = (
            "id", "url", "display", "trunk", "cable",
            "fibre_range_start", "fibre_range_end", "fibre_count",
            "description",
            "tags", "custom_fields", "created", "last_updated",
        )
        brief_fields = (
            "id", "url", "display", "trunk", "cable",
            "fibre_range_start", "fibre_range_end",
        )

    def validate(self, data):
        """Re-run TrunkBreakout.clean() so REST mutations surface clean
        400s keyed to the offending field (range start / end / overlap)."""
        data = super().validate(data)
        # Build a model instance with the candidate data so .clean() can
        # run the same sibling-overlap and parent-fibre-count checks the
        # admin form uses.
        instance = TrunkBreakout(**{
            k: v for k, v in data.items()
            if k in {
                "trunk", "cable",
                "fibre_range_start", "fibre_range_end",
                "description",
            }
        })
        if self.instance is not None:
            instance.pk = self.instance.pk
        try:
            instance.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            ) from exc
        return data


class FibreLinkStrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = FibreLinkStrand
        fields = ("id", "link", "strand", "position")


class FibreLinkSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_osp-api:fibrelink-detail")
    strand_count = serializers.IntegerField(read_only=True)
    total_loss_db = serializers.DecimalField(max_digits=8, decimal_places=3, read_only=True)
    loss_budget_pct = serializers.FloatField(read_only=True)
    loss_budget_band = serializers.CharField(read_only=True)

    class Meta:
        model = FibreLink
        fields = (
            "id", "url", "display", "name", "status",
            "a_termination_type", "a_termination_id",
            "b_termination_type", "b_termination_id",
            "connector_loss_db", "connectors_per_end", "target_loss_budget_db",
            "strand_count", "total_loss_db", "loss_budget_pct", "loss_budget_band",
            "description", "comments",
            "tags", "custom_fields", "created", "last_updated",
        )
        brief_fields = ("id", "url", "display", "name", "status")
