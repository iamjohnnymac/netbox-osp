"""FibreTrunk: multi-fibre rack-to-rack physical trunk.

PR A of the v0.2.0 cycle. FibreTrunk is the parent model for trunks like
MPO/MTP 12/24/72-fibre bundles, ribbon 144-fibre, or loose-tube indoor
runs between racks. Subsequent PRs build on this:
- PR B adds the `TrunkBreakout` through-table bridging to `dcim.Cable`.
- PR C adds the `MtpHarness` one-click deploy form.
- PR D ships cassette device-type JSON.
- PR E adds the visual core tracer.

PR A scope is the **parent model only** — no relationship to `dcim.Cable`
yet, no breakout children, no auto-computed route length, no map render.
The `route` GeoJSON field is shipped from the start because outdoor /
inter-building trunks benefit from it; intra-plant trunks just leave it
null. Operators can opt-out of map rendering via `show_on_map=False`.

Note on `fibre_count`: this is the source of truth for the trunk's
capacity. PR B's `TrunkBreakout` will validate `fibre_range_end <=
trunk.fibre_count`. If operators downsize `fibre_count` after assigning
breakouts the validation will catch it then — flagged here for PR B.

Note on auto-length: unlike `OspCable.save()`, FibreTrunk does not
auto-compute a `route_length_m` because trunks rarely carry a meaningful
geographic route. If a real use case emerges we'll add the field in a
follow-up migration.
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from netbox.models import NetBoxModel

from ..choices import OspStatusChoices, TrunkTypeChoices
from ._geo import validate_linestring


class FibreTrunk(NetBoxModel):
    cid = models.CharField(
        max_length=64,
        unique=True,
        help_text="Trunk ID (e.g. MTP-MMR-RACKA-001).",
    )
    trunk_type = models.CharField(
        max_length=32,
        choices=TrunkTypeChoices,
        default=TrunkTypeChoices.MPO_24,
    )
    fibre_count = models.PositiveSmallIntegerField(
        default=24,
        help_text="Total physical fibres in the trunk. Source of truth for "
                  "breakout-range validation in PR B.",
    )
    manufacturer = models.ForeignKey(
        "dcim.Manufacturer",
        related_name="fibre_trunks",
        on_delete=models.PROTECT,
        null=True, blank=True,
    )
    length_m = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Operator-supplied length in metres (decimal — patches "
                  "are often sub-metre).",
    )
    status = models.CharField(
        max_length=32,
        choices=OspStatusChoices,
        default=OspStatusChoices.STATUS_PLANNED,
    )
    route = models.JSONField(
        null=True, blank=True,
        help_text="Optional GeoJSON LineString in WGS84 ([lon, lat] order). "
                  "Useful for outdoor / inter-building trunks; leave null "
                  "for intra-plant patches.",
    )
    show_on_map = models.BooleanField(
        default=True,
        help_text="Whether to render this trunk's route on the network map. "
                  "Set to False to hide a draft route without nulling it.",
    )
    description = models.CharField(max_length=200, blank=True, default="")
    comments = models.TextField(blank=True, default="")
    tenant = models.ForeignKey(
        "tenancy.Tenant",
        related_name="fibre_trunks",
        on_delete=models.PROTECT,
        null=True, blank=True,
    )

    clone_fields = (
        "trunk_type", "fibre_count", "manufacturer", "status",
        "tenant", "show_on_map",
    )

    class Meta:
        ordering = ("cid",)
        verbose_name = "Fibre Trunk"
        verbose_name_plural = "Fibre Trunks"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(fibre_count__gt=0),
                name="fibretrunk_fibre_count_positive",
            ),
        ]

    def __str__(self):
        return self.cid

    def get_absolute_url(self):
        return reverse("plugins:netbox_osp:fibretrunk", args=[self.pk])

    def get_status_color(self):
        return OspStatusChoices.colors.get(self.status)

    def get_trunk_type_color(self):
        return TrunkTypeChoices.colors.get(self.trunk_type)

    def clean(self):
        super().clean()
        if self.route is not None:
            # Wrap shape-validation so the error surfaces on the `route`
            # form field rather than as a non-field error.
            try:
                validate_linestring(self.route)
            except ValidationError as exc:
                raise ValidationError({"route": exc.message}) from exc
        if self.fibre_count is not None and self.fibre_count <= 0:
            raise ValidationError({
                "fibre_count": "fibre_count must be greater than 0.",
            })
        # TODO(PR-B): once TrunkBreakout exists, validate that
        # sum(breakout fibre ranges) <= self.fibre_count. Skipped in PR A
        # because the through-table doesn't exist yet.
