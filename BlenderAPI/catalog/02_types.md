# 核心类型属性

`readonly` 表示只能读不能写；`enum` 是该属性的合法取值。

## Object（140）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| name | STRING |  |  |
| name_full | STRING | RO |  |
| id_type | ENUM | RO | ACTION, ARMATURE, BRUSH, CACHEFILE, CAMERA, COLLECTION … |
| session_uid | INT | RO | range -2147483648..2147483647 |
| is_evaluated | BOOLEAN | RO |  |
| original | POINTER | RO |  |
| users | INT | RO | range 0..2147483647 |
| use_fake_user | BOOLEAN |  |  |
| use_extra_user | BOOLEAN |  |  |
| is_embedded_data | BOOLEAN | RO |  |
| is_linked_packed | BOOLEAN | RO |  |
| is_missing | BOOLEAN | RO |  |
| is_runtime_data | BOOLEAN |  |  |
| is_editable | BOOLEAN | RO |  |
| tag | BOOLEAN |  |  |
| is_library_indirect | BOOLEAN | RO |  |
| library | POINTER | RO |  |
| library_weak_reference | POINTER | RO |  |
| asset_data | POINTER |  |  |
| override_library | POINTER | RO |  |
| preview | POINTER | RO |  |
| data | POINTER |  |  |
| type | ENUM | RO | MESH, CURVE, SURFACE, META, FONT, CURVES … |
| mode | ENUM | RO | OBJECT, EDIT, POSE, SCULPT, VERTEX_PAINT, WEIGHT_PAINT … |
| bound_box | FLOAT | RO |  |
| parent | POINTER |  |  |
| parent_type | ENUM |  | OBJECT, ARMATURE, LATTICE, VERTEX, VERTEX_3, BONE |
| parent_vertices | INT |  |  |
| parent_bone | STRING |  |  |
| parent_bone_head_tail_factor | FLOAT |  | range 0.0..1.0 |
| use_parent_final_indices | BOOLEAN |  |  |
| use_camera_lock_parent | BOOLEAN |  |  |
| track_axis | ENUM |  | POS_X, POS_Y, POS_Z, NEG_X, NEG_Y, NEG_Z |
| up_axis | ENUM |  | X, Y, Z |
| material_slots | COLLECTION | RO |  |
| active_material | POINTER |  |  |
| active_material_index | INT |  | range 0..2147483647 |
| location | FLOAT |  |  |
| rotation_quaternion | FLOAT |  |  |
| rotation_axis_angle | FLOAT |  |  |
| rotation_euler | FLOAT |  |  |
| rotation_mode | ENUM |  | QUATERNION, XYZ, XZY, YXZ, YZX, ZXY … |
| scale | FLOAT |  |  |
| dimensions | FLOAT |  |  |
| delta_location | FLOAT |  |  |
| delta_rotation_euler | FLOAT |  |  |
| delta_rotation_quaternion | FLOAT |  |  |
| delta_scale | FLOAT |  |  |
| lock_location | BOOLEAN |  |  |
| lock_rotation | BOOLEAN |  |  |
| lock_rotation_w | BOOLEAN |  |  |
| lock_rotations_4d | BOOLEAN |  |  |
| lock_scale | BOOLEAN |  |  |
| matrix_world | FLOAT |  |  |
| matrix_local | FLOAT |  |  |
| matrix_basis | FLOAT |  |  |
| matrix_parent_inverse | FLOAT |  |  |
| modifiers | COLLECTION | RO |  |
| shader_effects | COLLECTION | RO |  |
| constraints | COLLECTION | RO |  |
| vertex_groups | COLLECTION | RO |  |
| empty_display_type | ENUM |  | PLAIN_AXES, ARROWS, SINGLE_ARROW, CIRCLE, CUBE, SPHERE … |
| empty_display_size | FLOAT |  | range 9.999999747378752e-05..1000.0 |
| empty_image_offset | FLOAT |  |  |
| image_user | POINTER | RO |  |
| empty_image_depth | ENUM |  | DEFAULT, FRONT, BACK |
| show_empty_image_perspective | BOOLEAN |  |  |
| show_empty_image_orthographic | BOOLEAN |  |  |
| show_empty_image_only_axis_aligned | BOOLEAN |  |  |
| use_empty_image_alpha | BOOLEAN |  |  |
| empty_image_side | ENUM |  | DOUBLE_SIDED, FRONT, BACK |
| add_rest_position_attribute | BOOLEAN |  |  |
| pass_index | INT |  | range 0..32767 |
| color | FLOAT |  |  |
| field | POINTER | RO |  |
| collision | POINTER | RO |  |
| soft_body | POINTER | RO |  |
| particle_systems | COLLECTION | RO |  |
| rigid_body | POINTER | RO |  |
| rigid_body_constraint | POINTER | RO |  |
| use_simulation_cache | BOOLEAN |  |  |
| hide_viewport | BOOLEAN |  |  |
| hide_select | BOOLEAN |  |  |
| hide_render | BOOLEAN |  |  |
| hide_probe_volume | BOOLEAN |  |  |
| hide_probe_sphere | BOOLEAN |  |  |
| hide_probe_plane | BOOLEAN |  |  |
| hide_surface_pick | BOOLEAN |  |  |
| show_instancer_for_render | BOOLEAN |  |  |
| show_instancer_for_viewport | BOOLEAN |  |  |
| visible_camera | BOOLEAN |  |  |
| visible_diffuse | BOOLEAN |  |  |
| visible_glossy | BOOLEAN |  |  |
| visible_transmission | BOOLEAN |  |  |
| visible_volume_scatter | BOOLEAN |  |  |
| visible_shadow | BOOLEAN |  |  |
| is_holdout | BOOLEAN |  |  |
| is_shadow_catcher | BOOLEAN |  |  |
| visible_raycast | BOOLEAN |  |  |
| instance_type | ENUM |  | NONE, VERTS, FACES, COLLECTION |
| use_instance_vertices_rotation | BOOLEAN |  |  |
| use_instance_faces_scale | BOOLEAN |  |  |
| instance_faces_scale | FLOAT |  | range 0.0010000000474974513..10000.0 |
| instance_collection | POINTER |  |  |
| is_instancer | BOOLEAN | RO |  |
| display_type | ENUM |  | BOUNDS, WIRE, SOLID, TEXTURED |
| show_bounds | BOOLEAN |  |  |
| display_bounds_type | ENUM |  | BOX, SPHERE, CYLINDER, CONE, CAPSULE |
| show_name | BOOLEAN |  |  |
| show_axis | BOOLEAN |  |  |
| show_texture_space | BOOLEAN |  |  |
| show_wire | BOOLEAN |  |  |
| show_all_edges | BOOLEAN |  |  |
| use_grease_pencil_lights | BOOLEAN |  |  |
| show_transparent | BOOLEAN |  |  |
| show_in_front | BOOLEAN |  |  |
| pose | POINTER | RO |  |
| show_only_shape_key | BOOLEAN |  |  |
| use_shape_key_edit_mode | BOOLEAN |  |  |
| active_shape_key | POINTER | RO |  |
| active_shape_key_index | INT |  | range -32768..32767 |
| use_dynamic_topology_sculpting | BOOLEAN | RO |  |
| is_from_instancer | BOOLEAN | RO |  |
| is_from_set | BOOLEAN | RO |  |
| display | POINTER | RO |  |
| lineart | POINTER | RO |  |
| use_mesh_mirror_x | BOOLEAN |  |  |
| use_mesh_mirror_y | BOOLEAN |  |  |
| use_mesh_mirror_z | BOOLEAN |  |  |
| lightgroup | STRING |  |  |
| light_linking | POINTER | RO |  |
| shadow_terminator_normal_offset | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| shadow_terminator_geometry_offset | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| shadow_terminator_shading_offset | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| animation_data | POINTER | RO |  |
| animation_visualization | POINTER | RO |  |
| motion_path | POINTER | RO |  |
| selection_sets | COLLECTION | RO |  |
| active_selection_set | INT |  | range -2147483648..2147483647 |
| cycles | POINTER | RO |  |

