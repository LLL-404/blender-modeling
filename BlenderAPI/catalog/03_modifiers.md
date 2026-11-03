# 修改器与约束

## 修改器类型（83）

```
GREASE_PENCIL_VERTEX_WEIGHT_PROXIMITY DATA_TRANSFER MESH_CACHE MESH_SEQUENCE_CACHE NORMAL_EDIT WEIGHTED_NORMAL UV_PROJECT UV_WARP VERTEX_WEIGHT_EDIT VERTEX_WEIGHT_MIX VERTEX_WEIGHT_PROXIMITY GREASE_PENCIL_COLOR GREASE_PENCIL_TINT GREASE_PENCIL_OPACITY GREASE_PENCIL_VERTEX_WEIGHT_ANGLE GREASE_PENCIL_TIME GREASE_PENCIL_TEXTURE ARRAY BEVEL BOOLEAN BUILD DECIMATE EDGE_SPLIT NODES MASK MIRROR MESH_TO_VOLUME MULTIRES REMESH SCREW SKIN SOLIDIFY SUBSURF TRIANGULATE VOLUME_TO_MESH WELD WIREFRAME GREASE_PENCIL_ARRAY GREASE_PENCIL_BUILD GREASE_PENCIL_LENGTH LINEART GREASE_PENCIL_MIRROR GREASE_PENCIL_MULTIPLY GREASE_PENCIL_SIMPLIFY GREASE_PENCIL_SUBDIV GREASE_PENCIL_ENVELOPE GREASE_PENCIL_OUTLINE ARMATURE CAST CURVE DISPLACE HOOK LAPLACIANDEFORM LATTICE MESH_DEFORM SHRINKWRAP SIMPLE_DEFORM SMOOTH CORRECTIVE_SMOOTH LAPLACIANSMOOTH SURFACE_DEFORM WARP WAVE VOLUME_DISPLACE GREASE_PENCIL_HOOK GREASE_PENCIL_NOISE GREASE_PENCIL_OFFSET GREASE_PENCIL_SMOOTH GREASE_PENCIL_THICKNESS GREASE_PENCIL_LATTICE GREASE_PENCIL_DASH GREASE_PENCIL_ARMATURE GREASE_PENCIL_SHRINKWRAP CLOTH COLLISION DYNAMIC_PAINT EXPLODE FLUID OCEAN PARTICLE_INSTANCE PARTICLE_SYSTEM SOFT_BODY SURFACE
```

## 约束类型（29）

```
CAMERA_SOLVER FOLLOW_TRACK OBJECT_SOLVER COPY_LOCATION COPY_ROTATION COPY_SCALE COPY_TRANSFORMS LIMIT_DISTANCE LIMIT_LOCATION LIMIT_ROTATION LIMIT_SCALE MAINTAIN_VOLUME TRANSFORM TRANSFORM_CACHE CLAMP_TO DAMPED_TRACK IK LOCKED_TRACK SPLINE_IK STRETCH_TO TRACK_TO ACTION ARMATURE CHILD_OF FLOOR FOLLOW_PATH GEOMETRY_ATTRIBUTE PIVOT SHRINKWRAP
```

## 修改器参数（83 类）

参数名、类型、默认值都从**真实实例**读取：`host.modifiers.new(name, type)`
之后读 RNA，读完把实例删掉。已剔除下面这批所有修改器共有的通用属性：

`name` · `type` · `show_viewport` · `show_render` · `show_in_editmode` · `show_on_cage` · `show_expanded` · `is_active` · `use_pin_to_last` · `is_override_data` · `use_apply_on_spline` · `execution_time` · `persistent_uid` · `rna_type`

> **修改器的参数不在 `bpy.ops` 里。** `bpy.ops.modifier` 命名空间在 5.2 实测 0 条；
> 加修改器一律 `ob.modifiers.new(name, TYPE)` 再赋属性，属性名查下表。

### ARMATURE（7 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| object | POINTER |  |  |
| use_bone_envelopes | BOOLEAN | False |  |
| use_vertex_groups | BOOLEAN | True |  |
| use_deform_preserve_volume | BOOLEAN | False |  |
| use_multi_modifier | BOOLEAN | False |  |
| vertex_group | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |

### ARRAY（17 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| fit_type | ENUM | FIXED_COUNT | FIXED_COUNT, FIT_LENGTH, FIT_CURVE |
| count | INT | 2 | range 1..2147483647 |
| fit_length | FLOAT | 0 | range 0..2.15e+09 |
| curve | POINTER |  |  |
| use_constant_offset | BOOLEAN | False |  |
| constant_offset_displace | FLOAT | [1, 0, 0] |  |
| use_relative_offset | BOOLEAN | True |  |
| relative_offset_displace | FLOAT | [1, 0, 0] |  |
| use_merge_vertices | BOOLEAN | False |  |
| use_merge_vertices_cap | BOOLEAN | False |  |
| merge_threshold | FLOAT | 0.01 | range 0..3.4e+38 |
| use_object_offset | BOOLEAN | False |  |
| offset_object | POINTER |  |  |
| start_cap | POINTER |  |  |
| end_cap | POINTER |  |  |
| offset_u | FLOAT | 0 | range -1..1 |
| offset_v | FLOAT | 0 | range -1..1 |

### BEVEL（25 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| width | FLOAT | 0.1 | range 0..3.4e+38 |
| width_pct | FLOAT | 0.1 | range 0..3.4e+38 |
| segments | INT | 1 | range 1..1000 |
| affect | ENUM | EDGES | VERTICES, EDGES |
| limit_method | ENUM | ANGLE | NONE, ANGLE, WEIGHT, VGROUP |
| edge_weight | STRING | bevel_weight_edge |  |
| vertex_weight | STRING | bevel_weight_vert |  |
| angle_limit | FLOAT | 0.5236 | range 0..3.1416 |
| vertex_group | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| use_clamp_overlap | BOOLEAN | True |  |
| offset_type | ENUM | OFFSET | OFFSET, WIDTH, DEPTH, PERCENT, ABSOLUTE |
| profile_type | ENUM | SUPERELLIPSE | SUPERELLIPSE, CUSTOM |
| profile | FLOAT | 0.5 | range 0..1 |
| material | INT | -1 | range -1..32767 |
| loop_slide | BOOLEAN | True |  |
| mark_seam | BOOLEAN | False |  |
| mark_sharp | BOOLEAN | False |  |
| harden_normals | BOOLEAN | False |  |
| face_strength_mode | ENUM | FSTR_NONE | FSTR_NONE, FSTR_NEW, FSTR_AFFECTED, FSTR_ALL |
| miter_outer | ENUM | MITER_SHARP | MITER_SHARP, MITER_PATCH, MITER_ARC |
| miter_inner | ENUM | MITER_SHARP | MITER_SHARP, MITER_ARC |
| spread | FLOAT | 0.1 | range 0..3.4e+38 |
| custom_profile | POINTER |  |  |
| vmesh_method | ENUM | ADJ | ADJ, CUTOFF |

### BOOLEAN（10 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| object | POINTER |  |  |
| collection | POINTER |  |  |
| operation | ENUM | DIFFERENCE | INTERSECT, UNION, DIFFERENCE |
| operand_type | ENUM | OBJECT | OBJECT, COLLECTION |
| double_threshold | FLOAT | 0 | range 0..1 |
| solver | ENUM | EXACT | FLOAT, EXACT, MANIFOLD |
| use_self | BOOLEAN | False |  |
| use_hole_tolerant | BOOLEAN | False |  |
| material_mode | ENUM | INDEX | INDEX, TRANSFER |
| debug_options | ENUM | [] | SEPARATE, NO_DISSOLVE, NO_CONNECT_REGIONS |

### BUILD（5 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| frame_start | FLOAT | 1 | range -1.05e+06..1.05e+06 |
| frame_duration | FLOAT | 100 | range 1..1.05e+06 |
| use_reverse | BOOLEAN | False |  |
| use_random_order | BOOLEAN | False |  |
| seed | INT | 0 | range 1..1048574 |

