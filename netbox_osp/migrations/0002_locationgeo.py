"""Add the LocationGeo side-table for per-Location GPS markers."""
import django.db.models.deletion
import netbox.models.deletion
import taggit.managers
import utilities.json
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dcim", "0233_device_render_config_permission"),
        ("extras", "0138_customfieldchoiceset_choice_colors"),
        ("netbox_osp", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="LocationGeo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                ("custom_field_data", models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ("latitude",  models.DecimalField(blank=True, decimal_places=6, max_digits=10, null=True)),
                ("longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=10, null=True)),
                ("elevation_m", models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ("marker_color", models.CharField(default="#1565c0", max_length=16)),
                ("description", models.CharField(blank=True, default="", max_length=200)),
                ("location", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="geo",
                    to="dcim.location",
                )),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={
                "verbose_name": "Location GPS position",
                "verbose_name_plural": "Location GPS positions",
                "ordering": ("location__site", "location__name"),
            },
            bases=(netbox.models.deletion.DeleteMixin, models.Model),
        ),
    ]
