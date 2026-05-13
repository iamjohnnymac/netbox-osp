import json
import os
import sqlite3
import hashlib
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.core.signing import BadSignature, TimestampSigner
from django.db import IntegrityError, transaction
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View

from netbox.views import generic

from . import forms, models, tables, filtersets

# AbortRequest is the exception NetBox's `trace_paths` signal raises when
# a cable path is impossible (UnsupportedCablePath). Canonical path
# confirmed in NetBox 4.6.0 dcim/models/cables.py:24 and 343.
from utilities.exceptions import AbortRequest


# ============================================================================
# OspCable
# ============================================================================

class OspCableView(generic.ObjectView):
    queryset = models.OspCable.objects.all()

    def get_extra_context(self, request, instance):
        strands = instance.strands.select_related("tube", "cable_link").order_by("position")
        tubes = instance.tubes.order_by("number")
        strand_table = tables.StrandTable(strands)
        strand_table.configure(request)
        tube_table = tables.TubeTable(tubes)
        tube_table.configure(request)
        in_use = strands.exclude(status="spare").exclude(status="dark").count()
        return {
            "strand_table": strand_table,
            "tube_table": tube_table,
            "strand_in_use_count": in_use,
        }


class OspCableListView(generic.ObjectListView):
    queryset = models.OspCable.objects.all()
    table = tables.OspCableTable
    filterset = filtersets.OspCableFilterSet
    filterset_form = forms.OspCableFilterForm


class OspCableEditView(generic.ObjectEditView):
    queryset = models.OspCable.objects.all()
    form = forms.OspCableForm
    template_name = "netbox_osp/ospcable_edit.html"


class OspCableDeleteView(generic.ObjectDeleteView):
    queryset = models.OspCable.objects.all()


class OspCableBulkEditView(generic.BulkEditView):
    queryset = models.OspCable.objects.all()
    filterset = filtersets.OspCableFilterSet
    table = tables.OspCableTable
    form = forms.OspCableBulkEditForm


class OspCableBulkDeleteView(generic.BulkDeleteView):
    queryset = models.OspCable.objects.all()
    filterset = filtersets.OspCableFilterSet
    table = tables.OspCableTable


class OspCableBulkImportView(generic.BulkImportView):
    queryset = models.OspCable.objects.all()
    model_form = forms.OspCableImportForm
    table = tables.OspCableTable


# ============================================================================
# Tube
# ============================================================================

class TubeView(generic.ObjectView):
    queryset = models.Tube.objects.all()

    def get_extra_context(self, request, instance):
        strands = instance.strands.order_by("position")
        strand_table = tables.StrandTable(strands)
        strand_table.configure(request)
        return {"strand_table": strand_table}


class TubeListView(generic.ObjectListView):
    queryset = models.Tube.objects.select_related("cable").all()
    table = tables.TubeTable
    filterset = filtersets.TubeFilterSet
    filterset_form = forms.TubeFilterForm


class TubeEditView(generic.ObjectEditView):
    queryset = models.Tube.objects.all()
    form = forms.TubeForm


class TubeDeleteView(generic.ObjectDeleteView):
    queryset = models.Tube.objects.all()


class TubeBulkEditView(generic.BulkEditView):
    queryset = models.Tube.objects.select_related("cable").all()
    filterset = filtersets.TubeFilterSet
    table = tables.TubeTable
    form = forms.TubeBulkEditForm


class TubeBulkDeleteView(generic.BulkDeleteView):
    queryset = models.Tube.objects.select_related("cable").all()
    filterset = filtersets.TubeFilterSet
    table = tables.TubeTable


class TubeBulkImportView(generic.BulkImportView):
    queryset = models.Tube.objects.all()
    model_form = forms.TubeImportForm
    table = tables.TubeTable


# ============================================================================
# Strand
# ============================================================================

class StrandView(generic.ObjectView):
    queryset = models.Strand.objects.select_related("cable", "tube", "cable_link").all()


class StrandListView(generic.ObjectListView):
    queryset = models.Strand.objects.select_related("cable", "tube").all()
    table = tables.StrandTable
    filterset = filtersets.StrandFilterSet
    filterset_form = forms.StrandFilterForm


class StrandEditView(generic.ObjectEditView):
    queryset = models.Strand.objects.all()
    form = forms.StrandForm


class StrandDeleteView(generic.ObjectDeleteView):
    queryset = models.Strand.objects.all()


class StrandBulkEditView(generic.BulkEditView):
    queryset = models.Strand.objects.select_related("cable", "tube").all()
    filterset = filtersets.StrandFilterSet
    table = tables.StrandTable
    form = forms.StrandBulkEditForm


class StrandBulkDeleteView(generic.BulkDeleteView):
    queryset = models.Strand.objects.select_related("cable", "tube").all()
    filterset = filtersets.StrandFilterSet
    table = tables.StrandTable


class StrandBulkImportView(generic.BulkImportView):
    queryset = models.Strand.objects.all()
    model_form = forms.StrandImportForm
    table = tables.StrandTable


# ============================================================================
# SpliceClosure
# ============================================================================

class SpliceClosureView(generic.ObjectView):
    queryset = models.SpliceClosure.objects.all()

    def get_extra_context(self, request, instance):
        trays = instance.trays.order_by("number")
        tray_table = tables.SpliceTrayTable(trays)
        tray_table.configure(request)
        return {"tray_table": tray_table}


class SpliceClosureListView(generic.ObjectListView):
    queryset = models.SpliceClosure.objects.all()
    table = tables.SpliceClosureTable
    filterset = filtersets.SpliceClosureFilterSet
    filterset_form = forms.SpliceClosureFilterForm


class SpliceClosureEditView(generic.ObjectEditView):
    queryset = models.SpliceClosure.objects.all()
    form = forms.SpliceClosureForm


class SpliceClosureDeleteView(generic.ObjectDeleteView):
    queryset = models.SpliceClosure.objects.all()