## Mesh（70）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| name | STRING |  |  |
| name_full | STRING | RO |  |
| id_type | ENUM | RO | ACTION, ARMATURE, BRUSH, CACHEFILE, CAMERA, COLLECTION … |
| session_uid | INT | RO | range -2147483648..2147483647 |
| is_evaluated | BOOLEAN | RO |  |
| original | POINTER | RO |  |
| users | INT | RO | range 0..2147483647 |
| use_fake_user | BOOLEAN |  |  |
| use_extra_user | BOOLEAN |  |  |
| is_embedded_data | BOOLEAN | RO |  |
| is_linked_packed | BOOLEAN | RO |  |
| is_missing | BOOLEAN | RO |  |
| is_runtime_data | BOOLEAN |  |  |
| is_editable | BOOLEAN | RO |  |
| tag | BOOLEAN |  |  |
| is_library_indirect | BOOLEAN | RO |  |
| library | POINTER | RO |  |
| library_weak_reference | POINTER | RO |  |
| asset_data | POINTER |  |  |
| override_library | POINTER | RO |  |
| preview | POINTER | RO |  |
| vertices | COLLECTION | RO |  |
| edges | COLLECTION | RO |  |
| loops | COLLECTION | RO |  |
| polygons | COLLECTION | RO |  |
| normals_domain | ENUM | RO | POINT, FACE, CORNER |
| vertex_normals | COLLECTION | RO |  |
| polygon_normals | COLLECTION | RO |  |
| corner_normals | COLLECTION | RO |  |
| loop_triangles | COLLECTION | RO |  |
| loop_triangle_polygons | COLLECTION | RO |  |
| texture_mesh | POINTER |  |  |
| uv_layers | COLLECTION | RO |  |
| uv_layer_clone | POINTER |  |  |
| uv_layer_clone_index | INT |  | range 0..2147483647 |
| uv_layer_stencil | POINTER |  |  |
| uv_layer_stencil_index | INT |  | range 0..2147483647 |
| vertex_colors | COLLECTION | RO |  |
| skin_vertices | COLLECTION | RO |  |
| attributes | COLLECTION | RO |  |
| color_attributes | COLLECTION | RO |  |
| remesh_voxel_size | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| remesh_voxel_adaptivity | FLOAT |  | range 0.0..1.0 |
| use_remesh_fix_poles | BOOLEAN |  |  |
| use_remesh_preserve_volume | BOOLEAN |  |  |
| use_remesh_preserve_attributes | BOOLEAN |  |  |
| remesh_mode | ENUM |  | VOXEL, QUAD |
| use_mirror_x | BOOLEAN |  |  |
| use_mirror_y | BOOLEAN |  |  |
| use_mirror_z | BOOLEAN |  |  |
| use_mirror_vertex_groups | BOOLEAN |  |  |
| radial_symmetry | INT |  |  |
| has_custom_normals | BOOLEAN | RO |  |
| texco_mesh | POINTER |  |  |
| shape_keys | POINTER | RO |  |
| use_auto_texspace | BOOLEAN |  |  |
| use_mirror_topology | BOOLEAN |  |  |
| use_paint_bone_selection | BOOLEAN |  |  |
| use_paint_mask | BOOLEAN |  |  |
| use_paint_mask_vertex | BOOLEAN |  |  |
| total_vert_sel | INT | RO | range 0..2147483647 |
| total_edge_sel | INT | RO | range 0..2147483647 |
| total_face_sel | INT | RO | range 0..2147483647 |
| is_editmode | BOOLEAN | RO |  |
| animation_data | POINTER | RO |  |
| auto_texspace | BOOLEAN |  |  |
| texspace_location | FLOAT |  |  |
| texspace_size | FLOAT |  |  |
| materials | COLLECTION | RO |  |
| cycles | POINTER | RO |  |

## Material（60）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| name | STRING |  |  |
| name_full | STRING | RO |  |
| id_type | ENUM | RO | ACTION, ARMATURE, BRUSH, CACHEFILE, CAMERA, COLLECTION … |
| session_uid | INT | RO | range -2147483648..2147483647 |
| is_evaluated | BOOLEAN | RO |  |
| original | POINTER | RO |  |
| users | INT | RO | range 0..2147483647 |
| use_fake_user | BOOLEAN |  |  |
| use_extra_user | BOOLEAN |  |  |
| is_embedded_data | BOOLEAN | RO |  |
| is_linked_packed | BOOLEAN | RO |  |
| is_missing | BOOLEAN | RO |  |
| is_runtime_data | BOOLEAN |  |  |
| is_editable | BOOLEAN | RO |  |
| tag | BOOLEAN |  |  |
| is_library_indirect | BOOLEAN | RO |  |
| library | POINTER | RO |  |
| library_weak_reference | POINTER | RO |  |
| asset_data | POINTER |  |  |
| override_library | POINTER | RO |  |
| preview | POINTER | RO |  |
| surface_render_method | ENUM |  | DITHERED, BLENDED |
| displacement_method | ENUM |  | BUMP, DISPLACEMENT, BOTH |
| blend_method | ENUM |  | OPAQUE, CLIP, HASHED, BLEND |
| alpha_threshold | FLOAT |  | range 0.0..1.0 |
| use_transparency_overlap | BOOLEAN |  |  |
| show_transparent_back | BOOLEAN |  |  |
| use_backface_culling | BOOLEAN |  |  |
| use_backface_culling_shadow | BOOLEAN |  |  |
| use_backface_culling_lightprobe_volume | BOOLEAN |  |  |
| use_transparent_shadow | BOOLEAN |  |  |
| use_raytrace_refraction | BOOLEAN |  |  |
| use_screen_refraction | BOOLEAN |  |  |
| use_sss_translucency | BOOLEAN |  |  |
| refraction_depth | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| thickness_mode | ENUM |  | SPHERE, SLAB |
| use_thickness_from_shadow | BOOLEAN |  |  |
| volume_intersection_method | ENUM |  | FAST, ACCURATE |
| max_vertex_displacement | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| preview_render_type | ENUM |  | FLAT, SPHERE, CUBE, HAIR, SHADERBALL, CLOTH … |
| use_preview_world | BOOLEAN |  |  |
| pass_index | INT |  | range 0..32767 |
| node_tree | POINTER | RO |  |
| use_nodes | BOOLEAN |  |  |
| animation_data | POINTER | RO |  |
| texture_paint_images | COLLECTION | RO |  |
| texture_paint_slots | COLLECTION | RO |  |
| paint_active_slot | INT |  | range 0..32767 |
| paint_clone_slot | INT |  | range 0..32767 |
| diffuse_color | FLOAT |  |  |
| specular_color | FLOAT |  |  |
| roughness | FLOAT |  | range 0.0..1.0 |
| specular_intensity | FLOAT |  | range 0.0..1.0 |
| metallic | FLOAT |  | range 0.0..1.0 |
| line_color | FLOAT |  |  |
| line_priority | INT |  | range 0..32767 |
| grease_pencil | POINTER | RO |  |
| is_grease_pencil | BOOLEAN | RO |  |
| lineart | POINTER | RO |  |
| cycles | POINTER | RO |  |