### CAST（12 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| cast_type | ENUM | SPHERE | SPHERE, CYLINDER, CUBOID |
| object | POINTER |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| use_x | BOOLEAN | True |  |
| use_y | BOOLEAN | True |  |
| use_z | BOOLEAN | True |  |
| use_radius_as_size | BOOLEAN | True |  |
| use_transform | BOOLEAN | False |  |
| factor | FLOAT | 0.5 |  |
| radius | FLOAT | 0 | range 0..3.4e+38 |
| size | FLOAT | 0 | range 0..3.4e+38 |
| vertex_group | STRING |  |  |

### CLOTH（7 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| settings | POINTER |  |  |
| collision_settings | POINTER |  |  |
| solver_result | POINTER |  |  |
| point_cache | POINTER |  |  |
| hair_grid_min | FLOAT |  |  |
| hair_grid_max | FLOAT |  |  |
| hair_grid_resolution | INT |  |  |

### COLLISION（1 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| settings | POINTER |  |  |

### CORRECTIVE_SMOOTH（10 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| factor | FLOAT | 0.5 |  |
| iterations | INT | 5 | range 0..32767 |
| scale | FLOAT | 1 |  |
| rest_source | ENUM | ORCO | ORCO, BIND |
| smooth_type | ENUM | SIMPLE | SIMPLE, LENGTH_WEIGHTED |
| invert_vertex_group | BOOLEAN | False |  |
| vertex_group | STRING |  |  |
| is_bind | BOOLEAN |  |  |
| use_only_smooth | BOOLEAN | False |  |
| use_pin_boundary | BOOLEAN | False |  |

### CURVE（4 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| object | POINTER |  |  |
| vertex_group | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| deform_axis | ENUM | POS_X | POS_X, POS_Y, POS_Z, NEG_X, NEG_Y, NEG_Z |

### DATA_TRANSFER（30 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| object | POINTER |  |  |
| use_object_transform | BOOLEAN | True |  |
| use_vert_data | BOOLEAN | False |  |
| use_edge_data | BOOLEAN | False |  |
| use_loop_data | BOOLEAN | False |  |
| use_poly_data | BOOLEAN | False |  |
| data_types_verts | ENUM | [] | VGROUP_WEIGHTS, BEVEL_WEIGHT_VERT, COLOR_VERTEX |
| data_types_edges | ENUM | [] | SHARP_EDGE, SEAM, CREASE, BEVEL_WEIGHT_EDGE, FREESTYLE_EDGE |
| data_types_loops | ENUM | [] | CUSTOM_NORMAL, COLOR_CORNER, UV |
| data_types_polys | ENUM | [] | SMOOTH, FREESTYLE_FACE |
| vert_mapping | ENUM | NEAREST | TOPOLOGY, NEAREST, EDGE_NEAREST, EDGEINTERP_NEAREST, POLY_NEAREST, POLYINTERP_NEAREST … |
| edge_mapping | ENUM | NEAREST | TOPOLOGY, VERT_NEAREST, NEAREST, POLY_NEAREST, EDGEINTERP_VNORPROJ |
| loop_mapping | ENUM | NEAREST_POLYNOR | TOPOLOGY, NEAREST_NORMAL, NEAREST_POLYNOR, NEAREST_POLY, POLYINTERP_NEAREST, POLYINTERP_LNORPROJ |
| poly_mapping | ENUM | NEAREST | TOPOLOGY, NEAREST, NORMAL, POLYINTERP_PNORPROJ |
| use_max_distance | BOOLEAN | False |  |
| max_distance | FLOAT | 1 | range 0..3.4e+38 |
| ray_radius | FLOAT | 0 | range 0..3.4e+38 |
| islands_precision | FLOAT | 0 | range 0..1 |
| layers_vgroup_select_src | ENUM | ALL | ACTIVE, ALL, BONE_SELECT, BONE_DEFORM |
| layers_vcol_vert_select_src | ENUM | ALL | ACTIVE, ALL, BONE_SELECT, BONE_DEFORM |
| layers_vcol_loop_select_src | ENUM | ALL | ACTIVE, ALL, BONE_SELECT, BONE_DEFORM |
| layers_uv_select_src | ENUM | ALL | ACTIVE, ALL, BONE_SELECT, BONE_DEFORM |
| layers_vgroup_select_dst | ENUM | NAME | ACTIVE, NAME, INDEX |
| layers_vcol_vert_select_dst | ENUM | NAME | ACTIVE, NAME, INDEX |
| layers_vcol_loop_select_dst | ENUM | NAME | ACTIVE, NAME, INDEX |
| layers_uv_select_dst | ENUM | NAME | ACTIVE, NAME, INDEX |
| mix_mode | ENUM | REPLACE | REPLACE, ABOVE_THRESHOLD, BELOW_THRESHOLD, MIX, ADD, SUB … |
| mix_factor | FLOAT | 1 | range 0..1 |
| vertex_group | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |

### DECIMATE（13 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| decimate_type | ENUM | COLLAPSE | COLLAPSE, UNSUBDIV, DISSOLVE |
| ratio | FLOAT | 1 | range 0..1 |
| iterations | INT | 0 | range 0..32767 |
| angle_limit | FLOAT | 0.0873 | range 0..3.1416 |
| vertex_group | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| use_collapse_triangulate | BOOLEAN | False |  |
| use_symmetry | BOOLEAN | False |  |
| symmetry_axis | ENUM | X | X, Y, Z |
| vertex_group_factor | FLOAT | 1 | range 0..1000 |
| use_dissolve_boundaries | BOOLEAN | False |  |
| delimit | ENUM | [] | NORMAL, MATERIAL, SEAM, SHARP, UV |
| face_count | INT |  | range -2147483648..2147483647 |

### DISPLACE（11 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| vertex_group | STRING |  |  |
| mid_level | FLOAT | 0.5 |  |
| strength | FLOAT | 1 |  |
| direction | ENUM | NORMAL | X, Y, Z, NORMAL, CUSTOM_NORMAL, RGB_TO_XYZ |
| space | ENUM | LOCAL | LOCAL, GLOBAL |
| invert_vertex_group | BOOLEAN | False |  |
| texture | POINTER |  |  |
| texture_coords | ENUM | LOCAL | LOCAL, GLOBAL, OBJECT, UV |
| uv_layer | STRING |  |  |
| texture_coords_object | POINTER |  |  |
| texture_coords_bone | STRING |  |  |

### DYNAMIC_PAINT（3 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| canvas_settings | POINTER |  |  |
| brush_settings | POINTER |  |  |
| ui_type | ENUM | CANVAS | CANVAS, BRUSH |

### EDGE_SPLIT（3 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| split_angle | FLOAT | 0.5236 | range 0..3.1416 |
| use_edge_angle | BOOLEAN | True |  |
| use_edge_sharp | BOOLEAN | True |  |

### EXPLODE（9 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| vertex_group | STRING |  |  |
| protect | FLOAT | 0 | range 0..1 |
| use_edge_cut | BOOLEAN | False |  |
| show_unborn | BOOLEAN | True |  |
| show_alive | BOOLEAN | True |  |
| show_dead | BOOLEAN | True |  |
| use_size | BOOLEAN | False |  |
| particle_uv | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |

### FLUID（4 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| domain_settings | POINTER |  |  |
| flow_settings | POINTER |  |  |
| effector_settings | POINTER |  |  |
| fluid_type | ENUM | NONE | NONE, DOMAIN, FLOW, EFFECTOR |

### GREASE_PENCIL_ARMATURE（7 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| vertex_group_name | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| open_influence_panel | BOOLEAN | False |  |
| object | POINTER |  |  |
| use_bone_envelopes | BOOLEAN | False |  |
| use_vertex_groups | BOOLEAN | True |  |
| use_deform_preserve_volume | BOOLEAN | False |  |