class SpliceClosureBulkEditView(generic.BulkEditView):
    queryset = models.SpliceClosure.objects.all()
    filterset = filtersets.SpliceClosureFilterSet
    table = tables.SpliceClosureTable
    form = forms.SpliceClosureBulkEditForm


class SpliceClosureBulkDeleteView(generic.BulkDeleteView):
    queryset = models.SpliceClosure.objects.all()
    filterset = filtersets.SpliceClosureFilterSet
    table = tables.SpliceClosureTable


class SpliceClosureBulkImportView(generic.BulkImportView):
    queryset = models.SpliceClosure.objects.all()
    model_form = forms.SpliceClosureImportForm
    table = tables.SpliceClosureTable


# ============================================================================
# SpliceTray
# ============================================================================

class SpliceTrayView(generic.ObjectView):
    queryset = models.SpliceTray.objects.all()

    def get_extra_context(self, request, instance):
        splices = instance.splices.order_by("position").select_related(
            "strand_a__cable", "strand_b__cable"
        )
        splice_table = tables.SpliceTable(splices)
        splice_table.configure(request)
        return {"splice_table": splice_table}


class SpliceTrayListView(generic.ObjectListView):
    queryset = models.SpliceTray.objects.select_related("closure").all()
    table = tables.SpliceTrayTable
    filterset = filtersets.SpliceTrayFilterSet
    filterset_form = forms.SpliceTrayFilterForm


class SpliceTrayEditView(generic.ObjectEditView):
    queryset = models.SpliceTray.objects.all()
    form = forms.SpliceTrayForm


class SpliceTrayDeleteView(generic.ObjectDeleteView):
    queryset = models.SpliceTray.objects.all()


class SpliceTrayBulkEditView(generic.BulkEditView):
    queryset = models.SpliceTray.objects.select_related("closure").all()
    filterset = filtersets.SpliceTrayFilterSet
    table = tables.SpliceTrayTable
    form = forms.SpliceTrayBulkEditForm


class SpliceTrayBulkDeleteView(generic.BulkDeleteView):
    queryset = models.SpliceTray.objects.select_related("closure").all()
    filterset = filtersets.SpliceTrayFilterSet
    table = tables.SpliceTrayTable


class SpliceTrayBulkImportView(generic.BulkImportView):
    queryset = models.SpliceTray.objects.all()
    model_form = forms.SpliceTrayImportForm
    table = tables.SpliceTrayTable


# ============================================================================
# Splice
# ============================================================================

class SpliceView(generic.ObjectView):
    queryset = models.Splice.objects.select_related("tray__closure", "strand_a", "strand_b").all()


class SpliceListView(generic.ObjectListView):
    queryset = models.Splice.objects.select_related("tray__closure").all()
    table = tables.SpliceTable
    filterset = filtersets.SpliceFilterSet
    filterset_form = forms.SpliceFilterForm


class SpliceEditView(generic.ObjectEditView):
    queryset = models.Splice.objects.all()
    form = forms.SpliceForm


class SpliceDeleteView(generic.ObjectDeleteView):
    queryset = models.Splice.objects.all()


class SpliceBulkEditView(generic.BulkEditView):
    queryset = models.Splice.objects.select_related("tray__closure").all()
    filterset = filtersets.SpliceFilterSet
    table = tables.SpliceTable
    form = forms.SpliceBulkEditForm


class SpliceBulkDeleteView(generic.BulkDeleteView):
    queryset = models.Splice.objects.select_related("tray__closure").all()
    filterset = filtersets.SpliceFilterSet
    table = tables.SpliceTable


class SpliceBulkImportView(generic.BulkImportView):
    queryset = models.Splice.objects.all()
    model_form = forms.SpliceImportForm
    table = tables.SpliceTable


# ============================================================================
# FibreLink
# ============================================================================

class FibreLinkView(generic.ObjectView):
    queryset = models.FibreLink.objects.all()

    def get_extra_context(self, request, instance):
        hops = instance.trace()
        return {"hops": hops}


class FibreLinkListView(generic.ObjectListView):
    queryset = models.FibreLink.objects.all()
    table = tables.FibreLinkTable
    filterset = filtersets.FibreLinkFilterSet
    filterset_form = forms.FibreLinkFilterForm


class FibreLinkEditView(generic.ObjectEditView):
    queryset = models.FibreLink.objects.all()
    form = forms.FibreLinkForm


class FibreLinkDeleteView(generic.ObjectDeleteView):
    queryset = models.FibreLink.objects.all()


# ============================================================================
# LocationGeo (per-Location GPS markers)
# ============================================================================

class LocationGeoView(generic.ObjectView):
    queryset = models.LocationGeo.objects.select_related("location__site").all()


class LocationGeoListView(generic.ObjectListView):
    queryset = models.LocationGeo.objects.select_related("location__site").all()
    table = tables.LocationGeoTable
    filterset = filtersets.LocationGeoFilterSet
    filterset_form = forms.LocationGeoFilterForm


class LocationGeoEditView(generic.ObjectEditView):
    queryset = models.LocationGeo.objects.all()
    form = forms.LocationGeoForm


class LocationGeoDeleteView(generic.ObjectDeleteView):
    queryset = models.LocationGeo.objects.all()


class LocationGeoBulkEditView(generic.BulkEditView):
    queryset = models.LocationGeo.objects.select_related("location__site").all()
    filterset = filtersets.LocationGeoFilterSet
    table = tables.LocationGeoTable
    form = forms.LocationGeoBulkEditForm


class LocationGeoBulkDeleteView(generic.BulkDeleteView):
    queryset = models.LocationGeo.objects.select_related("location__site").all()
    filterset = filtersets.LocationGeoFilterSet
    table = tables.LocationGeoTable


class LocationGeoBulkImportView(generic.BulkImportView):
    queryset = models.LocationGeo.objects.all()
    model_form = forms.LocationGeoImportForm
    table = tables.LocationGeoTable