## Scene（83）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| name | STRING |  |  |
| name_full | STRING | RO |  |
| id_type | ENUM | RO | ACTION, ARMATURE, BRUSH, CACHEFILE, CAMERA, COLLECTION … |
| session_uid | INT | RO | range -2147483648..2147483647 |
| is_evaluated | BOOLEAN | RO |  |
| original | POINTER | RO |  |
| users | INT | RO | range 0..2147483647 |
| use_fake_user | BOOLEAN |  |  |
| use_extra_user | BOOLEAN |  |  |
| is_embedded_data | BOOLEAN | RO |  |
| is_linked_packed | BOOLEAN | RO |  |
| is_missing | BOOLEAN | RO |  |
| is_runtime_data | BOOLEAN |  |  |
| is_editable | BOOLEAN | RO |  |
| tag | BOOLEAN |  |  |
| is_library_indirect | BOOLEAN | RO |  |
| library | POINTER | RO |  |
| library_weak_reference | POINTER | RO |  |
| asset_data | POINTER |  |  |
| override_library | POINTER | RO |  |
| preview | POINTER | RO |  |
| camera | POINTER |  |  |
| background_set | POINTER |  |  |
| world | POINTER |  |  |
| objects | COLLECTION | RO |  |
| frame_current | INT |  | range -1048574..1048574 |
| frame_subframe | FLOAT |  | range 0.0..1.0 |
| frame_float | FLOAT |  | range -1048574.0..1048574.0 |
| frame_start | INT |  | range 0..1048574 |
| frame_end | INT |  | range 0..1048574 |
| frame_step | INT |  | range 0..1048574 |
| time_jump_unit | ENUM |  | FRAME, SECOND |
| time_jump_delta | FLOAT |  | range 0.10000000149011612..3.4028234663852886e+38 |
| frame_current_final | FLOAT | RO | range -1048574.0..1048574.0 |
| lock_frame_selection_to_range | BOOLEAN |  |  |
| allow_preroll | BOOLEAN |  |  |
| use_preview_range | BOOLEAN |  |  |
| frame_preview_start | INT |  | range -2147483648..2147483647 |
| frame_preview_end | INT |  | range -2147483648..2147483647 |
| show_subframe | BOOLEAN |  |  |
| show_keys_from_selected_only | BOOLEAN |  |  |
| use_stamp_note | STRING |  |  |
| animation_data | POINTER | RO |  |
| is_nla_tweakmode | BOOLEAN | RO |  |
| use_custom_simulation_range | BOOLEAN |  |  |
| simulation_frame_start | INT |  | range -2147483648..2147483647 |
| simulation_frame_end | INT |  | range -2147483648..2147483647 |
| sync_mode | ENUM |  | NONE, FRAME_DROP, AUDIO_SYNC |
| playback_loop_mode | ENUM |  | INFINITE, STOP_END_FRAME, STOP_START_FRAME, RESTORE, BOUNCE |
| compositing_node_group | POINTER |  |  |
| use_nodes | BOOLEAN |  |  |
| sequence_editor | POINTER | RO |  |
| keying_sets | COLLECTION | RO |  |
| keying_sets_all | COLLECTION | RO |  |
| rigidbody_world | POINTER | RO |  |
| tool_settings | POINTER | RO |  |
| unit_settings | POINTER | RO |  |
| gravity | FLOAT |  |  |
| use_gravity | BOOLEAN |  |  |
| render | POINTER | RO |  |
| safe_areas | POINTER | RO |  |
| timeline_markers | COLLECTION | RO |  |
| transform_orientation_slots | COLLECTION | RO |  |
| cursor | POINTER | RO |  |
| use_audio | BOOLEAN |  |  |
| use_audio_scrub | BOOLEAN |  |  |
| audio_doppler_speed | FLOAT |  | range 0.009999999776482582..3.4028234663852886e+38 |
| audio_doppler_factor | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| audio_distance_model | ENUM |  | NONE, INVERSE, INVERSE_CLAMPED, LINEAR, LINEAR_CLAMPED, EXPONENT … |
| audio_volume | FLOAT |  | range 0.0..100.0 |
| annotation | POINTER |  |  |
| active_clip | POINTER |  |  |
| view_settings | POINTER | RO |  |
| display_settings | POINTER | RO |  |
| sequencer_colorspace_settings | POINTER | RO |  |
| view_layers | COLLECTION | RO |  |
| collection | POINTER | RO |  |
| display | POINTER | RO |  |
| eevee | POINTER | RO |  |
| grease_pencil_settings | POINTER | RO |  |
| hydra | POINTER | RO |  |
| cycles | POINTER | RO |  |
| cycles_curves | POINTER | RO |  |

## World（39）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| name | STRING |  |  |
| name_full | STRING | RO |  |
| id_type | ENUM | RO | ACTION, ARMATURE, BRUSH, CACHEFILE, CAMERA, COLLECTION … |
| session_uid | INT | RO | range -2147483648..2147483647 |
| is_evaluated | BOOLEAN | RO |  |
| original | POINTER | RO |  |
| users | INT | RO | range 0..2147483647 |
| use_fake_user | BOOLEAN |  |  |
| use_extra_user | BOOLEAN |  |  |
| is_embedded_data | BOOLEAN | RO |  |
| is_linked_packed | BOOLEAN | RO |  |
| is_missing | BOOLEAN | RO |  |
| is_runtime_data | BOOLEAN |  |  |
| is_editable | BOOLEAN | RO |  |
| tag | BOOLEAN |  |  |
| is_library_indirect | BOOLEAN | RO |  |
| library | POINTER | RO |  |
| library_weak_reference | POINTER | RO |  |
| asset_data | POINTER |  |  |
| override_library | POINTER | RO |  |
| preview | POINTER | RO |  |
| animation_data | POINTER | RO |  |
| use_eevee_finite_volume | BOOLEAN |  |  |
| color | FLOAT |  |  |
| light_settings | POINTER | RO |  |
| mist_settings | POINTER | RO |  |
| node_tree | POINTER | RO |  |
| use_nodes | BOOLEAN |  |  |
| lightgroup | STRING |  |  |
| probe_resolution | ENUM |  | 128, 256, 512, 1024, 2048, 4096 |
| sun_threshold | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| sun_angle | FLOAT |  | range 0.0..3.1415927410125732 |
| use_sun_shadow | BOOLEAN |  |  |
| sun_shadow_maximum_resolution | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| sun_shadow_filter_radius | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| use_sun_shadow_jitter | BOOLEAN |  |  |
| sun_shadow_jitter_overblur | FLOAT |  | range 0.0..100.0 |
| cycles | POINTER | RO |  |
| cycles_visibility | POINTER | RO |  |