### GREASE_PENCIL_ARRAY（29 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| open_constant_offset_panel | BOOLEAN | False |  |
| open_relative_offset_panel | BOOLEAN | False |  |
| open_object_offset_panel | BOOLEAN | False |  |
| open_randomize_panel | BOOLEAN | False |  |
| open_influence_panel | BOOLEAN | False |  |
| count | INT | 2 | range 1..32767 |
| offset_object | POINTER |  |  |
| constant_offset | FLOAT | [0, 0, 0] |  |
| relative_offset | FLOAT | [1, 0, 0] |  |
| random_offset | FLOAT | [0, 0, 0] |  |
| random_rotation | FLOAT | [0, 0, 0] |  |
| random_scale | FLOAT | [0, 0, 0] |  |
| seed | INT | 1 | range 0..2147483647 |
| replace_material | INT | 0 | range 0..32767 |
| use_constant_offset | BOOLEAN | False |  |
| use_object_offset | BOOLEAN | False |  |
| use_relative_offset | BOOLEAN | True |  |
| use_uniform_random_scale | BOOLEAN | False |  |

### GREASE_PENCIL_BUILD（33 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| open_influence_panel | BOOLEAN | False |  |
| open_frame_range_panel | BOOLEAN | False |  |
| open_fading_panel | BOOLEAN | False |  |
| mode | ENUM | SEQUENTIAL | SEQUENTIAL, CONCURRENT, ADDITIVE |
| transition | ENUM | GROW | GROW, SHRINK, FADE |
| start_delay | FLOAT | 0 | range 0..1.05e+06 |
| length | FLOAT | 100 | range 1..1.05e+06 |
| concurrent_time_alignment | ENUM | START | START, END |
| time_mode | ENUM | FRAMES | DRAWSPEED, FRAMES, PERCENTAGE |
| speed_factor | FLOAT | 1.2 | range 0..100 |
| speed_maxgap | FLOAT | 0.5 | range 0..100 |
| use_restrict_frame_range | BOOLEAN | False |  |
| use_percentage | BOOLEAN | False |  |
| percentage_factor | FLOAT | 0 | range 0..1 |
| frame_start | FLOAT | 1 | range -1.05e+06..1.05e+06 |
| frame_end | FLOAT | 125 | range -1.05e+06..1.05e+06 |
| use_fading | BOOLEAN | False |  |
| fade_factor | FLOAT | 0 | range 0..1 |
| target_vertex_group | STRING |  |  |
| fade_opacity_strength | FLOAT | 0 | range 0..1 |
| fade_thickness_strength | FLOAT | 0 | range 0..1 |
| object | POINTER |  |  |

### GREASE_PENCIL_COLOR（18 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| use_custom_curve | BOOLEAN | False |  |
| custom_curve | POINTER |  |  |
| open_influence_panel | BOOLEAN | False |  |
| color_mode | ENUM | BOTH | BOTH, STROKE, FILL |
| hue | FLOAT | 0.5 | range 0..1 |
| saturation | FLOAT | 1 | range 0..3.4e+38 |
| value | FLOAT | 1 | range 0..3.4e+38 |

### GREASE_PENCIL_DASH（15 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| open_influence_panel | BOOLEAN | False |  |
| segments | COLLECTION |  |  |
| segment_active_index | INT | 0 | range 0..2147483647 |
| dash_offset | INT | 0 | range -2147483648..2147483647 |

### GREASE_PENCIL_ENVELOPE（20 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| vertex_group_name | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| open_influence_panel | BOOLEAN | False |  |
| mode | ENUM | SEGMENTS | DEFORM, SEGMENTS, FILLS |
| spread | INT | 10 | range 1..2147483647 |
| mat_nr | INT | -1 | range -1..32767 |
| thickness | FLOAT | 1 | range 0..3.4e+38 |
| strength | FLOAT | 1 | range 0..3.4e+38 |
| skip | INT | 0 | range 0..2147483647 |

### GREASE_PENCIL_HOOK（25 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| vertex_group_name | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| use_custom_curve | BOOLEAN | False |  |
| custom_curve | POINTER |  |  |
| open_influence_panel | BOOLEAN | False |  |
| open_falloff_panel | BOOLEAN | False |  |
| object | POINTER |  |  |
| subtarget | STRING |  |  |
| strength | FLOAT | 0.5 | range 0..1 |
| falloff_type | ENUM | SMOOTH | NONE, CURVE, SMOOTH, SPHERE, ROOT, INVERSE_SQUARE … |
| falloff_radius | FLOAT | 0 | range 0..3.4e+38 |
| center | FLOAT | [0, 0, 0] |  |
| matrix_inverse | FLOAT |  |  |
| use_falloff_uniform | BOOLEAN | False |  |

### GREASE_PENCIL_LATTICE（16 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| vertex_group_name | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| open_influence_panel | BOOLEAN | False |  |
| object | POINTER |  |  |
| strength | FLOAT | 1 |  |

### GREASE_PENCIL_LENGTH（31 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| open_random_panel | BOOLEAN | False |  |
| open_curvature_panel | BOOLEAN | False |  |
| open_influence_panel | BOOLEAN | False |  |
| start_factor | FLOAT | 0.1 |  |
| end_factor | FLOAT | 0.1 |  |
| start_length | FLOAT | 0.1 |  |
| end_length | FLOAT | 0.1 |  |
| random_start_factor | FLOAT | 0 |  |
| random_end_factor | FLOAT | 0 |  |
| random_offset | FLOAT | 0 |  |
| use_random | BOOLEAN | False |  |
| seed | INT | 0 | range 0..2147483647 |
| step | INT | 4 | range 1..100 |
| overshoot_factor | FLOAT | 0.1 | range 0..1 |
| mode | ENUM | RELATIVE | RELATIVE, ABSOLUTE |
| use_curvature | BOOLEAN | True |  |
| invert_curvature | BOOLEAN | False |  |
| point_density | FLOAT | 30 | range 0.1..1000 |
| segment_influence | FLOAT | 0 | range -2..3 |
| max_angle | FLOAT | 2.9671 | range 0..3.1416 |

### GREASE_PENCIL_MIRROR（16 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| open_influence_panel | BOOLEAN | False |  |
| object | POINTER |  |  |
| use_axis_x | BOOLEAN | True |  |
| use_axis_y | BOOLEAN | False |  |
| use_axis_z | BOOLEAN | False |  |

### GREASE_PENCIL_MULTIPLY（20 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| open_fading_panel | BOOLEAN | False |  |
| open_influence_panel | BOOLEAN | False |  |
| use_fade | BOOLEAN | False |  |
| duplicates | INT | 3 | range 0..999 |
| distance | FLOAT | 0.1 |  |
| offset | FLOAT | 0 |  |
| fading_thickness | FLOAT | 0.5 | range 0..1 |
| fading_opacity | FLOAT | 0.5 | range 0..1 |
| fading_center | FLOAT | 0.5 | range 0..1 |

### GREASE_PENCIL_NOISE（27 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| vertex_group_name | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| use_custom_curve | BOOLEAN | False |  |
| custom_curve | POINTER |  |  |
| open_influence_panel | BOOLEAN | False |  |
| open_random_panel | BOOLEAN | False |  |
| factor | FLOAT | 0.5 | range 0..3.4e+38 |
| factor_strength | FLOAT | 0 | range 0..3.4e+38 |
| factor_thickness | FLOAT | 0 | range 0..3.4e+38 |
| factor_uvs | FLOAT | 0 | range 0..3.4e+38 |
| use_random | BOOLEAN | True |  |
| seed | INT | 1 | range 0..2147483647 |
| noise_scale | FLOAT | 0 | range 0..1 |
| noise_offset | FLOAT | 0 | range 0..3.4e+38 |
| step | INT | 4 | range 1..100 |
| random_mode | ENUM | STEP | STEP, KEYFRAME |

### GREASE_PENCIL_OFFSET（26 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| vertex_group_name | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| open_general_panel | BOOLEAN | False |  |
| open_influence_panel | BOOLEAN | False |  |
| offset_mode | ENUM | RANDOM | RANDOM, LAYER, STROKE, MATERIAL |
| location | FLOAT | [0, 0, 0] |  |
| rotation | FLOAT | [0, 0, 0] |  |
| scale | FLOAT | [0, 0, 0] |  |
| stroke_location | FLOAT | [0, 0, 0] |  |
| stroke_rotation | FLOAT | [0, 0, 0] |  |
| stroke_scale | FLOAT | [0, 0, 0] |  |
| seed | INT | 0 | range 0..2147483647 |
| stroke_step | INT | 1 | range 1..500 |
| stroke_start_offset | INT | 0 | range 0..2147483647 |
| use_uniform_random_scale | BOOLEAN | False |  |