# ============================================================================
# FibreTrunk
# ============================================================================

class FibreTrunkView(generic.ObjectView):
    queryset = models.FibreTrunk.objects.select_related("manufacturer", "tenant").all()

    def get_extra_context(self, request, instance):
        breakouts = (
            instance.breakouts
            .select_related("cable")
            .order_by("fibre_range_start")
        )
        breakout_table = tables.TrunkBreakoutTable(breakouts)
        breakout_table.configure(request)
        return {
            "breakout_table": breakout_table,
        }


class FibreTrunkListView(generic.ObjectListView):
    queryset = models.FibreTrunk.objects.select_related("manufacturer", "tenant").all()
    table = tables.FibreTrunkTable
    filterset = filtersets.FibreTrunkFilterSet
    filterset_form = forms.FibreTrunkFilterForm


class FibreTrunkEditView(generic.ObjectEditView):
    queryset = models.FibreTrunk.objects.all()
    form = forms.FibreTrunkForm


class FibreTrunkDeleteView(generic.ObjectDeleteView):
    queryset = models.FibreTrunk.objects.all()


class FibreTrunkBulkEditView(generic.BulkEditView):
    queryset = models.FibreTrunk.objects.select_related("manufacturer", "tenant").all()
    filterset = filtersets.FibreTrunkFilterSet
    table = tables.FibreTrunkTable
    form = forms.FibreTrunkBulkEditForm


class FibreTrunkBulkDeleteView(generic.BulkDeleteView):
    queryset = models.FibreTrunk.objects.select_related("manufacturer", "tenant").all()
    filterset = filtersets.FibreTrunkFilterSet
    table = tables.FibreTrunkTable


class FibreTrunkBulkImportView(generic.BulkImportView):
    queryset = models.FibreTrunk.objects.all()
    model_form = forms.FibreTrunkImportForm
    table = tables.FibreTrunkTable


# ============================================================================
# TrunkBreakout
# ============================================================================

class TrunkBreakoutView(generic.ObjectView):
    queryset = models.TrunkBreakout.objects.select_related("trunk", "cable").all()


class TrunkBreakoutListView(generic.ObjectListView):
    queryset = models.TrunkBreakout.objects.select_related("trunk", "cable").all()
    table = tables.TrunkBreakoutTable
    filterset = filtersets.TrunkBreakoutFilterSet
    filterset_form = forms.TrunkBreakoutFilterForm


class TrunkBreakoutEditView(generic.ObjectEditView):
    queryset = models.TrunkBreakout.objects.all()
    form = forms.TrunkBreakoutForm


class TrunkBreakoutDeleteView(generic.ObjectDeleteView):
    queryset = models.TrunkBreakout.objects.all()


class TrunkBreakoutBulkEditView(generic.BulkEditView):
    queryset = models.TrunkBreakout.objects.select_related("trunk", "cable").all()
    filterset = filtersets.TrunkBreakoutFilterSet
    table = tables.TrunkBreakoutTable
    form = forms.TrunkBreakoutBulkEditForm


class TrunkBreakoutBulkDeleteView(generic.BulkDeleteView):
    queryset = models.TrunkBreakout.objects.select_related("trunk", "cable").all()
    filterset = filtersets.TrunkBreakoutFilterSet
    table = tables.TrunkBreakoutTable


class TrunkBreakoutBulkImportView(generic.BulkImportView):
    queryset = models.TrunkBreakout.objects.all()
    model_form = forms.TrunkBreakoutImportForm
    table = tables.TrunkBreakoutTable


class TrunkImportFromCablesView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """One-screen wizard: pick a set of dcim.Cables not yet bound to any
    TrunkBreakout, and assign sequential fibre ranges starting from
    `start_fibre`. Atomic — all-or-nothing.
    """
    permission_required = "netbox_osp.add_trunkbreakout"
    template_name = "netbox_osp/trunk_import_cables.html"
    form_class = forms.ImportCablesIntoTrunkForm

    def _get_trunk(self, pk):
        return get_object_or_404(models.FibreTrunk, pk=pk)

    def get(self, request, pk):
        trunk = self._get_trunk(pk)
        form = self.form_class()
        return render(request, self.template_name, {
            "trunk": trunk,
            "form": form,
        })

    def post(self, request, pk):
        trunk = self._get_trunk(pk)
        form = self.form_class(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {
                "trunk": trunk,
                "form": form,
            })

        cables = list(form.cleaned_data["cables"])
        cursor = form.cleaned_data["start_fibre"]

        try:
            with transaction.atomic():
                created = []
                for cable in cables:
                    # Each cable consumes its own fibre_count; we look at
                    # the dcim.Cable's length-of-rope semantics (cables
                    # don't carry an explicit fibre count, so default to
                    # 1 — operators can re-edit if needed). The wizard's
                    # primary use case is multi-cable assignment with
                    # operator-driven fibre sizing per row, so for v0.2
                    # we keep the default-1 fallback and let the operator
                    # edit individual breakouts afterwards.
                    fibre_size = getattr(cable, "fibre_count", None) or 1
                    end = cursor + fibre_size - 1
                    br = models.TrunkBreakout(
                        trunk=trunk,
                        cable=cable,
                        fibre_range_start=cursor,
                        fibre_range_end=end,
                    )
                    br.full_clean()
                    br.save()
                    created.append(br)
                    cursor = end + 1
        except ValidationError as exc:
            # Surface the first keyed error against the form
            # (atomic block already rolled back).
            if hasattr(exc, "message_dict"):
                for field, errs in exc.message_dict.items():
                    for e in errs:
                        form.add_error(None, f"{field}: {e}")
            else:
                form.add_error(None, "; ".join(exc.messages))
            return render(request, self.template_name, {
                "trunk": trunk,
                "form": form,
            })
        except IntegrityError as exc:
            # Race condition: another operator bound the same cable or
            # fibre_range_start to this trunk between our clean() and our
            # save(). unique_together at DB layer kicks in. Atomic block
            # rolled back; surface as a friendly form error.
            form.add_error(
                None,
                "Another operator just attached one of these cables to this "
                "trunk. Reload and try again."
            )
            return render(request, self.template_name, {
                "trunk": trunk,
                "form": form,
            })

        messages.success(
            request,
            f"Created {len(created)} TrunkBreakout row(s) on {trunk.cid}.",
        )
        return redirect(trunk.get_absolute_url())