## Camera（81）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| name | STRING |  |  |
| name_full | STRING | RO |  |
| id_type | ENUM | RO | ACTION, ARMATURE, BRUSH, CACHEFILE, CAMERA, COLLECTION … |
| session_uid | INT | RO | range -2147483648..2147483647 |
| is_evaluated | BOOLEAN | RO |  |
| original | POINTER | RO |  |
| users | INT | RO | range 0..2147483647 |
| use_fake_user | BOOLEAN |  |  |
| use_extra_user | BOOLEAN |  |  |
| is_embedded_data | BOOLEAN | RO |  |
| is_linked_packed | BOOLEAN | RO |  |
| is_missing | BOOLEAN | RO |  |
| is_runtime_data | BOOLEAN |  |  |
| is_editable | BOOLEAN | RO |  |
| tag | BOOLEAN |  |  |
| is_library_indirect | BOOLEAN | RO |  |
| library | POINTER | RO |  |
| library_weak_reference | POINTER | RO |  |
| asset_data | POINTER |  |  |
| override_library | POINTER | RO |  |
| preview | POINTER | RO |  |
| type | ENUM |  | PERSP, ORTHO, PANO, CUSTOM |
| sensor_fit | ENUM |  | AUTO, HORIZONTAL, VERTICAL |
| passepartout_alpha | FLOAT |  | range 0.0..1.0 |
| angle_x | FLOAT |  | range 0.006405358202755451..3.016749143600464 |
| angle_y | FLOAT |  | range 0.006405358202755451..3.016749143600464 |
| angle | FLOAT |  | range 0.006405358202755451..3.016749143600464 |
| clip_start | FLOAT |  | range 9.999999974752427e-07..3.4028234663852886e+38 |
| clip_end | FLOAT |  | range 9.999999974752427e-07..3.4028234663852886e+38 |
| lens | FLOAT |  | range 1.0..3.4028234663852886e+38 |
| sensor_width | FLOAT |  | range 1.0..3.4028234663852886e+38 |
| sensor_height | FLOAT |  | range 1.0..3.4028234663852886e+38 |
| ortho_scale | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| display_size | FLOAT |  | range 0.009999999776482582..1000.0 |
| shift_x | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| shift_y | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| stereo | POINTER | RO |  |
| show_limits | BOOLEAN |  |  |
| show_mist | BOOLEAN |  |  |
| show_passepartout | BOOLEAN |  |  |
| show_safe_areas | BOOLEAN |  |  |
| show_safe_center | BOOLEAN |  |  |
| show_name | BOOLEAN |  |  |
| show_sensor | BOOLEAN |  |  |
| show_background_images | BOOLEAN |  |  |
| lens_unit | ENUM |  | MILLIMETERS, FOV |
| composition_guide_color | FLOAT |  |  |
| show_composition_center | BOOLEAN |  |  |
| show_composition_center_diagonal | BOOLEAN |  |  |
| show_composition_thirds | BOOLEAN |  |  |
| show_composition_golden | BOOLEAN |  |  |
| show_composition_golden_tria_a | BOOLEAN |  |  |
| show_composition_golden_tria_b | BOOLEAN |  |  |
| show_composition_harmony_tri_a | BOOLEAN |  |  |
| show_composition_harmony_tri_b | BOOLEAN |  |  |
| panorama_type | ENUM |  | EQUIRECTANGULAR, EQUIANGULAR_CUBEMAP_FACE, MIRRORBALL, FISHEYE_EQUIDISTANT, FISHEYE_EQUISOLID, FISHEYE_LENS_POLYNOMIAL … |
| fisheye_fov | FLOAT |  | range 0.1745000034570694..31.415925979614258 |
| fisheye_lens | FLOAT |  | range 0.009999999776482582..100.0 |
| latitude_min | FLOAT |  | range -1.5707963705062866..1.5707963705062866 |
| latitude_max | FLOAT |  | range -1.5707963705062866..1.5707963705062866 |
| longitude_min | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| longitude_max | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| fisheye_polynomial_k0 | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| fisheye_polynomial_k1 | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| fisheye_polynomial_k2 | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| fisheye_polynomial_k3 | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| fisheye_polynomial_k4 | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| central_cylindrical_range_u_min | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| central_cylindrical_range_u_max | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| central_cylindrical_range_v_min | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| central_cylindrical_range_v_max | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| central_cylindrical_radius | FLOAT |  | range 9.999999747378752e-06..3.4028234663852886e+38 |
| custom_filepath | STRING |  |  |
| custom_shader | POINTER |  |  |
| custom_mode | ENUM |  | INTERNAL, EXTERNAL |
| custom_bytecode | STRING |  |  |
| custom_bytecode_hash | STRING |  |  |
| dof | POINTER | RO |  |
| background_images | COLLECTION | RO |  |
| animation_data | POINTER | RO |  |
| cycles_custom | POINTER | RO |  |

## Light（39）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| name | STRING |  |  |
| name_full | STRING | RO |  |
| id_type | ENUM | RO | ACTION, ARMATURE, BRUSH, CACHEFILE, CAMERA, COLLECTION … |
| session_uid | INT | RO | range -2147483648..2147483647 |
| is_evaluated | BOOLEAN | RO |  |
| original | POINTER | RO |  |
| users | INT | RO | range 0..2147483647 |
| use_fake_user | BOOLEAN |  |  |
| use_extra_user | BOOLEAN |  |  |
| is_embedded_data | BOOLEAN | RO |  |
| is_linked_packed | BOOLEAN | RO |  |
| is_missing | BOOLEAN | RO |  |
| is_runtime_data | BOOLEAN |  |  |
| is_editable | BOOLEAN | RO |  |
| tag | BOOLEAN |  |  |
| is_library_indirect | BOOLEAN | RO |  |
| library | POINTER | RO |  |
| library_weak_reference | POINTER | RO |  |
| asset_data | POINTER |  |  |
| override_library | POINTER | RO |  |
| preview | POINTER | RO |  |
| type | ENUM |  | POINT, SUN, SPOT, AREA |
| use_temperature | BOOLEAN |  |  |
| color | FLOAT |  |  |
| temperature | FLOAT |  | range 800.0..20000.0 |
| temperature_color | FLOAT | RO |  |
| specular_factor | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| diffuse_factor | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| transmission_factor | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| volume_factor | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| use_custom_distance | BOOLEAN |  |  |
| cutoff_distance | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| use_shadow | BOOLEAN |  |  |
| exposure | FLOAT |  | range -32.0..32.0 |
| normalize | BOOLEAN |  |  |
| node_tree | POINTER | RO |  |
| use_nodes | BOOLEAN |  |  |
| animation_data | POINTER | RO |  |
| cycles | POINTER | RO |  |

## Armature（36）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| name | STRING |  |  |
| name_full | STRING | RO |  |
| id_type | ENUM | RO | ACTION, ARMATURE, BRUSH, CACHEFILE, CAMERA, COLLECTION … |
| session_uid | INT | RO | range -2147483648..2147483647 |
| is_evaluated | BOOLEAN | RO |  |
| original | POINTER | RO |  |
| users | INT | RO | range 0..2147483647 |
| use_fake_user | BOOLEAN |  |  |
| use_extra_user | BOOLEAN |  |  |
| is_embedded_data | BOOLEAN | RO |  |
| is_linked_packed | BOOLEAN | RO |  |
| is_missing | BOOLEAN | RO |  |
| is_runtime_data | BOOLEAN |  |  |
| is_editable | BOOLEAN | RO |  |
| tag | BOOLEAN |  |  |
| is_library_indirect | BOOLEAN | RO |  |
| library | POINTER | RO |  |
| library_weak_reference | POINTER | RO |  |
| asset_data | POINTER |  |  |
| override_library | POINTER | RO |  |
| preview | POINTER | RO |  |
| animation_data | POINTER | RO |  |
| bones | COLLECTION | RO |  |
| edit_bones | COLLECTION | RO |  |
| collections | COLLECTION |  |  |
| collections_all | COLLECTION | RO |  |
| pose_position | ENUM |  | POSE, REST |
| display_type | ENUM |  | OCTAHEDRAL, STICK, BBONE, ENVELOPE, WIRE |
| show_axes | BOOLEAN |  |  |
| axes_position | FLOAT |  | range 0.0..1.0 |
| relation_line_position | ENUM |  | TAIL, HEAD |
| show_names | BOOLEAN |  |  |
| use_mirror_x | BOOLEAN |  |  |
| show_bone_custom_shapes | BOOLEAN |  |  |
| show_bone_colors | BOOLEAN |  |  |
| is_editmode | BOOLEAN | RO |  |