### GREASE_PENCIL_OPACITY（21 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| vertex_group_name | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| use_custom_curve | BOOLEAN | False |  |
| custom_curve | POINTER |  |  |
| open_influence_panel | BOOLEAN | False |  |
| color_mode | ENUM | BOTH | BOTH, STROKE, FILL, HARDNESS |
| color_factor | FLOAT | 1 |  |
| hardness_factor | FLOAT | 1 | range 0..3.4e+38 |
| use_weight_as_factor | BOOLEAN | False |  |
| use_uniform_opacity | BOOLEAN | False |  |

### GREASE_PENCIL_OUTLINE（18 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| open_influence_panel | BOOLEAN | False |  |
| thickness | INT | 1 | range 1..1000 |
| sample_length | FLOAT | 0 |  |
| subdivision | INT | 3 | range 0..10 |
| use_keep_shape | BOOLEAN | True |  |
| outline_material | POINTER |  |  |
| object | POINTER |  |  |

### GREASE_PENCIL_SHRINKWRAP（30 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| vertex_group_name | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| open_influence_panel | BOOLEAN | False |  |
| wrap_method | ENUM | NEAREST_SURFACEPOINT | NEAREST_SURFACEPOINT, PROJECT, NEAREST_VERTEX, TARGET_PROJECT |
| wrap_mode | ENUM | ON_SURFACE | ON_SURFACE, INSIDE, OUTSIDE, OUTSIDE_SURFACE, ABOVE_SURFACE |
| cull_face | ENUM | OFF | OFF, FRONT, BACK |
| target | POINTER |  |  |
| auxiliary_target | POINTER |  |  |
| offset | FLOAT | 0.05 |  |
| project_limit | FLOAT | 0 | range 0..3.4e+38 |
| use_project_x | BOOLEAN | False |  |
| use_project_y | BOOLEAN | False |  |
| use_project_z | BOOLEAN | False |  |
| subsurf_levels | INT | 0 | range 0..6 |
| use_negative_direction | BOOLEAN | False |  |
| use_positive_direction | BOOLEAN | True |  |
| use_invert_cull | BOOLEAN | False |  |
| smooth_factor | FLOAT | 0.05 | range 0..1 |
| smooth_step | INT | 1 | range 1..10 |

### GREASE_PENCIL_SIMPLIFY（20 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| vertex_group_name | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| open_influence_panel | BOOLEAN | False |  |
| factor | FLOAT | 0 | range 0..100 |
| mode | ENUM | FIXED | FIXED, ADAPTIVE, SAMPLE, MERGE |
| step | INT | 1 | range 1..50 |
| length | FLOAT | 0.1 | range 0..3.4e+38 |
| sharp_threshold | FLOAT | 0 | range 0..3.1416 |
| distance | FLOAT | 0.1 | range 0..3.4e+38 |

### GREASE_PENCIL_SMOOTH（24 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| vertex_group_name | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| use_custom_curve | BOOLEAN | False |  |
| custom_curve | POINTER |  |  |
| open_influence_panel | BOOLEAN | False |  |
| factor | FLOAT | 1 | range 0..1 |
| use_edit_position | BOOLEAN | True |  |
| use_edit_strength | BOOLEAN | False |  |
| use_edit_thickness | BOOLEAN | False |  |
| use_edit_uv | BOOLEAN | False |  |
| step | INT | 1 | range 1..1000 |
| use_keep_shape | BOOLEAN | False |  |
| use_smooth_ends | BOOLEAN | False |  |

### GREASE_PENCIL_SUBDIV（14 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| open_influence_panel | BOOLEAN | False |  |
| level | INT | 1 | range 0..16 |
| subdivision_type | ENUM | CATMULL_CLARK | CATMULL_CLARK, SIMPLE |

### GREASE_PENCIL_TEXTURE（20 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| open_influence_panel | BOOLEAN | False |  |
| uv_offset | FLOAT | 0 |  |
| uv_scale | FLOAT | 1 | range 0..3.4e+38 |
| alignment_rotation | FLOAT | 0 | range -1.5708..1.5708 |
| fill_rotation | FLOAT | 0 |  |
| fill_offset | FLOAT | [0, 0] |  |
| fill_scale | FLOAT | 1 | range 0.01..100 |
| fit_method | ENUM | CONSTANT_LENGTH | CONSTANT_LENGTH, FIT_STROKE |
| mode | ENUM | STROKE | STROKE, FILL, STROKE_AND_FILL |

### GREASE_PENCIL_THICKNESS（20 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| vertex_group_name | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| use_custom_curve | BOOLEAN | False |  |
| custom_curve | POINTER |  |  |
| open_influence_panel | BOOLEAN | False |  |
| thickness | FLOAT | 0.02 | range -10..100 |
| thickness_factor | FLOAT | 1 | range 0..3.4e+38 |
| use_weight_factor | BOOLEAN | False |  |
| use_uniform_thickness | BOOLEAN | False |  |

### GREASE_PENCIL_TIME（17 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| open_influence_panel | BOOLEAN | False |  |
| open_custom_range_panel | BOOLEAN | False |  |
| segments | COLLECTION |  |  |
| segment_active_index | INT | 0 | range 0..2147483647 |
| mode | ENUM | NORMAL | NORMAL, REVERSE, FIX, PINGPONG, CHAIN |
| offset | INT | 1 | range -32768..32767 |
| frame_scale | FLOAT | 1 | range 0.001..100 |
| frame_start | INT | 1 | range -1048574..1048574 |
| frame_end | INT | 250 | range -1048574..1048574 |
| use_keep_loop | BOOLEAN | True |  |
| use_custom_frame_range | BOOLEAN | False |  |

### GREASE_PENCIL_TINT（24 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| vertex_group_name | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| use_custom_curve | BOOLEAN | False |  |
| custom_curve | POINTER |  |  |
| open_influence_panel | BOOLEAN | False |  |
| color_mode | ENUM | BOTH | BOTH, STROKE, FILL |
| factor | FLOAT | 0.5 | range 0..2 |
| tint_mode | ENUM | UNIFORM | UNIFORM, GRADIENT |
| color | FLOAT | [1, 1, 1] |  |
| color_ramp | POINTER |  |  |
| object | POINTER |  |  |
| radius | FLOAT | 1 | range 1e-06..3.4e+38 |
| use_weight_as_factor | BOOLEAN | False |  |

### GREASE_PENCIL_VERTEX_WEIGHT_ANGLE（21 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| vertex_group_name | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| open_influence_panel | BOOLEAN | False |  |
| target_vertex_group | STRING |  |  |
| use_multiply | BOOLEAN | False |  |
| use_invert_output | BOOLEAN | False |  |
| angle | FLOAT | 0 | range 0..3.1416 |
| axis | ENUM | Y | X, Y, Z |
| space | ENUM | LOCAL | LOCAL, WORLD |
| minimum_weight | FLOAT | 0 | range 0..1 |

### GREASE_PENCIL_VERTEX_WEIGHT_PROXIMITY（21 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| tree_node_filter | STRING |  |  |
| use_layer_pass_filter | BOOLEAN | False |  |
| layer_pass_filter | INT | 0 | range 0..100 |
| invert_layer_filter | BOOLEAN | False |  |
| invert_layer_pass_filter | BOOLEAN | False |  |
| use_layer_group_filter | BOOLEAN | False |  |
| material_filter | POINTER |  |  |
| use_material_pass_filter | BOOLEAN | False |  |
| material_pass_filter | INT | 0 | range 0..100 |
| invert_material_filter | BOOLEAN | False |  |
| invert_material_pass_filter | BOOLEAN | False |  |
| vertex_group_name | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| open_influence_panel | BOOLEAN | False |  |
| use_multiply | BOOLEAN | False |  |
| use_invert_output | BOOLEAN | False |  |
| target_vertex_group | STRING |  |  |
| object | POINTER |  |  |
| distance_start | FLOAT | 0 | range 0..3.4e+38 |
| minimum_weight | FLOAT | 0 | range 0..1 |
| distance_end | FLOAT | 20 | range 0..3.4e+38 |

