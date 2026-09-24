from math import asin, cos, radians, sin, sqrt


def pin_style(latitude, longitude):
    if latitude is None or longitude is None:
        return "left: 50%; top: 50%;"
    x = max(4, min(96, (float(longitude) + 180) / 360 * 100))
    y = max(8, min(88, (90 - float(latitude)) / 180 * 100))
    return f"left: {x:.1f}%; top: {y:.1f}%;"


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(a))
