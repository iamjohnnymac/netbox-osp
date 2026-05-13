from django import forms
from netbox.forms import NetBoxModelFilterSetForm
from utilities.forms.fields import DynamicModelMultipleChoiceField

from dcim.models import Location, Site
from tenancy.models import Tenant

from ..choices import (
    ClosureTypeChoices,
    FibreLinkStatusChoices,
    LocationMarkerColorChoices,
    OspCableTypeChoices,
    OspStatusChoices,
    SpliceTypeChoices,
    StrandStatusChoices,
)
from ..models import (
    FibreLink, LocationGeo, OspCable, Splice, SpliceClosure, SpliceTray, Strand, Tube,
)


class OspCableFilterForm(NetBoxModelFilterSetForm):
    model = OspCable
    type = forms.MultipleChoiceField(choices=OspCableTypeChoices, required=False)
    status = forms.MultipleChoiceField(choices=OspStatusChoices, required=False)
    site_a_id = DynamicModelMultipleChoiceField(queryset=Site.objects.all(), required=False, label="Site A")
    site_b_id = DynamicModelMultipleChoiceField(queryset=Site.objects.all(), required=False, label="Site B")
    tenant_id = DynamicModelMultipleChoiceField(queryset=Tenant.objects.all(), required=False, label="Tenant")


class TubeFilterForm(NetBoxModelFilterSetForm):
    model = Tube
    cable_id = DynamicModelMultipleChoiceField(queryset=OspCable.objects.all(), required=False, label="Cable")


class StrandFilterForm(NetBoxModelFilterSetForm):
    model = Strand
    status = forms.MultipleChoiceField(choices=StrandStatusChoices, required=False)
    cable_id = DynamicModelMultipleChoiceField(queryset=OspCable.objects.all(), required=False, label="Cable")


class SpliceClosureFilterForm(NetBoxModelFilterSetForm):
    model = SpliceClosure
    closure_type = forms.MultipleChoiceField(choices=ClosureTypeChoices, required=False)
    status = forms.MultipleChoiceField(choices=OspStatusChoices, required=False)
    site_id = DynamicModelMultipleChoiceField(queryset=Site.objects.all(), required=False, label="Site")


class SpliceTrayFilterForm(NetBoxModelFilterSetForm):
    model = SpliceTray
    closure_id = DynamicModelMultipleChoiceField(queryset=SpliceClosure.objects.all(), required=False, label="Closure")


class SpliceFilterForm(NetBoxModelFilterSetForm):
    model = Splice
    splice_type = forms.MultipleChoiceField(choices=SpliceTypeChoices, required=False)
    tray_id = DynamicModelMultipleChoiceField(queryset=SpliceTray.objects.all(), required=False, label="Tray")


class FibreLinkFilterForm(NetBoxModelFilterSetForm):
    model = FibreLink
    status = forms.MultipleChoiceField(choices=FibreLinkStatusChoices, required=False)


class LocationGeoFilterForm(NetBoxModelFilterSetForm):
    model = LocationGeo
    location_id = DynamicModelMultipleChoiceField(queryset=Location.objects.all(), required=False, label="Location")
    site_id = DynamicModelMultipleChoiceField(queryset=Site.objects.all(), required=False, label="Site")
    marker_color = forms.MultipleChoiceField(choices=LocationMarkerColorChoices, required=False)
    has_coords = forms.NullBooleanField(required=False, label="Has coords")
