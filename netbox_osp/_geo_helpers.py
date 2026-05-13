"""GeoJSON building helpers for the map data endpoint."""
from .models._geo import site_to_point


def cable_feature(cable):
    """Build a GeoJSON Feature for an OspCable.
    Uses cable.route if set; otherwise a straight line between site_a and site_b
    if both have lat/lon."""
    geom = cable.route
    if not geom:
        a = site_to_point(cable.site_a)
        b = site_to_point(cable.site_b)
        if not (a and b):
            return None
        geom = {
            "type": "LineString",
            "coordinates": [a["coordinates"], b["coordinates"]],
        }
    return {
        "type": "Feature",
        "id": f"cable-{cable.pk}",
        "geometry": geom,
        "properties": {
            "kind": "cable",
            "pk": cable.pk,
            "cid": cable.cid,
            "status": cable.status,
            "type": cable.type,
            "fibre_count": cable.fibre_count,
            "length_m": cable.effective_length_m,
            "site_a": cable.site_a.name if cable.site_a else None,
            "site_b": cable.site_b.name if cable.site_b else None,
            "url": cable.get_absolute_url(),
        },
    }


def site_feature(site):
    p = site_to_point(site)
    if not p:
        return None
    return {
        "type": "Feature",
        "id": f"site-{site.pk}",
        "geometry": p,
        "properties": {
            "kind": "site",
            "pk": site.pk,
            "name": site.name,
            "slug": site.slug,
            "status": site.status,
            "url": site.get_absolute_url(),
        },
    }


def closure_feature(closure):
    return {
        "type": "Feature",
        "id": f"closure-{closure.pk}",
        "geometry": closure.location_point,
        "properties": {
            "kind": "closure",
            "pk": closure.pk,
            "name": closure.name,
            "closure_type": closure.closure_type,
            "status": closure.status,
            "capacity": closure.capacity_splices,
            "used": closure.used_splices,
            "site": closure.site.name if closure.site else None,
            "url": closure.get_absolute_url(),
        },
    }


def build_map_geojson(sites_qs, cables_qs, closures_qs):
    features = []
    for s in sites_qs:
        f = site_feature(s)
        if f:
            features.append(f)
    for c in cables_qs:
        f = cable_feature(c)
        if f:
            features.append(f)
    for cl in closures_qs:
        f = closure_feature(cl)
        if f:
            features.append(f)
    return {"type": "FeatureCollection", "features": features}
