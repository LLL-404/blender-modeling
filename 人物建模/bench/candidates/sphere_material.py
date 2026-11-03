import os
import sys

sys.path.insert(0, os.environ.get(
    "BAPI_DIR", r"D:/G/github/实用工具/Blender建模/BlenderAPI"))
import bapi

OUT = os.environ.get("BENCH_OUT_DIR") or os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)

bapi.env.reset()
bapi.env.engine("BLENDER_EEVEE")
ob = bapi.mesh.sphere(radius=0.6, seg=48, rings=24, name="bench_sphere")
bapi.mat.assign(ob, bapi.mat.principled(
    "bench", base_color=(0.2, 0.55, 0.85), roughness=0.25, metallic=0.1))
bapi.shot.world(color=(0.05, 0.05, 0.06))
bapi.shot.three_point(target=(0.0, 0.0, 0.0), scale=1.0)
cam = bapi.shot.camera_ortho(angle=20, target=(0.0, 0.0, 0.0), scale=1.8)
path, size = bapi.shot.render(
    os.path.join(OUT, "sphere_material.png"), cam=cam, w=512, h=512, samples=16)
stats = bapi.obj.stats(ob)
assert stats["polys"] > 100, stats
assert stats["materials"] == ["bench"], stats
assert size > 1000, (path, size)
print("[bench] sphere_material polys={0} png={1}".format(stats["polys"], size))
