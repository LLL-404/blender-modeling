# 环境与渲染

## 渲染引擎

```
BLENDER_EEVEE
```

## 色彩管理 view_transform（9）

> 取自 OCIO 配置并逐个写回验证过。**不要读 RNA 枚举**：
> Blender 5.2 的 `view_settings.bl_rna.properties['view_transform']
> .enum_items` 只返回一条占位 `NONE`，而实际当前值是 `AgX`。

> OCIO 配置：`D:\Program Files\Blender Foundation\Blender 5.2\5.2\datafiles\colormanagement\config.ocio`；当前 display：`sRGB`

```
Standard
ACES 1.3
ACES 2.0
Khronos PBR Neutral
AgX
Filmic
Filmic Log
False Color
Raw
```

### 其它 display 下的 view

**Display P3**（6）：`Standard`, `ACES 1.3`, `ACES 2.0`, `AgX`, `False Color`, `Raw`

**Rec.1886**（6）：`Standard`, `ACES 1.3`, `ACES 2.0`, `AgX`, `False Color`, `Raw`

**Rec.2020**（6）：`Standard`, `ACES 1.3`, `ACES 2.0`, `AgX`, `False Color`, `Raw`

**Rec.2100-PQ**（14）：`Standard`, `ACES 1.3 - HDR 1000 nits`, `ACES 1.3 - HDR 2000 nits`, `ACES 1.3 - HDR 4000 nits`, `ACES 1.3 - SDR`, `ACES 2.0 - HDR 500 nits`, `ACES 2.0 - HDR 1000 nits`, `ACES 2.0 - HDR 2000 nits`, `ACES 2.0 - HDR 4000 nits`, `ACES 2.0 - SDR`, `AgX - HDR 1000 nits`, `AgX - SDR`, `False Color`, `Raw`

**Rec.2100-HLG**（9）：`Standard`, `ACES 1.3 - HDR 1000 nits`, `ACES 1.3 - SDR`, `ACES 2.0 - HDR 1000 nits`, `ACES 2.0 - SDR`, `AgX - HDR 1000 nits`, `AgX - SDR`, `False Color`, `Raw`

## look（OCIO 共 27 个，当前 view_transform 下可用 9 个）

> **look 不是全局可用的**：它由当前 `view_settings.view_transform` 决定。
> 实测 5.2：`AgX` 下只有 `AgX - *` 那批能写，切到 `Filmic` / `Standard` / `Raw`
> 只剩 Filmic 那批。写错直接 `TypeError`。下表按 view_transform 分组。

| view_transform | 可用 look 数 | 可用的 look |
|---|---|---|
| Standard | 7 | `Very High Contrast`, `High Contrast`, `Medium High Contrast`, `Medium Contrast`, `Medium Low Contrast`, `Low Contrast`, `Very Low Contrast` |
| ACES 1.3 | 1 | `ACES 1.3 - Reference Gamut Compression` |
| ACES 2.0 | 1 | `ACES 2.0 - Reference Gamut Compression` |
| Khronos PBR Neutral | 7 | `Very High Contrast`, `High Contrast`, `Medium High Contrast`, `Medium Contrast`, `Medium Low Contrast`, `Low Contrast`, `Very Low Contrast` |
| AgX | 9 | `AgX - Punchy`, `AgX - Greyscale`, `AgX - Very High Contrast`, `AgX - High Contrast`, `AgX - Medium High Contrast`, `AgX - Base Contrast`, `AgX - Medium Low Contrast`, `AgX - Low Contrast`, `AgX - Very Low Contrast` |
| Filmic | 7 | `Very High Contrast`, `High Contrast`, `Medium High Contrast`, `Medium Contrast`, `Medium Low Contrast`, `Low Contrast`, `Very Low Contrast` |
| Filmic Log | 7 | `Very High Contrast`, `High Contrast`, `Medium High Contrast`, `Medium Contrast`, `Medium Low Contrast`, `Low Contrast`, `Very Low Contrast` |
| False Color | 9 | `False Color - Punchy`, `False Color - Greyscale`, `False Color - Very High Contrast`, `False Color - High Contrast`, `False Color - Medium High Contrast`, `False Color - Base Contrast`, `False Color - Medium Low Contrast`, `False Color - Low Contrast`, `False Color - Very Low Contrast` |
| Raw | 7 | `Very High Contrast`, `High Contrast`, `Medium High Contrast`, `Medium Contrast`, `Medium Low Contrast`, `Low Contrast`, `Very Low Contrast` |

## EEVEE 旋钮（54）

```
bokeh_max_size
bokeh_neighbor_max
bokeh_overblur
bokeh_threshold
clamp_surface_direct
clamp_surface_indirect
clamp_volume_direct
clamp_volume_indirect
direct_light_intensity
fast_gi_bias
fast_gi_distance
fast_gi_method
fast_gi_quality
fast_gi_ray_count
fast_gi_resolution
fast_gi_step_count
fast_gi_thickness_near
gi_cubemap_resolution
gi_diffuse_bounces
gi_glossy_clamp
gi_irradiance_pool_size
gi_visibility_resolution
indirect_light_intensity
light_threshold
motion_blur_depth_scale
motion_blur_max
motion_blur_steps
overscan_size
ray_tracing_method
ray_tracing_options
rna_type
shadow_pool_size
shadow_ray_count
shadow_resolution_scale
shadow_step_count
taa_render_samples
taa_samples
use_bokeh_jittered
use_fast_gi
use_overscan
use_raytracing
use_shadow_jitter_viewport
use_shadows
use_taa_reprojection
use_volume_custom_range
use_volumetric_shadows
volumetric_end
volumetric_light_clamp
volumetric_ray_depth
volumetric_sample_distribution
volumetric_samples
volumetric_shadow_samples
volumetric_start
volumetric_tile_size
```

## 图像格式

```
AVIF
JPEG
OPEN_EXR
PNG
WEBP
BMP
CINEON
DPX
IRIS
JPEG2000
HDR
TARGA
TARGA_RAW
TIFF
OPEN_EXR_MULTILAYER
FFMPEG
```
