from django import forms

from netbox.forms import NetBoxModelImportForm
from utilities.forms.fields import CSVChoiceField, CSVModelChoiceField

from dcim.models import Location

from ..choices import (
    LocationMarkerColorChoices,
    SpliceTypeChoices,
    StrandStatusChoices,
    TIA598ColorChoices,
)
from ..models import (
    LocationGeo,
    OspCable,
    Splice,
    SpliceClosure,
    SpliceTray,
    Strand,
    Tube,
)


class OspCableImportForm(NetBoxModelImportForm):
    class Meta:
        model = OspCable
        fields = (
            "cid", "type", "status", "install_method",
            "fibre_count", "tube_count", "fibres_per_tube",
            "length_m", "attenuation_db_per_km",
            "site_a", "site_b", "tenant", "manufacturer", "part_number",
            "description",
        )


class LocationGeoImportForm(NetBoxModelImportForm):
    location = CSVModelChoiceField(
        queryset=Location.objects.all(),
        to_field_name="slug",
        help_text="Location slug (one LocationGeo per Location).",
    )
    marker_color = CSVChoiceField(
        choices=LocationMarkerColorChoices,
        required=False,
        help_text="Leave blank to use the default blue.",
    )

    class Meta:
        model = LocationGeo
        fields = (
            "location", "latitude", "longitude",
            "elevation_m", "marker_color", "description",
        )

    def clean(self):
        super().clean()
        location = self.cleaned_data.get("location")
        if location is not None:
            qs = LocationGeo.objects.filter(location=location)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    {"location": f"a LocationGeo for {location} already exists."}
                )


class SpliceClosureImportForm(NetBoxModelImportForm):
    class Meta:
        model = SpliceClosure
        # location_point (GeoJSON) is excluded — CSV-pasting raw GeoJSON is hostile.
        # Set it via the UI or REST API after import.
        fields = (
            "name", "closure_type", "manufacturer", "model", "capacity_splices",
            "site", "location", "status", "installed_date", "elevation_m",
            "description",
        )


class TubeImportForm(NetBoxModelImportForm):
    cable = CSVModelChoiceField(
        queryset=OspCable.objects.all(),
        to_field_name="cid",
        help_text="OSP Cable CID (e.g. SITE-A-SITE-B-001).",
    )
    color = CSVChoiceField(
        choices=TIA598ColorChoices,
        required=False,
        help_text="TIA-598 colour. Leave blank to auto-assign by tube number.",
    )

    class Meta:
        model = Tube
        fields = ("cable", "number", "color", "description")

    def clean(self):
        super().clean()
        cable = self.cleaned_data.get("cable")
        number = self.cleaned_data.get("number")
        if cable and number is not None:
            qs = Tube.objects.filter(cable=cable, number=number)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    {"number": f"Tube {number} already exists on cable {cable.cid}."}
                )
            if cable.tube_count and number > cable.tube_count:
                raise forms.ValidationError(
                    {"number": f"Tube {number} exceeds cable.tube_count={cable.tube_count}."}
                )


class StrandImportForm(NetBoxModelImportForm):
    cable = CSVModelChoiceField(
        queryset=OspCable.objects.all(),
        to_field_name="cid",
        help_text="OSP Cable CID.",
    )
    tube = CSVModelChoiceField(
        queryset=Tube.objects.all(),
        to_field_name="pk",
        required=False,
        help_text="Tube PK (export the Tube list first). Leave blank and "
                  "Strand.save() auto-assigns by position.",
    )
    color = CSVChoiceField(
        choices=TIA598ColorChoices,
        required=False,
        help_text="Leave blank to auto-assign by position.",
    )
    status = CSVChoiceField(
        choices=StrandStatusChoices,
        required=False,
        help_text="Defaults to 'spare'.",
    )

    class Meta:
        model = Strand
        # Generic-FK terminations + cable_link are too fiddly for CSV;
        # wire them via the UI after import.
        fields = ("cable", "tube", "position", "color", "status", "description")

    def clean(self):
        super().clean()
        cable = self.cleaned_data.get("cable")
        tube = self.cleaned_data.get("tube")
        position = self.cleaned_data.get("position")
        if cable and position is not None:
            if cable.fibre_count and position > cable.fibre_count:
                raise forms.ValidationError(
                    {"position": f"position {position} exceeds cable.fibre_count={cable.fibre_count}."}
                )
            qs = Strand.objects.filter(cable=cable, position=position)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    {"position": f"position {position} already taken on cable {cable.cid}."}
                )
        if tube and cable and tube.cable_id != cable.id:
            raise forms.ValidationError(
                {"tube": f"tube {tube} does not belong to cable {cable.cid}."}
            )


class SpliceTrayImportForm(NetBoxModelImportForm):
    closure = CSVModelChoiceField(
        queryset=SpliceClosure.objects.all(),
        to_field_name="name",
        help_text="Splice closure name.",
    )

    class Meta:
        model = SpliceTray
        fields = ("closure", "number", "capacity", "description")

    def clean(self):
        super().clean()
        closure = self.cleaned_data.get("closure")
        number = self.cleaned_data.get("number")
        if closure and number is not None:
            qs = SpliceTray.objects.filter(closure=closure, number=number)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    {"number": f"tray {number} already exists in closure {closure.name}."}
                )


class SpliceImportForm(NetBoxModelImportForm):
    tray = CSVModelChoiceField(
        queryset=SpliceTray.objects.all(),
        to_field_name="pk",
        help_text="Tray PK (closure+tray-number is not globally unique). "
                  "Export the Splice Trays list first to look up PKs.",
    )
    strand_a = CSVModelChoiceField(
        queryset=Strand.objects.all(),
        to_field_name="pk",
        help_text="Strand PK (from the Strands export).",
    )
    strand_b = CSVModelChoiceField(
        queryset=Strand.objects.all(),
        to_field_name="pk",
        help_text="Strand PK.",
    )
    splice_type = CSVChoiceField(
        choices=SpliceTypeChoices,
        required=False,
        help_text="Defaults to 'fusion'.",
    )

    class Meta:
        model = Splice
        fields = (
            "tray", "position", "splice_type", "loss_db",
            "strand_a", "strand_b", "spliced_date", "spliced_by",
            "otdr_trace_url", "description",
        )

    def clean(self):
        super().clean()
        sa = self.cleaned_data.get("strand_a")
        sb = self.cleaned_data.get("strand_b")
        tray = self.cleaned_data.get("tray")
        position = self.cleaned_data.get("position")
        if sa and sb and sa.id == sb.id:
            # Mirrors the model's DB CheckConstraint; fail fast on the form
            # and key the error to strand_b so it surfaces on that field.
            raise forms.ValidationError(
                {"strand_b": "A splice cannot connect a strand to itself."}
            )
        if tray and position is not None:
            qs = Splice.objects.filter(tray=tray, position=position)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    {"position": f"position {position} already taken in tray {tray}."}
                )
            if tray.capacity and position > tray.capacity:
                raise forms.ValidationError(
                    {"position": f"position {position} exceeds tray.capacity={tray.capacity}."}
                )
