"""Shared fixture builders for netbox_osp tests.

Both test_views.py and test_api.py need the same FK universe (Sites,
Locations, OspCables, Closures, etc.) before they can build model
instances. We centralise the builders here so per-model setUpTestData()
classmethods stay focused on the model under test.
"""
from dcim.models import Location, Site

from netbox_osp.models import (
    OspCable,
    SpliceClosure,
    Strand,
    Tube,
)


def make_sites(n: int = 2):
    """Return a tuple of N sites with deterministic slugs."""
    return tuple(
        Site.objects.create(name=f"Test Site {i}", slug=f"test-site-{i}")
        for i in range(1, n + 1)
    )


def make_locations(site, n: int = 3):
    """Return a tuple of N Locations parented to the given site."""
    return tuple(
        Location.objects.create(
            name=f"Test Loc {i}", slug=f"test-loc-{i}", site=site,
        )
        for i in range(1, n + 1)
    )


def make_cable(cid, site_a, site_b, **overrides):
    """Create an OspCable with internally-consistent fibre arithmetic.

    Default geometry: 24 fibres = 2 tubes × 12 fibres/tube. Pass
    fibre_count / tube_count / fibres_per_tube together when overriding —
    OspCable.clean() enforces tube_count * fibres_per_tube == fibre_count.
    """
    defaults = {
        "fibre_count": 24, "tube_count": 2, "fibres_per_tube": 12,
        "site_a": site_a, "site_b": site_b,
    }
    defaults.update(overrides)
    return OspCable.objects.create(cid=cid, **defaults)


def make_tubes_and_strands(cable):
    """Populate Tubes 1..tube_count and Strands 1..fibre_count for a cable.

    Used by Strand/Splice tests that need a fully-built cable to splice
    against. Returns (list_of_tubes, list_of_strands).
    """
    tubes = [
        Tube.objects.create(cable=cable, number=i)
        for i in range(1, cable.tube_count + 1)
    ]
    strands = [
        Strand.objects.create(cable=cable, position=i)
        for i in range(1, cable.fibre_count + 1)
    ]
    return tubes, strands


def make_closure(name, **overrides):
    defaults = {"name": name, "capacity_splices": 288}
    defaults.update(overrides)
    return SpliceClosure.objects.create(**defaults)
