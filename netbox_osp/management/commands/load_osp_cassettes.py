"""Management command to load the bundled netbox-osp cassette device-types.

Ships five fibre-cassette / patch-panel `DeviceType` templates that pair
with the MTP harness deploy form (PR C). Operators run:

    python manage.py load_osp_cassettes

once to seed the catalogue. The command is idempotent — on re-run it
updates existing rows (matched by slug) and skips no-op work, so it is
safe to wire into provisioning scripts.

JSON shape follows the netbox-community/devicetype-library spec
(hyphenated `rear-ports` / `front-ports` keys, exactly as the upstream
loader consumes). See `netbox_osp/device_types/cassettes/*.json` for
the shipped catalogue.
"""

from __future__ import annotations

import json
from pathlib import Path

from dcim.models import (
    DeviceType,
    FrontPortTemplate,
    Manufacturer,
    PortTemplateMapping,
    RearPortTemplate,
)
from django.core.management.base import BaseCommand
from django.db import transaction

# Resolve the bundled catalogue directory once at import time. Lives next
# to the `netbox_osp/` package so it ships as package-data via the
# `device_types/**/*.json` glob in pyproject.toml.
CASSETTES_DIR = Path(__file__).resolve().parents[2] / "device_types" / "cassettes"


def discover_cassette_files() -> list[Path]:
    """Return the bundled cassette JSONs in stable (sorted) order.

    Sorted so output is deterministic for tests + CI logs. The directory
    is shipped as package-data, so the same set of files is always
    present at runtime.
    """
    return sorted(CASSETTES_DIR.glob("*.json"))


def load_cassette_spec(path: Path) -> dict:
    """Read + parse one cassette JSON. Raises on malformed input."""
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


@transaction.atomic
def apply_cassette(spec: dict) -> tuple[DeviceType, bool]:
    """Materialise one cassette spec as a NetBox `DeviceType` + port
    templates, idempotently.

    Returns `(device_type, created)`. The caller uses `created` to
    distinguish "this run brought it in" from "already in the DB —
    refreshed in place" for the CLI summary line.

    Idempotency contract:
    - Manufacturer matched by `name`, slugified on first create.
    - DeviceType matched by `slug`. If it exists, model / u_height /
      is_full_depth / comments are refreshed; port templates are
      regenerated from the JSON so the JSON remains the source of truth.
    - Front+rear port templates + PortTemplateMapping rows are torn down
      and rebuilt under the same atomic transaction. Cleaner than diffing
      individual rows and the rebuild is cheap (≤ 24 ports per cassette).
    """
    mf_name = spec["manufacturer"]
    manufacturer, _ = Manufacturer.objects.get_or_create(
        name=mf_name,
        defaults={"slug": _slugify(mf_name)},
    )

    slug = spec["slug"]
    defaults = {
        "manufacturer": manufacturer,
        "model": spec["model"],
        "u_height": spec.get("u_height", 0),
        "is_full_depth": spec.get("is_full_depth", False),
        "subdevice_role": spec.get("subdevice_role") or "",
        "comments": spec.get("comments", "") or "",
    }
    device_type, created = DeviceType.objects.update_or_create(
        slug=slug,
        defaults=defaults,
    )

    # Rebuild port templates from JSON so JSON is source of truth.
    # Cascade through PortTemplateMapping → safe because we recreate
    # mappings below.
    FrontPortTemplate.objects.filter(device_type=device_type).delete()
    RearPortTemplate.objects.filter(device_type=device_type).delete()

    rear_by_name: dict[str, RearPortTemplate] = {}
    for rear in spec.get("rear-ports", []):
        rt = RearPortTemplate.objects.create(
            device_type=device_type,
            name=rear["name"],
            type=rear["type"],
            positions=rear.get("positions", 1),
        )
        rear_by_name[rear["name"]] = rt

    for front in spec.get("front-ports", []):
        ft = FrontPortTemplate.objects.create(
            device_type=device_type,
            name=front["name"],
            type=front["type"],
            positions=front.get("positions", 1),
        )
        rear_name = front.get("rear_port")
        if rear_name is None:
            continue
        rear = rear_by_name.get(rear_name)
        if rear is None:
            msg = f"Cassette '{slug}': front-port '{front['name']}' references unknown rear-port '{rear_name}'"
            raise ValueError(msg)
        PortTemplateMapping.objects.create(
            device_type=device_type,
            front_port=ft,
            rear_port=rear,
            front_port_position=front.get("front_port_position", 1),
            rear_port_position=front.get("rear_port_position", 1),
        )

    return device_type, created


def _slugify(name: str) -> str:
    """Local slugifier — avoids Django's `slugify` import cycle in some
    plugin loader paths and matches the simple ASCII-lower convention
    used by `netbox-community/devicetype-library`."""
    return name.strip().lower().replace(" ", "-")


class Command(BaseCommand):
    help = (
        "Load the bundled netbox-osp cassette device-types (MPO/MTP and "
        "LC patch panels) into NetBox. Idempotent: re-running refreshes "
        "the catalogue from JSON."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List what would be loaded without writing.",
        )

    def handle(self, *args, **options):
        files = discover_cassette_files()
        if not files:
            self.stdout.write(
                self.style.WARNING(
                    f"No cassette JSONs found under {CASSETTES_DIR}",
                )
            )
            return

        if options["dry_run"]:
            self.stdout.write(f"Would load {len(files)} cassette(s):")
            for f in files:
                self.stdout.write(f"  - {f.name}")
            return

        created_count = 0
        updated_count = 0
        for path in files:
            spec = load_cassette_spec(path)
            _, was_created = apply_cassette(spec)
            if was_created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  created  {spec['slug']}",
                    )
                )
            else:
                updated_count += 1
                self.stdout.write(
                    f"  refreshed {spec['slug']}",
                )

        self.stdout.write(
            self.style.SUCCESS(f"Done — {created_count} created, {updated_count} refreshed ({len(files)} total).")
        )
