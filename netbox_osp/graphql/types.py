"""strawberry-django types for the netbox-osp GraphQL schema.

Each model gets a `<Model>Type` with `fields='__all__'` for DB columns.
Generic-FK termination fields (Strand / FibreLink) are excluded — GFKs need
a custom union resolver, and the v0.1.0 surface keeps that for a followup.

Model `@property` methods (loss_db, total_loss_db, utilization_pct, etc.)
are re-declared as explicit `@strawberry_django.field` methods on each type
so they appear in the GraphQL schema.
"""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Annotated

import strawberry
import strawberry_django

from netbox.graphql.types import BaseObjectType, NetBoxObjectType

from netbox_osp import models
from . import filters

if TYPE_CHECKING:
    from dcim.graphql.types import (
        CableType, LocationType, ManufacturerType, SiteType,
    )
    from tenancy.graphql.types import TenantType


# ---- OspCable + children ------------------------------------------------

@strawberry_django.type(
    models.OspCable,
    fields="__all__",
    filters=filters.OspCableFilter,
    pagination=True,
)
class OspCableType(NetBoxObjectType):
    site_a: Annotated["SiteType", strawberry.lazy("dcim.graphql.types")] | None
    site_b: Annotated["SiteType", strawberry.lazy("dcim.graphql.types")] | None
    tenant: Annotated["TenantType", strawberry.lazy("tenancy.graphql.types")] | None

    @strawberry_django.field
    def effective_length_m(self) -> int:
        return self.effective_length_m

    @strawberry_django.field
    def loss_db_value(self) -> Decimal:
        # Renamed (`loss_db_value`) to avoid colliding with strawberry-django's
        # auto-introspection of any underlying DB column with the same name.
        return self.loss_db


@strawberry_django.type(
    models.Tube,
    fields="__all__",
    filters=filters.TubeFilter,
    pagination=True,
)
class TubeType(NetBoxObjectType):
    pass


@strawberry_django.type(
    models.Strand,
    fields="__all__",
    exclude=(
        # Generic-FK fields need a custom union resolver; deferred to v0.2.
        "a_termination_type", "a_termination_id",
        "b_termination_type", "b_termination_id",
    ),
    filters=filters.StrandFilter,
    pagination=True,
)
class StrandType(NetBoxObjectType):
    @strawberry_django.field
    def loss_db_value(self) -> Decimal:
        return self.loss_db


# ---- SpliceClosure + Tray + Splice -------------------------------------

@strawberry_django.type(
    models.SpliceClosure,
    fields="__all__",
    filters=filters.SpliceClosureFilter,
    pagination=True,
)
class SpliceClosureType(NetBoxObjectType):
    site: Annotated["SiteType", strawberry.lazy("dcim.graphql.types")] | None
    location: Annotated["LocationType", strawberry.lazy("dcim.graphql.types")] | None

    @strawberry_django.field
    def used_splices(self) -> int:
        return self.used_splices

    @strawberry_django.field
    def utilization_pct(self) -> float:
        return self.utilization_pct


@strawberry_django.type(
    models.SpliceTray,
    fields="__all__",
    filters=filters.SpliceTrayFilter,
    pagination=True,
)
class SpliceTrayType(NetBoxObjectType):
    @strawberry_django.field
    def used(self) -> int:
        return self.used


@strawberry_django.type(
    models.Splice,
    fields="__all__",
    filters=filters.SpliceFilter,
    pagination=True,
)
class SpliceType(NetBoxObjectType):
    pass


# ---- FibreLink + through-table -----------------------------------------

@strawberry_django.type(
    models.FibreLink,
    fields="__all__",
    exclude=(
        "a_termination_type", "a_termination_id",
        "b_termination_type", "b_termination_id",
    ),
    filters=filters.FibreLinkFilter,
    pagination=True,
)
class FibreLinkType(NetBoxObjectType):
    @strawberry_django.field
    def strand_count(self) -> int:
        return self.strand_count

    @strawberry_django.field
    def splice_loss_db(self) -> Decimal:
        return self.splice_loss_db

    @strawberry_django.field
    def strand_loss_db(self) -> Decimal:
        return self.strand_loss_db

    @strawberry_django.field
    def connector_total_loss_db(self) -> Decimal:
        return self.connector_total_loss_db

    @strawberry_django.field
    def total_loss_db_value(self) -> Decimal:
        return self.total_loss_db

    @strawberry_django.field
    def loss_budget_pct(self) -> float:
        return self.loss_budget_pct

    @strawberry_django.field
    def loss_budget_band(self) -> str:
        return self.loss_budget_band


@strawberry_django.type(
    models.FibreLinkStrand,
    fields="__all__",
    filters=filters.FibreLinkStrandFilter,
    pagination=True,
)
class FibreLinkStrandType(BaseObjectType):
    pass


# ---- LocationGeo -------------------------------------------------------

@strawberry_django.type(
    models.LocationGeo,
    fields="__all__",
    filters=filters.LocationGeoFilter,
    pagination=True,
)
class LocationGeoType(NetBoxObjectType):
    location: Annotated["LocationType", strawberry.lazy("dcim.graphql.types")]

    @strawberry_django.field
    def has_coords(self) -> bool:
        return self.has_coords


# ---- FibreTrunk + TrunkBreakout ----------------------------------------

@strawberry_django.type(
    models.FibreTrunk,
    fields="__all__",
    filters=filters.FibreTrunkFilter,
    pagination=True,
)
class FibreTrunkType(NetBoxObjectType):
    tenant: Annotated["TenantType", strawberry.lazy("tenancy.graphql.types")] | None
    manufacturer: Annotated[
        "ManufacturerType", strawberry.lazy("dcim.graphql.types"),
    ] | None

    @strawberry_django.field
    def fibres_used(self) -> int:
        return self.fibres_used

    @strawberry_django.field
    def fibres_remaining(self) -> int:
        return self.fibres_remaining

    @strawberry_django.field
    def fibres_utilization_pct(self) -> float:
        return self.fibres_utilization_pct


@strawberry_django.type(
    models.TrunkBreakout,
    fields="__all__",
    filters=filters.FibreTrunkBreakoutFilter,
    pagination=True,
)
class FibreTrunkBreakoutType(NetBoxObjectType):
    cable: Annotated["CableType", strawberry.lazy("dcim.graphql.types")]

    @strawberry_django.field
    def fibre_count(self) -> int:
        return self.fibre_count