### HOOK（12 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| strength | FLOAT | 1 | range 0..1 |
| falloff_type | ENUM | SMOOTH | NONE, CURVE, SMOOTH, SPHERE, ROOT, INVERSE_SQUARE … |
| falloff_radius | FLOAT | 0 | range 0..3.4e+38 |
| falloff_curve | POINTER |  |  |
| center | FLOAT | [0, 0, 0] |  |
| matrix_inverse | FLOAT |  |  |
| object | POINTER |  |  |
| subtarget | STRING |  |  |
| use_falloff_uniform | BOOLEAN | False |  |
| vertex_group | STRING |  |  |
| vertex_indices | INT |  |  |
| invert_vertex_group | BOOLEAN | False |  |

### LAPLACIANDEFORM（4 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| vertex_group | STRING |  |  |
| iterations | INT | 1 | range 0..2147483647 |
| is_bind | BOOLEAN |  |  |
| invert_vertex_group | BOOLEAN | False |  |

### LAPLACIANSMOOTH（10 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| use_x | BOOLEAN | True |  |
| use_y | BOOLEAN | True |  |
| use_z | BOOLEAN | True |  |
| use_volume_preserve | BOOLEAN | True |  |
| use_normalized | BOOLEAN | True |  |
| lambda_factor | FLOAT | 0.01 |  |
| lambda_border | FLOAT | 0.01 |  |
| iterations | INT | 1 | range 0..32767 |
| vertex_group | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |

### LATTICE（4 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| object | POINTER |  |  |
| vertex_group | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| strength | FLOAT | 1 |  |

### LINEART（65 条 · 宿主 grease_pencil）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| use_custom_camera | BOOLEAN | False |  |
| use_fuzzy_intersections | BOOLEAN | False |  |
| use_fuzzy_all | BOOLEAN | False |  |
| use_object_instances | BOOLEAN | True |  |
| use_edge_overlap | BOOLEAN | False |  |
| use_clip_plane_boundaries | BOOLEAN | True |  |
| crease_threshold | FLOAT | 2.4435 | range 0..3.1416 |
| split_angle | FLOAT | 0 | range 0..3.1416 |
| smooth_tolerance | FLOAT | 0 | range 0..30 |
| use_loose_as_contour | BOOLEAN | False |  |
| invert_source_vertex_group | BOOLEAN | False |  |
| use_output_vertex_group_match_by_name | BOOLEAN | True |  |
| use_face_mark | BOOLEAN | False |  |
| use_face_mark_invert | BOOLEAN | False |  |
| use_face_mark_boundaries | BOOLEAN | False |  |
| use_face_mark_keep_contour | BOOLEAN | True |  |
| chaining_image_threshold | FLOAT | 0.001 | range 0..0.3 |
| use_loose_edge_chain | BOOLEAN | False |  |
| use_geometry_space_chain | BOOLEAN | False |  |
| use_detail_preserve | BOOLEAN | False |  |
| use_overlap_edge_type_support | BOOLEAN | False |  |
| stroke_depth_offset | FLOAT | 0.05 | range -0.1..3.4e+38 |
| use_offset_towards_custom_camera | BOOLEAN | False |  |
| source_camera | POINTER |  |  |
| light_contour_object | POINTER |  |  |
| source_type | ENUM | COLLECTION | COLLECTION, OBJECT, SCENE |
| source_object | POINTER |  |  |
| source_collection | POINTER |  |  |
| use_contour | BOOLEAN | True |  |
| use_loose | BOOLEAN | True |  |
| use_crease | BOOLEAN | True |  |
| use_material | BOOLEAN | False |  |
| use_edge_mark | BOOLEAN | True |  |
| use_intersection | BOOLEAN | True |  |
| use_light_contour | BOOLEAN | False |  |
| use_shadow | BOOLEAN | False |  |
| shadow_region_filtering | ENUM | NONE | NONE, ILLUMINATED, SHADED, ILLUMINATED_ENCLOSED |
| silhouette_filtering | ENUM | NONE | NONE, GROUP, INDIVIDUAL |
| fill_strokes | BOOLEAN | False |  |
| use_multiple_levels | BOOLEAN | False |  |
| level_start | INT | 0 | range 0..128 |
| level_end | INT | 0 | range 0..128 |
| target_layer | STRING |  |  |
| target_material | POINTER |  |  |
| source_vertex_group | STRING |  |  |
| vertex_group | STRING |  |  |
| is_baked | BOOLEAN | False |  |
| use_cache | BOOLEAN | False |  |
| overscan | FLOAT | 0.1 | range 0..0.5 |
| radius | FLOAT | 0.0025 | range 0..1 |
| opacity | FLOAT | 1 | range 0..1 |
| use_material_mask | BOOLEAN | False |  |
| use_material_mask_match | BOOLEAN | False |  |
| use_material_mask_bits | BOOLEAN | [0, 0, 0, …] |  |
| use_intersection_match | BOOLEAN | False |  |
| use_intersection_mask | BOOLEAN | [0, 0, 0, …] |  |
| use_crease_on_smooth | BOOLEAN | False |  |
| use_crease_on_sharp | BOOLEAN | True |  |
| use_image_boundary_trimming | BOOLEAN | False |  |
| use_back_face_culling | BOOLEAN | False |  |
| shadow_camera_near | FLOAT | 0.1 | range 0..10000 |
| shadow_camera_far | FLOAT | 200 | range 0..10000 |
| shadow_camera_size | FLOAT | 200 | range 0..10000 |
| use_invert_collection | BOOLEAN | False |  |
| use_invert_silhouette | BOOLEAN | False |  |

### MASK（6 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| mode | ENUM | VERTEX_GROUP | VERTEX_GROUP, ARMATURE |
| armature | POINTER |  |  |
| vertex_group | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| use_smooth | BOOLEAN | False |  |
| threshold | FLOAT | 0 | range 0..1 |

### MESH_CACHE（17 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| cache_format | ENUM | MDD | MDD, PC2 |
| interpolation | ENUM | LINEAR | NONE, LINEAR |
| time_mode | ENUM | FRAME | FRAME, TIME, FACTOR |
| play_mode | ENUM | SCENE | SCENE, CUSTOM |
| deform_mode | ENUM | OVERWRITE | OVERWRITE, INTEGRATE |
| filepath | STRING |  |  |
| factor | FLOAT | 1 | range 0..1 |
| vertex_group | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| forward_axis | ENUM | POS_Y | POS_X, POS_Y, POS_Z, NEG_X, NEG_Y, NEG_Z |
| up_axis | ENUM | POS_Z | POS_X, POS_Y, POS_Z, NEG_X, NEG_Y, NEG_Z |
| flip_axis | BOOLEAN | [0, 0, 0] |  |
| frame_start | FLOAT | 0 | range -1.05e+06..1.05e+06 |
| frame_scale | FLOAT | 1 | range 0..100 |
| eval_frame | FLOAT | 0 | range 0..1.05e+06 |
| eval_time | FLOAT | 0 | range 0..3.4e+38 |
| eval_factor | FLOAT | 0 | range 0..1 |

### MESH_DEFORM（6 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| object | POINTER |  |  |
| is_bound | BOOLEAN |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| vertex_group | STRING |  |  |
| precision | INT | 5 | range 2..10 |
| use_dynamic_bind | BOOLEAN | False |  |

### MESH_SEQUENCE_CACHE（5 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| cache_file | POINTER |  |  |
| object_path | STRING |  |  |
| read_data | ENUM |  | VERT, POLY, UV, COLOR, ATTRIBUTES |
| use_vertex_interpolation | BOOLEAN | False |  |
| velocity_scale | FLOAT | 1 | range 0..3.4e+38 |

