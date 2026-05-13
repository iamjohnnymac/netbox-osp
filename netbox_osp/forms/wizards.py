"""Multi-step / wizard forms.

These are vanilla `forms.Form` instances — NOT `NetBoxModelForm` — because
the underlying view operates on N candidate rows at once and constructs
the model objects itself inside a `transaction.atomic` block. Following
the same shape as `views.NetworkMapView` (a `forms.Form` carrying a
selection plus a starting position).
"""
from django import forms
from django.conf import settings as dj_settings
from django.forms import formset_factory

from dcim.models import Cable, Device, DeviceRole, DeviceType, Manufacturer, Rack, RearPort
from utilities.forms.fields import DynamicModelChoiceField

from ..choices import TrunkTypeChoices


class ImportCablesIntoTrunkForm(forms.Form):
    """One-screen wizard: select N candidate cables and a starting fibre
    position. The view (`TrunkImportFromCablesView`) assigns sequential
    fibre ranges in order.

    The candidate queryset excludes any Cable already bound to a
    TrunkBreakout, so operators can't accidentally double-allocate a
    cable.
    """
    cables = forms.ModelMultipleChoiceField(
        queryset=Cable.objects.exclude(
            osp_trunk_breakouts__isnull=False,
        ).distinct(),
        widget=forms.CheckboxSelectMultiple,
        label="Cables to attach",
        help_text="Only cables not yet bound to any TrunkBreakout appear here.",
    )
    start_fibre = forms.IntegerField(
        min_value=1,
        initial=1,
        label="Starting fibre position",
        help_text="1-indexed. First cable in the selection grabs "
                  "[start_fibre .. start_fibre + cable.fibre_count - 1]; "
                  "subsequent cables are appended.",
    )


# ============================================================================
# MTP Harness one-click deploy
# ============================================================================

# Fibre-grade subset of NetBox's dcim CableTypeChoices. Operators almost
# always pick one of these for MTP/MPO harness work; the full dcim list
# is exposed via the regular Cable edit form for the rare exception.
_FIBRE_CABLE_TYPE_CHOICES = [
    ("smf", "SMF"),
    ("smf-os2", "SMF OS2"),
    ("mmf-om3", "MMF OM3"),
    ("mmf-om4", "MMF OM4"),
    ("mmf-om5", "MMF OM5"),
]

_DEST_DEVICE_MODE_CHOICES = [
    ("create", "Create new cassette"),
    ("existing", "Reuse existing device"),
]

_DEST_FACE_CHOICES = [
    ("front", "Front"),
    ("rear", "Rear"),
]


def _default_cable_type():
    plugin_settings = dj_settings.PLUGINS_CONFIG.get("netbox_osp", {})
    return plugin_settings.get("default_cable_type", "smf")


class MtpHarnessForm(forms.Form):
    """Parent form for the MTP harness one-click deploy view.

    Captures the trunk-level metadata (CID, type, fibre count, source
    patch-panel rear port) and the deploy-time defaults applied to every
    destination row (cassette device-type, cable type, default cable
    length).

    The destination rows live in a separate formset
    (`MtpHarnessDestinationFormSet`) so the operator can deploy 1..24
    cassettes from one form. See `views.MtpHarnessDeployView`.

    Vanilla `forms.Form` (NOT `NetBoxModelForm`) because the view writes
    to four different model classes (`FibreTrunk`, `dcim.Device`,
    `dcim.Cable`, `TrunkBreakout`) inside one atomic block.
    """

    trunk_cid = forms.CharField(
        max_length=64,
        label="Trunk CID",
        help_text="Operator-facing identifier for the new trunk "
                  "(e.g. MTP-MMR-RACKA-001). Must be unique.",
    )
    trunk_type = forms.ChoiceField(
        choices=TrunkTypeChoices,
        initial=TrunkTypeChoices.MPO_24,
        label="Trunk type",
    )
    fibre_count = forms.IntegerField(
        min_value=1,
        max_value=576,
        initial=24,
        label="Fibre count",
        help_text="Total physical fibres in the trunk. Override the default "
                  "if your trunk type is non-standard.",
    )
    length_m = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label="Trunk length (m)",
        help_text="Optional. Total trunk length in metres.",
    )
    manufacturer = DynamicModelChoiceField(
        queryset=Manufacturer.objects.all(),
        required=False,
        label="Trunk manufacturer",
    )

    # Source patch panel side.
    source_rack = DynamicModelChoiceField(
        queryset=Rack.objects.all(),
        required=True,
        label="Source rack",
        help_text="Rack containing the source patch panel "
                  "(typically the meet-me room).",
    )
    source_device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        required=True,
        label="Source device",
        query_params={"rack_id": "$source_rack"},
        help_text="The patch-panel device the trunk originates from.",
    )
    source_rear_port = DynamicModelChoiceField(
        queryset=RearPort.objects.all(),
        required=True,
        label="Source rear port",
        query_params={
            "device_id": "$source_device",
            "cabled": "false",
        },
        help_text="A free RearPort on the source device. Already-cabled "
                  "ports are filtered out.",
    )

    # Cassette destination defaults.
    cassette_device_type = DynamicModelChoiceField(
        queryset=DeviceType.objects.all(),
        required=True,
        label="Cassette device type",
        help_text="DeviceType deployed at every destination rack. Must have "
                  "at least one RearPort template.",
    )
    cassette_device_role = DynamicModelChoiceField(
        queryset=DeviceRole.objects.all(),
        required=True,
        label="Cassette device role",
        help_text="DeviceRole assigned to every newly-created cassette.",
    )

    cable_type = forms.ChoiceField(
        choices=_FIBRE_CABLE_TYPE_CHOICES,
        initial=_default_cable_type,
        label="Cable type",
        help_text="Applied to every cable in the harness.",
    )
    default_cable_length_m = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label="Default cable length (m)",
        help_text="Pre-fills each destination row's cable length. Per-row "
                  "override allowed.",
    )


