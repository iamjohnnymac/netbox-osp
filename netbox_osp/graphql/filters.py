"""strawberry-django filter classes for the netbox-osp GraphQL schema.

We hand-write these instead of using the legacy `autotype_decorator` shortcut
because that has been removed from NetBox `main` (PR #18618). Our existing
`NetBoxModelFilterSet` classes in `netbox_osp.filtersets` continue to power
the REST API + UI list pages — only GraphQL goes through these.
"""
from __future__ import annotations

import strawberry
import strawberry_django
from strawberry_django import FilterLookup

from netbox.graphql.filters import NetBoxModelFilter, PrimaryModelFilter

from netbox_osp import models


@strawberry_django.filter_type(models.OspCable, lookups=True)
class OspCableFilter(PrimaryModelFilter):
    cid: FilterLookup[str] | None = strawberry_django.filter_field()
    type: FilterLookup[str] | None = strawberry_django.filter_field()
    status: FilterLookup[str] | None = strawberry_django.filter_field()
    install_method: FilterLookup[str] | None = strawberry_django.filter_field()
    fibre_count: FilterLookup[int] | None = strawberry_django.filter_field()
    tube_count: FilterLookup[int] | None = strawberry_django.filter_field()
    fibres_per_tube: FilterLookup[int] | None = strawberry_django.filter_field()
    length_m: FilterLookup[int] | None = strawberry_django.filter_field()
    part_number: FilterLookup[str] | None = strawberry_django.filter_field()
    site_a_id: FilterLookup[int] | None = strawberry_django.filter_field()
    site_b_id: FilterLookup[int] | None = strawberry_django.filter_field()
    tenant_id: FilterLookup[int] | None = strawberry_django.filter_field()
    manufacturer_id: FilterLookup[int] | None = strawberry_django.filter_field()


@strawberry_django.filter_type(models.Tube, lookups=True)
class TubeFilter(NetBoxModelFilter):
    number: FilterLookup[int] | None = strawberry_django.filter_field()
    color: FilterLookup[str] | None = strawberry_django.filter_field()
    description: FilterLookup[str] | None = strawberry_django.filter_field()
    cable_id: FilterLookup[int] | None = strawberry_django.filter_field()


@strawberry_django.filter_type(models.Strand, lookups=True)
class StrandFilter(NetBoxModelFilter):
    position: FilterLookup[int] | None = strawberry_django.filter_field()
    color: FilterLookup[str] | None = strawberry_django.filter_field()
    status: FilterLookup[str] | None = strawberry_django.filter_field()
    description: FilterLookup[str] | None = strawberry_django.filter_field()
    cable_id: FilterLookup[int] | None = strawberry_django.filter_field()
    tube_id: FilterLookup[int] | None = strawberry_django.filter_field()
    cable_link_id: FilterLookup[int] | None = strawberry_django.filter_field()


@strawberry_django.filter_type(models.SpliceClosure, lookups=True)
class SpliceClosureFilter(PrimaryModelFilter):
    name: FilterLookup[str] | None = strawberry_django.filter_field()
    closure_type: FilterLookup[str] | None = strawberry_django.filter_field()
    model: FilterLookup[str] | None = strawberry_django.filter_field()
    capacity_splices: FilterLookup[int] | None = strawberry_django.filter_field()
    status: FilterLookup[str] | None = strawberry_django.filter_field()
    site_id: FilterLookup[int] | None = strawberry_django.filter_field()
    location_id: FilterLookup[int] | None = strawberry_django.filter_field()
    manufacturer_id: FilterLookup[int] | None = strawberry_django.filter_field()


@strawberry_django.filter_type(models.SpliceTray, lookups=True)
class SpliceTrayFilter(NetBoxModelFilter):
    number: FilterLookup[int] | None = strawberry_django.filter_field()
    capacity: FilterLookup[int] | None = strawberry_django.filter_field()
    description: FilterLookup[str] | None = strawberry_django.filter_field()
    closure_id: FilterLookup[int] | None = strawberry_django.filter_field()


@strawberry_django.filter_type(models.Splice, lookups=True)
class SpliceFilter(NetBoxModelFilter):
    position: FilterLookup[int] | None = strawberry_django.filter_field()
    splice_type: FilterLookup[str] | None = strawberry_django.filter_field()
    tray_id: FilterLookup[int] | None = strawberry_django.filter_field()
    strand_a_id: FilterLookup[int] | None = strawberry_django.filter_field()
    strand_b_id: FilterLookup[int] | None = strawberry_django.filter_field()


@strawberry_django.filter_type(models.FibreLink, lookups=True)
class FibreLinkFilter(PrimaryModelFilter):
    name: FilterLookup[str] | None = strawberry_django.filter_field()
    status: FilterLookup[str] | None = strawberry_django.filter_field()
    connectors_per_end: FilterLookup[int] | None = strawberry_django.filter_field()


@strawberry_django.filter_type(models.FibreLinkStrand, lookups=True)
class FibreLinkStrandFilter:
    id: strawberry.auto
    position: FilterLookup[int] | None = strawberry_django.filter_field()
    link_id: FilterLookup[int] | None = strawberry_django.filter_field()
    strand_id: FilterLookup[int] | None = strawberry_django.filter_field()


@strawberry_django.filter_type(models.LocationGeo, lookups=True)
class LocationGeoFilter(NetBoxModelFilter):
    marker_color: FilterLookup[str] | None = strawberry_django.filter_field()
    description: FilterLookup[str] | None = strawberry_django.filter_field()
    location_id: FilterLookup[int] | None = strawberry_django.filter_field()


@strawberry_django.filter_type(models.FibreTrunk, lookups=True)
class FibreTrunkFilter(PrimaryModelFilter):
    cid: FilterLookup[str] | None = strawberry_django.filter_field()
    trunk_type: FilterLookup[str] | None = strawberry_django.filter_field()
    status: FilterLookup[str] | None = strawberry_django.filter_field()
    fibre_count: FilterLookup[int] | None = strawberry_django.filter_field()
    tenant_id: FilterLookup[int] | None = strawberry_django.filter_field()
    manufacturer_id: FilterLookup[int] | None = strawberry_django.filter_field()


@strawberry_django.filter_type(models.TrunkBreakout, lookups=True)
class FibreTrunkBreakoutFilter(NetBoxModelFilter):
    trunk_id: FilterLookup[int] | None = strawberry_django.filter_field()
    cable_id: FilterLookup[int] | None = strawberry_django.filter_field()
    fibre_range_start: FilterLookup[int] | None = strawberry_django.filter_field()
    fibre_range_end: FilterLookup[int] | None = strawberry_django.filter_field()
