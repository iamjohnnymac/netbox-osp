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

from ..choices import MpoPolarityChoices, OspStatusChoices, TrunkTypeChoices
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
    polarity = models.CharField(
        max_length=16,
        choices=MpoPolarityChoices,
        blank=True,
        default="",
        help_text="MPO polarity type per TIA-568.3-D. Leave blank for "
                  "non-MPO trunks or when polarity is unknown.",
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

    def get_polarity_color(self):
        if not self.polarity:
            return None
        return MpoPolarityChoices.colors.get(self.polarity)

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
        # PR B: enforce sum(breakout fibre ranges) <= self.fibre_count.
        # Guarded by self.pk because clean() runs at form-validation time
        # before the row exists — there are no breakouts yet on a
        # brand-new trunk.
        if self.pk and self.fibre_count is not None:
            total = sum(
                (br.fibre_range_end - br.fibre_range_start + 1)
                for br in self.breakouts.all()
            )
            if total > self.fibre_count:
                raise ValidationError({
                    "fibre_count": (
                        f"breakout fibre ranges sum to {total} but "
                        f"fibre_count={self.fibre_count}. Adjust "
                        "breakouts or increase fibre_count."
                    ),
                })

    @property
    def fibres_used(self) -> int:
        """Total fibres allocated to TrunkBreakout children. PR B."""
        if not self.pk:
            return 0
        return sum(
            (br.fibre_range_end - br.fibre_range_start + 1)
            for br in self.breakouts.all()
        )

    @property
    def fibres_remaining(self) -> int:
        """Unallocated fibres on this trunk. Floored at 0."""
        if self.fibre_count is None:
            return 0
        return max(self.fibre_count - self.fibres_used, 0)

    @property
    def fibres_utilization_pct(self) -> float:
        if not self.fibre_count:
            return 0.0
        return round(100 * self.fibres_used / self.fibre_count, 1)


class TrunkBreakout(NetBoxModel):
    """Through-table bridging a FibreTrunk to a native dcim.Cable.

    A 24F MTP trunk → 12F breakout to rack A + 12F breakout to rack B
    becomes one FibreTrunk parent + two TrunkBreakout rows pointing at
    the two dcim.Cables already terminated on cassette RearPorts.
    """
    trunk = models.ForeignKey(
        FibreTrunk,
        related_name="breakouts",
        on_delete=models.CASCADE,
        help_text="Parent fibre trunk.",
    )
    cable = models.ForeignKey(
        "dcim.Cable",
        related_name="osp_trunk_breakouts",
        on_delete=models.PROTECT,
        help_text="Native NetBox cable carrying this fibre range. PROTECT "
                  "so the cable can't be deleted while the breakout still "
                  "references it.",
    )
    fibre_range_start = models.PositiveSmallIntegerField(
        help_text="1-indexed start fibre position (matches operator "
                  "cable labelling).",
    )
    fibre_range_end = models.PositiveSmallIntegerField(
        help_text="Inclusive end fibre position. Range size = "
                  "end - start + 1.",
    )
    description = models.CharField(max_length=200, blank=True, default="")

    clone_fields = ("trunk", "fibre_range_start", "fibre_range_end")

    class Meta:
        ordering = ("trunk", "fibre_range_start")
        verbose_name = "Trunk Breakout"
        verbose_name_plural = "Trunk Breakouts"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(fibre_range_start__gte=1),
                name="trunkbreakout_range_start_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    fibre_range_end__gte=models.F("fibre_range_start"),
                ),
                name="trunkbreakout_range_end_gte_start",
            ),
        ]
        unique_together = (
            ("trunk", "cable"),
            ("trunk", "fibre_range_start"),
        )

    def __str__(self):
        return (
            f"{self.trunk.cid} "
            f"[{self.fibre_range_start}-{self.fibre_range_end}] "
            f"→ {self.cable}"
        )

    def get_absolute_url(self):
        return reverse("plugins:netbox_osp:trunkbreakout", args=[self.pk])

    @property
    def fibre_count(self) -> int:
        """Number of fibres covered by this breakout."""
        if self.fibre_range_start is None or self.fibre_range_end is None:
            return 0
        return self.fibre_range_end - self.fibre_range_start + 1

    def clean(self):
        super().clean()
        # 1. range_start >= 1 — surface as a form-keyed error before the
        #    DB constraint fires.
        if self.fibre_range_start is not None and self.fibre_range_start < 1:
            raise ValidationError({
                "fibre_range_start": (
                    "must be >= 1 (cables are labelled 1-indexed)."
                ),
            })
        # 2. start <= end
        if (
            self.fibre_range_start is not None
            and self.fibre_range_end is not None
            and self.fibre_range_end < self.fibre_range_start
        ):
            raise ValidationError({
                "fibre_range_end": "must be >= fibre_range_start.",
            })
        # 3. end <= parent.fibre_count
        if self.trunk_id and self.fibre_range_end is not None:
            trunk_fc = self.trunk.fibre_count
            if trunk_fc is not None and self.fibre_range_end > trunk_fc:
                raise ValidationError({
                    "fibre_range_end": (
                        f"exceeds parent trunk fibre_count={trunk_fc}."
                    ),
                })
        # 4. no overlap with sibling breakouts on the same trunk.
        if (
            self.trunk_id
            and self.fibre_range_start is not None
            and self.fibre_range_end is not None
        ):
            siblings = TrunkBreakout.objects.filter(trunk_id=self.trunk_id)
            if self.pk:
                siblings = siblings.exclude(pk=self.pk)
            for s in siblings:
                if not (
                    self.fibre_range_end < s.fibre_range_start
                    or self.fibre_range_start > s.fibre_range_end
                ):
                    raise ValidationError({
                        "fibre_range_start": (
                            f"range [{self.fibre_range_start}-"
                            f"{self.fibre_range_end}] overlaps with "
                            f"existing breakout [{s.fibre_range_start}-"
                            f"{s.fibre_range_end}] on the same trunk."
                        ),
                    })
