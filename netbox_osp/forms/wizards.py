"""Multi-step / wizard forms.

These are vanilla `forms.Form` instances — NOT `NetBoxModelForm` — because
the underlying view operates on N candidate rows at once and constructs
the model objects itself inside a `transaction.atomic` block. Following
the same shape as `views.NetworkMapView` (a `forms.Form` carrying a
selection plus a starting position).
"""
from django import forms

from dcim.models import Cable


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