# ============================================================================
# MTP Harness one-click deploy
# ============================================================================

# Signer namespace for the preview-state token. The same secret-key derived
# signer is used for both signing (after the validate step) and verifying
# (on the confirm step). The salt is fixed per-view so tokens minted by
# this view can't be replayed against another signed-state endpoint.
_HARNESS_STATE_SIGNER = TimestampSigner(salt="netbox_osp.mtp_harness.preview")


def _free_rear_ports_for_device(device):
    """Return RearPorts on `device` that aren't cabled yet, ordered by name.

    NetBox 4.6 wires cables to terminations via CableTermination
    (GenericForeignKey), not a direct FK on RearPort. So we need an
    inverse-pk exclusion rather than `cable__isnull=True`.
    """
    from django.contrib.contenttypes.models import ContentType

    from dcim.models import CableTermination, RearPort

    rp_ct = ContentType.objects.get_for_model(RearPort)
    cabled_pks = list(
        CableTermination.objects
        .filter(termination_type=rp_ct)
        .values_list("termination_id", flat=True)
    )
    return RearPort.objects.filter(device=device).exclude(
        pk__in=cabled_pks
    ).order_by("name")


def _count_free_rear_ports(device):
    return _free_rear_ports_for_device(device).count()

# Max age (seconds) for a preview-state token. The operator has ten
# minutes between previewing and confirming, after which they have to
# re-validate. Defends against stale tabs.
_HARNESS_STATE_MAX_AGE = 600


def _sign_harness_state(payload: dict) -> str:
    """Return a timestamped, signed JSON token of `payload`.

    Used to round-trip the cleaned form state between the preview and
    confirm steps without trusting the operator's browser. The signer
    derives from SECRET_KEY so any tampering is detectable.
    """
    raw = json.dumps(payload, default=str, sort_keys=True)
    return _HARNESS_STATE_SIGNER.sign(raw)


def _unsign_harness_state(token: str) -> dict | None:
    """Verify a previously-signed state token and return its payload.

    Returns None on tampered / expired tokens. Callers should treat that
    as "operator's preview state is stale; restart the form" rather than
    a hard error.
    """
    try:
        raw = _HARNESS_STATE_SIGNER.unsign(token, max_age=_HARNESS_STATE_MAX_AGE)
    except BadSignature:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