## Bone（52）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| parent | POINTER | RO |  |
| children | COLLECTION | RO |  |
| collections | COLLECTION | RO |  |
| name | STRING |  |  |
| color | POINTER | RO |  |
| display_type | ENUM |  | ARMATURE_DEFINED, OCTAHEDRAL, STICK, BBONE, ENVELOPE, WIRE |
| use_connect | BOOLEAN | RO |  |
| use_inherit_rotation | BOOLEAN |  |  |
| use_envelope_multiply | BOOLEAN |  |  |
| use_deform | BOOLEAN |  |  |
| inherit_scale | ENUM |  | FULL, FIX_SHEAR, ALIGNED, AVERAGE, NONE, NONE_LEGACY |
| use_local_location | BOOLEAN |  |  |
| use_relative_parent | BOOLEAN |  |  |
| show_wire | BOOLEAN |  |  |
| use_cyclic_offset | BOOLEAN |  |  |
| hide_select | BOOLEAN |  |  |
| envelope_distance | FLOAT |  | range 0.0..1000.0 |
| envelope_weight | FLOAT |  | range 0.0..1000.0 |
| head_radius | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| tail_radius | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_segments | INT |  | range 1..32 |
| bbone_mapping_mode | ENUM |  | STRAIGHT, CURVED |
| bbone_x | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_z | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_handle_type_start | ENUM |  | AUTO, ABSOLUTE, RELATIVE, TANGENT |
| bbone_custom_handle_start | POINTER |  |  |
| bbone_handle_use_scale_start | BOOLEAN |  |  |
| bbone_handle_use_ease_start | BOOLEAN |  |  |
| bbone_handle_type_end | ENUM |  | AUTO, ABSOLUTE, RELATIVE, TANGENT |
| bbone_custom_handle_end | POINTER |  |  |
| bbone_handle_use_scale_end | BOOLEAN |  |  |
| bbone_handle_use_ease_end | BOOLEAN |  |  |
| bbone_rollin | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_rollout | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| use_endroll_as_inroll | BOOLEAN |  |  |
| bbone_curveinx | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_curveinz | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_curveoutx | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_curveoutz | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_easein | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_easeout | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| use_scale_easing | BOOLEAN |  |  |
| bbone_scalein | FLOAT |  |  |
| bbone_scaleout | FLOAT |  |  |
| hide | BOOLEAN |  |  |
| matrix | FLOAT | RO |  |
| matrix_local | FLOAT | RO |  |
| tail | FLOAT | RO |  |
| tail_local | FLOAT | RO |  |
| head | FLOAT | RO |  |
| head_local | FLOAT | RO |  |
| length | FLOAT | RO | range -3.4028234663852886e+38..3.4028234663852886e+38 |

## EditBone（53）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| collections | COLLECTION | RO |  |
| parent | POINTER |  |  |
| roll | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| head | FLOAT |  |  |
| tail | FLOAT |  |  |
| length | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| name | STRING |  |  |
| color | POINTER | RO |  |
| display_type | ENUM |  | ARMATURE_DEFINED, OCTAHEDRAL, STICK, BBONE, ENVELOPE, WIRE |
| use_connect | BOOLEAN |  |  |
| use_inherit_rotation | BOOLEAN |  |  |
| use_envelope_multiply | BOOLEAN |  |  |
| use_deform | BOOLEAN |  |  |
| inherit_scale | ENUM |  | FULL, FIX_SHEAR, ALIGNED, AVERAGE, NONE, NONE_LEGACY |
| use_local_location | BOOLEAN |  |  |
| use_relative_parent | BOOLEAN |  |  |
| show_wire | BOOLEAN |  |  |
| use_cyclic_offset | BOOLEAN |  |  |
| hide_select | BOOLEAN |  |  |
| envelope_distance | FLOAT |  | range 0.0..1000.0 |
| envelope_weight | FLOAT |  | range 0.0..1000.0 |
| head_radius | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| tail_radius | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_segments | INT |  | range 1..32 |
| bbone_mapping_mode | ENUM |  | STRAIGHT, CURVED |
| bbone_x | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_z | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_handle_type_start | ENUM |  | AUTO, ABSOLUTE, RELATIVE, TANGENT |
| bbone_custom_handle_start | POINTER |  |  |
| bbone_handle_use_scale_start | BOOLEAN |  |  |
| bbone_handle_use_ease_start | BOOLEAN |  |  |
| bbone_handle_type_end | ENUM |  | AUTO, ABSOLUTE, RELATIVE, TANGENT |
| bbone_custom_handle_end | POINTER |  |  |
| bbone_handle_use_scale_end | BOOLEAN |  |  |
| bbone_handle_use_ease_end | BOOLEAN |  |  |
| bbone_rollin | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_rollout | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| use_endroll_as_inroll | BOOLEAN |  |  |
| bbone_curveinx | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_curveinz | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_curveoutx | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_curveoutz | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_easein | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_easeout | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| use_scale_easing | BOOLEAN |  |  |
| bbone_scalein | FLOAT |  |  |
| bbone_scaleout | FLOAT |  |  |
| hide | BOOLEAN |  |  |
| lock | BOOLEAN |  |  |
| select | BOOLEAN |  |  |
| select_head | BOOLEAN |  |  |
| select_tail | BOOLEAN |  |  |
| matrix | FLOAT |  |  |

## PoseBone（68）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| constraints | COLLECTION | RO |  |
| name | STRING |  |  |
| motion_path | POINTER | RO |  |
| bone | POINTER | RO |  |
| parent | POINTER | RO |  |
| child | POINTER | RO |  |
| location | FLOAT |  |  |
| scale | FLOAT |  |  |
| rotation_quaternion | FLOAT |  |  |
| rotation_axis_angle | FLOAT |  |  |
| rotation_euler | FLOAT |  |  |
| rotation_mode | ENUM |  | QUATERNION, XYZ, XZY, YXZ, YZX, ZXY … |
| bbone_rollin | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_rollout | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_curveinx | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_curveinz | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_curveoutx | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_curveoutz | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_easein | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_easeout | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bbone_scalein | FLOAT |  |  |
| bbone_scaleout | FLOAT |  |  |
| bbone_custom_handle_start | POINTER | RO |  |
| bbone_custom_handle_end | POINTER | RO |  |
| matrix_channel | FLOAT | RO |  |
| matrix_basis | FLOAT |  |  |
| matrix | FLOAT |  |  |
| head | FLOAT | RO |  |
| tail | FLOAT | RO |  |
| length | FLOAT | RO | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| is_in_ik_chain | BOOLEAN | RO |  |
| lock_ik_x | BOOLEAN |  |  |
| lock_ik_y | BOOLEAN |  |  |
| lock_ik_z | BOOLEAN |  |  |
| use_ik_limit_x | BOOLEAN |  |  |
| use_ik_limit_y | BOOLEAN |  |  |
| use_ik_limit_z | BOOLEAN |  |  |
| use_ik_rotation_control | BOOLEAN |  |  |
| use_ik_linear_control | BOOLEAN |  |  |
| ik_min_x | FLOAT |  | range -3.1415927410125732..0.0 |
| ik_max_x | FLOAT |  | range 0.0..3.1415927410125732 |
| ik_min_y | FLOAT |  | range -3.1415927410125732..0.0 |
| ik_max_y | FLOAT |  | range 0.0..3.1415927410125732 |
| ik_min_z | FLOAT |  | range -3.1415927410125732..0.0 |
| ik_max_z | FLOAT |  | range 0.0..3.1415927410125732 |
| ik_stiffness_x | FLOAT |  | range 0.0..0.9900000095367432 |
| ik_stiffness_y | FLOAT |  | range 0.0..0.9900000095367432 |
| ik_stiffness_z | FLOAT |  | range 0.0..0.9900000095367432 |
| ik_stretch | FLOAT |  | range 0.0..1.0 |
| ik_rotation_weight | FLOAT |  | range 0.0..1.0 |
| ik_linear_weight | FLOAT |  | range 0.0..1.0 |
| custom_shape | POINTER |  |  |
| custom_shape_scale_xyz | FLOAT |  |  |
| custom_shape_translation | FLOAT |  |  |
| custom_shape_rotation_euler | FLOAT |  |  |
| use_transform_at_custom_shape | BOOLEAN |  |  |
| use_transform_around_custom_shape | BOOLEAN |  |  |
| use_custom_shape_bone_size | BOOLEAN |  |  |
| hide | BOOLEAN |  |  |
| select | BOOLEAN |  |  |
| custom_shape_transform | POINTER |  |  |
| custom_shape_wire_width | FLOAT |  | range 1.0..16.0 |
| color | POINTER | RO |  |
| lock_location | BOOLEAN |  |  |
| lock_rotation | BOOLEAN |  |  |
| lock_rotation_w | BOOLEAN |  |  |
| lock_rotations_4d | BOOLEAN |  |  |
| lock_scale | BOOLEAN |  |  |

