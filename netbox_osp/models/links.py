from decimal import Decimal

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse

from netbox.models import NetBoxModel

from ..choices import FibreLinkStatusChoices


class FibreLink(NetBoxModel):
    name = models.CharField(max_length=64, unique=True)
    status = models.CharField(
        max_length=32, choices=FibreLinkStatusChoices,
        default=FibreLinkStatusChoices.STATUS_PLANNED,
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
    strands = models.ManyToManyField(
        "netbox_osp.Strand",
        through="netbox_osp.FibreLinkStrand",
        related_name="links",
    )
    connector_loss_db = models.DecimalField(
        max_digits=5, decimal_places=3, default=0.30,
    )
    connectors_per_end = models.PositiveSmallIntegerField(default=2)
    target_loss_budget_db = models.DecimalField(
        max_digits=6, decimal_places=3, default=10.00,
    )
    description = models.CharField(max_length=200, blank=True, default="")
    comments = models.TextField(blank=True, default="")

    clone_fields = ("status", "connector_loss_db", "connectors_per_end", "target_loss_budget_db")

    class Meta:
        ordering = ("name",)
        verbose_name = "Fibre Link"
        verbose_name_plural = "Fibre Links"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("plugins:netbox_osp:fibrelink", args=[self.pk])

    def get_status_color(self):
        return FibreLinkStatusChoices.colors.get(self.status)

    @property
    def strand_count(self):
        return self.strands.count()

    @property
    def splice_loss_db(self):
        from .splices import Splice
        strand_ids = list(self.strands.values_list("id", flat=True))
        if not strand_ids:
            return Decimal("0")
        splices = Splice.objects.filter(
            models.Q(strand_a_id__in=strand_ids) | models.Q(strand_b_id__in=strand_ids)
        ).distinct()
        return sum((s.loss_db for s in splices), Decimal("0"))

    @property
    def strand_loss_db(self):
        return sum((s.loss_db for s in self.strands.all()), Decimal("0"))

    @property
    def connector_total_loss_db(self):
        return self.connector_loss_db * Decimal(self.connectors_per_end * 2)

    @property
    def total_loss_db(self):
        return self.strand_loss_db + self.splice_loss_db + self.connector_total_loss_db

    @property
    def loss_budget_pct(self):
        if not self.target_loss_budget_db:
            return 0
        return float((self.total_loss_db / self.target_loss_budget_db) * 100)

    @property
    def loss_budget_band(self):
        pct = self.loss_budget_pct
        if pct <= 80:
            return "ok"
        if pct <= 100:
            return "warn"
        return "fail"

    def trace(self):
        """Return the ordered list of (Strand, Splice|None) hops that make up this link.
        Splice is None for the last hop (terminates at b)."""
        from .splices import Splice
        ordered = list(
            self.link_strands.select_related("strand").order_by("position")
        )
        hops = []
        for i, ls in enumerate(ordered):
            strand = ls.strand
            splice = None
            if i + 1 < len(ordered):
                next_strand = ordered[i + 1].strand
                splice = Splice.objects.filter(
                    models.Q(strand_a=strand, strand_b=next_strand)
                    | models.Q(strand_a=next_strand, strand_b=strand)
                ).first()
            hops.append((strand, splice))
        return hops


class FibreLinkStrand(models.Model):
    link = models.ForeignKey(FibreLink, related_name="link_strands", on_delete=models.CASCADE)
    strand = models.ForeignKey("netbox_osp.Strand", related_name="link_strands", on_delete=models.PROTECT)
    position = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ("link", "position")
        unique_together = (("link", "position"), ("link", "strand"))

    def __str__(self):
        return f"{self.link.name} hop {self.position}: {self.strand}"
