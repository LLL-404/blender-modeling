import os
import sys

sys.path.insert(0, os.environ.get(
    "BAPI_DIR", r"D:/G/github/实用工具/Blender建模/BlenderAPI"))
import bapi

OUT = os.environ.get("BENCH_OUT_DIR") or os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)

bapi.env.reset()
bapi.env.engine("BLENDER_EEVEE")
ob = bapi.mesh.cube(size=1.0, name="bench_cube")
bapi.mod.bevel(ob, width=0.08, segments=4)
bapi.mat.assign(ob, bapi.mat.principled(
    "bench", base_color=(0.75, 0.25, 0.2), roughness=0.3))
bapi.shot.world(color=(0.05, 0.05, 0.06))
bapi.shot.three_point(target=(0.0, 0.0, 0.0), scale=1.0)
cam = bapi.shot.camera_ortho(angle=30, target=(0.0, 0.0, 0.0), scale=2.2)
path, size = bapi.shot.render(
    os.path.join(OUT, "cube_bevel.png"), cam=cam, w=512, h=512, samples=16)
stats = bapi.obj.stats(ob)
# 素立方体 6 面；4 段倒角后实测 150 面，低于 100 说明 bevel 没生效。
assert stats["polys"] >= 100, stats
assert stats["materials"] == ["bench"], stats
assert size > 1000, (path, size)
print("[bench] cube_bevel polys={0} png={1}".format(stats["polys"], size))