## Action（33）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| name | STRING |  |  |
| name_full | STRING | RO |  |
| id_type | ENUM | RO | ACTION, ARMATURE, BRUSH, CACHEFILE, CAMERA, COLLECTION … |
| session_uid | INT | RO | range -2147483648..2147483647 |
| is_evaluated | BOOLEAN | RO |  |
| original | POINTER | RO |  |
| users | INT | RO | range 0..2147483647 |
| use_fake_user | BOOLEAN |  |  |
| use_extra_user | BOOLEAN |  |  |
| is_embedded_data | BOOLEAN | RO |  |
| is_linked_packed | BOOLEAN | RO |  |
| is_missing | BOOLEAN | RO |  |
| is_runtime_data | BOOLEAN |  |  |
| is_editable | BOOLEAN | RO |  |
| tag | BOOLEAN |  |  |
| is_library_indirect | BOOLEAN | RO |  |
| library | POINTER | RO |  |
| library_weak_reference | POINTER | RO |  |
| asset_data | POINTER |  |  |
| override_library | POINTER | RO |  |
| preview | POINTER | RO |  |
| is_empty | BOOLEAN | RO |  |
| is_action_legacy | BOOLEAN | RO |  |
| is_action_layered | BOOLEAN | RO |  |
| slots | COLLECTION | RO |  |
| layers | COLLECTION | RO |  |
| pose_markers | COLLECTION | RO |  |
| use_frame_range | BOOLEAN |  |  |
| use_cyclic | BOOLEAN |  |  |
| frame_start | FLOAT |  | range -1048574.0..1048574.0 |
| frame_end | FLOAT |  | range -1048574.0..1048574.0 |
| frame_range | FLOAT |  |  |
| curve_frame_range | FLOAT | RO |  |

## Collection（38）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| name | STRING |  |  |
| name_full | STRING | RO |  |
| id_type | ENUM | RO | ACTION, ARMATURE, BRUSH, CACHEFILE, CAMERA, COLLECTION … |
| session_uid | INT | RO | range -2147483648..2147483647 |
| is_evaluated | BOOLEAN | RO |  |
| original | POINTER | RO |  |
| users | INT | RO | range 0..2147483647 |
| use_fake_user | BOOLEAN |  |  |
| use_extra_user | BOOLEAN |  |  |
| is_embedded_data | BOOLEAN | RO |  |
| is_linked_packed | BOOLEAN | RO |  |
| is_missing | BOOLEAN | RO |  |
| is_runtime_data | BOOLEAN |  |  |
| is_editable | BOOLEAN | RO |  |
| tag | BOOLEAN |  |  |
| is_library_indirect | BOOLEAN | RO |  |
| library | POINTER | RO |  |
| library_weak_reference | POINTER | RO |  |
| asset_data | POINTER |  |  |
| override_library | POINTER | RO |  |
| preview | POINTER | RO |  |
| instance_offset | FLOAT |  |  |
| objects | COLLECTION | RO |  |
| all_objects | COLLECTION | RO |  |
| children | COLLECTION | RO |  |
| collection_objects | COLLECTION | RO |  |
| collection_children | COLLECTION | RO |  |
| exporters | COLLECTION | RO |  |
| active_exporter_index | INT |  | range 0..2147483647 |
| hide_select | BOOLEAN |  |  |
| hide_viewport | BOOLEAN |  |  |
| hide_render | BOOLEAN |  |  |
| lineart_usage | ENUM |  | INCLUDE, OCCLUSION_ONLY, EXCLUDE, INTERSECTION_ONLY, NO_INTERSECTION, FORCE_INTERSECTION |
| lineart_use_intersection_mask | BOOLEAN |  |  |
| lineart_intersection_mask | BOOLEAN |  |  |
| lineart_intersection_priority | INT |  | range 0..255 |
| use_lineart_intersection_priority | BOOLEAN |  |  |
| color_tag | ENUM |  | NONE, COLOR_01, COLOR_02, COLOR_03, COLOR_04, COLOR_05 … |

## Curve（63）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| name | STRING |  |  |
| name_full | STRING | RO |  |
| id_type | ENUM | RO | ACTION, ARMATURE, BRUSH, CACHEFILE, CAMERA, COLLECTION … |
| session_uid | INT | RO | range -2147483648..2147483647 |
| is_evaluated | BOOLEAN | RO |  |
| original | POINTER | RO |  |
| users | INT | RO | range 0..2147483647 |
| use_fake_user | BOOLEAN |  |  |
| use_extra_user | BOOLEAN |  |  |
| is_embedded_data | BOOLEAN | RO |  |
| is_linked_packed | BOOLEAN | RO |  |
| is_missing | BOOLEAN | RO |  |
| is_runtime_data | BOOLEAN |  |  |
| is_editable | BOOLEAN | RO |  |
| tag | BOOLEAN |  |  |
| is_library_indirect | BOOLEAN | RO |  |
| library | POINTER | RO |  |
| library_weak_reference | POINTER | RO |  |
| asset_data | POINTER |  |  |
| override_library | POINTER | RO |  |
| preview | POINTER | RO |  |
| shape_keys | POINTER | RO |  |
| splines | COLLECTION | RO |  |
| path_duration | INT |  | range 1..1048574 |
| use_path | BOOLEAN |  |  |
| use_path_follow | BOOLEAN |  |  |
| use_path_clamp | BOOLEAN |  |  |
| use_stretch | BOOLEAN |  |  |
| use_deform_bounds | BOOLEAN |  |  |
| use_radius | BOOLEAN |  |  |
| bevel_mode | ENUM |  | ROUND, OBJECT, PROFILE |
| bevel_profile | POINTER | RO |  |
| bevel_resolution | INT |  | range 0..32 |
| offset | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| extrude | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| bevel_depth | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| resolution_u | INT |  | range 1..1024 |
| resolution_v | INT |  | range 1..1024 |
| render_resolution_u | INT |  | range 0..1024 |
| render_resolution_v | INT |  | range 0..1024 |
| eval_time | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| bevel_object | POINTER |  |  |
| taper_object | POINTER |  |  |
| dimensions | ENUM |  | 2D, 3D |
| fill_mode | ENUM |  | FULL, BACK, FRONT, HALF |
| fill_solver | ENUM |  | SWEEP_LINE, CDT |
| fill_rule | ENUM |  | EVEN_ODD, NONZERO |
| twist_mode | ENUM |  | Z_UP, MINIMUM, TANGENT |
| taper_radius_mode | ENUM |  | OVERRIDE, MULTIPLY, ADD |
| bevel_factor_mapping_start | ENUM |  | RESOLUTION, SEGMENTS, SPLINE |
| bevel_factor_mapping_end | ENUM |  | RESOLUTION, SEGMENTS, SPLINE |
| twist_smooth | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| use_fill_caps | BOOLEAN |  |  |
| use_map_taper | BOOLEAN |  |  |
| use_auto_texspace | BOOLEAN |  |  |
| texspace_location | FLOAT |  |  |
| texspace_size | FLOAT |  |  |
| materials | COLLECTION | RO |  |
| bevel_factor_start | FLOAT |  | range 0.0..1.0 |
| bevel_factor_end | FLOAT |  | range 0.0..1.0 |
| is_editmode | BOOLEAN | RO |  |
| animation_data | POINTER | RO |  |
| cycles | POINTER | RO |  |

