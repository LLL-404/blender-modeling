import json, struct, os, sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def fix(path):
    data = open(path, "rb").read()
    magic, ver, total = struct.unpack("<III", data[:12])
    off = 12
    js = None
    bin_chunk = None
    while off < len(data):
        clen, ctype = struct.unpack("<II", data[off:off + 8])
        payload = data[off + 8:off + 8 + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(payload.decode("utf-8"))
        elif ctype == 0x004E4942:
            bin_chunk = payload
        off += 8 + clen

    for im in js.get("images", []):
        uri = im.get("uri")
        if uri:
            im["uri"] = os.path.basename(uri.replace("\\", "/"))
            im.pop("bufferView", None)
            im.pop("mimeType", None)
            print("  image ->", im["uri"])

    jb = json.dumps(js, separators=(",", ":")).encode("utf-8")
    jb += b" " * ((4 - len(jb) % 4) % 4)
    if bin_chunk is not None:
        bin_chunk += b"\x00" * ((4 - len(bin_chunk) % 4) % 4)
        total_len = 12 + 8 + len(jb) + 8 + len(bin_chunk)
    else:
        total_len = 12 + 8 + len(jb)

    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total_len))
        f.write(struct.pack("<II", len(jb), 0x4E4F534A))
        f.write(jb)
        if bin_chunk is not None:
            f.write(struct.pack("<II", len(bin_chunk), 0x004E4942))
            f.write(bin_chunk)
    print("FIXED", path, "->", os.path.getsize(path), "bytes")


for n in ["core_jade", "tower_ballista"]:
    fix(os.path.join(OUT, n + ".glb"))