### MESH_TO_VOLUME（6 条 · 宿主 volume）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| object | POINTER |  |  |
| resolution_mode | ENUM | VOXEL_AMOUNT | VOXEL_AMOUNT, VOXEL_SIZE |
| voxel_size | FLOAT | 0.1 | range 0..3.4e+38 |
| voxel_amount | INT | 32 | range 0..2147483647 |
| interior_band_width | FLOAT | 0.2 | range 0..3.4e+38 |
| density | FLOAT | 1 | range 0..3.4e+38 |

### MIRROR（16 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| use_axis | BOOLEAN | [1, 0, 0] |  |
| use_bisect_axis | BOOLEAN | [0, 0, 0] |  |
| use_bisect_flip_axis | BOOLEAN | [0, 0, 0] |  |
| use_clip | BOOLEAN | False |  |
| use_mirror_vertex_groups | BOOLEAN | True |  |
| use_mirror_merge | BOOLEAN | True |  |
| use_mirror_u | BOOLEAN | False |  |
| use_mirror_v | BOOLEAN | False |  |
| use_mirror_udim | BOOLEAN | False |  |
| mirror_offset_u | FLOAT | 0 | range -1..1 |
| mirror_offset_v | FLOAT | 0 | range -1..1 |
| offset_u | FLOAT | 0 | range -10000..10000 |
| offset_v | FLOAT | 0 | range -10000..10000 |
| merge_threshold | FLOAT | 0.001 | range 0..3.4e+38 |
| bisect_threshold | FLOAT | 0.001 | range 0..3.4e+38 |
| mirror_object | POINTER |  |  |

### MULTIRES（13 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| uv_smooth | ENUM | PRESERVE_BOUNDARIES | NONE, PRESERVE_CORNERS, PRESERVE_CORNERS_AND_JUNCTIONS, PRESERVE_CORNERS_JUNCTIONS_AND_CONCAVE, PRESERVE_BOUNDARIES, SMOOTH_ALL |
| quality | INT | 4 | range 1..10 |
| boundary_smooth | ENUM | ALL | PRESERVE_CORNERS, ALL |
| levels | INT | 0 | range 0..255 |
| sculpt_levels | INT | 0 | range 0..255 |
| render_levels | INT | 0 | range 0..255 |
| total_levels | INT |  | range 0..255 |
| is_external | BOOLEAN |  |  |
| filepath | STRING |  |  |
| show_only_control_edges | BOOLEAN | True |  |
| use_creases | BOOLEAN | True |  |
| use_custom_normals | BOOLEAN | False |  |
| use_sculpt_base_mesh | BOOLEAN | False |  |

### NODES（15 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| node_group | POINTER |  |  |
| bake_directory | STRING |  |  |
| bake_target | ENUM | PACKED | PACKED, DISK |
| bakes | COLLECTION |  |  |
| panels | COLLECTION |  |  |
| show_group_selector | BOOLEAN | True |  |
| show_manage_panel | BOOLEAN | True |  |
| node_warnings | COLLECTION |  |  |
| open_output_attributes_panel | BOOLEAN | False |  |
| open_manage_panel | BOOLEAN | False |  |
| open_bake_panel | BOOLEAN | False |  |
| open_named_attributes_panel | BOOLEAN | False |  |
| open_bake_data_blocks_panel | BOOLEAN | False |  |
| open_warnings_panel | BOOLEAN | True |  |
| properties | POINTER |  |  |

### NORMAL_EDIT（10 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| mode | ENUM | RADIAL | RADIAL, DIRECTIONAL |
| offset | FLOAT | [0, 0, 0] |  |
| mix_mode | ENUM | COPY | COPY, ADD, SUB, MUL |
| mix_factor | FLOAT | 1 | range 0..1 |
| mix_limit | FLOAT | 3.1416 | range 0..3.1416 |
| no_polynors_fix | BOOLEAN | False |  |
| vertex_group | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| target | POINTER |  |  |
| use_direction_parallel | BOOLEAN | False |  |

### OCEAN（32 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| geometry_mode | ENUM | GENERATE | GENERATE, DISPLACE |
| size | FLOAT | 1 | range 0..3.4e+38 |
| repeat_x | INT | 1 | range 1..1024 |
| repeat_y | INT | 1 | range 1..1024 |
| use_normals | BOOLEAN | False |  |
| use_foam | BOOLEAN | False |  |
| use_spray | BOOLEAN | False |  |
| invert_spray | BOOLEAN | False |  |
| spray_layer_name | STRING |  |  |
| resolution | INT | 7 | range 1..1024 |
| viewport_resolution | INT | 7 | range 1..1024 |
| spatial_size | INT | 50 | range -2147483648..2147483647 |
| wind_velocity | FLOAT | 30 |  |
| damping | FLOAT | 0.5 | range 0..1 |
| wave_scale_min | FLOAT | 0.01 | range 0..3.4e+38 |
| wave_alignment | FLOAT | 0 | range 0..1 |
| wave_direction | FLOAT | 0 |  |
| wave_scale | FLOAT | 1 | range 0..3.4e+38 |
| depth | FLOAT | 200 |  |
| foam_coverage | FLOAT | 0 |  |
| bake_foam_fade | FLOAT | 0.98 | range 0..3.4e+38 |
| foam_layer_name | STRING |  |  |
| choppiness | FLOAT | 1 | range 0..3.4e+38 |
| time | FLOAT | 1 | range 0..3.4e+38 |
| spectrum | ENUM | PHILLIPS | PHILLIPS, PIERSON_MOSKOWITZ, JONSWAP, TEXEL_MARSEN_ARSLOE |
| fetch_jonswap | FLOAT | 120 | range 0..3.4e+38 |
| sharpen_peak_jonswap | FLOAT | 0 | range 0..1 |
| random_seed | INT | 0 | range 0..2147483647 |
| frame_start | INT | 1 | range -2147483648..2147483647 |
| frame_end | INT | 250 | range -2147483648..2147483647 |
| is_cached | BOOLEAN |  |  |
| filepath | STRING | C:\Users\23501\AppData\Local\Temp\blender_a34160\cache_ocean |  |

### PARTICLE_INSTANCE（21 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| object | POINTER |  |  |
| particle_system_index | INT | 1 | range 1..32767 |
| particle_system | POINTER |  |  |
| axis | ENUM | Z | X, Y, Z |
| space | ENUM | WORLD | LOCAL, WORLD |
| use_normal | BOOLEAN | True |  |
| use_children | BOOLEAN | False |  |
| use_path | BOOLEAN | False |  |
| show_unborn | BOOLEAN | True |  |
| show_alive | BOOLEAN | True |  |
| show_dead | BOOLEAN | True |  |
| use_preserve_shape | BOOLEAN | False |  |
| use_size | BOOLEAN | False |  |
| position | FLOAT | 1 | range 0..1 |
| random_position | FLOAT | 0 | range 0..1 |
| rotation | FLOAT | 0 | range 0..1 |
| random_rotation | FLOAT | 0 | range 0..1 |
| particle_amount | FLOAT | 1 | range 0..1 |
| particle_offset | FLOAT | 0 | range 0..1 |
| index_layer_name | STRING |  |  |
| value_layer_name | STRING |  |  |

### PARTICLE_SYSTEM（1 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| particle_system | POINTER |  |  |

### REMESH（9 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| mode | ENUM | VOXEL | BLOCKS, SMOOTH, SHARP, VOXEL |
| scale | FLOAT | 0.9 | range 0..0.99 |
| threshold | FLOAT | 1 | range 0..1 |
| octree_depth | INT | 4 | range 1..24 |
| sharpness | FLOAT | 1 |  |
| voxel_size | FLOAT | 0.1 | range 0..3.4e+38 |
| adaptivity | FLOAT | 0 |  |
| use_remove_disconnected | BOOLEAN | True |  |
| use_smooth_shade | BOOLEAN | False |  |