## Spline（21）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| points | COLLECTION | RO |  |
| bezier_points | COLLECTION | RO |  |
| tilt_interpolation | ENUM |  | LINEAR, CARDINAL, BSPLINE, EASE |
| radius_interpolation | ENUM |  | LINEAR, CARDINAL, BSPLINE, EASE |
| type | ENUM |  | POLY, BEZIER, NURBS |
| point_count_u | INT | RO | range 0..2147483647 |
| point_count_v | INT | RO | range 0..2147483647 |
| order_u | INT |  | range 2..64 |
| order_v | INT |  | range 2..64 |
| resolution_u | INT |  | range 1..1024 |
| resolution_v | INT |  | range 1..1024 |
| use_cyclic_u | BOOLEAN |  |  |
| use_cyclic_v | BOOLEAN |  |  |
| use_endpoint_u | BOOLEAN |  |  |
| use_endpoint_v | BOOLEAN |  |  |
| use_bezier_u | BOOLEAN |  |  |
| use_bezier_v | BOOLEAN |  |  |
| use_smooth | BOOLEAN |  |  |
| hide | BOOLEAN |  |  |
| material_index | INT |  | range 0..32767 |
| character_index | INT | RO | range 0..2147483647 |

## Image（56）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| name | STRING |  |  |
| name_full | STRING | RO |  |
| id_type | ENUM | RO | ACTION, ARMATURE, BRUSH, CACHEFILE, CAMERA, COLLECTION … |
| session_uid | INT | RO | range -2147483648..2147483647 |
| is_evaluated | BOOLEAN | RO |  |
| original | POINTER | RO |  |
| users | INT | RO | range 0..2147483647 |
| use_fake_user | BOOLEAN |  |  |
| use_extra_user | BOOLEAN |  |  |
| is_embedded_data | BOOLEAN | RO |  |
| is_linked_packed | BOOLEAN | RO |  |
| is_missing | BOOLEAN | RO |  |
| is_runtime_data | BOOLEAN |  |  |
| is_editable | BOOLEAN | RO |  |
| tag | BOOLEAN |  |  |
| is_library_indirect | BOOLEAN | RO |  |
| library | POINTER | RO |  |
| library_weak_reference | POINTER | RO |  |
| asset_data | POINTER |  |  |
| override_library | POINTER | RO |  |
| preview | POINTER | RO |  |
| filepath | STRING |  |  |
| filepath_raw | STRING |  |  |
| file_format | ENUM |  | AVIF, JPEG, OPEN_EXR, PNG, WEBP, BMP … |
| source | ENUM |  | FILE, SEQUENCE, MOVIE, GENERATED, VIEWER, TILED |
| type | ENUM | RO | IMAGE, MULTILAYER, UV_TEST, RENDER_RESULT, COMPOSITING |
| packed_file | POINTER | RO |  |
| packed_files | COLLECTION | RO |  |
| use_view_as_render | BOOLEAN |  |  |
| use_deinterlace | BOOLEAN |  |  |
| use_multiview | BOOLEAN |  |  |
| is_stereo_3d | BOOLEAN | RO |  |
| is_multiview | BOOLEAN | RO |  |
| is_dirty | BOOLEAN | RO |  |
| generated_type | ENUM |  | BLANK, UV_GRID, COLOR_GRID |
| generated_width | INT |  | range 1..65536 |
| generated_height | INT |  | range 1..65536 |
| use_generated_float | BOOLEAN |  |  |
| generated_color | FLOAT |  |  |
| display_aspect | FLOAT |  |  |
| render_slots | COLLECTION | RO |  |
| tiles | COLLECTION | RO |  |
| has_data | BOOLEAN | RO |  |
| depth | INT | RO | range 0..2147483647 |
| size | INT | RO |  |
| resolution | FLOAT |  |  |
| frame_duration | INT | RO | range 0..2147483647 |
| pixels | FLOAT |  |  |
| channels | INT | RO | range 0..2147483647 |
| is_float | BOOLEAN | RO |  |
| colorspace_settings | POINTER | RO |  |
| alpha_mode | ENUM |  | STRAIGHT, PREMUL, CHANNEL_PACKED, NONE |
| use_half_precision | BOOLEAN |  |  |
| seam_margin | INT |  | range -32768..32767 |
| views_format | ENUM |  | INDIVIDUAL, STEREO_3D |
| stereo_3d_format | POINTER | RO |  |

## NodeTree（36）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| name | STRING |  |  |
| name_full | STRING | RO |  |
| id_type | ENUM | RO | ACTION, ARMATURE, BRUSH, CACHEFILE, CAMERA, COLLECTION … |
| session_uid | INT | RO | range -2147483648..2147483647 |
| is_evaluated | BOOLEAN | RO |  |
| original | POINTER | RO |  |
| users | INT | RO | range 0..2147483647 |
| use_fake_user | BOOLEAN |  |  |
| use_extra_user | BOOLEAN |  |  |
| is_embedded_data | BOOLEAN | RO |  |
| is_linked_packed | BOOLEAN | RO |  |
| is_missing | BOOLEAN | RO |  |
| is_runtime_data | BOOLEAN |  |  |
| is_editable | BOOLEAN | RO |  |
| tag | BOOLEAN |  |  |
| is_library_indirect | BOOLEAN | RO |  |
| library | POINTER | RO |  |
| library_weak_reference | POINTER | RO |  |
| asset_data | POINTER |  |  |
| override_library | POINTER | RO |  |
| preview | POINTER | RO |  |
| color_tag | ENUM |  | NONE, ATTRIBUTE, COLOR, CONVERTER, DISTORT, FILTER … |
| default_group_node_width | INT |  | range 60..700 |
| view_center | FLOAT | RO |  |
| description | STRING |  |  |
| animation_data | POINTER | RO |  |
| nodes | COLLECTION | RO |  |
| links | COLLECTION | RO |  |
| annotation | POINTER |  |  |
| type | ENUM | RO | UNDEFINED, CUSTOM, SHADER, TEXTURE, COMPOSITING, GEOMETRY |
| interface | POINTER | RO |  |
| bl_idname | STRING |  |  |
| bl_label | STRING |  |  |
| bl_description | STRING |  |  |
| bl_icon | ENUM |  | NONE, CHAR_NOTDEF, CHAR_REPLACEMENT, NOT_FOUND, BLANK1, AUTOMERGE_OFF … |
| bl_use_group_interface | BOOLEAN |  |  |

