"""Optional GPS coordinates for a `dcim.Location`.

NetBox core gives Sites lat/lon but not Locations. This 1:1 side-table fills
that gap, letting the OSP network map plot fine-grained intra-site markers
(MCR, server room, jetty pole, etc.) alongside the Site markers.

The table is opt-in: a Location without a `LocationGeo` row is simply absent
from the map. A `LocationGeo` row may also exist with `latitude=None,
longitude=None` if the operator hasn't surveyed the coords yet — only rows
with both set are rendered.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from netbox.models import NetBoxModel

from ..choices import LocationMarkerColorChoices


class LocationGeo(NetBoxModel):
    location = models.OneToOneField(
        "dcim.Location",
        related_name="geo",
        on_delete=models.CASCADE,
        help_text="The NetBox Location this GPS record decorates.",
    )
    latitude = models.DecimalField(
        max_digits=10, decimal_places=6,
        null=True, blank=True,
        help_text="WGS84 latitude in degrees, range [-90, 90].",
    )
    longitude = models.DecimalField(
        max_digits=10, decimal_places=6,
        null=True, blank=True,
        help_text="WGS84 longitude in degrees, range [-180, 180].",
    )
    elevation_m = models.DecimalField(
        max_digits=7, decimal_places=2,
        null=True, blank=True,
        help_text="Elevation above sea level in metres (optional).",
    )
    marker_color = models.CharField(
        max_length=16,
        choices=LocationMarkerColorChoices,
        default=LocationMarkerColorChoices.BLUE,
        help_text="Map marker fill colour. Use a distinct tint per Location class.",
    )
    description = models.CharField(max_length=200, blank=True, default="")

    clone_fields = ("marker_color",)

    class Meta:
        ordering = ("location__site", "location__name")
        verbose_name = "Location GPS position"
        verbose_name_plural = "Location GPS positions"

    def __str__(self):
        return f"{self.location} GPS"

    def get_absolute_url(self):
        return reverse("plugins:netbox_osp:locationgeo", args=[self.pk])

    def clean(self):
        super().clean()
        # Lat/lon are nullable as a pair, but if one is set both must be.
        if (self.latitude is None) ^ (self.longitude is None):
            raise ValidationError(
                "Set latitude and longitude together (or leave both blank)."
            )
        if self.latitude is not None and not (Decimal("-90") <= self.latitude <= Decimal("90")):
            raise ValidationError({
                "latitude": f"latitude {self.latitude} out of range [-90, 90].",
            })
        if self.longitude is not None and not (Decimal("-180") <= self.longitude <= Decimal("180")):
            raise ValidationError({
                "longitude": f"longitude {self.longitude} out of range [-180, 180].",
            })

    @property
    def has_coords(self) -> bool:
        """True iff both latitude and longitude are set."""
        return self.latitude is not None and self.longitude is not None