### SCREW（15 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| object | POINTER |  |  |
| steps | INT | 16 | range 1..10000 |
| render_steps | INT | 16 | range 1..10000 |
| iterations | INT | 1 | range 1..10000 |
| axis | ENUM | Z | X, Y, Z |
| angle | FLOAT | 6.2832 |  |
| screw_offset | FLOAT | 0 |  |
| merge_threshold | FLOAT | 0.01 | range 0..3.4e+38 |
| use_normal_flip | BOOLEAN | False |  |
| use_normal_calculate | BOOLEAN | False |  |
| use_object_screw_offset | BOOLEAN | False |  |
| use_merge_vertices | BOOLEAN | False |  |
| use_smooth_shade | BOOLEAN | True |  |
| use_stretch_u | BOOLEAN | False |  |
| use_stretch_v | BOOLEAN | False |  |

### SHRINKWRAP（16 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| wrap_method | ENUM | NEAREST_SURFACEPOINT | NEAREST_SURFACEPOINT, PROJECT, NEAREST_VERTEX, TARGET_PROJECT |
| wrap_mode | ENUM | ON_SURFACE | ON_SURFACE, INSIDE, OUTSIDE, OUTSIDE_SURFACE, ABOVE_SURFACE |
| cull_face | ENUM | OFF | OFF, FRONT, BACK |
| target | POINTER |  |  |
| auxiliary_target | POINTER |  |  |
| vertex_group | STRING |  |  |
| offset | FLOAT | 0 |  |
| project_limit | FLOAT | 0 | range 0..3.4e+38 |
| use_project_x | BOOLEAN | False |  |
| use_project_y | BOOLEAN | False |  |
| use_project_z | BOOLEAN | False |  |
| subsurf_levels | INT | 0 | range 0..6 |
| use_negative_direction | BOOLEAN | False |  |
| use_positive_direction | BOOLEAN | True |  |
| use_invert_cull | BOOLEAN | False |  |
| invert_vertex_group | BOOLEAN | False |  |

### SIMPLE_DEFORM（11 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| deform_method | ENUM | TWIST | TWIST, BEND, TAPER, STRETCH |
| vertex_group | STRING |  |  |
| deform_axis | ENUM | X | X, Y, Z |
| origin | POINTER |  |  |
| factor | FLOAT | 0.7854 |  |
| angle | FLOAT | 0.7854 |  |
| limits | FLOAT | [0, 1] |  |
| lock_x | BOOLEAN | False |  |
| lock_y | BOOLEAN | False |  |
| lock_z | BOOLEAN | False |  |
| invert_vertex_group | BOOLEAN | False |  |

### SKIN（5 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| branch_smoothing | FLOAT | 0 | range 0..1 |
| use_smooth_shade | BOOLEAN | False |  |
| use_x_symmetry | BOOLEAN | True |  |
| use_y_symmetry | BOOLEAN | False |  |
| use_z_symmetry | BOOLEAN | False |  |

### SMOOTH（7 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| use_x | BOOLEAN | True |  |
| use_y | BOOLEAN | True |  |
| use_z | BOOLEAN | True |  |
| factor | FLOAT | 0.5 |  |
| iterations | INT | 1 | range 0..32767 |
| vertex_group | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |

### SOFT_BODY（2 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| settings | POINTER |  |  |
| point_cache | POINTER |  |  |

### SOLIDIFY（25 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| solidify_mode | ENUM | EXTRUDE | EXTRUDE, NON_MANIFOLD |
| thickness | FLOAT | 0.01 |  |
| thickness_clamp | FLOAT | 0 | range 0..100 |
| use_thickness_angle_clamp | BOOLEAN | False |  |
| thickness_vertex_group | FLOAT | 0 | range 0..1 |
| offset | FLOAT | -1 |  |
| edge_crease_inner | FLOAT | 0 | range 0..1 |
| edge_crease_outer | FLOAT | 0 | range 0..1 |
| edge_crease_rim | FLOAT | 0 | range 0..1 |
| material_offset | INT | 0 | range -32768..32767 |
| material_offset_rim | INT | 0 | range -32768..32767 |
| vertex_group | STRING |  |  |
| shell_vertex_group | STRING |  |  |
| rim_vertex_group | STRING |  |  |
| use_rim | BOOLEAN | True |  |
| use_even_offset | BOOLEAN | False |  |
| use_quality_normals | BOOLEAN | False |  |
| invert_vertex_group | BOOLEAN | False |  |
| use_flat_faces | BOOLEAN | False |  |
| use_flip_normals | BOOLEAN | False |  |
| use_rim_only | BOOLEAN | False |  |
| nonmanifold_thickness_mode | ENUM | CONSTRAINTS | FIXED, EVEN, CONSTRAINTS |
| nonmanifold_boundary_mode | ENUM | NONE | NONE, ROUND, FLAT |
| nonmanifold_merge_threshold | FLOAT | 0.0001 | range 0..1 |
| bevel_convex | FLOAT | 0 | range -1..1 |

### SUBSURF（16 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| uv_smooth | ENUM | PRESERVE_BOUNDARIES | NONE, PRESERVE_CORNERS, PRESERVE_CORNERS_AND_JUNCTIONS, PRESERVE_CORNERS_JUNCTIONS_AND_CONCAVE, PRESERVE_BOUNDARIES, SMOOTH_ALL |
| quality | INT | 3 | range 1..10 |
| boundary_smooth | ENUM | ALL | PRESERVE_CORNERS, ALL |
| subdivision_type | ENUM | CATMULL_CLARK | CATMULL_CLARK, SIMPLE |
| levels | INT | 1 | range 0..11 |
| render_levels | INT | 2 | range 0..11 |
| show_only_control_edges | BOOLEAN | True |  |
| use_creases | BOOLEAN | True |  |
| use_custom_normals | BOOLEAN | False |  |
| use_limit_surface | BOOLEAN | True |  |
| use_adaptive_subdivision | BOOLEAN | False |  |
| adaptive_space | ENUM | PIXEL | PIXEL, OBJECT |
| adaptive_pixel_size | FLOAT | 1 | range 0.1..1000 |
| adaptive_object_edge_length | FLOAT | 0.01 | range 0.0001..1000 |
| open_adaptive_subdivision_panel | BOOLEAN | False |  |
| open_advanced_panel | BOOLEAN | False |  |

### SURFACE（0 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|

### SURFACE_DEFORM（7 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| target | POINTER |  |  |
| falloff | FLOAT | 4 | range 2..16 |
| is_bound | BOOLEAN |  |  |
| vertex_group | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| use_sparse_bind | BOOLEAN | False |  |
| strength | FLOAT | 1 | range -100..100 |

### TRIANGULATE（4 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| quad_method | ENUM | SHORTEST_DIAGONAL | BEAUTY, FIXED, FIXED_ALTERNATE, SHORTEST_DIAGONAL, LONGEST_DIAGONAL |
| ngon_method | ENUM | BEAUTY | BEAUTY, CLIP |
| min_vertices | INT | 4 | range 4..2147483647 |
| keep_custom_normals | BOOLEAN | False |  |

### UV_PROJECT（7 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| uv_layer | STRING |  |  |
| projector_count | INT | 1 | range 1..10 |
| projectors | COLLECTION |  |  |
| aspect_x | FLOAT | 1 | range 1..3.4e+38 |
| aspect_y | FLOAT | 1 | range 1..3.4e+38 |
| scale_x | FLOAT | 1 | range 0..3.4e+38 |
| scale_y | FLOAT | 1 | range 0..3.4e+38 |

### UV_WARP（13 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| axis_u | ENUM | X | X, Y, Z |
| axis_v | ENUM | Y | X, Y, Z |
| center | FLOAT | [0.5, 0.5] |  |
| offset | FLOAT | [0, 0] |  |
| scale | FLOAT | [1, 1] |  |
| rotation | FLOAT | 0 |  |
| object_from | POINTER |  |  |
| bone_from | STRING |  |  |
| object_to | POINTER |  |  |
| bone_to | STRING |  |  |
| vertex_group | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| uv_layer | STRING |  |  |

