"""GraphQL Query schema for netbox-osp.

NetBox's plugin loader reads the module-level `schema` attribute (a list of
Query classes) and merges it into the global `/graphql/` endpoint.
"""
import strawberry
import strawberry_django

from .types import (
    FibreLinkStrandType,
    FibreLinkType,
    FibreTrunkType,
    LocationGeoType,
    OspCableType,
    SpliceClosureType,
    SpliceTrayType,
    SpliceType,
    StrandType,
    TubeType,
)


@strawberry.type(name="Query")
class NetBoxOspQuery:
    osp_cable: OspCableType = strawberry_django.field()
    osp_cable_list: list[OspCableType] = strawberry_django.field()

    osp_tube: TubeType = strawberry_django.field()
    osp_tube_list: list[TubeType] = strawberry_django.field()

    osp_strand: StrandType = strawberry_django.field()
    osp_strand_list: list[StrandType] = strawberry_django.field()

    osp_splice_closure: SpliceClosureType = strawberry_django.field()
    osp_splice_closure_list: list[SpliceClosureType] = strawberry_django.field()

    osp_splice_tray: SpliceTrayType = strawberry_django.field()
    osp_splice_tray_list: list[SpliceTrayType] = strawberry_django.field()

    osp_splice: SpliceType = strawberry_django.field()
    osp_splice_list: list[SpliceType] = strawberry_django.field()

    osp_fibre_link: FibreLinkType = strawberry_django.field()
    osp_fibre_link_list: list[FibreLinkType] = strawberry_django.field()

    osp_fibre_link_strand: FibreLinkStrandType = strawberry_django.field()
    osp_fibre_link_strand_list: list[FibreLinkStrandType] = strawberry_django.field()

    osp_location_geo: LocationGeoType = strawberry_django.field()
    osp_location_geo_list: list[LocationGeoType] = strawberry_django.field()

    osp_fibre_trunk: FibreTrunkType = strawberry_django.field()
    osp_fibre_trunk_list: list[FibreTrunkType] = strawberry_django.field()


schema = [NetBoxOspQuery]
