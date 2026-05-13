from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from netbox.api.viewsets import NetBoxModelViewSet

from .. import filtersets, models
from . import serializers


class OspCableViewSet(NetBoxModelViewSet):
    queryset = models.OspCable.objects.prefetch_related("tags").all()
    serializer_class = serializers.OspCableSerializer
    filterset_class = filtersets.OspCableFilterSet


class TubeViewSet(NetBoxModelViewSet):
    queryset = models.Tube.objects.prefetch_related("tags").all()
    serializer_class = serializers.TubeSerializer
    filterset_class = filtersets.TubeFilterSet


class StrandViewSet(NetBoxModelViewSet):
    queryset = models.Strand.objects.prefetch_related("tags").all()
    serializer_class = serializers.StrandSerializer
    filterset_class = filtersets.StrandFilterSet


class SpliceClosureViewSet(NetBoxModelViewSet):
    queryset = models.SpliceClosure.objects.prefetch_related("tags").all()
    serializer_class = serializers.SpliceClosureSerializer
    filterset_class = filtersets.SpliceClosureFilterSet


class SpliceTrayViewSet(NetBoxModelViewSet):
    queryset = models.SpliceTray.objects.prefetch_related("tags").all()
    serializer_class = serializers.SpliceTraySerializer
    filterset_class = filtersets.SpliceTrayFilterSet


class SpliceViewSet(NetBoxModelViewSet):
    queryset = models.Splice.objects.prefetch_related("tags").all()
    serializer_class = serializers.SpliceSerializer
    filterset_class = filtersets.SpliceFilterSet


class FibreLinkViewSet(NetBoxModelViewSet):
    queryset = models.FibreLink.objects.prefetch_related("tags").all()
    serializer_class = serializers.FibreLinkSerializer
    filterset_class = filtersets.FibreLinkFilterSet


class LocationGeoViewSet(NetBoxModelViewSet):
    queryset = models.LocationGeo.objects.select_related("location__site").prefetch_related("tags").all()
    serializer_class = serializers.LocationGeoSerializer
    filterset_class = filtersets.LocationGeoFilterSet


class FibreTrunkViewSet(NetBoxModelViewSet):
    queryset = models.FibreTrunk.objects.prefetch_related("tags").all()
    serializer_class = serializers.FibreTrunkSerializer
    filterset_class = filtersets.FibreTrunkFilterSet


class TrunkBreakoutViewSet(NetBoxModelViewSet):
    queryset = (
        models.TrunkBreakout.objects
        .select_related("trunk", "cable")
        .prefetch_related("tags")
        .all()
    )
    serializer_class = serializers.TrunkBreakoutSerializer
    filterset_class = filtersets.TrunkBreakoutFilterSet


class CoreTraceView(APIView):
    """`GET /api/plugins/osp/cores/<strand_id>/trace/` — return the
    end-to-end hop list for a strand. PR E of v0.2.0.

    The response shape is documented in `netbox_osp.tracer.trace_strand`.
    Auth required; falls back to DRF's IsAuthenticated default.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        from ..tracer import trace_strand

        strand = get_object_or_404(
            models.Strand.objects.select_related("cable", "tube"),
            pk=pk,
        )
        return Response(trace_strand(strand))
