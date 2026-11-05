"""Pack a character model (tools/model2obj: OBJ, one group per region | permutation | material) for the Settings tab's 3D
bot view: native/bin/models/<name>.mdl, read straight into GPU buffers.

  header  "HBMD", uint32 version 1, groups, vertices, indices, then 3 floats min, 3 floats max (model bounds)
  groups  per group: char region[24], char perm[32], int32 perm index, int32 kind, uint32 first index, uint32 count
  verts   float3 position, float3 normal (Halo axes: x forward, y left, z up; world units)
  indices uint32
kind (how the view colours it): 0 armor (primary colour), 1 under-suit, 2 visor, 3 lights, 4 skin, 5 decals (not drawn)

usage: python -I model_pack.py <in.obj> <out.mdl> [region filter: permutations starting with these are dropped, e.g. el_]
"""
import os
import struct
import sys

import numpy as np

KINDS = [("light shield", 5), ("teeth", 4), ("visor", 2), ("lights", 3), ("glow", 3), ("eyemembrane", 1), ("eye", 3), ("rubber", 1), ("black", 1),
         ("techsuit", 1), ("gripsuit", 1), ("emblem", 5), ("decal", 5), ("inscription", 5), ("\\head", 4)]


def kind_of(material):
    m = material.lower()
    if m == "head":                  # Halo 3's Elite face: the skin (drawn as armor, it wore the primary colour)
        return 4
    for key, k in KINDS:
        if key in m:
            return k
    return 0


def main():
    src, out = sys.argv[1], sys.argv[2]
    drop = tuple(sys.argv[3].split(",")) if len(sys.argv) > 3 else ()
    pos, nrm, groups, cur = [], [], {}, None
    faces = {}
    for line in open(src, encoding="utf-8"):
        if line.startswith("v "):
            pos.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("vn "):
            nrm.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("g "):
            region, pi, perm, mat = line[2:].rstrip("\n").split("|")
            cur = (region, int(pi), perm, kind_of(mat))
            if drop and perm.startswith(drop):
                cur = None
            elif cur not in faces:
                faces[cur] = []
        elif line.startswith("f ") and cur is not None:
            faces[cur].extend(int(t.split("/")[0]) - 1 for t in line.split()[1:4])
    pos = np.array(pos, np.float32)
    nrm = np.array(nrm, np.float32) if len(nrm) == len(pos) else np.zeros_like(pos)
    used = sorted({i for f in faces.values() for i in f})
    remap = np.full(len(pos), -1, np.int64)
    remap[used] = np.arange(len(used))
    verts = np.hstack([pos[used], nrm[used]]).astype(np.float32)
    idx, table = [], []
    for (region, pi, perm, kind), f in sorted(faces.items()):
        if not f:
            continue
        table.append((region, perm, pi, kind, len(idx), len(f)))
        idx.extend(remap[f].tolist())
    idx = np.array(idx, np.uint32)
    lo, hi = verts[:, :3].min(0), verts[:, :3].max(0)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "wb") as fh:
        fh.write(b"HBMD" + struct.pack("<IIII", 1, len(table), len(verts), len(idx)) + struct.pack("<6f", *lo, *hi))
        for region, perm, pi, kind, first, n in table:
            fh.write(region.encode()[:23].ljust(24, b"\0") + perm.encode()[:31].ljust(32, b"\0")
                     + struct.pack("<iiII", pi, kind, first, n))
        fh.write(verts.tobytes())
        fh.write(idx.tobytes())
    print(f"{out}: {len(table)} groups, {len(verts)} vertices, {len(idx) // 3} triangles, "
          f"{os.path.getsize(out) / 1e6:.1f} MB, bounds {lo.round(2)} .. {hi.round(2)}")


if __name__ == "__main__":
    main()