class MtpHarnessDeployView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """One-click MTP harness deploy.

    A single form submit creates the parent `FibreTrunk` + N cassette
    `dcim.Device`s + N `dcim.Cable`s + N `TrunkBreakout`s atomically.
    Replaces ~30 individual NetBox object writes with one form.

    Flow:
      - GET → render empty parent form + destinations formset.
      - POST without `confirm=1` → validate form + formset + cross-form
        rules. On success render the preview page with a signed state
        token embedded in a hidden field. On failure re-render the form
        with errors.
      - POST with `confirm=1` → verify the signed state token, then run
        the atomic deploy. On success redirect to the new trunk's detail
        page; on validation / integrity / cable-path failure re-render
        the form with errors.

    Mirrors `TrunkImportFromCablesView` for the exception-ladder shape:
    `ValidationError` → form-keyed error, `IntegrityError` → friendly
    race-condition message, `AbortRequest` → cable-path-impossible
    message.
    """

    permission_required = (
        "netbox_osp.add_fibretrunk",
        "netbox_osp.add_trunkbreakout",
        "dcim.add_cable",
    )
    template_name = "netbox_osp/mtp_harness_deploy.html"
    preview_template_name = "netbox_osp/mtp_harness_preview.html"

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _validate_harness(parent_form, dest_formset):
        """Cross-form validation that doesn't belong on a single form.

        Runs after both forms' `is_valid()` calls pass. Errors are added
        directly to the form fields they correspond to so the operator
        sees them on the right input.
        """
        cleaned_rows = [
            row for row in dest_formset.cleaned_data
            if row and not row.get("DELETE")
        ]
        if not cleaned_rows:
            dest_formset._non_form_errors = dest_formset.error_class(
                ["At least one destination row is required."]
            )
            return False

        ok = True

        # 1. Duplicate destination racks.
        rack_pks = [row["dest_rack"].pk for row in cleaned_rows]
        if len(set(rack_pks)) != len(rack_pks):
            dest_formset._non_form_errors = dest_formset.error_class(
                ["Each destination rack must be unique."]
            )
            ok = False

        # 2. Sum of fibre ranges <= trunk.fibre_count.
        trunk_fc = parent_form.cleaned_data["fibre_count"]
        total = sum(
            (row["fibre_range_end"] - row["fibre_range_start"] + 1)
            for row in cleaned_rows
        )
        if total > trunk_fc:
            parent_form.add_error(
                "fibre_count",
                f"Destination breakouts sum to {total} fibres but "
                f"trunk fibre_count={trunk_fc}.",
            )
            ok = False

        # 3. No overlapping fibre ranges across rows.
        sorted_rows = sorted(cleaned_rows, key=lambda r: r["fibre_range_start"])
        for i in range(1, len(sorted_rows)):
            prev = sorted_rows[i - 1]
            cur = sorted_rows[i]
            if cur["fibre_range_start"] <= prev["fibre_range_end"]:
                # Find the formset index of the offending row to attach
                # the error to the right form.
                for idx, form in enumerate(dest_formset.forms):
                    if (
                        form.cleaned_data
                        and form.cleaned_data.get("fibre_range_start") == cur["fibre_range_start"]
                        and form.cleaned_data.get("fibre_range_end") == cur["fibre_range_end"]
                    ):
                        dest_formset.forms[idx].add_error(
                            "fibre_range_start",
                            f"range [{cur['fibre_range_start']}-"
                            f"{cur['fibre_range_end']}] overlaps with "
                            f"[{prev['fibre_range_start']}-{prev['fibre_range_end']}].",
                        )
                        break
                ok = False
                break

        # 4. Source device has enough free RearPorts for all destinations.
        # Each destination consumes one source-side RearPort. NetBox 4.6
        # stores cable terminations via GenericForeignKey on
        # CableTermination, so we filter by the inverse-pk set rather
        # than the (non-existent) cable FK on RearPort itself.
        source_device = parent_form.cleaned_data.get("source_device")
        if source_device is not None:
            free_count = _count_free_rear_ports(source_device)
            if free_count < len(cleaned_rows):
                parent_form.add_error(
                    "source_device",
                    f"Source device has {free_count} free RearPort(s) but "
                    f"the harness needs {len(cleaned_rows)}. Pick a device "
                    "with more free ports, or remove destination rows.",
                )
                ok = False

        return ok

    @staticmethod
    def _serialise_state(parent_form, dest_formset):
        """Capture the cleaned data of the parent form + each destination
        row into a primitive-only dict suitable for signing into a
        TimestampSigner token.

        ModelChoice instances are reduced to PKs; everything else is
        passed through `default=str` in `_sign_harness_state` for JSON
        compatibility.
        """
        def _pk_or_none(obj):
            return obj.pk if obj is not None else None

        parent = parent_form.cleaned_data
        parent_payload = {
            "trunk_cid": parent["trunk_cid"],
            "trunk_type": parent["trunk_type"],
            "fibre_count": parent["fibre_count"],
            "length_m": str(parent["length_m"]) if parent.get("length_m") is not None else None,
            "manufacturer": _pk_or_none(parent.get("manufacturer")),
            "source_rack": _pk_or_none(parent.get("source_rack")),
            "source_device": _pk_or_none(parent.get("source_device")),
            "cassette_device_type": _pk_or_none(parent.get("cassette_device_type")),
            "cassette_device_role": _pk_or_none(parent.get("cassette_device_role")),
            "cable_type": parent["cable_type"],
            "default_cable_length_m": (
                str(parent["default_cable_length_m"])
                if parent.get("default_cable_length_m") is not None else None
            ),
        }

        rows_payload = []
        for row in dest_formset.cleaned_data:
            if not row or row.get("DELETE"):
                continue
            rows_payload.append({
                "dest_rack": _pk_or_none(row.get("dest_rack")),
                "dest_device_mode": row.get("dest_device_mode"),
                "dest_device_name": row.get("dest_device_name") or "",
                "dest_position_u": (
                    str(row["dest_position_u"])
                    if row.get("dest_position_u") is not None else None
                ),
                "dest_face": row.get("dest_face") or "",
                "dest_device_existing": _pk_or_none(row.get("dest_device_existing")),
                "dest_rear_port": _pk_or_none(row.get("dest_rear_port")),
                "fibre_range_start": row["fibre_range_start"],
                "fibre_range_end": row["fibre_range_end"],
                "cable_label": row.get("cable_label") or "",
                "cable_length_m": (
                    str(row["cable_length_m"])
                    if row.get("cable_length_m") is not None else None
                ),
            })

        return {"parent": parent_payload, "rows": rows_payload}

    @staticmethod
    def _resolve_state(payload):
        """Turn a deserialised signed-state payload back into the model
        instances and primitive values the deploy step needs.

        Returns a `(parent_resolved, rows_resolved)` tuple or raises
        ValidationError if any FK target has been deleted between preview
        and confirm.
        """
        from decimal import Decimal

        from dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Rack, RearPort

        def _decimal(s):
            return Decimal(s) if s not in (None, "") else None

        def _fetch(model, pk, label):
            if pk is None:
                return None
            try:
                return model.objects.get(pk=pk)
            except model.DoesNotExist as exc:
                raise ValidationError(
                    f"{label} (pk={pk}) was deleted between preview and "
                    "confirm. Reload the form."
                ) from exc

        parent = payload["parent"]
        parent_resolved = {
            "trunk_cid": parent["trunk_cid"],
            "trunk_type": parent["trunk_type"],
            "fibre_count": parent["fibre_count"],
            "length_m": _decimal(parent.get("length_m")),
            "manufacturer": _fetch(Manufacturer, parent.get("manufacturer"), "Manufacturer"),
            "source_rack": _fetch(Rack, parent.get("source_rack"), "Source rack"),
            "source_device": _fetch(Device, parent.get("source_device"), "Source device"),
            "cassette_device_type": _fetch(
                DeviceType, parent.get("cassette_device_type"), "Cassette device type",
            ),
            "cassette_device_role": _fetch(
                DeviceRole, parent.get("cassette_device_role"), "Cassette device role",
            ),
            "cable_type": parent["cable_type"],
            "default_cable_length_m": _decimal(parent.get("default_cable_length_m")),
        }

        rows_resolved = []
        for row in payload.get("rows", []):
            rows_resolved.append({
                "dest_rack": _fetch(Rack, row.get("dest_rack"), "Destination rack"),
                "dest_device_mode": row["dest_device_mode"],
                "dest_device_name": row.get("dest_device_name") or "",
                "dest_position_u": _decimal(row.get("dest_position_u")),
                "dest_face": row.get("dest_face") or "",
                "dest_device_existing": _fetch(
                    Device, row.get("dest_device_existing"), "Existing destination device",
                ),
                "dest_rear_port": _fetch(
                    RearPort, row.get("dest_rear_port"), "Destination rear port",
                ),
                "fibre_range_start": row["fibre_range_start"],
                "fibre_range_end": row["fibre_range_end"],
                "cable_label": row.get("cable_label") or "",
                "cable_length_m": _decimal(row.get("cable_length_m")),
            })

        return parent_resolved, rows_resolved

    def _build_preview_rows(self, parent_resolved, rows_resolved):
        """Pre-compute a list of dicts describing what WOULD be created
        in the deploy step. Rendered on the preview template so the
        operator sees the full plan before committing."""
        preview_rows = []
        for row in rows_resolved:
            if row["dest_device_mode"] == "create":
                device_desc = (
                    f"NEW {row['dest_device_name']} "
                    f"({parent_resolved['cassette_device_type']}) "
                    f"in rack {row['dest_rack']} @ U{row['dest_position_u']} "
                    f"({row['dest_face']})"
                )
            else:
                device_desc = f"existing {row['dest_device_existing']}"

            preview_rows.append({
                "rack": row["dest_rack"],
                "device": device_desc,
                "rear_port": (
                    row["dest_rear_port"]
                    if row["dest_device_mode"] == "existing"
                    else "(first RearPort of new cassette)"
                ),
                "fibre_range": f"[{row['fibre_range_start']}-{row['fibre_range_end']}]",
                "cable_label": (
                    row["cable_label"]
                    or f"{parent_resolved['trunk_cid']}-{row['dest_rack']}"
                ),
                "cable_length_m": (
                    row["cable_length_m"]
                    or parent_resolved["default_cable_length_m"]
                ),
            })

        return preview_rows

    def _deploy(self, parent_resolved, rows_resolved):
        """Run the atomic deploy. Returns `(trunk, created_devices,
        created_cables, created_breakouts)` on success. Any failure
        propagates as the original exception so the caller's exception
        ladder can format the message.
        """
        from dcim.models import Cable
        # NetBox 4.6 stores cable status on `LinkStatusChoices` in
        # `dcim.choices`; the actual string value is "connected".
        cable_status_connected = "connected"

        # Auto-pick one free source-side RearPort per destination row,
        # alphabetical by RearPort name. _validate_harness() has already
        # confirmed there are enough free ports — but keep this guard so
        # a race between preview and confirm fails cleanly.
        source_device = parent_resolved["source_device"]
        source_rps = list(
            _free_rear_ports_for_device(source_device)[:len(rows_resolved)]
        )
        if len(source_rps) < len(rows_resolved):
            raise ValidationError({
                "source_device":
                f"Source device has only {len(source_rps)} free RearPort(s) "
                f"but {len(rows_resolved)} destinations were requested. "
                "Another operator may have cabled one between preview and "
                "confirm — reload and retry.",
            })

        with transaction.atomic():
            # Step 1: parent FibreTrunk.
            from .choices import OspStatusChoices
            trunk = models.FibreTrunk(
                cid=parent_resolved["trunk_cid"],
                trunk_type=parent_resolved["trunk_type"],
                fibre_count=parent_resolved["fibre_count"],
                length_m=parent_resolved.get("length_m"),
                manufacturer=parent_resolved.get("manufacturer"),
                status=OspStatusChoices.STATUS_PLANNED,
            )
            trunk.full_clean()
            trunk.save()

            created_devices = []
            created_cables = []
            created_breakouts = []

            for row, source_rp in zip(rows_resolved, source_rps):
                # Step 2a: resolve destination device + RearPort.
                if row["dest_device_mode"] == "create":
                    from dcim.models import Device
                    dev = Device(
                        site=row["dest_rack"].site,
                        rack=row["dest_rack"],
                        device_type=parent_resolved["cassette_device_type"],
                        role=parent_resolved["cassette_device_role"],
                        name=row["dest_device_name"],
                        position=row["dest_position_u"],
                        face=row["dest_face"],
                        status="active",
                    )
                    dev.full_clean()
                    dev.save()
                    created_devices.append(dev)

                    # `save()` auto-spawns the device-type's components.
                    # Pick the first RearPort (alpha by name).
                    dest_rp = dev.rearports.order_by("name").first()
                    if dest_rp is None:
                        raise ValidationError({
                            "cassette_device_type":
                            "Cassette device-type has no RearPort "
                            "templates. Pick a device-type with at least "
                            "one RearPort.",
                        })
                else:
                    dest_rp = row["dest_rear_port"]

                # Step 2b: dcim.Cable from source_rp -> dest_rp.
                effective_length = (
                    row.get("cable_length_m")
                    or parent_resolved.get("default_cable_length_m")
                )
                cable = Cable(
                    type=parent_resolved["cable_type"],
                    status=cable_status_connected,
                    label=row.get("cable_label") or "",
                    length=effective_length,
                    length_unit="m" if effective_length is not None else None,
                )
                cable.a_terminations = [source_rp]
                cable.b_terminations = [dest_rp]
                cable.full_clean()
                cable.save()
                created_cables.append(cable)

                # Step 2c: TrunkBreakout binding cable to trunk.
                br = models.TrunkBreakout(
                    trunk=trunk,
                    cable=cable,
                    fibre_range_start=row["fibre_range_start"],
                    fibre_range_end=row["fibre_range_end"],
                )
                br.full_clean()
                br.save()
                created_breakouts.append(br)

        return trunk, created_devices, created_cables, created_breakouts

    @staticmethod
    def _render_form_errors_for_validation(parent_form, dest_formset, exc):
        """Surface a ValidationError raised inside the atomic block onto
        the parent form's non-field errors. Used after rollback so the
        operator sees a coherent error message at the top of the page.
        """
        if hasattr(exc, "message_dict"):
            for field, errs in exc.message_dict.items():
                for e in errs:
                    parent_form.add_error(None, f"{field}: {e}")
        else:
            parent_form.add_error(None, "; ".join(exc.messages))

    # -- request dispatch ----------------------------------------------------

    def get(self, request):
        parent_form = forms.MtpHarnessForm()
        dest_formset = forms.MtpHarnessDestinationFormSet()
        return render(request, self.template_name, {
            "form": parent_form,
            "formset": dest_formset,
        })

    def post(self, request):
        import sys
        print(f"[HARNESS-DEBUG] post() entered, confirm={request.POST.get('confirm')!r}", file=sys.stderr, flush=True)
        print(f"[HARNESS-DEBUG] post() keys={sorted(request.POST.keys())[:15]}", file=sys.stderr, flush=True)
        if request.POST.get("confirm") == "1":
            return self._post_confirm(request)
        return self._post_preview(request)

    def _post_preview(self, request):
        """Validate the form. On success render the preview template
        with a signed state token; on failure re-render the edit form
        with field errors.
        """
        import sys
        print("[HARNESS-DEBUG] _post_preview entered", file=sys.stderr, flush=True)
        parent_form = forms.MtpHarnessForm(request.POST)
        dest_formset = forms.MtpHarnessDestinationFormSet(request.POST)

        parent_valid = parent_form.is_valid()
        formset_valid = dest_formset.is_valid()
        print(f"[HARNESS-DEBUG] parent_valid={parent_valid} errors={dict(parent_form.errors)}", file=sys.stderr, flush=True)
        print(f"[HARNESS-DEBUG] formset_valid={formset_valid} errors={[dict(f.errors) for f in dest_formset.forms]}", file=sys.stderr, flush=True)
        forms_valid = parent_valid & formset_valid
        cross_ok = forms_valid and self._validate_harness(parent_form, dest_formset)
        print(f"[HARNESS-DEBUG] forms_valid={forms_valid} cross_ok={cross_ok}", file=sys.stderr, flush=True)

        if not (forms_valid and cross_ok):
            print("[HARNESS-DEBUG] returning re-rendered form (validation failed)", file=sys.stderr, flush=True)
            return render(request, self.template_name, {
                "form": parent_form,
                "formset": dest_formset,
            })

        # Forms are clean. Sign the state and render the preview page.
        payload = self._serialise_state(parent_form, dest_formset)
        state_token = _sign_harness_state(payload)

        # Resolve once for the preview rows so the operator sees real
        # object labels rather than PKs.
        try:
            parent_resolved, rows_resolved = self._resolve_state(payload)
        except ValidationError as exc:
            self._render_form_errors_for_validation(parent_form, dest_formset, exc)
            return render(request, self.template_name, {
                "form": parent_form,
                "formset": dest_formset,
            })

        preview_rows = self._build_preview_rows(parent_resolved, rows_resolved)

        return render(request, self.preview_template_name, {
            "parent": parent_resolved,
            "preview_rows": preview_rows,
            "state_token": state_token,
        })

    def _post_confirm(self, request):
        """Verify the signed state token, then run the atomic deploy."""
        import sys
        print(f"[HARNESS-DEBUG] _post_confirm entered, token len={len(request.POST.get('state_token') or '')}", file=sys.stderr, flush=True)
        token = request.POST.get("state_token") or ""
        payload = _unsign_harness_state(token)
        print(f"[HARNESS-DEBUG] payload is None: {payload is None}", file=sys.stderr, flush=True)
        if payload is None:
            print("[HARNESS-DEBUG] redirecting: invalid/expired state", file=sys.stderr, flush=True)
            messages.error(
                request,
                "Preview state was invalid or expired. Please restart "
                "the harness deploy form.",
            )
            return redirect("plugins:netbox_osp:mtp_harness_deploy")

        try:
            parent_resolved, rows_resolved = self._resolve_state(payload)
        except ValidationError as exc:
            print(f"[HARNESS-DEBUG] _resolve_state ValidationError: {exc}", file=sys.stderr, flush=True)
            messages.error(request, "; ".join(exc.messages))
            return redirect("plugins:netbox_osp:mtp_harness_deploy")
        print(f"[HARNESS-DEBUG] resolved OK, rows={len(rows_resolved)}, entering deploy", file=sys.stderr, flush=True)

        # Build empty bound forms for the rollback-path render so the
        # operator sees the original values + the error message at the
        # top of the page rather than a blank form.
        parent_form = forms.MtpHarnessForm()
        dest_formset = forms.MtpHarnessDestinationFormSet()

        try:
            trunk, devs, cables, breakouts = self._deploy(parent_resolved, rows_resolved)
        except ValidationError as exc:
            import sys
            print(f"[HARNESS-DEBUG] _deploy ValidationError: {exc}", file=sys.stderr, flush=True)
            self._render_form_errors_for_validation(parent_form, dest_formset, exc)
            return render(request, self.template_name, {
                "form": parent_form,
                "formset": dest_formset,
            })
        except IntegrityError:
            parent_form.add_error(
                None,
                "Another operator just modified one of the resources "
                "referenced by this harness (trunk CID, source port, rack "
                "position, or cable). Reload and try again.",
            )
            return render(request, self.template_name, {
                "form": parent_form,
                "formset": dest_formset,
            })
        except AbortRequest as exc:
            parent_form.add_error(None, f"Cable path invalid: {exc}")
            return render(request, self.template_name, {
                "form": parent_form,
                "formset": dest_formset,
            })

        messages.success(
            request,
            f"Deployed harness {trunk.cid}: "
            f"{len(breakouts)} breakout(s), "
            f"{len(devs)} new cassette(s), "
            f"{len(cables)} cable(s).",
        )
        return redirect(trunk.get_absolute_url())


