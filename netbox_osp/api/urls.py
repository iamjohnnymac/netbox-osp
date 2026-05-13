from netbox.api.routers import NetBoxRouter
from . import views


app_name = "netbox_osp-api"

router = NetBoxRouter()
router.register("cables", views.OspCableViewSet, basename="ospcable")
router.register("tubes", views.TubeViewSet, basename="tube")
router.register("strands", views.StrandViewSet, basename="strand")
router.register("closures", views.SpliceClosureViewSet, basename="spliceclosure")
router.register("trays", views.SpliceTrayViewSet, basename="splicetray")
router.register("splices", views.SpliceViewSet, basename="splice")
router.register("links", views.FibreLinkViewSet, basename="fibrelink")
router.register("location-geos", views.LocationGeoViewSet, basename="locationgeo")
router.register("trunks", views.FibreTrunkViewSet, basename="fibretrunk")
router.register("trunk-breakouts", views.TrunkBreakoutViewSet, basename="trunkbreakout")

urlpatterns = router.urls