class MtpHarnessDestinationForm(forms.Form):
    """One row of the harness-deploy destinations formset.

    Each row spawns: optionally one new `dcim.Device` (when
    `dest_device_mode == 'create'`), one `dcim.Cable` from the parent
    form's `source_rear_port` to this row's RearPort, and one
    `TrunkBreakout` binding the cable to the parent trunk at the chosen
    fibre range.

    Conditional fields (validated in `clean()` rather than at the field
    level because the choice of `dest_device_mode` decides which downstream
    fields are required):

      - `dest_device_mode == 'create'`: requires `dest_device_name`,
        `dest_position_u`, `dest_face`.
      - `dest_device_mode == 'existing'`: requires `dest_device_existing`
        and `dest_rear_port`.
    """

    dest_rack = DynamicModelChoiceField(
        queryset=Rack.objects.all(),
        required=True,
        label="Destination rack",
    )
    dest_device_mode = forms.ChoiceField(
        choices=_DEST_DEVICE_MODE_CHOICES,
        initial="create",
        label="Destination mode",
        help_text='"Create" deploys a new cassette; "Reuse existing" '
                  "cables into a device that already exists in the rack.",
    )

    # 'create' branch fields
    dest_device_name = forms.CharField(
        max_length=64,
        required=False,
        label="New cassette name",
        help_text="Name for the new cassette device. Required when mode is "
                  "'Create new cassette'.",
    )
    dest_position_u = forms.DecimalField(
        max_digits=4,
        decimal_places=1,
        required=False,
        label="Rack position (U)",
        help_text="Rack unit for the new cassette (0.5 increments).",
    )
    dest_face = forms.ChoiceField(
        choices=_DEST_FACE_CHOICES,
        initial="front",
        required=False,
        label="Rack face",
    )

    # 'existing' branch fields
    dest_device_existing = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        required=False,
        label="Existing device",
        query_params={"rack_id": "$dest_rack"},
        help_text="Required when mode is 'Reuse existing device'.",
    )
    dest_rear_port = DynamicModelChoiceField(
        queryset=RearPort.objects.all(),
        required=False,
        label="Destination rear port",
        query_params={
            "device_id": "$dest_device_existing",
            "cabled": "false",
        },
        help_text="Free RearPort on the existing device.",
    )

    # Fibre allocation.
    fibre_range_start = forms.IntegerField(
        min_value=1,
        label="Fibre range start",
        help_text="1-indexed starting fibre position on the parent trunk.",
    )
    fibre_range_end = forms.IntegerField(
        min_value=1,
        label="Fibre range end",
        help_text="Inclusive end fibre position.",
    )

    # Cable per-row metadata.
    cable_label = forms.CharField(
        max_length=100,
        required=False,
        label="Cable label",
        help_text="Optional. Auto-suggest: <trunk_cid>-<dest_rack>.",
    )
    cable_length_m = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label="Cable length (m)",
        help_text="Per-cable physical length. Falls back to the parent "
                  "form's default if blank.",
    )

    def clean(self):
        cleaned = super().clean()
        mode = cleaned.get("dest_device_mode")

        if mode == "create":
            missing = []
            if not cleaned.get("dest_device_name"):
                missing.append(("dest_device_name", "Required when creating a new cassette."))
            if cleaned.get("dest_position_u") in (None, ""):
                missing.append(("dest_position_u", "Required when creating a new cassette."))
            if not cleaned.get("dest_face"):
                missing.append(("dest_face", "Required when creating a new cassette."))
            for field, msg in missing:
                self.add_error(field, msg)
        elif mode == "existing":
            if not cleaned.get("dest_device_existing"):
                self.add_error(
                    "dest_device_existing",
                    "Required when reusing an existing device.",
                )
            if not cleaned.get("dest_rear_port"):
                self.add_error(
                    "dest_rear_port",
                    "Required when reusing an existing device.",
                )

        # Range sanity.
        start = cleaned.get("fibre_range_start")
        end = cleaned.get("fibre_range_end")
        if start is not None and end is not None and end < start:
            self.add_error(
                "fibre_range_end",
                "fibre_range_end must be >= fibre_range_start.",
            )

        return cleaned


MtpHarnessDestinationFormSet = formset_factory(
    MtpHarnessDestinationForm,
    extra=2,
    min_num=1,
    max_num=24,
    validate_min=True,
    validate_max=True,
    can_delete=False,
)
