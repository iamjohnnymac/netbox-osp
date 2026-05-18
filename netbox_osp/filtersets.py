import django_filters
from django.db.models import Q

from netbox.filtersets import NetBoxModelFilterSet
from dcim.models import Cable, Location, Site

from .choices import (
    ClosureTypeChoices,
    FibreLinkStatusChoices,
    MpoPolarityChoices,
    OspCableTypeChoices,
    OspStatusChoices,
    SpliceTypeChoices,
    StrandStatusChoices,
    TrunkTypeChoices,
)
from .models import (
    FibreLink,
    FibreTrunk,
    LocationGeo,
    OspCable,
    Splice,
    SpliceClosure,
    SpliceTray,
    Strand,
    TrunkBreakout,
    Tube,
)


class OspCableFilterSet(NetBoxModelFilterSet):
    type = django_filters.MultipleChoiceFilter(choices=OspCableTypeChoices)
    status = django_filters.MultipleChoiceFilter(choices=OspStatusChoices)
    site_a_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Site.objects.all(), field_name="site_a",
    )
    site_b_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Site.objects.all(), field_name="site_b",
    )

    class Meta:
        model = OspCable
        fields = ("id", "cid", "type", "status", "fibre_count", "tenant", "manufacturer")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(cid__icontains=value)
            | Q(description__icontains=value)
            | Q(part_number__icontains=value)
        )


class TubeFilterSet(NetBoxModelFilterSet):
    cable_id = django_filters.ModelMultipleChoiceFilter(
        queryset=OspCable.objects.all(), field_name="cable",
    )

    class Meta:
        model = Tube
        fields = ("id", "number", "color", "cable")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(description__icontains=value)


class StrandFilterSet(NetBoxModelFilterSet):
    cable_id = django_filters.ModelMultipleChoiceFilter(
        queryset=OspCable.objects.all(), field_name="cable",
    )
    status = django_filters.MultipleChoiceFilter(choices=StrandStatusChoices)

    class Meta:
        model = Strand
        fields = ("id", "position", "color", "status", "cable", "tube")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(description__icontains=value)


class SpliceClosureFilterSet(NetBoxModelFilterSet):
    closure_type = django_filters.MultipleChoiceFilter(choices=ClosureTypeChoices)
    status = django_filters.MultipleChoiceFilter(choices=OspStatusChoices)

    class Meta:
        model = SpliceClosure
        fields = ("id", "name", "closure_type", "manufacturer", "model", "status", "site", "location")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(model__icontains=value)
            | Q(description__icontains=value)
        )


class SpliceTrayFilterSet(NetBoxModelFilterSet):
    closure_id = django_filters.ModelMultipleChoiceFilter(
        queryset=SpliceClosure.objects.all(), field_name="closure",
    )

    class Meta:
        model = SpliceTray
        fields = ("id", "closure", "number", "capacity")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(description__icontains=value)


class SpliceFilterSet(NetBoxModelFilterSet):
    splice_type = django_filters.MultipleChoiceFilter(choices=SpliceTypeChoices)
    tray_id = django_filters.ModelMultipleChoiceFilter(
        queryset=SpliceTray.objects.all(), field_name="tray",
    )

    class Meta:
        model = Splice
        fields = ("id", "splice_type", "tray", "strand_a", "strand_b")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(description__icontains=value)
            | Q(spliced_by__icontains=value)
        )


class FibreLinkFilterSet(NetBoxModelFilterSet):
    status = django_filters.MultipleChoiceFilter(choices=FibreLinkStatusChoices)

    class Meta:
        model = FibreLink
        fields = ("id", "name", "status")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(description__icontains=value)
        )


class LocationGeoFilterSet(NetBoxModelFilterSet):
    location_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Location.objects.all(), field_name="location",
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Site.objects.all(), field_name="location__site",
    )
    has_coords = django_filters.BooleanFilter(method="_has_coords")

    class Meta:
        model = LocationGeo
        fields = ("id", "location", "marker_color")

    def _has_coords(self, queryset, name, value):
        if value is True:
            return queryset.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
        if value is False:
            return queryset.filter(Q(latitude__isnull=True) | Q(longitude__isnull=True))
        return queryset

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(location__name__icontains=value)
            | Q(description__icontains=value)
        )


class FibreTrunkFilterSet(NetBoxModelFilterSet):
    trunk_type = django_filters.MultipleChoiceFilter(choices=TrunkTypeChoices)
    polarity = django_filters.MultipleChoiceFilter(choices=MpoPolarityChoices)
    status = django_filters.MultipleChoiceFilter(choices=OspStatusChoices)

    class Meta:
        model = FibreTrunk
        fields = (
            "id", "cid", "trunk_type", "polarity", "status", "fibre_count",
            "tenant", "manufacturer", "show_on_map",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(cid__icontains=value)
            | Q(description__icontains=value)
        )


class TrunkBreakoutFilterSet(NetBoxModelFilterSet):
    trunk_id = django_filters.ModelMultipleChoiceFilter(
        queryset=FibreTrunk.objects.all(), field_name="trunk",
    )
    cable_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Cable.objects.all(), field_name="cable",
    )

    class Meta:
        model = TrunkBreakout
        fields = (
            "id", "trunk", "cable",
            "fibre_range_start", "fibre_range_end",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(description__icontains=value)