# ============================================================================
# Network Map
# ============================================================================

class NetworkMapView(LoginRequiredMixin, View):
    """Render the full-screen Leaflet map. JS hydrates from /map/data/."""
    template_name = "netbox_osp/network_map.html"

    def get(self, request):
        from django.shortcuts import render
        from django.conf import settings as dj_settings
        plugin_config = dj_settings.PLUGINS_CONFIG.get("netbox_osp", {})
        return render(request, self.template_name, {
            "map_center": plugin_config.get("map_default_center", [0.0, 0.0]),
            "map_zoom": plugin_config.get("map_default_zoom", 2),
        })


class NetworkMapDataView(LoginRequiredMixin, View):
    """Return GeoJSON FeatureCollection: sites (as Points), osp cables (as LineStrings),
    and splice closures (as Points). Filterable by ?site=&status=&type=."""

    def get(self, request):
        from dcim.models import Site
        from django.db.models import Q
        from ._geo_helpers import build_map_geojson

        site_ids = request.GET.getlist("site")
        statuses = request.GET.getlist("status")
        types = request.GET.getlist("type")

        cables_qs = models.OspCable.objects.select_related("site_a", "site_b")
        if site_ids:
            cables_qs = cables_qs.filter(
                Q(site_a_id__in=site_ids) | Q(site_b_id__in=site_ids)
            )
        if statuses:
            cables_qs = cables_qs.filter(status__in=statuses)
        if types:
            cables_qs = cables_qs.filter(type__in=types)

        # Only surface sites that actually appear as an OSP cable endpoint —
        # otherwise the map auto-fit pulls in unrelated sites and zooms way
        # out past the tile coverage area.
        cable_site_ids = set(cables_qs.values_list("site_a_id", flat=True)) | set(
            cables_qs.values_list("site_b_id", flat=True)
        )
        sites_qs = (
            Site.objects
            .filter(pk__in=cable_site_ids)
            .exclude(latitude__isnull=True)
            .exclude(longitude__isnull=True)
        )
        if site_ids:
            sites_qs = sites_qs.filter(pk__in=site_ids)
        closures_qs = models.SpliceClosure.objects.exclude(location_point__isnull=True)

        # LocationGeo: only those with both coords set, filtered by site if asked.
        loc_geos_qs = (
            models.LocationGeo.objects
            .select_related("location__site")
            .exclude(latitude__isnull=True)
            .exclude(longitude__isnull=True)
        )
        if site_ids:
            loc_geos_qs = loc_geos_qs.filter(location__site_id__in=site_ids)

        return JsonResponse(build_map_geojson(sites_qs, cables_qs, closures_qs, loc_geos_qs))


