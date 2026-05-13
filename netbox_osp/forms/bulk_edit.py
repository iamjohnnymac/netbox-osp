from django import forms

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
)
from ..models import (
    FibreLink,
    LocationGeo,
    OspCable,
    Splice,
    SpliceClosure,
    SpliceTray,
    Strand,
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
