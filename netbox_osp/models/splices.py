from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, F
from django.urls import reverse

from netbox.models import NetBoxModel

from ..choices import ClosureTypeChoices, SpliceTypeChoices, OspStatusChoices
from ._geo import validate_point


class SpliceClosure(NetBoxModel):
    name = models.CharField(max_length=64, unique=True)
    closure_type = models.CharField(
        max_length=32, choices=ClosureTypeChoices,
        default=ClosureTypeChoices.DOME,
    )
    manufacturer = models.ForeignKey(
        "dcim.Manufacturer",
        related_name="splice_closures",
        on_delete=models.PROTECT,
        null=True, blank=True,
    )
    model = models.CharField(max_length=64, blank=True, default="")
    capacity_splices = models.PositiveSmallIntegerField(default=288)
    site = models.ForeignKey(
        "dcim.Site",
        related_name="splice_closures",
        on_delete=models.PROTECT,
        null=True, blank=True,
    )
    location = models.ForeignKey(
        "dcim.Location",
        related_name="splice_closures",
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    status = models.CharField(
        max_length=32, choices=OspStatusChoices,
        default=OspStatusChoices.STATUS_PLANNED,
    )
    installed_date = models.DateField(null=True, blank=True)
    location_point = models.JSONField(
        null=True, blank=True,
        help_text="GeoJSON Point in WGS84 ([lon, lat] order).",
    )
    elevation_m = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True,
    )
    description = models.CharField(max_length=200, blank=True, default="")
    comments = models.TextField(blank=True, default="")

    clone_fields = ("closure_type", "manufacturer", "model", "capacity_splices", "site", "status")

    class Meta:
        ordering = ("name",)
        verbose_name = "Splice Closure"
        verbose_name_plural = "Splice Closures"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("plugins:netbox_osp:spliceclosure", args=[self.pk])

    def get_status_color(self):
        return OspStatusChoices.colors.get(self.status)

    def get_closure_type_color(self):
        return ClosureTypeChoices.colors.get(self.closure_type)

    def clean(self):
        super().clean()
        if self.location_point is not None:
            validate_point(self.location_point)

    @property
    def used_splices(self):
        return Splice.objects.filter(tray__closure=self).count()

    @property
    def utilization_pct(self):
        if not self.capacity_splices:
            return 0
        return round(100 * self.used_splices / self.capacity_splices, 1)


class SpliceTray(NetBoxModel):
    closure = models.ForeignKey(
        SpliceClosure, related_name="trays", on_delete=models.CASCADE,
    )
    number = models.PositiveSmallIntegerField()
    capacity = models.PositiveSmallIntegerField(default=12)
    description = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ("closure", "number")
        unique_together = (("closure", "number"),)

    def __str__(self):
        return f"{self.closure.name} tray {self.number}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_osp:splicetray", args=[self.pk])

    @property
    def used(self):
        return self.splices.count()


class Splice(NetBoxModel):
    tray = models.ForeignKey(
        SpliceTray, related_name="splices", on_delete=models.CASCADE,
    )
    position = models.PositiveSmallIntegerField()
    splice_type = models.CharField(
        max_length=16, choices=SpliceTypeChoices,
        default=SpliceTypeChoices.FUSION,
    )
    loss_db = models.DecimalField(
        max_digits=5, decimal_places=3, default=0.10,
    )
    strand_a = models.ForeignKey(
        "netbox_osp.Strand",
        related_name="splices_a",
        on_delete=models.PROTECT,
    )
    strand_b = models.ForeignKey(
        "netbox_osp.Strand",
        related_name="splices_b",
        on_delete=models.PROTECT,
    )
    spliced_date = models.DateField(null=True, blank=True)
    spliced_by = models.CharField(max_length=64, blank=True, default="")
    otdr_trace_url = models.URLField(blank=True, default="")
    description = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ("tray", "position")
        unique_together = (("tray", "position"),)
        constraints = [
            models.CheckConstraint(
                condition=~Q(strand_a=F("strand_b")),
                name="splice_no_self_splice",
            ),
        ]

    def __str__(self):
        return f"{self.tray.closure.name}/{self.tray.number}/{self.position}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_osp:splice", args=[self.pk])

    def get_splice_type_color(self):
        return SpliceTypeChoices.colors.get(self.splice_type)

    def clean(self):
        super().clean()
        if self.strand_a_id and self.strand_b_id and self.strand_a_id == self.strand_b_id:
            raise ValidationError("A splice cannot connect a strand to itself.")
