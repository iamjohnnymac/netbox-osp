from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from netbox.models import NetBoxModel

from ..choices import (
    InstallMethodChoices,
    OspCableTypeChoices,
    OspStatusChoices,
    StrandStatusChoices,
    TIA598ColorChoices,
)
from ._geo import linestring_length_m, validate_linestring


class OspCable(NetBoxModel):
    cid = models.CharField(
        max_length=64,
        unique=True,
        help_text="Cable ID (e.g. SITE-A-SITE-B-001).",
    )
    type = models.CharField(
        max_length=32,
        choices=OspCableTypeChoices,
        default=OspCableTypeChoices.TYPE_LOOSE_TUBE,
    )
    status = models.CharField(
        max_length=32,
        choices=OspStatusChoices,
        default=OspStatusChoices.STATUS_PLANNED,
    )
    install_method = models.CharField(
        max_length=32,
        choices=InstallMethodChoices,
        blank=True,
        default="",
    )
    fibre_count = models.PositiveSmallIntegerField(default=24)
    tube_count = models.PositiveSmallIntegerField(default=2)
    fibres_per_tube = models.PositiveSmallIntegerField(default=12)
    length_m = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Operator-supplied length in metres. Falls back to route_length_m if unset.",
    )
    attenuation_db_per_km = models.DecimalField(
        max_digits=5, decimal_places=3, default=0.22,
        help_text="Per-km attenuation in dB (default 0.22 for OS2 1550nm).",
    )
    site_a = models.ForeignKey(
        "dcim.Site",
        related_name="osp_cables_a",
        on_delete=models.PROTECT,
    )
    site_b = models.ForeignKey(
        "dcim.Site",
        related_name="osp_cables_b",
        on_delete=models.PROTECT,
    )
    tenant = models.ForeignKey(
        "tenancy.Tenant",
        related_name="osp_cables",
        on_delete=models.PROTECT,
        null=True, blank=True,
    )
    manufacturer = models.ForeignKey(
        "dcim.Manufacturer",
        related_name="osp_cables",
        on_delete=models.PROTECT,
        null=True, blank=True,
    )
    part_number = models.CharField(max_length=64, blank=True, default="")
    installed_date = models.DateField(null=True, blank=True)
    route = models.JSONField(
        null=True, blank=True,
        help_text="GeoJSON LineString in WGS84 ([lon, lat] order).",
    )
    route_length_m = models.PositiveIntegerField(
        null=True, blank=True, editable=False,
        help_text="Auto-computed from route geometry on save.",
    )
    description = models.CharField(max_length=200, blank=True, default="")
    comments = models.TextField(blank=True, default="")

    clone_fields = (
        "type", "status", "install_method", "fibre_count", "tube_count",
        "fibres_per_tube", "attenuation_db_per_km", "site_a", "site_b",
        "tenant", "manufacturer",
    )

    class Meta:
        ordering = ("cid",)
        verbose_name = "OSP Cable"
        verbose_name_plural = "OSP Cables"

    def __str__(self):
        return self.cid

    def get_absolute_url(self):
        return reverse("plugins:netbox_osp:ospcable", args=[self.pk])

    def get_status_color(self):
        return OspStatusChoices.colors.get(self.status)

    def get_type_color(self):
        return OspCableTypeChoices.colors.get(self.type)

    def clean(self):
        super().clean()
        if self.route is not None:
            validate_linestring(self.route)
        if self.tube_count and self.fibres_per_tube:
            expected = self.tube_count * self.fibres_per_tube
            if self.fibre_count and expected != self.fibre_count:
                raise ValidationError({
                    "fibre_count":
                        f"fibre_count={self.fibre_count} does not match "
                        f"tube_count×fibres_per_tube={expected}.",
                })

    def save(self, *args, **kwargs):
        if self.route:
            self.route_length_m = int(round(linestring_length_m(self.route)))
        else:
            self.route_length_m = None
        super().save(*args, **kwargs)

    @property
    def effective_length_m(self):
        return self.length_m or self.route_length_m or 0

    @property
    def loss_db(self):
        from decimal import Decimal
        if not self.effective_length_m:
            return Decimal("0")
        return (Decimal(self.effective_length_m) / Decimal(1000)) * Decimal(self.attenuation_db_per_km)


class Tube(NetBoxModel):
    cable = models.ForeignKey(
        OspCable, related_name="tubes", on_delete=models.CASCADE,
    )
    number = models.PositiveSmallIntegerField()
    color = models.CharField(
        max_length=16, choices=TIA598ColorChoices, blank=True, default="",
    )
    description = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ("cable", "number")
        unique_together = (("cable", "number"),)

    def __str__(self):
        return f"{self.cable.cid} tube {self.number}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_osp:tube", args=[self.pk])

    def save(self, *args, **kwargs):
        if not self.color:
            self.color = TIA598ColorChoices.for_position(self.number or 1)
        super().save(*args, **kwargs)


class Strand(NetBoxModel):
    cable = models.ForeignKey(
        OspCable, related_name="strands", on_delete=models.CASCADE,
    )
    tube = models.ForeignKey(
        Tube, related_name="strands", on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    position = models.PositiveSmallIntegerField(
        help_text="1-indexed position within the cable (1..fibre_count).",
    )
    color = models.CharField(
        max_length=16, choices=TIA598ColorChoices, blank=True, default="",
    )
    status = models.CharField(
        max_length=32, choices=StrandStatusChoices,
        default=StrandStatusChoices.STATUS_SPARE,
    )
    cable_link = models.ForeignKey(
        "dcim.Cable",
        related_name="osp_strands",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="The dcim.Cable row representing this strand at the patch-panel level "
                  "(legacy strand-as-cable model). Optional.",
    )
    a_termination_type = models.ForeignKey(
        ContentType, on_delete=models.PROTECT,
        related_name="+", null=True, blank=True,
    )
    a_termination_id = models.PositiveBigIntegerField(null=True, blank=True)
    a_termination = GenericForeignKey("a_termination_type", "a_termination_id")
    b_termination_type = models.ForeignKey(
        ContentType, on_delete=models.PROTECT,
        related_name="+", null=True, blank=True,
    )
    b_termination_id = models.PositiveBigIntegerField(null=True, blank=True)
    b_termination = GenericForeignKey("b_termination_type", "b_termination_id")
    description = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ("cable", "position")
        unique_together = (("cable", "position"),)

    def __str__(self):
        return f"{self.cable.cid} strand {self.position}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_osp:strand", args=[self.pk])

    def get_status_color(self):
        return StrandStatusChoices.colors.get(self.status)

    def save(self, *args, **kwargs):
        if not self.color:
            self.color = TIA598ColorChoices.for_position(self.position or 1)
        if self.tube_id is None and self.cable_id and self.cable.fibres_per_tube:
            tube_number = ((self.position - 1) // self.cable.fibres_per_tube) + 1
            self.tube = Tube.objects.filter(
                cable=self.cable, number=tube_number,
            ).first()
        super().save(*args, **kwargs)

    @property
    def loss_db(self):
        return self.cable.loss_db
