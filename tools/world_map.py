"""(Nov 19, the owner: on Project Reach's Psych Profile page "id like the same world map. and then a static heat map
of the service websites player locations") Writes native/world_map.h, the world map built into botcore: the land and
the US states' outlines and centres, from Natural Earth's 1:110m vector data (public domain, naturalearthdata.com;
github.com/nvkelso/natural-earth-vector, geojson/ne_110m_land.geojson and geojson/ne_110m_admin_1_states_provinces.geojson).
The GeoJSON files are not kept in the repository: get them again from there to rebuild the header.

Each polygon's outer ring, at a tenth of a degree (int16 lon*10, lat*10), points that round to the one before dropped,
the ring's closing point dropped. The states keep their two-letter code and Natural Earth's label point (its latitude
and longitude), where the heat of the Service Record's home states is drawn (native/proving_grounds_reach.inc).

usage: python -I tools/world_map.py <ne_110m_land.geojson> <ne_110m_admin_1_states_provinces.geojson> [out.h]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "native", "world_map.h")


def outer_rings(geometry):
    """Each polygon's outer ring ([[lon, lat], ...]) of a Polygon or MultiPolygon."""
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"][0]]
    if geometry["type"] == "MultiPolygon":
        return [poly[0] for poly in geometry["coordinates"]]
    return []


def tenths(ring):
    """A ring at a tenth of a degree: [(lon10, lat10), ...], repeats and the closing point dropped (None: too small)."""
    out = []
    for lon, lat in ring:
        p = (int(round(lon * 10)), int(round(lat * 10)))
        if not out or p != out[-1]:
            out.append(p)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out if len(out) >= 3 else None


def flat(rings):
    pts, counts = [], []
    for r in rings:
        counts.append(len(r))
        for lon, lat in r:
            pts += [lon, lat]
    return pts, counts


def numbers(values, per_line=16):
    lines = []
    for i in range(0, len(values), per_line):
        lines.append("    " + ", ".join(str(v) for v in values[i:i + per_line]) + ",")
    return "\n".join(lines)


def build(land_path, states_path):
    with open(land_path, encoding="utf-8") as f:
        land = json.load(f)
    with open(states_path, encoding="utf-8") as f:
        provinces = json.load(f)
    land_rings = [r for feat in land["features"] for r in map(tenths, outer_rings(feat["geometry"])) if r]
    states, state_rings = [], []
    us = [feat for feat in provinces["features"] if feat["properties"].get("iso_a2") == "US"]
    for feat in sorted(us, key=lambda x: x["properties"]["postal"]):
        p = feat["properties"]
        rings = [r for r in map(tenths, outer_rings(feat["geometry"])) if r]
        states.append((p["postal"], int(round(p["latitude"] * 10)), int(round(p["longitude"] * 10)), len(state_rings),
                       len(rings)))
        state_rings += rings
    if len(land_rings) < 50 or len(states) != 51:
        raise SystemExit(f"unexpected data: {len(land_rings)} land rings, {len(states)} US states (50 and DC expected)")
    lp, lc = flat(land_rings)
    sp, sc = flat(state_rings)
    rows = ",\n".join(f'    {{"{c}", {la}, {lo}, {r0}, {n}}}' for c, la, lo, r0, n in states)
    return f"""// world_map.h: made by tools/world_map.py, do not edit. The world's land and the US states' outlines and label
// points, from Natural Earth's 1:110m vector data (public domain, naturalearthdata.com): each polygon's outer ring at a
// tenth of a degree (lon * 10, lat * 10). Drawn on Project Reach's Psych Profile page (proving_grounds_reach.inc).
#pragma once
#include <stdint.h>

static const int16_t WM_LAND_PTS[] = {{
{numbers(lp)}
}};
static const uint16_t WM_LAND_RING[] = {{   // points in each ring, in order
{numbers(lc)}
}};
static const int WM_LAND_RINGS = {len(lc)};

static const int16_t WM_STATE_PTS[] = {{
{numbers(sp)}
}};
static const uint16_t WM_STATE_RING[] = {{
{numbers(sc)}
}};
struct wm_state {{ char code[3]; int16_t lat10, lon10; uint16_t ring0, rings; }};
static const wm_state WM_STATES[] = {{   // the 50 states and DC by code: label point, their rings in WM_STATE_RING
{rows}
}};
static const int WM_NSTATES = {len(states)};
"""


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    text = build(sys.argv[1], sys.argv[2])
    out = sys.argv[3] if len(sys.argv) > 3 else OUT
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, out)
    print(f"wrote {os.path.normpath(out)} ({len(text) // 1024} KB)")


if __name__ == "__main__":
    main()