## Node（34）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| type | STRING | RO |  |
| location | FLOAT |  |  |
| location_absolute | FLOAT |  |  |
| width | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| height | FLOAT |  | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| dimensions | FLOAT | RO |  |
| name | STRING |  |  |
| label | STRING |  |  |
| inputs | COLLECTION | RO |  |
| outputs | COLLECTION | RO |  |
| panel_states | COLLECTION | RO |  |
| internal_links | COLLECTION | RO |  |
| parent | POINTER |  |  |
| warning_propagation | ENUM |  | ALL, ERRORS_AND_WARNINGS, ERRORS, NONE |
| use_custom_color | BOOLEAN |  |  |
| color | FLOAT |  |  |
| color_tag | ENUM | RO | NONE, ATTRIBUTE, COLOR, CONVERTER, DISTORT, FILTER … |
| select | BOOLEAN |  |  |
| show_options | BOOLEAN |  |  |
| show_preview | BOOLEAN |  |  |
| hide | BOOLEAN |  |  |
| mute | BOOLEAN |  |  |
| show_texture | BOOLEAN |  |  |
| bl_idname | STRING |  |  |
| bl_label | STRING |  |  |
| bl_description | STRING |  |  |
| bl_icon | ENUM |  | NONE, CHAR_NOTDEF, CHAR_REPLACEMENT, NOT_FOUND, BLANK1, AUTOMERGE_OFF … |
| bl_static_type | STRING | RO |  |
| bl_width_default | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| bl_width_min | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| bl_width_max | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| bl_height_default | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| bl_height_min | FLOAT |  | range 0.0..3.4028234663852886e+38 |
| bl_height_max | FLOAT |  | range 0.0..3.4028234663852886e+38 |

## NodeSocket（24）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| name | STRING |  |  |
| label | STRING | RO |  |
| identifier | STRING | RO |  |
| description | STRING |  |  |
| is_output | BOOLEAN | RO |  |
| select | BOOLEAN | RO |  |
| hide | BOOLEAN |  |  |
| enabled | BOOLEAN |  |  |
| link_limit | INT |  | range 1..4095 |
| is_linked | BOOLEAN | RO |  |
| is_unavailable | BOOLEAN | RO |  |
| is_multi_input | BOOLEAN | RO |  |
| show_expanded | BOOLEAN |  |  |
| is_inactive | BOOLEAN | RO |  |
| is_icon_visible | BOOLEAN | RO |  |
| hide_value | BOOLEAN |  |  |
| pin_gizmo | BOOLEAN |  |  |
| node | POINTER | RO |  |
| type | ENUM |  | CUSTOM, VALUE, INT, BOOLEAN, VECTOR, ROTATION … |
| display_shape | ENUM |  | CIRCLE, SQUARE, DIAMOND, CIRCLE_DOT, SQUARE_DOT, DIAMOND_DOT … |
| inferred_structure_type | ENUM | RO | AUTO, DYNAMIC, FIELD, GRID, LIST, SINGLE |
| bl_idname | STRING |  |  |
| bl_label | STRING |  |  |
| bl_subtype_label | STRING |  |  |

## Modifier（13）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| name | STRING |  |  |
| type | ENUM | RO | GREASE_PENCIL_VERTEX_WEIGHT_PROXIMITY, DATA_TRANSFER, MESH_CACHE, MESH_SEQUENCE_CACHE, NORMAL_EDIT, WEIGHTED_NORMAL … |
| show_viewport | BOOLEAN |  |  |
| show_render | BOOLEAN |  |  |
| show_in_editmode | BOOLEAN |  |  |
| show_on_cage | BOOLEAN |  |  |
| show_expanded | BOOLEAN |  |  |
| is_active | BOOLEAN |  |  |
| use_pin_to_last | BOOLEAN |  |  |
| is_override_data | BOOLEAN | RO |  |
| use_apply_on_spline | BOOLEAN |  |  |
| execution_time | FLOAT | RO | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| persistent_uid | INT | RO | range -2147483648..2147483647 |

## Constraint（15）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| name | STRING |  |  |
| type | ENUM | RO | CAMERA_SOLVER, FOLLOW_TRACK, OBJECT_SOLVER, COPY_LOCATION, COPY_ROTATION, COPY_SCALE … |
| is_override_data | BOOLEAN | RO |  |
| owner_space | ENUM |  | WORLD, CUSTOM, POSE, LOCAL_WITH_PARENT, LOCAL |
| target_space | ENUM |  | WORLD, CUSTOM, POSE, LOCAL_WITH_PARENT, LOCAL, LOCAL_OWNER_ORIENT |
| space_object | POINTER |  |  |
| space_subtarget | STRING |  |  |
| mute | BOOLEAN |  |  |
| enabled | BOOLEAN |  |  |
| show_expanded | BOOLEAN |  |  |
| is_valid | BOOLEAN | RO |  |
| active | BOOLEAN |  |  |
| influence | FLOAT |  | range 0.0..1.0 |
| error_location | FLOAT | RO | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| error_rotation | FLOAT | RO | range -3.4028234663852886e+38..3.4028234663852886e+38 |

## VertexGroup（3）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| name | STRING |  |  |
| lock_weight | BOOLEAN |  |  |
| index | INT | RO | range 0..2147483647 |

## ShapeKey（13）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| name | STRING |  |  |
| select | BOOLEAN |  |  |
| frame | FLOAT | RO | range -3.4028234663852886e+38..3.4028234663852886e+38 |
| value | FLOAT |  | range 0.0..1.0 |
| interpolation | ENUM |  | KEY_LINEAR, KEY_CARDINAL, KEY_CATMULL_ROM, KEY_BSPLINE |
| vertex_group | STRING |  |  |
| relative_key | POINTER |  |  |
| mute | BOOLEAN |  |  |
| lock_shape | BOOLEAN |  |  |
| slider_min | FLOAT |  | range -10.0..10.0 |
| slider_max | FLOAT |  | range -10.0..10.0 |
| data | COLLECTION | RO |  |
| points | COLLECTION | RO |  |

## Text（34）

| 属性 | 类型 |  | 取值/范围 |
|---|---|---|---|
| name | STRING |  |  |
| name_full | STRING | RO |  |
| id_type | ENUM | RO | ACTION, ARMATURE, BRUSH, CACHEFILE, CAMERA, COLLECTION … |
| session_uid | INT | RO | range -2147483648..2147483647 |
| is_evaluated | BOOLEAN | RO |  |
| original | POINTER | RO |  |
| users | INT | RO | range 0..2147483647 |
| use_fake_user | BOOLEAN |  |  |
| use_extra_user | BOOLEAN |  |  |
| is_embedded_data | BOOLEAN | RO |  |
| is_linked_packed | BOOLEAN | RO |  |
| is_missing | BOOLEAN | RO |  |
| is_runtime_data | BOOLEAN |  |  |
| is_editable | BOOLEAN | RO |  |
| tag | BOOLEAN |  |  |
| is_library_indirect | BOOLEAN | RO |  |
| library | POINTER | RO |  |
| library_weak_reference | POINTER | RO |  |
| asset_data | POINTER |  |  |
| override_library | POINTER | RO |  |
| preview | POINTER | RO |  |
| filepath | STRING |  |  |
| is_dirty | BOOLEAN | RO |  |
| is_modified | BOOLEAN | RO |  |
| is_in_memory | BOOLEAN | RO |  |
| use_module | BOOLEAN |  |  |
| indentation | ENUM |  | TABS, SPACES |
| lines | COLLECTION | RO |  |
| current_line | POINTER | RO |  |
| current_character | INT |  | range 0..2147483647 |
| current_line_index | INT |  | range -2147483648..2147483647 |
| select_end_line | POINTER | RO |  |
| select_end_line_index | INT |  | range -2147483648..2147483647 |
| select_end_character | INT |  | range 0..2147483647 |
