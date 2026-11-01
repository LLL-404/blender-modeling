# -*- coding: utf-8 -*-
"""出图工具：把一组 PNG 横向拼成一张对比图（只做中转，不参与建模）。"""
import os
import subprocess

PS = r"""
Add-Type -AssemblyName System.Drawing
$dir = '{dir}'
$names = @({names})
$imgs = @()
foreach ($n in $names) {{
  $p = Join-Path $dir $n
  if (Test-Path $p) {{ $imgs += [System.Drawing.Image]::FromFile($p) }}
}}
if ($imgs.Count -eq 0) {{ Write-Output 'no images'; exit 1 }}
$w = 0; $h = 0
foreach ($i in $imgs) {{ $w += [int]$i.Width; if ($i.Height -gt $h) {{ $h = [int]$i.Height }} }}
$bmp = [System.Drawing.Bitmap]::new([int]$w, [int]$h)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.Clear([System.Drawing.Color]::FromArgb(18, 18, 20))
$x = 0
foreach ($i in $imgs) {{ $g.DrawImage($i, [int]$x, 0, [int]$i.Width, [int]$i.Height); $x += [int]$i.Width }}
$out = Join-Path $dir '{out}'
$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
foreach ($i in $imgs) {{ $i.Dispose() }}
Write-Output $out
"""


def sheet(dirpath, names, out_name):
    quoted = ", ".join("'" + n + "'" for n in names)
    script = PS.format(dir=dirpath, names=quoted, out=out_name)
    r = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                       capture_output=True)
    out = _decode(r.stdout) or _decode(r.stderr)
    print(out)
    return os.path.join(dirpath, out_name)


def _decode(raw):
    for enc in ("utf-8", "gbk"):
        try:
            return raw.decode(enc).strip()
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace").strip()