### VERTEX_WEIGHT_EDIT（19 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| vertex_group | STRING |  |  |
| falloff_type | ENUM | LINEAR | LINEAR, CURVE, SHARP, SMOOTH, ROOT, ICON_SPHERECURVE … |
| invert_falloff | BOOLEAN | False |  |
| normalize | BOOLEAN | False |  |
| map_curve | POINTER |  |  |
| use_add | BOOLEAN | False |  |
| use_remove | BOOLEAN | False |  |
| default_weight | FLOAT | 0 | range 0..1 |
| add_threshold | FLOAT | 0.01 | range -1000..1000 |
| remove_threshold | FLOAT | 0.01 | range -1000..1000 |
| mask_constant | FLOAT | 1 |  |
| mask_vertex_group | STRING |  |  |
| invert_mask_vertex_group | BOOLEAN | False |  |
| mask_texture | POINTER |  |  |
| mask_tex_use_channel | ENUM | INT | INT, RED, GREEN, BLUE, HUE, SAT … |
| mask_tex_mapping | ENUM | LOCAL | LOCAL, GLOBAL, OBJECT, UV |
| mask_tex_uv_layer | STRING |  |  |
| mask_tex_map_object | POINTER |  |  |
| mask_tex_map_bone | STRING |  |  |

### VERTEX_WEIGHT_MIX（18 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| vertex_group_a | STRING |  |  |
| vertex_group_b | STRING |  |  |
| invert_vertex_group_a | BOOLEAN | False |  |
| invert_vertex_group_b | BOOLEAN | False |  |
| default_weight_a | FLOAT | 0 | range 0..1 |
| default_weight_b | FLOAT | 0 | range 0..1 |
| mix_mode | ENUM | SET | SET, ADD, SUB, MUL, DIV, DIF … |
| mix_set | ENUM | AND | ALL, A, B, OR, AND |
| normalize | BOOLEAN | False |  |
| mask_constant | FLOAT | 1 |  |
| mask_vertex_group | STRING |  |  |
| invert_mask_vertex_group | BOOLEAN | False |  |
| mask_texture | POINTER |  |  |
| mask_tex_use_channel | ENUM | INT | INT, RED, GREEN, BLUE, HUE, SAT … |
| mask_tex_mapping | ENUM | LOCAL | LOCAL, GLOBAL, OBJECT, UV |
| mask_tex_uv_layer | STRING |  |  |
| mask_tex_map_object | POINTER |  |  |
| mask_tex_map_bone | STRING |  |  |

### VERTEX_WEIGHT_PROXIMITY（19 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| vertex_group | STRING |  |  |
| proximity_mode | ENUM | OBJECT | OBJECT, GEOMETRY |
| proximity_geometry | ENUM |  | VERTEX, EDGE, FACE |
| target | POINTER |  |  |
| min_dist | FLOAT | 0 | range 0..3.4e+38 |
| max_dist | FLOAT | 1 | range 0..3.4e+38 |
| falloff_type | ENUM | LINEAR | LINEAR, CURVE, SHARP, SMOOTH, ROOT, ICON_SPHERECURVE … |
| invert_falloff | BOOLEAN | False |  |
| normalize | BOOLEAN | False |  |
| map_curve | POINTER |  |  |
| mask_constant | FLOAT | 1 |  |
| mask_vertex_group | STRING |  |  |
| invert_mask_vertex_group | BOOLEAN | False |  |
| mask_texture | POINTER |  |  |
| mask_tex_use_channel | ENUM | INT | INT, RED, GREEN, BLUE, HUE, SAT … |
| mask_tex_mapping | ENUM | LOCAL | LOCAL, GLOBAL, OBJECT, UV |
| mask_tex_uv_layer | STRING |  |  |
| mask_tex_map_object | POINTER |  |  |
| mask_tex_map_bone | STRING |  |  |

### VOLUME_DISPLACE（6 条 · 宿主 volume）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| strength | FLOAT | 0.5 |  |
| texture | POINTER |  |  |
| texture_map_mode | ENUM | LOCAL | LOCAL, GLOBAL, OBJECT |
| texture_map_object | POINTER |  |  |
| texture_mid_level | FLOAT | [0.5, 0.5, 0.5] |  |
| texture_sample_radius | FLOAT | 1 | range 0..3.4e+38 |

### VOLUME_TO_MESH（8 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| object | POINTER |  |  |
| threshold | FLOAT | 0.1 | range 0..3.4e+38 |
| adaptivity | FLOAT | 0 | range 0..1 |
| use_smooth_shade | BOOLEAN | False |  |
| grid_name | STRING | density |  |
| resolution_mode | ENUM | GRID | GRID, VOXEL_AMOUNT, VOXEL_SIZE |
| voxel_size | FLOAT | 0.1 | range 0..3.4e+38 |
| voxel_amount | INT | 32 | range 0..2147483647 |

### WARP（16 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| object_from | POINTER |  |  |
| bone_from | STRING |  |  |
| object_to | POINTER |  |  |
| bone_to | STRING |  |  |
| strength | FLOAT | 1 |  |
| falloff_type | ENUM | SMOOTH | NONE, CURVE, SMOOTH, SPHERE, ROOT, INVERSE_SQUARE … |
| falloff_radius | FLOAT | 1 |  |
| falloff_curve | POINTER |  |  |
| use_volume_preserve | BOOLEAN | False |  |
| vertex_group | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| texture | POINTER |  |  |
| texture_coords | ENUM | LOCAL | LOCAL, GLOBAL, OBJECT, UV |
| uv_layer | STRING |  |  |
| texture_coords_object | POINTER |  |  |
| texture_coords_bone | STRING |  |  |

### WAVE（25 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| use_x | BOOLEAN | True |  |
| use_y | BOOLEAN | True |  |
| use_cyclic | BOOLEAN | True |  |
| use_normal | BOOLEAN | False |  |
| use_normal_x | BOOLEAN | True |  |
| use_normal_y | BOOLEAN | True |  |
| use_normal_z | BOOLEAN | True |  |
| time_offset | FLOAT | 0 | range -1.05e+06..1.05e+06 |
| lifetime | FLOAT | 0 | range -1.05e+06..1.05e+06 |
| damping_time | FLOAT | 10 | range -1.05e+06..1.05e+06 |
| falloff_radius | FLOAT | 0 | range 0..3.4e+38 |
| start_position_x | FLOAT | 0 |  |
| start_position_y | FLOAT | 0 |  |
| start_position_object | POINTER |  |  |
| vertex_group | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| speed | FLOAT | 0.25 |  |
| height | FLOAT | 0.5 |  |
| width | FLOAT | 1.5 | range 0..3.4e+38 |
| narrowness | FLOAT | 1.5 | range 0..3.4e+38 |
| texture | POINTER |  |  |
| texture_coords | ENUM | LOCAL | LOCAL, GLOBAL, OBJECT, UV |
| uv_layer | STRING |  |  |
| texture_coords_object | POINTER |  |  |
| texture_coords_bone | STRING |  |  |

### WEIGHTED_NORMAL（7 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| weight | INT | 50 | range 1..100 |
| mode | ENUM | FACE_AREA | FACE_AREA, CORNER_ANGLE, FACE_AREA_WITH_ANGLE |
| thresh | FLOAT | 0.01 | range 0..10 |
| keep_sharp | BOOLEAN | False |  |
| vertex_group | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| use_face_influence | BOOLEAN | False |  |

### WELD（5 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| mode | ENUM | ALL | ALL, CONNECTED |
| merge_threshold | FLOAT | 0.001 | range 0..3.4e+38 |
| vertex_group | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
| loose_edges | BOOLEAN | False |  |

### WIREFRAME（12 条 · 宿主 mesh）

| 属性 | 类型 | 默认 | 取值/范围 |
|---|---|---|---|
| thickness | FLOAT | 0.02 |  |
| thickness_vertex_group | FLOAT | 0 | range 0..1 |
| offset | FLOAT | 0 |  |
| use_replace | BOOLEAN | True |  |
| use_boundary | BOOLEAN | False |  |
| use_even_offset | BOOLEAN | True |  |
| use_relative_offset | BOOLEAN | False |  |
| use_crease | BOOLEAN | False |  |
| crease_weight | FLOAT | 1 |  |
| material_offset | INT | 0 | range -32768..32767 |
| vertex_group | STRING |  |  |
| invert_vertex_group | BOOLEAN | False |  |
