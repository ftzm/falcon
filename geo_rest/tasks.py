import geocoder
from typing import List, Optional


def lookup_address(address: str) -> Optional[str]:
    """
    Return the coordinates associated with an address, or None if no match is found
    """
    g = geocoder.osm(address)
    if g.ok:
        return str(tuple(g.latlng))
    else:
        return None


def lookup_coordinates(coordinates: List[float]) -> Optional[str]:
    """
    Return the address associated with coordinates, or None if no match is found
    """
    g = geocoder.osm(coordinates, method="reverse")
    if g.ok:
        return g.address
    else:
        return None