# ============================================================================
# Tile proxy (offline MBTiles)
# ============================================================================

import threading

_MBTILES_LOCAL = threading.local()


def _open_mbtiles(path):
    """Open one connection per thread per file. SQLite is fine for read-only
    concurrent access as long as each thread has its own handle."""
    cache = getattr(_MBTILES_LOCAL, "conns", None)
    if cache is None:
        cache = {}
        _MBTILES_LOCAL.conns = cache
    conn = cache.get(path)
    if conn is None:
        conn = sqlite3.connect(path, check_same_thread=False, uri=False)
        cache[path] = conn
    return conn


class TileProxyView(LoginRequiredMixin, View):
    """Serve a single tile from a bundled MBTiles file.

    MBTiles uses TMS y-axis (origin bottom-left); Leaflet uses XYZ (top-left).
    Convert: tms_y = (2^z - 1) - y.

    Lookup order:
      1. MEDIA_ROOT/osp_tiles/*.mbtiles (user-supplied high-res overlays)
      2. <plugin>/static/netbox_osp/tiles/basemap.mbtiles
    """

    def get(self, request, z, x, y, ext):
        if ext.lower() not in ("png", "jpg", "jpeg", "webp"):
            return HttpResponseNotFound("unsupported tile extension")

        tms_y = (1 << z) - 1 - y

        candidate_paths = []
        media_dir = Path(getattr(settings, "MEDIA_ROOT", "/opt/netbox/netbox/media")) / "osp_tiles"
        if media_dir.is_dir():
            candidate_paths.extend(sorted(media_dir.glob("*.mbtiles")))
        plugin_tiles = Path(__file__).parent / "static" / "netbox_osp" / "tiles"
        if plugin_tiles.is_dir():
            # All *.mbtiles in the plugin tiles dir, alpha-sorted, but with
            # basemap.mbtiles forced last so real-imagery bundles override
            # the stub fallback when keys overlap (e.g. z=0).
            files = [p for p in plugin_tiles.glob("*.mbtiles") if p.name != "basemap.mbtiles"]
            candidate_paths.extend(sorted(files))
            basemap = plugin_tiles / "basemap.mbtiles"
            if basemap.is_file():
                candidate_paths.append(basemap)

        tile_blob = None
        for p in candidate_paths:
            try:
                conn = _open_mbtiles(str(p))
                row = conn.execute(
                    "SELECT tile_data FROM tiles "
                    "WHERE zoom_level=? AND tile_column=? AND tile_row=?",
                    (z, x, tms_y),
                ).fetchone()
                if row is not None:
                    tile_blob = row[0]
                    break
            except sqlite3.Error:
                continue

        if tile_blob is None:
            # 1x1 transparent PNG so the map doesn't show 404s in F12
            blank = bytes.fromhex(
                "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
                "890000000d49444154789c63600000000005000160d4a83f0000000049454e44"
                "ae426082"
            )
            resp = HttpResponse(blank, content_type="image/png")
            resp["Cache-Control"] = "public, max-age=86400"
            return resp

        etag = hashlib.md5(tile_blob).hexdigest()
        if request.META.get("HTTP_IF_NONE_MATCH") == f'"{etag}"':
            return HttpResponse(status=304)

        if ext.lower() in ("jpg", "jpeg"):
            content_type = "image/jpeg"
        elif ext.lower() == "webp":
            content_type = "image/webp"
        else:
            content_type = "image/png"

        resp = HttpResponse(tile_blob, content_type=content_type)
        resp["ETag"] = f'"{etag}"'
        resp["Cache-Control"] = "public, max-age=31536000, immutable"
        return resp
