import os
import sys

sys.path.insert(0, os.environ.get(
    "BAPI_DIR", r"D:/G/github/实用工具/Blender建模/BlenderAPI"))
import bapi

OUT = os.environ.get("BENCH_OUT_DIR") or os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)

bapi.env.reset()
bapi.env.engine("BLENDER_EEVEE")
ob = bapi.mesh.cube(size=1.0, name="bench_subsurf")
bapi.mod.subsurf(ob, levels=2)
bapi.mat.assign(ob, bapi.mat.principled(
    "bench", base_color=(0.55, 0.25, 0.75), roughness=0.4))
bapi.shot.world(color=(0.05, 0.05, 0.06))
bapi.shot.three_point(target=(0.0, 0.0, 0.0), scale=1.0)
cam = bapi.shot.camera_persp(angle=35, target=(0.0, 0.0, 0.0), distance=3.0, lens=60)
path, size = bapi.shot.render(
    os.path.join(OUT, "cube_subsurf.png"), cam=cam, w=512, h=512, samples=16)
stats = bapi.obj.stats(ob)
# 素立方体 6 面；subsurf level=2 后实测 96 面，低于 90 说明细分没生效。
assert stats["polys"] >= 90, stats
assert stats["materials"] == ["bench"], stats
assert size > 1000, (path, size)
print("[bench] cube_subsurf polys={0} png={1}".format(stats["polys"], size))
