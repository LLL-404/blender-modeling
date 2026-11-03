import math
import os
import sys

sys.path.insert(0, os.environ.get(
    "BAPI_DIR", r"D:/G/github/实用工具/Blender建模/BlenderAPI"))
import bapi

OUT = os.environ.get("BENCH_OUT_DIR") or os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)

bapi.env.reset()
bapi.env.engine("BLENDER_EEVEE")
ob = bapi.mesh.cylinder(z0=-0.5, z1=0.5, r=0.4, seg=32, name="bench_cylinder")
bapi.mod.solidify(ob, thickness=0.03, offset=0.0)
bapi.mat.assign(ob, bapi.mat.principled(
    "bench", base_color=(0.85, 0.65, 0.2), roughness=0.35))
# 侧视正交看不出圆柱：把轴向朝相机倾一点，让顶盖椭圆露出来。
ob.rotation_euler = (math.radians(38), 0.0, math.radians(18))
bapi.shot.world(color=(0.05, 0.05, 0.06))
bapi.shot.three_point(target=(0.0, 0.0, 0.0), scale=1.0)
cam = bapi.shot.camera_ortho(angle=20, target=(0.0, 0.0, 0.0), scale=1.7)
path, size = bapi.shot.render(
    os.path.join(OUT, "cylinder_solidify.png"), cam=cam, w=512, h=512, samples=16)
stats = bapi.obj.stats(ob)
# 素圆柱 96 面；solidify 后应翻倍，低于 180 说明加厚没生效。
assert stats["polys"] >= 180, stats
assert stats["materials"] == ["bench"], stats
assert size > 1000, (path, size)
print("[bench] cylinder_solidify polys={0} png={1}".format(stats["polys"], size))
