"""
GeoJSON validators. RFC 7946: coordinates are [longitude, latitude] in WGS84,
longitude in (-180, 180], latitude in [-90, 90].

Internal storage convention: GeoJSON [lon, lat]
NetBox Site native fields:    latitude, longitude
Leaflet:                       [lat, lon]
Convert at the boundaries only — never in the middle.
"""
from django.core.exceptions import ValidationError


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _check_lon_lat(coord, where):
    if not isinstance(coord, (list, tuple)) or len(coord) < 2:
        raise ValidationError(f"{where}: coordinate must be [lon, lat]")
    lon, lat = coord[0], coord[1]
    if not _is_number(lon) or not _is_number(lat):
        raise ValidationError(f"{where}: lon and lat must be numbers")
    if not (-180.0 <= lon <= 180.0):
        raise ValidationError(
            f"{where}: longitude {lon} out of range [-180, 180]; "
            "did you swap lon and lat? GeoJSON is [lon, lat]."
        )
    if not (-90.0 <= lat <= 90.0):
        raise ValidationError(
            f"{where}: latitude {lat} out of range [-90, 90]; "
            "did you swap lon and lat? GeoJSON is [lon, lat]."
        )


def validate_point(value):
    """Validate a GeoJSON Point geometry: {'type': 'Point', 'coordinates': [lon, lat]}."""
    if value in (None, "", {}):
        return
    if not isinstance(value, dict):
        raise ValidationError("Point must be a JSON object")
    if value.get("type") != "Point":
        raise ValidationError("type must be 'Point'")
    coords = value.get("coordinates")
    _check_lon_lat(coords, "Point.coordinates")


def validate_linestring(value):
    """Validate a GeoJSON LineString: {'type': 'LineString', 'coordinates': [[lon,lat], ...]}."""
    if value in (None, "", {}):
        return
    if not isinstance(value, dict):
        raise ValidationError("LineString must be a JSON object")
    if value.get("type") != "LineString":
        raise ValidationError("type must be 'LineString'")
    coords = value.get("coordinates")
    if not isinstance(coords, list) or len(coords) < 2:
        raise ValidationError("LineString.coordinates must have at least 2 points")
    for i, c in enumerate(coords):
        _check_lon_lat(c, f"LineString.coordinates[{i}]")


def linestring_length_m(value):
    """Approximate length in metres using the equirectangular (flat-earth) formula.
    Good to ~0.5% for distances <100 km. Returns 0 for empty/None."""
    import math
    if not value or value.get("type") != "LineString":
        return 0
    coords = value.get("coordinates") or []
    if len(coords) < 2:
        return 0
    total = 0.0
    R = 6371008.8  # mean Earth radius in metres (WGS84)
    for (lon1, lat1), (lon2, lat2) in zip(coords[:-1], coords[1:]):
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        x = (math.radians(lon2 - lon1)) * math.cos((phi1 + phi2) / 2)
        y = math.radians(lat2 - lat1)
        total += R * math.hypot(x, y)
    return total


def site_to_point(site):
    """Convert a NetBox Site (with .latitude/.longitude) to a GeoJSON Point.
    Returns None if either coord is missing."""
    if site is None or site.latitude is None or site.longitude is None:
        return None
    return {"type": "Point", "coordinates": [float(site.longitude), float(site.latitude)]}


def point_in_polygon(point, polygon):
    """Ray-casting point-in-polygon test.

    point   : [lon, lat]   (GeoJSON order, matches our stored convention)
    polygon : iterable of [lon, lat] vertices forming a ring. We close
              the ring implicitly (the last vertex does not have to equal
              the first).

    Edge / vertex behaviour is implementation-defined per the standard
    ray-casting algorithm — points lying exactly on an edge may be
    classified either way. For our use (validating cable routes against
    a generous operator-drawn boundary) that is fine.

    Returns True if the point is strictly inside the polygon, False
    otherwise. Degenerate polygons (< 3 vertices) always return False.
    """
    if not isinstance(point, (list, tuple)) or len(point) < 2:
        return False
    if not isinstance(polygon, (list, tuple)) or len(polygon) < 3:
        return False
    lon, lat = point[0], point[1]
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        try:
            lon_i, lat_i = polygon[i][0], polygon[i][1]
            lon_j, lat_j = polygon[j][0], polygon[j][1]
        except (IndexError, TypeError):
            return False
        # Standard ray-casting test: count crossings of a horizontal ray
        # going to the right from the test point.
        if (lat_i > lat) != (lat_j > lat):
            # Crossing y; check x coordinate of the edge at lat=lat.
            x_cross = (lon_j - lon_i) * (lat - lat_i) / (lat_j - lat_i) + lon_i
            if lon < x_cross:
                inside = not inside
        j = i
    return inside


def validate_route_within_boundary(route, boundary):
    """Validate that every vertex of a GeoJSON LineString lies inside a polygon.

    route    : a GeoJSON LineString dict (or None — skipped silently).
    boundary : list of [lon, lat] vertices (or falsy — skipped silently).

    Raises ValidationError with the index + coordinates of the first
    offending vertex. Used by OspCable.clean() when the operator
    configures PLUGINS_CONFIG['netbox_osp']['plant_boundary'].
    """
    if not route or not boundary:
        return
    if not isinstance(boundary, (list, tuple)) or len(boundary) < 3:
        # Defensive: an invalid boundary spec is ignored rather than
        # bringing the plugin down. The startup log will have warned.
        return
    coords = route.get("coordinates") if isinstance(route, dict) else None
    if not coords:
        return
    for i, c in enumerate(coords):
        if not point_in_polygon(c, boundary):
            lon = c[0] if isinstance(c, (list, tuple)) and len(c) > 0 else "?"
            lat = c[1] if isinstance(c, (list, tuple)) and len(c) > 1 else "?"
            raise ValidationError(
                f"route vertex {i} at lon={lon}, lat={lat} is outside the "
                f"configured plant_boundary."
            )
