from django import forms
from netbox.forms import NetBoxModelBulkEditForm
from utilities.forms.fields import DynamicModelChoiceField

from tenancy.models import Tenant

from ..choices import (
    FibreLinkStatusChoices,
    OspCableTypeChoices,
    OspStatusChoices,
    ClosureTypeChoices,
)
from ..models import FibreLink, OspCable, SpliceClosure


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
