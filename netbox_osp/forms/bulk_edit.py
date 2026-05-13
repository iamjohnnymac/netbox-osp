from django import forms

from dcim.models import Manufacturer
from netbox.forms import NetBoxModelBulkEditForm
from tenancy.models import Tenant
from utilities.forms.fields import DynamicModelChoiceField

from ..choices import (
    ClosureTypeChoices,
    FibreLinkStatusChoices,
    LocationMarkerColorChoices,
    OspCableTypeChoices,
    OspStatusChoices,
    SpliceTypeChoices,
    StrandStatusChoices,
    TIA598ColorChoices,
    TrunkTypeChoices,
)
from ..models import (
    FibreLink,
    FibreTrunk,
    LocationGeo,
    OspCable,
    Splice,
    SpliceClosure,
    SpliceTray,
    Strand,
    TrunkBreakout,
    Tube,
)


class OspCableBulkEditForm(NetBoxModelBulkEditForm):
    type = forms.ChoiceField(choices=OspCableTypeChoices, required=False)
    status = forms.ChoiceField(choices=OspStatusChoices, required=False)
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)

    model = OspCable
    nullable_fields = ("tenant", "manufacturer", "part_number", "description")


class SpliceClosureBulkEditForm(NetBoxModelBulkEditForm):
    closure_type = forms.ChoiceField(choices=ClosureTypeChoices, required=False)
    status = forms.ChoiceField(choices=OspStatusChoices, required=False)

    model = SpliceClosure
    nullable_fields = ("manufacturer", "model", "description")


class FibreLinkBulkEditForm(NetBoxModelBulkEditForm):
    status = forms.ChoiceField(choices=FibreLinkStatusChoices, required=False)

    model = FibreLink
    nullable_fields = ("description",)


class TubeBulkEditForm(NetBoxModelBulkEditForm):
    color = forms.ChoiceField(choices=TIA598ColorChoices, required=False)

    model = Tube
    # description is synthesised from nullable_fields — no explicit declaration
    # (matches the OspCableBulkEditForm / SpliceClosureBulkEditForm pattern).
    nullable_fields = ("description",)


class StrandBulkEditForm(NetBoxModelBulkEditForm):
    status = forms.ChoiceField(choices=StrandStatusChoices, required=False)

    # position + color are physical/sacred per-strand identifiers
    # (TIA-598 drives splice tracing). NOT in bulk-edit.
    model = Strand
    nullable_fields = ("description",)


class SpliceTrayBulkEditForm(NetBoxModelBulkEditForm):
    capacity = forms.IntegerField(required=False, min_value=1)

    model = SpliceTray
    nullable_fields = ("description",)


class SpliceBulkEditForm(NetBoxModelBulkEditForm):
    splice_type = forms.ChoiceField(choices=SpliceTypeChoices, required=False)
    loss_db = forms.DecimalField(required=False, max_digits=5, decimal_places=3)
    spliced_by = forms.CharField(max_length=64, required=False)

    model = Splice
    nullable_fields = ("description", "spliced_by", "otdr_trace_url")


class LocationGeoBulkEditForm(NetBoxModelBulkEditForm):
    marker_color = forms.ChoiceField(choices=LocationMarkerColorChoices, required=False)

    model = LocationGeo
    nullable_fields = ("description", "elevation_m")


class FibreTrunkBulkEditForm(NetBoxModelBulkEditForm):
    trunk_type = forms.ChoiceField(choices=TrunkTypeChoices, required=False)
    status = forms.ChoiceField(choices=OspStatusChoices, required=False)
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    manufacturer = DynamicModelChoiceField(queryset=Manufacturer.objects.all(), required=False)
    show_on_map = forms.NullBooleanField(required=False)

    model = FibreTrunk
    nullable_fields = ("tenant", "manufacturer", "length_m", "description")


class TrunkBreakoutBulkEditForm(NetBoxModelBulkEditForm):
    # Range fields intentionally NOT bulk-editable: re-running the
    # overlap-validation pass across an N-row update is fragile, and
    # operators almost never want to slide every breakout's range at
    # once. Edit them individually.
    trunk = DynamicModelChoiceField(queryset=FibreTrunk.objects.all(), required=False)

    model = TrunkBreakout
    nullable_fields = ("description",)
