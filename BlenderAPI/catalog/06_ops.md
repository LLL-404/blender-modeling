# 操作符

无头模式下 `bpy.ops` 的 poll 可能失败。标 ⚠ 的是本仓实测在 `-b` 下不可靠的命名空间。

## object（250）

| 操作符 | 说明 |
|---|---|
| add | bpy.ops.object.add(radius=1, type='EMPTY', enter_editmode=False, align='WORLD', location=(0, 0, 0),  |
| add_modifier_menu | bpy.ops.object.add_modifier_menu() |
| add_named | bpy.ops.object.add_named(linked=False, name="", session_uid=0, matrix=((0, 0, 0, 0), (0, 0, 0, 0), ( |
| align | bpy.ops.object.align(bb_quality=True, align_mode='OPT_2', relative_to='OPT_4', align_axis=set()) |
| anim_transforms_to_deltas | bpy.ops.object.anim_transforms_to_deltas() |
| armature_add | bpy.ops.object.armature_add(radius=1, enter_editmode=False, align='WORLD', location=(0, 0, 0), rotat |
| assign_property_defaults | bpy.ops.object.assign_property_defaults(process_data=True, process_bones=True) |
| bake | bpy.ops.object.bake(type='COMBINED', pass_filter=set(), filepath="", width=512, height=512, margin=1 |
| bake_image | bpy.ops.object.bake_image() |
| camera_add | bpy.ops.object.camera_add(enter_editmode=False, align='WORLD', location=(0, 0, 0), rotation=(0, 0, 0 |
| camera_custom_update | bpy.ops.object.camera_custom_update() |
| clear_override_library | bpy.ops.object.clear_override_library() |
| collection_add | bpy.ops.object.collection_add() |
| collection_external_asset_drop | bpy.ops.object.collection_external_asset_drop(session_uid=0, align='WORLD', location=(0, 0, 0), rota |
| collection_instance_add | bpy.ops.object.collection_instance_add(name="Collection", collection='<UNKNOWN ENUM>', align='WORLD' |
| collection_link | bpy.ops.object.collection_link(collection='<UNKNOWN ENUM>') |
| collection_objects_select | bpy.ops.object.collection_objects_select() |
| collection_remove | bpy.ops.object.collection_remove() |
| collection_unlink | bpy.ops.object.collection_unlink() |
| constraint_add | bpy.ops.object.constraint_add(type='<UNKNOWN ENUM>') |
| constraint_add_with_targets | bpy.ops.object.constraint_add_with_targets(type='<UNKNOWN ENUM>') |
| constraints_clear | bpy.ops.object.constraints_clear() |
| constraints_copy | bpy.ops.object.constraints_copy() |
| convert | bpy.ops.object.convert(target='MESH', keep_original=False, merge_customdata=True, thickness=5, faces |
| copy_global_transform | bpy.ops.object.copy_global_transform() |
| copy_relative_transform | bpy.ops.object.copy_relative_transform() |
| correctivesmooth_bind | bpy.ops.object.correctivesmooth_bind(modifier="") |
| curves_empty_hair_add | bpy.ops.object.curves_empty_hair_add(align='WORLD', location=(0, 0, 0), rotation=(0, 0, 0), scale=(0 |
| curves_random_add | bpy.ops.object.curves_random_add(align='WORLD', location=(0, 0, 0), rotation=(0, 0, 0), scale=(0, 0, |
| data_instance_add | bpy.ops.object.data_instance_add(name="", session_uid=0, type='ACTION', align='WORLD', location=(0,  |
| data_transfer | bpy.ops.object.data_transfer(use_reverse_transfer=False, use_freeze=False, data_type='VGROUP_WEIGHTS |
| datalayout_transfer | bpy.ops.object.datalayout_transfer(modifier="", data_type='<UNKNOWN ENUM>', use_delete=False, layers |
| delete | bpy.ops.object.delete(use_global=False, confirm=True) |
| delete_fix_to_camera_keys | bpy.ops.object.delete_fix_to_camera_keys() |
| drop_geometry_nodes | bpy.ops.object.drop_geometry_nodes(session_uid=0, show_datablock_in_modifier=True) |
| drop_named_material | bpy.ops.object.drop_named_material(name="", session_uid=0) |
| duplicate | bpy.ops.object.duplicate(linked=False, mode='TRANSLATION') |
| duplicate_move | bpy.ops.object.duplicate_move(OBJECT_OT_duplicate={"linked":False, "mode":'TRANSLATION'}, TRANSFORM_ |
| duplicate_move_linked | bpy.ops.object.duplicate_move_linked(OBJECT_OT_duplicate={"linked":False, "mode":'TRANSLATION'}, TRA |
| duplicates_make_real | bpy.ops.object.duplicates_make_real(use_base_parent=False, use_hierarchy=False) |
| editmode_toggle | bpy.ops.object.editmode_toggle() |
| effector_add | bpy.ops.object.effector_add(type='FORCE', radius=1, enter_editmode=False, align='WORLD', location=(0 |
| empty_add | bpy.ops.object.empty_add(type='PLAIN_AXES', radius=1, align='WORLD', location=(0, 0, 0), rotation=(0 |
| empty_image_add | bpy.ops.object.empty_image_add(filepath="", hide_props_region=True, check_existing=False, filter_ble |
| explode_refresh | bpy.ops.object.explode_refresh(modifier="") |
| fix_to_camera | bpy.ops.object.fix_to_camera(use_location=True, use_rotation=True, use_scale=True) |
| forcefield_toggle | bpy.ops.object.forcefield_toggle() |
| geometry_node_bake_delete_single | bpy.ops.object.geometry_node_bake_delete_single(session_uid=0, modifier_name="", bake_id=0) |
| geometry_node_bake_pack_single | bpy.ops.object.geometry_node_bake_pack_single(session_uid=0, modifier_name="", bake_id=0) |
| geometry_node_bake_single | bpy.ops.object.geometry_node_bake_single(session_uid=0, modifier_name="", bake_id=0) |
| geometry_node_bake_unpack_single | bpy.ops.object.geometry_node_bake_unpack_single(session_uid=0, modifier_name="", bake_id=0, method=' |
| geometry_node_tree_copy_assign | bpy.ops.object.geometry_node_tree_copy_assign() |
| geometry_nodes_input_attribute_toggle | bpy.ops.object.geometry_nodes_input_attribute_toggle(input_name="", modifier_name="") |
| geometry_nodes_move_to_nodes | bpy.ops.object.geometry_nodes_move_to_nodes(use_selected_objects=False) |
| grease_pencil_add | bpy.ops.object.grease_pencil_add(type='EMPTY', use_in_front=True, stroke_depth_offset=0.05, use_ligh |
| grease_pencil_dash_modifier_segment_add | bpy.ops.object.grease_pencil_dash_modifier_segment_add(modifier="") |
| grease_pencil_dash_modifier_segment_move | bpy.ops.object.grease_pencil_dash_modifier_segment_move(modifier="", type='UP') |
| grease_pencil_dash_modifier_segment_remove | bpy.ops.object.grease_pencil_dash_modifier_segment_remove(modifier="", index=0) |
| grease_pencil_time_modifier_segment_add | bpy.ops.object.grease_pencil_time_modifier_segment_add(modifier="") |
| grease_pencil_time_modifier_segment_move | bpy.ops.object.grease_pencil_time_modifier_segment_move(modifier="", type='UP') |
| grease_pencil_time_modifier_segment_remove | bpy.ops.object.grease_pencil_time_modifier_segment_remove(modifier="", index=0) |
| hide_collection | bpy.ops.object.hide_collection(collection_index=-1, toggle=False, extend=False) |
| hide_render_clear_all | bpy.ops.object.hide_render_clear_all() |
| hide_view_clear | bpy.ops.object.hide_view_clear(select=True) |
| hide_view_set | bpy.ops.object.hide_view_set(unselected=False) |
| hook_add_newob | bpy.ops.object.hook_add_newob() |
| hook_add_selob | bpy.ops.object.hook_add_selob(use_bone=False) |
| hook_assign | bpy.ops.object.hook_assign(modifier='<UNKNOWN ENUM>') |
| hook_recenter | bpy.ops.object.hook_recenter(modifier='<UNKNOWN ENUM>') |
| hook_remove | bpy.ops.object.hook_remove(modifier='<UNKNOWN ENUM>') |
| hook_reset | bpy.ops.object.hook_reset(modifier='<UNKNOWN ENUM>') |
| hook_select | bpy.ops.object.hook_select(modifier='<UNKNOWN ENUM>') |
| instance_offset_from_cursor | bpy.ops.object.instance_offset_from_cursor() |
| instance_offset_from_object | bpy.ops.object.instance_offset_from_object() |
| instance_offset_to_cursor | bpy.ops.object.instance_offset_to_cursor() |
| isolate_type_render | bpy.ops.object.isolate_type_render() |
| join | bpy.ops.object.join() |
| join_shapes | bpy.ops.object.join_shapes(use_mirror=False) |
| join_uvs | bpy.ops.object.join_uvs() |
| laplaciandeform_bind | bpy.ops.object.laplaciandeform_bind(modifier="") |
| lattice_add_to_selected | bpy.ops.object.lattice_add_to_selected(fit_to_selected=True, radius=1, margin=0, add_modifiers=True, |
| light_add | bpy.ops.object.light_add(type='POINT', radius=1, align='WORLD', location=(0, 0, 0), rotation=(0, 0,  |
| light_linking_blocker_collection_new | bpy.ops.object.light_linking_blocker_collection_new() |
| light_linking_blockers_link | bpy.ops.object.light_linking_blockers_link(link_state='INCLUDE') |
| light_linking_blockers_select | bpy.ops.object.light_linking_blockers_select() |
| light_linking_receiver_collection_new | bpy.ops.object.light_linking_receiver_collection_new() |
| light_linking_receivers_link | bpy.ops.object.light_linking_receivers_link(link_state='INCLUDE') |
| light_linking_receivers_select | bpy.ops.object.light_linking_receivers_select() |
| light_linking_unlink_from_collection | bpy.ops.object.light_linking_unlink_from_collection() |
| lightprobe_add | bpy.ops.object.lightprobe_add(type='SPHERE', radius=1, enter_editmode=False, align='WORLD', location |
| lightprobe_cache_bake | bpy.ops.object.lightprobe_cache_bake(subset='ALL') |
| lightprobe_cache_free | bpy.ops.object.lightprobe_cache_free(subset='SELECTED') |
| lineart_bake_strokes | bpy.ops.object.lineart_bake_strokes(bake_all=False) |
| lineart_clear | bpy.ops.object.lineart_clear(clear_all=False) |
| link_to_collection | bpy.ops.object.link_to_collection(collection_uid=-1, is_new=False, new_collection_name="") |
| location_clear | bpy.ops.object.location_clear(clear_delta=False) |
| make_dupli_face | bpy.ops.object.make_dupli_face() |
| make_links_data | bpy.ops.object.make_links_data(type='OBDATA') |
| make_links_scene | bpy.ops.object.make_links_scene(scene='<UNKNOWN ENUM>') |
| make_local | bpy.ops.object.make_local(type='SELECT_OBJECT') |
| make_override_library | bpy.ops.object.make_override_library(collection=0) |
| make_single_user | bpy.ops.object.make_single_user(type='SELECTED_OBJECTS', object=False, obdata=False, material=False, |
| material_slot_add | bpy.ops.object.material_slot_add() |
| material_slot_assign | bpy.ops.object.material_slot_assign() |
| material_slot_copy | bpy.ops.object.material_slot_copy() |
| material_slot_deselect | bpy.ops.object.material_slot_deselect() |
| material_slot_move | bpy.ops.object.material_slot_move(direction='UP') |
| material_slot_remove | bpy.ops.object.material_slot_remove() |
| material_slot_remove_all | bpy.ops.object.material_slot_remove_all() |
| material_slot_remove_unused | bpy.ops.object.material_slot_remove_unused() |
| material_slot_select | bpy.ops.object.material_slot_select() |
| meshdeform_bind | bpy.ops.object.meshdeform_bind(modifier="") |
| metaball_add | bpy.ops.object.metaball_add(type='BALL', radius=2, enter_editmode=False, align='WORLD', location=(0, |
| mode_set | bpy.ops.object.mode_set(mode='OBJECT', toggle=False) |
| mode_set_with_submode | bpy.ops.object.mode_set_with_submode(mode='OBJECT', toggle=False, mesh_select_mode=set()) |
| modifier_add | bpy.ops.object.modifier_add(type='SUBSURF', use_selected_objects=False) |
| modifier_add_node_group | bpy.ops.object.modifier_add_node_group(asset_library_type='LOCAL', asset_library_identifier="", rela |
| modifier_apply | bpy.ops.object.modifier_apply(modifier="", report=False, merge_customdata=True, single_user=False, a |
| modifier_apply_as_shapekey | bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=False, modifier="", report=False, use_select |
| modifier_convert | bpy.ops.object.modifier_convert(modifier="") |
| modifier_copy | bpy.ops.object.modifier_copy(modifier="", use_selected_objects=False) |
| modifier_copy_to_selected | bpy.ops.object.modifier_copy_to_selected(modifier="") |
| modifier_move_down | bpy.ops.object.modifier_move_down(modifier="") |
| modifier_move_to_index | bpy.ops.object.modifier_move_to_index(modifier="", index=0, use_selected_objects=False) |
| modifier_move_up | bpy.ops.object.modifier_move_up(modifier="") |
| modifier_remove | bpy.ops.object.modifier_remove(modifier="", report=False, use_selected_objects=False) |
| modifier_set_active | bpy.ops.object.modifier_set_active(modifier="") |
| modifiers_clear | bpy.ops.object.modifiers_clear() |
| modifiers_copy_to_selected | bpy.ops.object.modifiers_copy_to_selected() |
| move_to_collection | bpy.ops.object.move_to_collection(collection_uid=-1, is_new=False, new_collection_name="") |
| multires_base_apply | bpy.ops.object.multires_base_apply(modifier="", apply_heuristic=True) |
| multires_external_pack | bpy.ops.object.multires_external_pack() |
| multires_external_save | bpy.ops.object.multires_external_save(filepath="", hide_props_region=True, check_existing=True, filt |
| multires_higher_levels_delete | bpy.ops.object.multires_higher_levels_delete(modifier="") |
| multires_rebuild_subdiv | bpy.ops.object.multires_rebuild_subdiv(modifier="") |
| multires_reshape | bpy.ops.object.multires_reshape(modifier="") |
| multires_subdivide | bpy.ops.object.multires_subdivide(modifier="", mode='CATMULL_CLARK') |
| multires_unsubdivide | bpy.ops.object.multires_unsubdivide(modifier="") |
| ocean_bake | bpy.ops.object.ocean_bake(modifier="", free=False) |
| origin_clear | bpy.ops.object.origin_clear() |
| origin_set | bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='MEDIAN') |
| parent_clear | bpy.ops.object.parent_clear(type='CLEAR') |
| parent_inverse_apply | bpy.ops.object.parent_inverse_apply() |
| parent_no_inverse_set | bpy.ops.object.parent_no_inverse_set(keep_transform=False) |
| parent_set | bpy.ops.object.parent_set(type='OBJECT', xmirror=False, keep_transform=False) |
| particle_system_add | bpy.ops.object.particle_system_add() |
| particle_system_remove | bpy.ops.object.particle_system_remove() |
| paste_transform | bpy.ops.object.paste_transform(method='CURRENT', bake_step=0, use_mirror=False, mirror_axis_loc='x', |
| paths_calculate | bpy.ops.object.paths_calculate(display_type='RANGE', range='SCENE') |
| paths_clear | bpy.ops.object.paths_clear(only_selected=False) |
| paths_update | bpy.ops.object.paths_update() |
| paths_update_visible | bpy.ops.object.paths_update_visible() |
| pointcloud_random_add | bpy.ops.object.pointcloud_random_add(align='WORLD', location=(0, 0, 0), rotation=(0, 0, 0), scale=(0 |
| posemode_toggle | bpy.ops.object.posemode_toggle() |
| quadriflow_remesh | bpy.ops.object.quadriflow_remesh(use_mesh_symmetry=True, use_preserve_sharp=False, use_preserve_boun |
| quick_explode | bpy.ops.object.quick_explode(style='EXPLODE', amount=100, frame_duration=50, frame_start=1, frame_en |
| quick_fur | bpy.ops.object.quick_fur(density='MEDIUM', length=0.1, radius=0.001, view_percentage=1, apply_hair_g |
| quick_liquid | bpy.ops.object.quick_liquid(show_flows=False) |
| quick_smoke | bpy.ops.object.quick_smoke(style='SMOKE', show_flows=False) |
| randomize_transform | bpy.ops.object.randomize_transform(random_seed=0, use_delta=False, use_loc=True, loc=(0, 0, 0), use_ |
| reset_override_library | bpy.ops.object.reset_override_library() |
| rotation_clear | bpy.ops.object.rotation_clear(clear_delta=False) |
| scale_clear | bpy.ops.object.scale_clear(clear_delta=False) |
| select_all | bpy.ops.object.select_all(action='TOGGLE') |
| select_by_type | bpy.ops.object.select_by_type(extend=False, type='MESH') |
| select_camera | bpy.ops.object.select_camera(extend=False) |
| select_grouped | bpy.ops.object.select_grouped(extend=False, type='CHILDREN_RECURSIVE') |
| select_hierarchy | bpy.ops.object.select_hierarchy(direction='PARENT', extend=False) |
| select_less | bpy.ops.object.select_less() |
| select_linked | bpy.ops.object.select_linked(extend=False, type='OBDATA') |
| select_mirror | bpy.ops.object.select_mirror(extend=False) |
| select_more | bpy.ops.object.select_more() |
| select_pattern | bpy.ops.object.select_pattern(pattern="*", case_sensitive=False, extend=True) |
| select_random | bpy.ops.object.select_random(ratio=0.5, seed=0, action='SELECT') |
| select_same_collection | bpy.ops.object.select_same_collection(collection="") |
| shade_auto_smooth | bpy.ops.object.shade_auto_smooth(use_auto_smooth=True, angle=0.523599) |
| shade_flat | bpy.ops.object.shade_flat(keep_sharp_edges=True) |
| shade_smooth | bpy.ops.object.shade_smooth(keep_sharp_edges=True) |
| shade_smooth_by_angle | bpy.ops.object.shade_smooth_by_angle(angle=0.523599, keep_sharp_edges=True) |
| shaderfx_add | bpy.ops.object.shaderfx_add(type='FX_BLUR') |
| shaderfx_copy | bpy.ops.object.shaderfx_copy(shaderfx="") |
| shaderfx_move_down | bpy.ops.object.shaderfx_move_down(shaderfx="") |
| shaderfx_move_to_index | bpy.ops.object.shaderfx_move_to_index(shaderfx="", index=0) |
| shaderfx_move_up | bpy.ops.object.shaderfx_move_up(shaderfx="") |
| shaderfx_remove | bpy.ops.object.shaderfx_remove(shaderfx="", report=False) |
| shape_key_add | bpy.ops.object.shape_key_add(from_mix=True) |
| shape_key_apply_to_basis | bpy.ops.object.shape_key_apply_to_basis() |
| shape_key_clear | bpy.ops.object.shape_key_clear() |
| shape_key_copy | bpy.ops.object.shape_key_copy() |
| shape_key_lock | bpy.ops.object.shape_key_lock(action='LOCK') |
| shape_key_make_basis | bpy.ops.object.shape_key_make_basis() |
| shape_key_mirror | bpy.ops.object.shape_key_mirror(use_topology=False) |
| shape_key_move | bpy.ops.object.shape_key_move(type='TOP') |
| shape_key_remove | bpy.ops.object.shape_key_remove(all=False, apply_mix=False) |
| shape_key_retime | bpy.ops.object.shape_key_retime() |
| shape_key_transfer | bpy.ops.object.shape_key_transfer(mode='OFFSET', use_clamp=False) |
| simulation_nodes_cache_bake | bpy.ops.object.simulation_nodes_cache_bake(selected=False) |
| simulation_nodes_cache_calculate_to_frame | bpy.ops.object.simulation_nodes_cache_calculate_to_frame(selected=False) |
| simulation_nodes_cache_delete | bpy.ops.object.simulation_nodes_cache_delete(selected=False) |
| skin_armature_create | bpy.ops.object.skin_armature_create(modifier="") |
| skin_loose_mark_clear | bpy.ops.object.skin_loose_mark_clear(action='MARK') |
| skin_radii_equalize | bpy.ops.object.skin_radii_equalize() |
| skin_root_mark | bpy.ops.object.skin_root_mark() |
| speaker_add | bpy.ops.object.speaker_add(enter_editmode=False, align='WORLD', location=(0, 0, 0), rotation=(0, 0,  |
| subdivision_set | bpy.ops.object.subdivision_set(level=1, relative=False, ensure_modifier=True) |
| surfacedeform_bind | bpy.ops.object.surfacedeform_bind(modifier="") |
| text_add | bpy.ops.object.text_add(radius=1, enter_editmode=False, align='WORLD', location=(0, 0, 0), rotation= |
| track_clear | bpy.ops.object.track_clear(type='CLEAR') |
| track_set | bpy.ops.object.track_set(type='DAMPTRACK') |
| transfer_mode | bpy.ops.object.transfer_mode(use_flash_on_transfer=True) |
| transform_apply | bpy.ops.object.transform_apply(location=True, rotation=True, scale=True, properties=True, corrective |
| transform_axis_target | bpy.ops.object.transform_axis_target() |
| transform_to_mouse | bpy.ops.object.transform_to_mouse(name="", session_uid=0, matrix=((0, 0, 0, 0), (0, 0, 0, 0), (0, 0, |
| transforms_to_deltas | bpy.ops.object.transforms_to_deltas(mode='ALL', reset_values=True) |
| unlink_data | bpy.ops.object.unlink_data() |
| update_shapes | bpy.ops.object.update_shapes(use_mirror=False) |
| vertex_group_add | bpy.ops.object.vertex_group_add() |
| vertex_group_assign | bpy.ops.object.vertex_group_assign() |
| vertex_group_assign_new | bpy.ops.object.vertex_group_assign_new() |
| vertex_group_clean | bpy.ops.object.vertex_group_clean(group_select_mode='ACTIVE', limit=0, keep_single=False) |
| vertex_group_copy | bpy.ops.object.vertex_group_copy() |
| vertex_group_copy_to_selected | bpy.ops.object.vertex_group_copy_to_selected() |
| vertex_group_deselect | bpy.ops.object.vertex_group_deselect() |
| vertex_group_invert | bpy.ops.object.vertex_group_invert(group_select_mode='ACTIVE', auto_assign=True, auto_remove=True) |
| vertex_group_levels | bpy.ops.object.vertex_group_levels(group_select_mode='ACTIVE', offset=0, gain=1) |
| vertex_group_limit_total | bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4) |
| vertex_group_lock | bpy.ops.object.vertex_group_lock(action='TOGGLE', mask='ALL') |
| vertex_group_mirror | bpy.ops.object.vertex_group_mirror(mirror_weights=True, flip_group_names=True, all_groups=False, use |
| vertex_group_move | bpy.ops.object.vertex_group_move(direction='UP') |
| vertex_group_normalize | bpy.ops.object.vertex_group_normalize() |
| vertex_group_normalize_all | bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=True) |
| vertex_group_quantize | bpy.ops.object.vertex_group_quantize(group_select_mode='ACTIVE', steps=4) |
| vertex_group_remove | bpy.ops.object.vertex_group_remove(all=False, all_unlocked=False) |
| vertex_group_remove_from | bpy.ops.object.vertex_group_remove_from(use_all_groups=False, use_all_verts=False) |
| vertex_group_select | bpy.ops.object.vertex_group_select() |
| vertex_group_set_active | bpy.ops.object.vertex_group_set_active(group='<UNKNOWN ENUM>') |
| vertex_group_smooth | bpy.ops.object.vertex_group_smooth(group_select_mode='ACTIVE', factor=0.5, repeat=1, expand=0) |
| vertex_group_sort | bpy.ops.object.vertex_group_sort(sort_type='NAME') |
| vertex_parent_set | bpy.ops.object.vertex_parent_set() |
| vertex_weight_copy | bpy.ops.object.vertex_weight_copy() |
| vertex_weight_delete | bpy.ops.object.vertex_weight_delete(weight_group=-1) |
| vertex_weight_normalize_active_vertex | bpy.ops.object.vertex_weight_normalize_active_vertex() |
| vertex_weight_paste | bpy.ops.object.vertex_weight_paste(weight_group=-1) |
| vertex_weight_set_active | bpy.ops.object.vertex_weight_set_active(weight_group=-1) |
| visual_geometry_to_objects | bpy.ops.object.visual_geometry_to_objects() |
| visual_transform_apply | bpy.ops.object.visual_transform_apply() |
| volume_add | bpy.ops.object.volume_add(align='WORLD', location=(0, 0, 0), rotation=(0, 0, 0), scale=(0, 0, 0)) |
| volume_import | bpy.ops.object.volume_import(filepath="", directory="", files=[], hide_props_region=True, check_exis |
| voxel_remesh | bpy.ops.object.voxel_remesh() |
| voxel_size_edit | bpy.ops.object.voxel_size_edit() |

## mesh（167）

| 操作符 | 说明 |
|---|---|
| attribute_set | bpy.ops.mesh.attribute_set(value_float=0, value_float_vector_2d=(0, 0), value_float_vector_3d=(0, 0, |
| average_normals | bpy.ops.mesh.average_normals(average_type='CUSTOM_NORMAL', weight=50, threshold=0.01) |
| beautify_fill | bpy.ops.mesh.beautify_fill(angle_limit=3.14159) |
| bevel | bpy.ops.mesh.bevel(offset_type='OFFSET', offset=0, profile_type='SUPERELLIPSE', offset_pct=0, segmen |
| bisect | bpy.ops.mesh.bisect(plane_co=(0, 0, 0), plane_no=(0, 0, 0), use_fill=False, clear_inner=False, clear |
| blend_from_shape | bpy.ops.mesh.blend_from_shape(shape='<UNKNOWN ENUM>', blend=1, add=True) |
| bridge_edge_loops | bpy.ops.mesh.bridge_edge_loops(type='SINGLE', use_merge=False, merge_factor=0.5, twist_offset=0, num |
| circularize | bpy.ops.mesh.circularize(factor=1, fit_method='LEAST_SQUARE', angle=0, use_custom_radius=False, cust |
| colors_reverse | bpy.ops.mesh.colors_reverse() |
| colors_rotate | bpy.ops.mesh.colors_rotate(use_ccw=False) |
| convex_hull | bpy.ops.mesh.convex_hull(delete_unused=True, use_existing_faces=True, make_holes=False, join_triangl |
| customdata_custom_splitnormals_add | bpy.ops.mesh.customdata_custom_splitnormals_add() |
| customdata_custom_splitnormals_clear | bpy.ops.mesh.customdata_custom_splitnormals_clear() |
| customdata_face_sets_clear | bpy.ops.mesh.customdata_face_sets_clear() |
| customdata_mask_clear | bpy.ops.mesh.customdata_mask_clear() |
| customdata_skin_add | bpy.ops.mesh.customdata_skin_add() |
| customdata_skin_clear | bpy.ops.mesh.customdata_skin_clear() |
| decimate | bpy.ops.mesh.decimate(ratio=1, use_vertex_group=False, vertex_group_factor=1, invert_vertex_group=Fa |
| delete | bpy.ops.mesh.delete(type='VERT') |
| delete_edgeloop | bpy.ops.mesh.delete_edgeloop(use_face_split=True) |
| delete_loose | bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False) |
| dissolve_degenerate | bpy.ops.mesh.dissolve_degenerate(threshold=0.0001) |
| dissolve_edges | bpy.ops.mesh.dissolve_edges(use_verts=True, angle_threshold=3.14159, use_face_split=False, use_prese |
| dissolve_faces | bpy.ops.mesh.dissolve_faces(use_verts=False) |
| dissolve_limited | bpy.ops.mesh.dissolve_limited(angle_limit=0.0872665, use_dissolve_boundaries=False, delimit={'NORMAL |
| dissolve_mode | bpy.ops.mesh.dissolve_mode(use_verts=False, angle_threshold=3.14159, use_preserve_quads=True, use_fa |
| dissolve_verts | bpy.ops.mesh.dissolve_verts(use_face_split=False, use_boundary_tear=False) |
| dupli_extrude_cursor | bpy.ops.mesh.dupli_extrude_cursor(rotate_source=True) |
| duplicate | bpy.ops.mesh.duplicate(mode=1) |
| duplicate_move | bpy.ops.mesh.duplicate_move(MESH_OT_duplicate={"mode":1}, TRANSFORM_OT_translate={"value":(0, 0, 0), |
| edge_collapse | bpy.ops.mesh.edge_collapse() |
| edge_face_add | bpy.ops.mesh.edge_face_add() |
| edge_rotate | bpy.ops.mesh.edge_rotate(use_ccw=False) |
| edge_split | bpy.ops.mesh.edge_split(type='EDGE') |
| edgering_select | bpy.ops.mesh.edgering_select(delimit_edge_ring={'NGONS'}, extend=False, deselect=False, toggle=False |
| edges_select_sharp | bpy.ops.mesh.edges_select_sharp(sharpness=0.523599) |
| extrude_context | bpy.ops.mesh.extrude_context(use_normal_flip=False, use_dissolve_ortho_edges=False, mirror=False) |
| extrude_context_move | bpy.ops.mesh.extrude_context_move(MESH_OT_extrude_context={"use_normal_flip":False, "use_dissolve_or |
| extrude_edges_indiv | bpy.ops.mesh.extrude_edges_indiv(use_normal_flip=False, mirror=False) |
| extrude_edges_move | bpy.ops.mesh.extrude_edges_move(MESH_OT_extrude_edges_indiv={"use_normal_flip":False, "mirror":False |
| extrude_faces_indiv | bpy.ops.mesh.extrude_faces_indiv(mirror=False) |
| extrude_faces_move | bpy.ops.mesh.extrude_faces_move(MESH_OT_extrude_faces_indiv={"mirror":False}, TRANSFORM_OT_shrink_fa |
| extrude_manifold | bpy.ops.mesh.extrude_manifold(MESH_OT_extrude_region={"use_normal_flip":False, "use_dissolve_ortho_e |
| extrude_region | bpy.ops.mesh.extrude_region(use_normal_flip=False, use_dissolve_ortho_edges=False, mirror=False) |
| extrude_region_move | bpy.ops.mesh.extrude_region_move(MESH_OT_extrude_region={"use_normal_flip":False, "use_dissolve_orth |
| extrude_region_shrink_fatten | bpy.ops.mesh.extrude_region_shrink_fatten(MESH_OT_extrude_region={"use_normal_flip":False, "use_diss |
| extrude_repeat | bpy.ops.mesh.extrude_repeat(steps=10, offset=(0, 0, 0), scale_offset=1) |
| extrude_vertices_move | bpy.ops.mesh.extrude_vertices_move(MESH_OT_extrude_verts_indiv={"mirror":False}, TRANSFORM_OT_transl |
| extrude_verts_indiv | bpy.ops.mesh.extrude_verts_indiv(mirror=False) |
| face_make_planar | bpy.ops.mesh.face_make_planar(factor=1, repeat=1) |
| face_split_by_edges | bpy.ops.mesh.face_split_by_edges() |
| faces_select_linked_flat | bpy.ops.mesh.faces_select_linked_flat(sharpness=0.0174533) |
| faces_shade_flat | bpy.ops.mesh.faces_shade_flat() |
| faces_shade_smooth | bpy.ops.mesh.faces_shade_smooth() |
| fill | bpy.ops.mesh.fill(use_beauty=True) |
| fill_grid | bpy.ops.mesh.fill_grid(span=1, offset=0, use_interp_simple=False) |
| fill_holes | bpy.ops.mesh.fill_holes(sides=4) |
| flatten | bpy.ops.mesh.flatten(factor=1, method='BEST_FIT', lock=(False, False, False)) |
| flip_normals | bpy.ops.mesh.flip_normals(only_clnors=False) |
| flip_quad_tessellation | bpy.ops.mesh.flip_quad_tessellation() |
| hide | bpy.ops.mesh.hide(unselected=False) |
| inset | bpy.ops.mesh.inset(use_boundary=True, use_even_offset=True, use_relative_offset=False, use_edge_rail |
| intersect | bpy.ops.mesh.intersect(mode='SELECT_UNSELECT', separate_mode='CUT', threshold=1e-06, solver='EXACT') |
| intersect_boolean | bpy.ops.mesh.intersect_boolean(operation='DIFFERENCE', use_swap=False, use_self=False, threshold=1e- |
| knife_project | bpy.ops.mesh.knife_project(cut_through=False) |
| knife_tool | bpy.ops.mesh.knife_tool(use_occlude_geometry=True, only_selected=False, xray=True, visible_measureme |
| loop_select | bpy.ops.mesh.loop_select(delimit_edge_loop={'NGONS', 'OUTER_CORNERS'}, delimit_face_loop=set(), exte |
| loop_to_region | bpy.ops.mesh.loop_to_region(select_bigger=False) |
| loopcut | bpy.ops.mesh.loopcut(number_cuts=1, smoothness=0, falloff='INVERSE_SQUARE', object_index=-1, edge_in |
| loopcut_slide | bpy.ops.mesh.loopcut_slide(MESH_OT_loopcut={"number_cuts":1, "smoothness":0, "falloff":'INVERSE_SQUA |
| mark_freestyle_edge | bpy.ops.mesh.mark_freestyle_edge(clear=False) |
| mark_freestyle_face | bpy.ops.mesh.mark_freestyle_face(clear=False) |
| mark_seam | bpy.ops.mesh.mark_seam(clear=False) |
| mark_sharp | bpy.ops.mesh.mark_sharp(clear=False, use_verts=False) |
| merge | bpy.ops.mesh.merge(type='CENTER', uvs=False) |
| merge_normals | bpy.ops.mesh.merge_normals() |
| mod_weighted_strength | bpy.ops.mesh.mod_weighted_strength(set=False, face_strength='MEDIUM') |
| normals_make_consistent | bpy.ops.mesh.normals_make_consistent(inside=False) |
| normals_tools | bpy.ops.mesh.normals_tools(mode='COPY', absolute=False) |
| offset_edge_loops | bpy.ops.mesh.offset_edge_loops(use_cap_endpoint=False) |
| offset_edge_loops_slide | bpy.ops.mesh.offset_edge_loops_slide(MESH_OT_offset_edge_loops={"use_cap_endpoint":False}, TRANSFORM |
| point_normals | bpy.ops.mesh.point_normals(mode='COORDINATES', invert=False, align=False, target_location=(0, 0, 0), |
| poke | bpy.ops.mesh.poke(offset=0, use_relative_offset=False, center_mode='MEDIAN_WEIGHTED') |
| polybuild_delete_at_cursor | bpy.ops.mesh.polybuild_delete_at_cursor(mirror=False, use_proportional_edit=False, proportional_edit |
| polybuild_dissolve_at_cursor | bpy.ops.mesh.polybuild_dissolve_at_cursor() |
| polybuild_extrude_at_cursor_move | bpy.ops.mesh.polybuild_extrude_at_cursor_move(MESH_OT_polybuild_transform_at_cursor={"mirror":False, |
| polybuild_face_at_cursor | bpy.ops.mesh.polybuild_face_at_cursor(create_quads=True, mirror=False, use_proportional_edit=False,  |
| polybuild_face_at_cursor_move | bpy.ops.mesh.polybuild_face_at_cursor_move(MESH_OT_polybuild_face_at_cursor={"create_quads":True, "m |
| polybuild_split_at_cursor | bpy.ops.mesh.polybuild_split_at_cursor(mirror=False, use_proportional_edit=False, proportional_edit_ |
| polybuild_split_at_cursor_move | bpy.ops.mesh.polybuild_split_at_cursor_move(MESH_OT_polybuild_split_at_cursor={"mirror":False, "use_ |
| polybuild_transform_at_cursor | bpy.ops.mesh.polybuild_transform_at_cursor(mirror=False, use_proportional_edit=False, proportional_e |
| polybuild_transform_at_cursor_move | bpy.ops.mesh.polybuild_transform_at_cursor_move(MESH_OT_polybuild_transform_at_cursor={"mirror":Fals |
| primitive_circle_add | bpy.ops.mesh.primitive_circle_add(vertices=32, radius=1, fill_type='NOTHING', calc_uvs=True, enter_e |
| primitive_cone_add | bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=1, radius2=0, depth=2, end_fill_type='NGON', ca |
| primitive_cube_add | bpy.ops.mesh.primitive_cube_add(size=2, calc_uvs=True, enter_editmode=False, align='WORLD', location |
| primitive_cube_add_gizmo | bpy.ops.mesh.primitive_cube_add_gizmo(calc_uvs=True, enter_editmode=False, align='WORLD', location=( |
| primitive_cylinder_add | bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=1, depth=2, end_fill_type='NGON', calc_uvs=T |
| primitive_grid_add | bpy.ops.mesh.primitive_grid_add(x_subdivisions=10, y_subdivisions=10, size=2, calc_uvs=True, enter_e |
| primitive_ico_sphere_add | bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, calc_uvs=True, enter_editmode=False, |
| primitive_monkey_add | bpy.ops.mesh.primitive_monkey_add(size=2, calc_uvs=True, enter_editmode=False, align='WORLD', locati |
| primitive_plane_add | bpy.ops.mesh.primitive_plane_add(size=2, calc_uvs=True, enter_editmode=False, align='WORLD', locatio |
| primitive_torus_add | bpy.ops.mesh.primitive_torus_add(align='WORLD', location=(0, 0, 0), rotation=(0, 0, 0), major_segmen |
| primitive_uv_sphere_add | bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, calc_uvs=True, enter_edit |
| quads_convert_to_tris | bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY') |
| region_to_loop | bpy.ops.mesh.region_to_loop() |
| remove_doubles | bpy.ops.mesh.remove_doubles(threshold=0.0001, use_centroid=True, use_unselected=False, use_sharp_edg |
| reorder_vertices_spatial | bpy.ops.mesh.reorder_vertices_spatial() |
| reveal | bpy.ops.mesh.reveal(select=True) |
| rip | bpy.ops.mesh.rip(mirror=False, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', prop |
| rip_edge | bpy.ops.mesh.rip_edge(location=(0, 0, 0), direction=(0, 0, 0)) |
| rip_edge_move | bpy.ops.mesh.rip_edge_move(MESH_OT_rip_edge={"location":(0, 0, 0), "direction":(0, 0, 0)}, TRANSFORM |
| rip_move | bpy.ops.mesh.rip_move(MESH_OT_rip={"mirror":False, "use_proportional_edit":False, "proportional_edit |
| screw | bpy.ops.mesh.screw(steps=9, turns=1, center=(0, 0, 0), axis=(0, 0, 0)) |
| select_all | bpy.ops.mesh.select_all(action='TOGGLE') |
| select_axis | bpy.ops.mesh.select_axis(orientation='LOCAL', sign='POS', axis='X', threshold=0.0001) |
| select_boundary_loop_multi | bpy.ops.mesh.select_boundary_loop_multi(extend=True, delimit_edge_loop=set()) |
| select_by_attribute | bpy.ops.mesh.select_by_attribute() |
| select_by_pole_count | bpy.ops.mesh.select_by_pole_count(pole_count=4, type='NOTEQUAL', extend=False, exclude_nonmanifold=T |
| select_edge_loop_multi | bpy.ops.mesh.select_edge_loop_multi(delimit_edge_loop={'NGONS', 'OUTER_CORNERS'}) |
| select_edge_ring_multi | bpy.ops.mesh.select_edge_ring_multi(delimit_edge_ring={'NGONS'}) |
| select_face_by_sides | bpy.ops.mesh.select_face_by_sides(number=4, type='EQUAL', extend=True) |
| select_interior_faces | bpy.ops.mesh.select_interior_faces() |
| select_less | bpy.ops.mesh.select_less(use_face_step=True) |
| select_linked | bpy.ops.mesh.select_linked(delimit={'SEAM'}) |
| select_linked_pick | bpy.ops.mesh.select_linked_pick(deselect=False, delimit={'SEAM'}, object_index=-1, index=-1) |
| select_loose | bpy.ops.mesh.select_loose(extend=False) |
| select_mirror | bpy.ops.mesh.select_mirror(axis={'X'}, extend=False) |
| select_mode | bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT', action='TOGGLE') |
| select_more | bpy.ops.mesh.select_more(use_face_step=True) |
| select_next_item | bpy.ops.mesh.select_next_item() |
| select_non_manifold | bpy.ops.mesh.select_non_manifold(extend=True, use_wire=True, use_boundary=True, use_multi_face=True, |
| select_nth | bpy.ops.mesh.select_nth(skip=1, nth=1, offset=0) |
| select_prev_item | bpy.ops.mesh.select_prev_item() |
| select_random | bpy.ops.mesh.select_random(ratio=0.5, seed=0, action='SELECT') |
| select_similar | bpy.ops.mesh.select_similar(type='VERT_NORMAL', compare='EQUAL', threshold=0) |
| select_similar_region | bpy.ops.mesh.select_similar_region() |
| select_ungrouped | bpy.ops.mesh.select_ungrouped(extend=False) |
| separate | bpy.ops.mesh.separate(type='SELECTED') |
| set_normals_from_faces | bpy.ops.mesh.set_normals_from_faces(keep_sharp=False) |
| set_sharpness_by_angle | bpy.ops.mesh.set_sharpness_by_angle(angle=0.523599, extend=False) |
| shape_propagate_to_all | bpy.ops.mesh.shape_propagate_to_all() |
| shortest_path_pick | bpy.ops.mesh.shortest_path_pick(edge_mode='SELECT', use_face_step=False, use_topology_distance=False |
| shortest_path_select | bpy.ops.mesh.shortest_path_select(edge_mode='SELECT', use_face_step=False, use_topology_distance=Fal |
| smooth_normals | bpy.ops.mesh.smooth_normals(factor=0.5) |
| solidify | bpy.ops.mesh.solidify(thickness=0.01) |
| sort_elements | bpy.ops.mesh.sort_elements(type='VIEW_ZAXIS', elements={'VERT'}, reverse=False, seed=0) |
| space_edge_loops_evenly | bpy.ops.mesh.space_edge_loops_evenly(factor=1, interpolation='CUBIC', lock=(False, False, False)) |
| spin | bpy.ops.mesh.spin(steps=12, dupli=False, angle=1.5708, use_auto_merge=True, use_normal_flip=False, c |
| split | bpy.ops.mesh.split() |
| split_normals | bpy.ops.mesh.split_normals() |
| subdivide | bpy.ops.mesh.subdivide(number_cuts=1, smoothness=0, ngon=True, quadcorner='STRAIGHT_CUT', fractal=0, |
| subdivide_edgering | bpy.ops.mesh.subdivide_edgering(number_cuts=10, interpolation='PATH', smoothness=1, profile_shape_fa |
| symmetrize | bpy.ops.mesh.symmetrize(direction='NEGATIVE_X', threshold=0.0001) |
| symmetry_snap | bpy.ops.mesh.symmetry_snap(direction='NEGATIVE_X', threshold=0.05, factor=0.5, use_center=True, use_ |
| tris_convert_to_quads | bpy.ops.mesh.tris_convert_to_quads(face_threshold=0.698132, shape_threshold=0.698132, topology_influ |
| unsubdivide | bpy.ops.mesh.unsubdivide(iterations=2) |
| uv_texture_add | bpy.ops.mesh.uv_texture_add() |
| uv_texture_remove | bpy.ops.mesh.uv_texture_remove() |
| uvs_reverse | bpy.ops.mesh.uvs_reverse() |
| uvs_rotate | bpy.ops.mesh.uvs_rotate(use_ccw=False) |
| vert_connect | bpy.ops.mesh.vert_connect() |
| vert_connect_concave | bpy.ops.mesh.vert_connect_concave() |
| vert_connect_nonplanar | bpy.ops.mesh.vert_connect_nonplanar(angle_limit=0.0872665) |
| vert_connect_path | bpy.ops.mesh.vert_connect_path() |
| vertices_smooth | bpy.ops.mesh.vertices_smooth(factor=0, repeat=1, xaxis=True, yaxis=True, zaxis=True, wait_for_input= |
| vertices_smooth_laplacian | bpy.ops.mesh.vertices_smooth_laplacian(repeat=1, lambda_factor=1, lambda_border=5e-05, use_x=True, u |
| wireframe | bpy.ops.mesh.wireframe(use_boundary=True, use_even_offset=True, use_relative_offset=False, use_repla |

## modifier（0）

| 操作符 | 说明 |
|---|---|

## material（3）

| 操作符 | 说明 |
|---|---|
| copy | bpy.ops.material.copy() |
| new | bpy.ops.material.new() |
| paste | bpy.ops.material.paste() |

## node（182）

| 操作符 | 说明 |
|---|---|
| activate_viewer | bpy.ops.node.activate_viewer() |
| add_closure_zone | bpy.ops.node.add_closure_zone(settings=[], use_transform=False, offset=(150, 0)) |
| add_collection | bpy.ops.node.add_collection(name="", session_uid=0) |
| add_color | bpy.ops.node.add_color(color=(0, 0, 0, 0), gamma=False, has_alpha=False) |
| add_empty_group | bpy.ops.node.add_empty_group(settings=[], use_transform=False) |
| add_foreach_geometry_element_zone | bpy.ops.node.add_foreach_geometry_element_zone(settings=[], use_transform=False, offset=(150, 0)) |
| add_group | bpy.ops.node.add_group(name="", session_uid=0, show_datablock_in_node=True) |
| add_group_asset | bpy.ops.node.add_group_asset(asset_library_type='LOCAL', asset_library_identifier="", relative_asset |
| add_group_input_node | bpy.ops.node.add_group_input_node(only_selected_sockets=True, all_panel_contents=False) |
| add_image | bpy.ops.node.add_image(filepath="", directory="", files=[], hide_props_region=True, check_existing=F |
| add_import_node | bpy.ops.node.add_import_node(directory="", files=[]) |
| add_mask | bpy.ops.node.add_mask(name="", session_uid=0) |
| add_material | bpy.ops.node.add_material(name="", session_uid=0) |
| add_node | bpy.ops.node.add_node(settings=[], use_transform=False, type="", visible_output="") |
| add_object | bpy.ops.node.add_object(name="", session_uid=0) |
| add_repeat_zone | bpy.ops.node.add_repeat_zone(settings=[], use_transform=False, offset=(150, 0)) |
| add_reroute | bpy.ops.node.add_reroute(path=[], cursor=11) |
| add_simulation_zone | bpy.ops.node.add_simulation_zone(settings=[], use_transform=False, offset=(150, 0)) |
| add_typed_bundle | bpy.ops.node.add_typed_bundle(settings=[], use_transform=False) |
| add_zone | bpy.ops.node.add_zone(settings=[], use_transform=False, offset=(150, 0), input_node_type="", output_ |
| attach | bpy.ops.node.attach() |
| backimage_fit | bpy.ops.node.backimage_fit() |
| backimage_move | bpy.ops.node.backimage_move() |
| backimage_sample | bpy.ops.node.backimage_sample() |
| backimage_zoom | bpy.ops.node.backimage_zoom(factor=1.2, use_mouse_pos=True) |
| bake_node_item_add | bpy.ops.node.bake_node_item_add(node_identifier=0, show_dialog=False, init_from_active=True, socket_ |
| bake_node_item_move | bpy.ops.node.bake_node_item_move(direction='UP', node_identifier=0) |
| bake_node_item_remove | bpy.ops.node.bake_node_item_remove(node_identifier=0) |
| capture_attribute_item_add | bpy.ops.node.capture_attribute_item_add(node_identifier=0, show_dialog=False, init_from_active=True, |
| capture_attribute_item_move | bpy.ops.node.capture_attribute_item_move(direction='UP', node_identifier=0) |
| capture_attribute_item_remove | bpy.ops.node.capture_attribute_item_remove(node_identifier=0) |
| clear_viewer_border | bpy.ops.node.clear_viewer_border() |
| clipboard_copy | bpy.ops.node.clipboard_copy() |
| clipboard_paste | bpy.ops.node.clipboard_paste(offset=(0, 0)) |
| closure_input_item_add | bpy.ops.node.closure_input_item_add(node_identifier=0, show_dialog=False, init_from_active=True, soc |
| closure_input_item_move | bpy.ops.node.closure_input_item_move(direction='UP', node_identifier=0) |
| closure_input_item_remove | bpy.ops.node.closure_input_item_remove(node_identifier=0) |
| closure_output_item_add | bpy.ops.node.closure_output_item_add(node_identifier=0, show_dialog=False, init_from_active=True, so |
| closure_output_item_move | bpy.ops.node.closure_output_item_move(direction='UP', node_identifier=0) |
| closure_output_item_remove | bpy.ops.node.closure_output_item_remove(node_identifier=0) |
| closure_to_list_item_add | bpy.ops.node.closure_to_list_item_add(node_identifier=0, show_dialog=False, init_from_active=True, s |
| closure_to_list_item_move | bpy.ops.node.closure_to_list_item_move(direction='UP', node_identifier=0) |
| closure_to_list_item_remove | bpy.ops.node.closure_to_list_item_remove(node_identifier=0) |
| collapse_hide_unused_toggle | bpy.ops.node.collapse_hide_unused_toggle() |
| combine_bundle_item_add | bpy.ops.node.combine_bundle_item_add(node_identifier=0, show_dialog=False, init_from_active=True, so |
| combine_bundle_item_move | bpy.ops.node.combine_bundle_item_move(direction='UP', node_identifier=0) |
| combine_bundle_item_remove | bpy.ops.node.combine_bundle_item_remove(node_identifier=0) |
| connect_to_output | bpy.ops.node.connect_to_output(run_in_geometry_nodes=True) |
| cryptomatte_layer_add | bpy.ops.node.cryptomatte_layer_add() |
| cryptomatte_layer_remove | bpy.ops.node.cryptomatte_layer_remove() |
| deactivate_viewer | bpy.ops.node.deactivate_viewer() |
| default_group_width_set | bpy.ops.node.default_group_width_set() |
| delete | bpy.ops.node.delete() |
| delete_copy_reconnect | bpy.ops.node.delete_copy_reconnect(NODE_OT_clipboard_copy={}, NODE_OT_delete_reconnect={}) |
| delete_reconnect | bpy.ops.node.delete_reconnect() |
| detach | bpy.ops.node.detach() |
| detach_translate_attach | bpy.ops.node.detach_translate_attach(NODE_OT_detach={}, TRANSFORM_OT_translate={"value":(0, 0, 0), " |
| duplicate | bpy.ops.node.duplicate(keep_inputs=False, linked=True) |
| duplicate_compositing_modifier_node_group | bpy.ops.node.duplicate_compositing_modifier_node_group() |
| duplicate_compositing_node_group | bpy.ops.node.duplicate_compositing_node_group() |
| duplicate_move | bpy.ops.node.duplicate_move(NODE_OT_duplicate={"keep_inputs":False, "linked":True}, NODE_OT_translat |
| duplicate_move_keep_inputs | bpy.ops.node.duplicate_move_keep_inputs(NODE_OT_duplicate={"keep_inputs":False, "linked":True}, NODE |
| duplicate_move_linked | bpy.ops.node.duplicate_move_linked(NODE_OT_duplicate={"keep_inputs":False, "linked":True}, NODE_OT_t |
| enum_definition_item_add | bpy.ops.node.enum_definition_item_add(node_identifier=0, show_dialog=False, init_from_active=True, i |
| enum_definition_item_move | bpy.ops.node.enum_definition_item_move(direction='UP', node_identifier=0) |
| enum_definition_item_remove | bpy.ops.node.enum_definition_item_remove(node_identifier=0) |
| evaluate_closure_input_item_add | bpy.ops.node.evaluate_closure_input_item_add(node_identifier=0, show_dialog=False, init_from_active= |
| evaluate_closure_input_item_move | bpy.ops.node.evaluate_closure_input_item_move(direction='UP', node_identifier=0) |
| evaluate_closure_input_item_remove | bpy.ops.node.evaluate_closure_input_item_remove(node_identifier=0) |
| evaluate_closure_output_item_add | bpy.ops.node.evaluate_closure_output_item_add(node_identifier=0, show_dialog=False, init_from_active |
| evaluate_closure_output_item_move | bpy.ops.node.evaluate_closure_output_item_move(direction='UP', node_identifier=0) |
| evaluate_closure_output_item_remove | bpy.ops.node.evaluate_closure_output_item_remove(node_identifier=0) |
| field_to_grid_item_add | bpy.ops.node.field_to_grid_item_add(node_identifier=0, show_dialog=False, init_from_active=True, soc |
| field_to_grid_item_move | bpy.ops.node.field_to_grid_item_move(direction='UP', node_identifier=0) |
| field_to_grid_item_remove | bpy.ops.node.field_to_grid_item_remove(node_identifier=0) |
| field_to_list_item_add | bpy.ops.node.field_to_list_item_add(node_identifier=0, show_dialog=False, init_from_active=True, soc |
| field_to_list_item_move | bpy.ops.node.field_to_list_item_move(direction='UP', node_identifier=0) |
| field_to_list_item_remove | bpy.ops.node.field_to_list_item_remove(node_identifier=0) |
| file_output_item_add | bpy.ops.node.file_output_item_add(node_identifier=0, show_dialog=False, init_from_active=True, socke |
| file_output_item_move | bpy.ops.node.file_output_item_move(direction='UP', node_identifier=0) |
| file_output_item_remove | bpy.ops.node.file_output_item_remove(node_identifier=0) |
| find_node | bpy.ops.node.find_node() |
| foreach_geometry_element_zone_generation_item_add | bpy.ops.node.foreach_geometry_element_zone_generation_item_add(node_identifier=0, show_dialog=False, |
| foreach_geometry_element_zone_generation_item_move | bpy.ops.node.foreach_geometry_element_zone_generation_item_move(direction='UP', node_identifier=0) |
| foreach_geometry_element_zone_generation_item_remove | bpy.ops.node.foreach_geometry_element_zone_generation_item_remove(node_identifier=0) |
| foreach_geometry_element_zone_input_item_add | bpy.ops.node.foreach_geometry_element_zone_input_item_add(node_identifier=0, show_dialog=False, init |
| foreach_geometry_element_zone_input_item_move | bpy.ops.node.foreach_geometry_element_zone_input_item_move(direction='UP', node_identifier=0) |
| foreach_geometry_element_zone_input_item_remove | bpy.ops.node.foreach_geometry_element_zone_input_item_remove(node_identifier=0) |
| foreach_geometry_element_zone_main_item_add | bpy.ops.node.foreach_geometry_element_zone_main_item_add(node_identifier=0, show_dialog=False, init_ |
| foreach_geometry_element_zone_main_item_move | bpy.ops.node.foreach_geometry_element_zone_main_item_move(direction='UP', node_identifier=0) |
| foreach_geometry_element_zone_main_item_remove | bpy.ops.node.foreach_geometry_element_zone_main_item_remove(node_identifier=0) |
| format_string_item_add | bpy.ops.node.format_string_item_add(node_identifier=0, show_dialog=False, init_from_active=True, soc |
| format_string_item_move | bpy.ops.node.format_string_item_move(direction='UP', node_identifier=0) |
| format_string_item_remove | bpy.ops.node.format_string_item_remove(node_identifier=0) |
| geometry_nodes_viewer_item_add | bpy.ops.node.geometry_nodes_viewer_item_add(node_identifier=0, show_dialog=False, init_from_active=T |
| geometry_nodes_viewer_item_move | bpy.ops.node.geometry_nodes_viewer_item_move(direction='UP', node_identifier=0) |
| geometry_nodes_viewer_item_remove | bpy.ops.node.geometry_nodes_viewer_item_remove(node_identifier=0) |
| gltf_settings_node_operator | bpy.ops.node.gltf_settings_node_operator() |
| group_edit | bpy.ops.node.group_edit(exit=False) |
| group_enter_exit | bpy.ops.node.group_enter_exit() |
| group_insert | bpy.ops.node.group_insert() |
| group_make | bpy.ops.node.group_make() |
| group_separate | bpy.ops.node.group_separate(type='COPY') |
| group_ungroup | bpy.ops.node.group_ungroup() |
| hide_socket_toggle | bpy.ops.node.hide_socket_toggle() |
| hide_toggle | bpy.ops.node.hide_toggle() |
| index_switch_item_add | bpy.ops.node.index_switch_item_add(node_identifier=0, show_dialog=False, init_from_active=True) |
| index_switch_item_move | bpy.ops.node.index_switch_item_move(direction='UP', node_identifier=0) |
| index_switch_item_remove | bpy.ops.node.index_switch_item_remove(index=0) |
| insert_offset | bpy.ops.node.insert_offset() |
| interface_item_duplicate | bpy.ops.node.interface_item_duplicate() |
| interface_item_make_panel_toggle | bpy.ops.node.interface_item_make_panel_toggle() |
| interface_item_new | bpy.ops.node.interface_item_new(item_type='INPUT') |
| interface_item_new_panel_toggle | bpy.ops.node.interface_item_new_panel_toggle() |
| interface_item_remove | bpy.ops.node.interface_item_remove() |
| interface_item_unlink_panel_toggle | bpy.ops.node.interface_item_unlink_panel_toggle() |
| join | bpy.ops.node.join() |
| join_named | bpy.ops.node.join_named(NODE_OT_join={}, WM_OT_call_panel={"name":"", "keep_open":True}) |
| join_nodes | bpy.ops.node.join_nodes() |
| link | bpy.ops.node.link(detach=False, drag_start=(0, 0), inside_padding=2, outside_padding=0, speed_ramp=1 |
| link_drag_operation_test | bpy.ops.node.link_drag_operation_test(find_link_operations=False, link_operation_index=-1) |
| link_make | bpy.ops.node.link_make(replace=False) |
| link_viewer | bpy.ops.node.link_viewer() |
| links_cut | bpy.ops.node.links_cut(path=[], cursor=15) |
| links_detach | bpy.ops.node.links_detach() |
| links_mute | bpy.ops.node.links_mute(path=[], cursor=39) |
| move_detach_links | bpy.ops.node.move_detach_links(NODE_OT_links_detach={}, TRANSFORM_OT_translate={"value":(0, 0, 0), " |
| move_detach_links_release | bpy.ops.node.move_detach_links_release(NODE_OT_links_detach={}, NODE_OT_translate_attach={"TRANSFORM |
| mute_toggle | bpy.ops.node.mute_toggle() |
| new_compositing_node_group | bpy.ops.node.new_compositing_node_group(name="") |
| new_compositor_sequencer_node_group | bpy.ops.node.new_compositor_sequencer_node_group(name="Sequencer Compositor Nodes") |
| new_geometry_node_group_assign | bpy.ops.node.new_geometry_node_group_assign() |
| new_geometry_node_group_tool | bpy.ops.node.new_geometry_node_group_tool() |
| new_geometry_nodes_modifier | bpy.ops.node.new_geometry_nodes_modifier() |
| new_node_tree | bpy.ops.node.new_node_tree(type='GeometryNodeTree', name="NodeTree") |
| node_color_preset_add | bpy.ops.node.node_color_preset_add(name="", remove_name=False, remove_active=False) |
| node_copy_color | bpy.ops.node.node_copy_color() |
| options_toggle | bpy.ops.node.options_toggle() |
| parent_set | bpy.ops.node.parent_set() |
| preview_toggle | bpy.ops.node.preview_toggle() |
| read_viewlayers | bpy.ops.node.read_viewlayers() |
| render_changed | bpy.ops.node.render_changed() |
| repeat_zone_item_add | bpy.ops.node.repeat_zone_item_add(node_identifier=0, show_dialog=False, init_from_active=True, socke |
| repeat_zone_item_move | bpy.ops.node.repeat_zone_item_move(direction='UP', node_identifier=0) |
| repeat_zone_item_remove | bpy.ops.node.repeat_zone_item_remove(node_identifier=0) |
| resize | bpy.ops.node.resize() |
| sample_attribute_items_item_add | bpy.ops.node.sample_attribute_items_item_add(node_identifier=0, show_dialog=False, init_from_active= |
| sample_attribute_items_item_move | bpy.ops.node.sample_attribute_items_item_move(direction='UP', node_identifier=0) |
| sample_attribute_items_item_remove | bpy.ops.node.sample_attribute_items_item_remove(node_identifier=0) |
| select | bpy.ops.node.select(extend=False, deselect=False, toggle=False, deselect_all=False, select_passthrou |
| select_all | bpy.ops.node.select_all(action='TOGGLE') |
| select_box | bpy.ops.node.select_box(tweak=False, xmin=0, xmax=0, ymin=0, ymax=0, wait_for_input=True, mode='SET' |
| select_circle | bpy.ops.node.select_circle(x=0, y=0, radius=25, wait_for_input=True, mode='SET') |
| select_grouped | bpy.ops.node.select_grouped(extend=False, type='TYPE') |
| select_lasso | bpy.ops.node.select_lasso(tweak=False, path=[], use_smooth_stroke=False, smooth_stroke_factor=0.75,  |
| select_link_viewer | bpy.ops.node.select_link_viewer(NODE_OT_select={"extend":False, "deselect":False, "toggle":False, "d |
| select_linked_from | bpy.ops.node.select_linked_from() |
| select_linked_to | bpy.ops.node.select_linked_to() |
| select_same_type_step | bpy.ops.node.select_same_type_step(prev=False) |
| separate_bundle_item_add | bpy.ops.node.separate_bundle_item_add(node_identifier=0, show_dialog=False, init_from_active=True, s |
| separate_bundle_item_move | bpy.ops.node.separate_bundle_item_move(direction='UP', node_identifier=0) |
| separate_bundle_item_remove | bpy.ops.node.separate_bundle_item_remove(node_identifier=0) |
| shader_script_update | bpy.ops.node.shader_script_update() |
| simulation_zone_item_add | bpy.ops.node.simulation_zone_item_add(node_identifier=0, show_dialog=False, init_from_active=True, s |
| simulation_zone_item_move | bpy.ops.node.simulation_zone_item_move(direction='UP', node_identifier=0) |
| simulation_zone_item_remove | bpy.ops.node.simulation_zone_item_remove(node_identifier=0) |
| sockets_sync | bpy.ops.node.sockets_sync(node_name="") |
| swap_empty_group | bpy.ops.node.swap_empty_group(settings=[]) |
| swap_group_asset | bpy.ops.node.swap_group_asset(asset_library_type='LOCAL', asset_library_identifier="", relative_asse |
| swap_node | bpy.ops.node.swap_node(settings=[], type="", visible_output="") |
| swap_typed_bundle | bpy.ops.node.swap_typed_bundle(settings=[]) |
| swap_zone | bpy.ops.node.swap_zone(settings=[], offset=(150, 0), input_node_type="", output_node_type="", add_de |
| test_inlining_shader_nodes | bpy.ops.node.test_inlining_shader_nodes() |
| toggle_viewer | bpy.ops.node.toggle_viewer() |
| translate_attach | bpy.ops.node.translate_attach(TRANSFORM_OT_translate={"value":(0, 0, 0), "orient_type":'GLOBAL', "or |
| translate_attach_remove_on_cancel | bpy.ops.node.translate_attach_remove_on_cancel(TRANSFORM_OT_translate={"value":(0, 0, 0), "orient_ty |
| tree_path_parent | bpy.ops.node.tree_path_parent(parent_tree_index=0) |
| view_all | bpy.ops.node.view_all() |
| view_selected | bpy.ops.node.view_selected() |
| viewer_border | bpy.ops.node.viewer_border(xmin=0, xmax=0, ymin=0, ymax=0, wait_for_input=True) |
| viewer_shortcut_get | bpy.ops.node.viewer_shortcut_get(viewer_index=0) |
| viewer_shortcut_set | bpy.ops.node.viewer_shortcut_set(viewer_index=0) |

## render（16）

| 操作符 | 说明 |
|---|---|
| clear_texture_cache | bpy.ops.render.clear_texture_cache() |
| color_management_white_balance_preset_add | bpy.ops.render.color_management_white_balance_preset_add(name="", remove_name=False, remove_active=F |
| cycles_integrator_preset_add | bpy.ops.render.cycles_integrator_preset_add(name="", remove_name=False, remove_active=False) |
| cycles_performance_preset_add | bpy.ops.render.cycles_performance_preset_add(name="", remove_name=False, remove_active=False) |
| cycles_sampling_preset_add | bpy.ops.render.cycles_sampling_preset_add(name="", remove_name=False, remove_active=False) |
| cycles_viewport_sampling_preset_add | bpy.ops.render.cycles_viewport_sampling_preset_add(name="", remove_name=False, remove_active=False) |
| eevee_raytracing_preset_add | bpy.ops.render.eevee_raytracing_preset_add(name="", remove_name=False, remove_active=False) |
| generate_texture_cache | bpy.ops.render.generate_texture_cache(generate_sequences=True) |
| opengl | bpy.ops.render.opengl(animation=False, render_keyed_only=False, sequencer=False, write_still=False,  |
| play_rendered_anim | bpy.ops.render.play_rendered_anim() |
| preset_add | bpy.ops.render.preset_add(name="", remove_name=False, remove_active=False) |
| render | bpy.ops.render.render(animation=False, write_still=False, use_viewport=False, use_sequencer_scene=Fa |
| shutter_curve_preset | bpy.ops.render.shutter_curve_preset(shape='SMOOTH') |
| swap_dimensions | bpy.ops.render.swap_dimensions() |
| view_cancel | bpy.ops.render.view_cancel() |
| view_show | bpy.ops.render.view_show() |

## export_scene（2）

| 操作符 | 说明 |
|---|---|
| fbx | bpy.ops.export_scene.fbx(filepath="", check_existing=True, filter_glob="*.fbx", use_selection=False, |
| gltf | bpy.ops.export_scene.gltf(filepath="", check_existing=True, export_import_convert_lighting_mode='SPE |

## import_scene（2）

| 操作符 | 说明 |
|---|---|
| fbx | bpy.ops.import_scene.fbx(filepath="", directory="", filter_glob="*.fbx", files=[], ui_tab='MAIN', us |
| gltf | bpy.ops.import_scene.gltf(filepath="", export_import_convert_lighting_mode='SPEC', filter_glob="*.gl |

## curve（51）

| 操作符 | 说明 |
|---|---|
| cyclic_toggle | bpy.ops.curve.cyclic_toggle(direction='CYCLIC_U') |
| de_select_first | bpy.ops.curve.de_select_first() |
| de_select_last | bpy.ops.curve.de_select_last() |
| decimate | bpy.ops.curve.decimate(ratio=1) |
| delete | bpy.ops.curve.delete(type='VERT') |
| dissolve_verts | bpy.ops.curve.dissolve_verts() |
| draw | bpy.ops.curve.draw(error_threshold=0, fit_method='REFIT', corner_angle=1.22173, use_cyclic=True, str |
| duplicate | bpy.ops.curve.duplicate() |
| duplicate_move | bpy.ops.curve.duplicate_move(CURVE_OT_duplicate={}, TRANSFORM_OT_translate={"value":(0, 0, 0), "orie |
| extrude | bpy.ops.curve.extrude(mode='TRANSLATION') |
| extrude_move | bpy.ops.curve.extrude_move(CURVE_OT_extrude={"mode":'TRANSLATION'}, TRANSFORM_OT_translate={"value": |
| handle_type_set | bpy.ops.curve.handle_type_set(type='AUTOMATIC') |
| hide | bpy.ops.curve.hide(unselected=False) |
| make_segment | bpy.ops.curve.make_segment() |
| match_texture_space | bpy.ops.curve.match_texture_space() |
| normals_make_consistent | bpy.ops.curve.normals_make_consistent(calc_length=False) |
| pen | bpy.ops.curve.pen(extend=False, deselect=False, toggle=False, deselect_all=False, select_passthrough |
| primitive_bezier_circle_add | bpy.ops.curve.primitive_bezier_circle_add(radius=1, enter_editmode=False, align='WORLD', location=(0 |
| primitive_bezier_curve_add | bpy.ops.curve.primitive_bezier_curve_add(radius=1, enter_editmode=False, align='WORLD', location=(0, |
| primitive_nurbs_circle_add | bpy.ops.curve.primitive_nurbs_circle_add(radius=1, enter_editmode=False, align='WORLD', location=(0, |
| primitive_nurbs_curve_add | bpy.ops.curve.primitive_nurbs_curve_add(radius=1, enter_editmode=False, align='WORLD', location=(0,  |
| primitive_nurbs_path_add | bpy.ops.curve.primitive_nurbs_path_add(radius=1, enter_editmode=False, align='WORLD', location=(0, 0 |
| radius_set | bpy.ops.curve.radius_set(radius=1) |
| reveal | bpy.ops.curve.reveal(select=True) |
| select_all | bpy.ops.curve.select_all(action='TOGGLE') |
| select_less | bpy.ops.curve.select_less() |
| select_linked | bpy.ops.curve.select_linked() |
| select_linked_pick | bpy.ops.curve.select_linked_pick(deselect=False) |
| select_more | bpy.ops.curve.select_more() |
| select_next | bpy.ops.curve.select_next() |
| select_nth | bpy.ops.curve.select_nth(skip=1, nth=1, offset=0) |
| select_previous | bpy.ops.curve.select_previous() |
| select_random | bpy.ops.curve.select_random(ratio=0.5, seed=0, action='SELECT') |
| select_row | bpy.ops.curve.select_row() |
| select_similar | bpy.ops.curve.select_similar(type='WEIGHT', compare='EQUAL', threshold=0.1) |
| separate | bpy.ops.curve.separate() |
| shade_flat | bpy.ops.curve.shade_flat() |
| shade_smooth | bpy.ops.curve.shade_smooth() |
| shortest_path_pick | bpy.ops.curve.shortest_path_pick() |
| smooth | bpy.ops.curve.smooth() |
| smooth_radius | bpy.ops.curve.smooth_radius() |
| smooth_tilt | bpy.ops.curve.smooth_tilt() |
| smooth_weight | bpy.ops.curve.smooth_weight() |
| spin | bpy.ops.curve.spin(center=(0, 0, 0), axis=(0, 0, 0)) |
| spline_type_set | bpy.ops.curve.spline_type_set(type='POLY', use_handles=False) |
| spline_weight_set | bpy.ops.curve.spline_weight_set(weight=1) |
| split | bpy.ops.curve.split() |
| subdivide | bpy.ops.curve.subdivide(number_cuts=1) |
| switch_direction | bpy.ops.curve.switch_direction() |
| tilt_clear | bpy.ops.curve.tilt_clear() |
| vertex_add | bpy.ops.curve.vertex_add(location=(0, 0, 0)) |

## armature（49）

| 操作符 | 说明 |
|---|---|
| align | bpy.ops.armature.align() |
| assign_to_collection | bpy.ops.armature.assign_to_collection(collection_index=-1, new_collection_name="") |
| autoside_names | bpy.ops.armature.autoside_names(type='XAXIS') |
| bone_primitive_add | bpy.ops.armature.bone_primitive_add(name="Bone", space='OBJECT', align='UP', length=1, use_deform=Tr |
| calculate_roll | bpy.ops.armature.calculate_roll(type='POS_X', axis_flip=False, axis_only=False) |
| click_extrude | bpy.ops.armature.click_extrude() |
| collection_add | bpy.ops.armature.collection_add() |
| collection_assign | bpy.ops.armature.collection_assign(name="") |
| collection_create_and_assign | bpy.ops.armature.collection_create_and_assign(name="") |
| collection_deselect | bpy.ops.armature.collection_deselect() |
| collection_move | bpy.ops.armature.collection_move(direction='UP') |
| collection_remove | bpy.ops.armature.collection_remove() |
| collection_remove_unused | bpy.ops.armature.collection_remove_unused() |
| collection_select | bpy.ops.armature.collection_select() |
| collection_show_all | bpy.ops.armature.collection_show_all() |
| collection_unassign | bpy.ops.armature.collection_unassign(name="") |
| collection_unassign_named | bpy.ops.armature.collection_unassign_named(name="", bone_name="") |
| collection_unsolo_all | bpy.ops.armature.collection_unsolo_all() |
| copy_bone_color_to_selected | bpy.ops.armature.copy_bone_color_to_selected(bone_type='EDIT') |
| delete | bpy.ops.armature.delete(confirm=True) |
| dissolve | bpy.ops.armature.dissolve() |
| duplicate | bpy.ops.armature.duplicate(do_flip_names=False) |
| duplicate_move | bpy.ops.armature.duplicate_move(ARMATURE_OT_duplicate={"do_flip_names":False}, TRANSFORM_OT_translat |
| duplicate_rename | bpy.ops.armature.duplicate_rename(do_flip_names=False, search="", replace="") |
| extrude | bpy.ops.armature.extrude(forked=False) |
| extrude_forked | bpy.ops.armature.extrude_forked(ARMATURE_OT_extrude={"forked":False}, TRANSFORM_OT_translate={"value |
| extrude_move | bpy.ops.armature.extrude_move(ARMATURE_OT_extrude={"forked":False}, TRANSFORM_OT_translate={"value": |
| fill | bpy.ops.armature.fill() |
| flip_names | bpy.ops.armature.flip_names(do_strip_numbers=False) |
| hide | bpy.ops.armature.hide(unselected=False) |
| move_to_collection | bpy.ops.armature.move_to_collection(collection_index=-1, new_collection_name="") |
| parent_clear | bpy.ops.armature.parent_clear(type='CLEAR') |
| parent_set | bpy.ops.armature.parent_set(type='CONNECTED') |
| reveal | bpy.ops.armature.reveal(select=True) |
| roll_clear | bpy.ops.armature.roll_clear(roll=0) |
| select_all | bpy.ops.armature.select_all(action='TOGGLE') |
| select_hierarchy | bpy.ops.armature.select_hierarchy(direction='PARENT', extend=False) |
| select_less | bpy.ops.armature.select_less() |
| select_linked | bpy.ops.armature.select_linked(all_forks=False) |
| select_linked_pick | bpy.ops.armature.select_linked_pick(deselect=False, all_forks=False) |
| select_mirror | bpy.ops.armature.select_mirror(only_active=False, extend=False) |
| select_more | bpy.ops.armature.select_more() |
| select_similar | bpy.ops.armature.select_similar(type='LENGTH', threshold=0.1) |
| separate | bpy.ops.armature.separate() |
| shortest_path_pick | bpy.ops.armature.shortest_path_pick() |
| split | bpy.ops.armature.split() |
| subdivide | bpy.ops.armature.subdivide(number_cuts=1) |
| switch_direction | bpy.ops.armature.switch_direction() |
| symmetrize | bpy.ops.armature.symmetrize(direction='NEGATIVE_X', copy_bone_colors=False) |

## pose（51）

| 操作符 | 说明 |
|---|---|
| armature_apply | bpy.ops.pose.armature_apply(selected=False) |
| autoside_names | bpy.ops.pose.autoside_names(axis='XAXIS') |
| blend_to_neighbor | bpy.ops.pose.blend_to_neighbor(factor=0.5, prev_frame=0, next_frame=0, channels='ALL', axis_lock='FR |
| blend_with_rest | bpy.ops.pose.blend_with_rest(factor=0.5, prev_frame=0, next_frame=0, channels='ALL', axis_lock='FREE |
| breakdown | bpy.ops.pose.breakdown(factor=0.5, prev_frame=0, next_frame=0, channels='ALL', axis_lock='FREE') |
| constraint_add | bpy.ops.pose.constraint_add(type='CHILD_OF') |
| constraint_add_with_targets | bpy.ops.pose.constraint_add_with_targets(type='CHILD_OF') |
| constraints_clear | bpy.ops.pose.constraints_clear() |
| constraints_copy | bpy.ops.pose.constraints_copy() |
| copy | bpy.ops.pose.copy() |
| flip_names | bpy.ops.pose.flip_names(do_strip_numbers=False) |
| hide | bpy.ops.pose.hide(unselected=False) |
| ik_add | bpy.ops.pose.ik_add(with_targets=True) |
| ik_clear | bpy.ops.pose.ik_clear() |
| loc_clear | bpy.ops.pose.loc_clear() |
| paste | bpy.ops.pose.paste(flipped=False, selected_mask=False) |
| paths_calculate | bpy.ops.pose.paths_calculate(display_type='RANGE', range='SCENE', bake_location='HEADS') |
| paths_clear | bpy.ops.pose.paths_clear(only_selected=False) |
| paths_range_update | bpy.ops.pose.paths_range_update() |
| paths_update | bpy.ops.pose.paths_update() |
| propagate | bpy.ops.pose.propagate(mode='NEXT_KEY', end_frame=250) |
| push | bpy.ops.pose.push(factor=0.5, prev_frame=0, next_frame=0, channels='ALL', axis_lock='FREE') |
| quaternions_flip | bpy.ops.pose.quaternions_flip() |
| relax | bpy.ops.pose.relax(factor=0.5, prev_frame=0, next_frame=0, channels='ALL', axis_lock='FREE') |
| reveal | bpy.ops.pose.reveal(select=True) |
| rot_clear | bpy.ops.pose.rot_clear() |
| rotation_mode_set | bpy.ops.pose.rotation_mode_set(type='QUATERNION') |
| scale_clear | bpy.ops.pose.scale_clear() |
| select_all | bpy.ops.pose.select_all(action='TOGGLE') |
| select_constraint_target | bpy.ops.pose.select_constraint_target() |
| select_grouped | bpy.ops.pose.select_grouped(extend=False, type='COLLECTION') |
| select_hierarchy | bpy.ops.pose.select_hierarchy(direction='PARENT', extend=False) |
| select_linked | bpy.ops.pose.select_linked() |
| select_linked_pick | bpy.ops.pose.select_linked_pick(extend=False) |
| select_mirror | bpy.ops.pose.select_mirror(only_active=False, extend=False) |
| select_parent | bpy.ops.pose.select_parent() |
| selection_set_add | bpy.ops.pose.selection_set_add() |
| selection_set_add_and_assign | bpy.ops.pose.selection_set_add_and_assign() |
| selection_set_assign | bpy.ops.pose.selection_set_assign() |
| selection_set_copy | bpy.ops.pose.selection_set_copy() |
| selection_set_delete_all | bpy.ops.pose.selection_set_delete_all() |
| selection_set_deselect | bpy.ops.pose.selection_set_deselect() |
| selection_set_move | bpy.ops.pose.selection_set_move(direction='UP') |
| selection_set_paste | bpy.ops.pose.selection_set_paste() |
| selection_set_remove | bpy.ops.pose.selection_set_remove() |
| selection_set_remove_bones | bpy.ops.pose.selection_set_remove_bones() |
| selection_set_select | bpy.ops.pose.selection_set_select(selection_set_index=-1) |
| selection_set_unassign | bpy.ops.pose.selection_set_unassign() |
| transforms_clear | bpy.ops.pose.transforms_clear() |
| user_transforms_clear | bpy.ops.pose.user_transforms_clear(only_selected=True) |
| visual_transform_apply | bpy.ops.pose.visual_transform_apply() |

## sculpt（39） ⚠

| 操作符 | 说明 |
|---|---|
| brush_stroke | bpy.ops.sculpt.brush_stroke(stroke=[], mode='NORMAL', brush_toggle='None', pen_flip=False, override_ |
| cloth_filter | bpy.ops.sculpt.cloth_filter(start_mouse=(0, 0), area_normal_radius=0.25, strength=1, iteration_count |
| color_filter | bpy.ops.sculpt.color_filter(start_mouse=(0, 0), area_normal_radius=0.25, strength=1, iteration_count |
| detail_flood_fill | bpy.ops.sculpt.detail_flood_fill() |
| dynamic_topology_toggle | bpy.ops.sculpt.dynamic_topology_toggle() |
| dyntopo_detail_size_edit | bpy.ops.sculpt.dyntopo_detail_size_edit() |
| expand | bpy.ops.sculpt.expand(target='MASK', falloff_type='GEODESIC', invert=False, use_mask_preserve=False, |
| face_set_box_gesture | bpy.ops.sculpt.face_set_box_gesture(xmin=0, xmax=0, ymin=0, ymax=0, wait_for_input=True, use_front_f |
| face_set_change_visibility | bpy.ops.sculpt.face_set_change_visibility(mode='TOGGLE', active_face_set=0) |
| face_set_edit | bpy.ops.sculpt.face_set_edit(active_face_set=1, mode='GROW', strength=1, modify_hidden=False) |
| face_set_extract | bpy.ops.sculpt.face_set_extract(add_boundary_loop=True, smooth_iterations=4, apply_shrinkwrap=True,  |
| face_set_lasso_gesture | bpy.ops.sculpt.face_set_lasso_gesture(path=[], use_smooth_stroke=False, smooth_stroke_factor=0.75, s |
| face_set_line_gesture | bpy.ops.sculpt.face_set_line_gesture(xstart=0, xend=0, ystart=0, yend=0, flip=False, cursor=5, use_f |
| face_set_polyline_gesture | bpy.ops.sculpt.face_set_polyline_gesture(path=[], use_front_faces_only=False) |
| face_sets_create | bpy.ops.sculpt.face_sets_create(mode='MASKED') |
| face_sets_init | bpy.ops.sculpt.face_sets_init(mode='LOOSE_PARTS', threshold=0.5) |
| face_sets_randomize_colors | bpy.ops.sculpt.face_sets_randomize_colors() |
| mask_by_color | bpy.ops.sculpt.mask_by_color(contiguous=False, invert=False, preserve_previous_mask=False, threshold |
| mask_filter | bpy.ops.sculpt.mask_filter(filter_type='SMOOTH', iterations=1, auto_iteration_count=True) |
| mask_from_boundary | bpy.ops.sculpt.mask_from_boundary(mix_mode='MIX', mix_factor=1, settings_source='OPERATOR', boundary |
| mask_from_cavity | bpy.ops.sculpt.mask_from_cavity(mix_mode='MIX', mix_factor=1, settings_source='OPERATOR', factor=0.5 |
| mask_init | bpy.ops.sculpt.mask_init(mode='RANDOM_PER_VERTEX') |
| mesh_filter | bpy.ops.sculpt.mesh_filter(start_mouse=(0, 0), area_normal_radius=0.25, strength=1, iteration_count= |
| optimize | bpy.ops.sculpt.optimize() |
| paint_mask_extract | bpy.ops.sculpt.paint_mask_extract(mask_threshold=0.5, add_boundary_loop=True, smooth_iterations=4, a |
| paint_mask_slice | bpy.ops.sculpt.paint_mask_slice(mask_threshold=0.5, fill_holes=True, new_object=True) |
| project_line_gesture | bpy.ops.sculpt.project_line_gesture(xstart=0, xend=0, ystart=0, yend=0, flip=False, cursor=5, use_fr |
| sample_detail_size | bpy.ops.sculpt.sample_detail_size(location=(0, 0), mode='DYNTOPO') |
| sculptmode_toggle | bpy.ops.sculpt.sculptmode_toggle() |
| set_persistent_base | bpy.ops.sculpt.set_persistent_base() |
| set_pivot_position | bpy.ops.sculpt.set_pivot_position(mode='UNMASKED', mouse_x=0, mouse_y=0) |
| symmetrize | bpy.ops.sculpt.symmetrize(merge_tolerance=0.0005) |
| trim_box_gesture | bpy.ops.sculpt.trim_box_gesture(xmin=0, xmax=0, ymin=0, ymax=0, wait_for_input=True, use_front_faces |
| trim_lasso_gesture | bpy.ops.sculpt.trim_lasso_gesture(path=[], use_smooth_stroke=False, smooth_stroke_factor=0.75, smoot |
| trim_line_gesture | bpy.ops.sculpt.trim_line_gesture(xstart=0, xend=0, ystart=0, yend=0, flip=False, cursor=5, use_front |
| trim_polyline_gesture | bpy.ops.sculpt.trim_polyline_gesture(path=[], use_front_faces_only=False, location=(0, 0), trim_mode |
| uv_sculpt_grab | bpy.ops.sculpt.uv_sculpt_grab(use_invert=False) |
| uv_sculpt_pinch | bpy.ops.sculpt.uv_sculpt_pinch(use_invert=False) |
| uv_sculpt_relax | bpy.ops.sculpt.uv_sculpt_relax(use_invert=False, relax_method='LAPLACIAN') |

## uv（55）

| 操作符 | 说明 |
|---|---|
| align | bpy.ops.uv.align(axis='ALIGN_AUTO', position_mode='MEAN') |
| align_rotation | bpy.ops.uv.align_rotation(method='AUTO', axis='X', correct_aspect=False) |
| arrange_islands | bpy.ops.uv.arrange_islands(initial_position='BOUNDING_BOX', axis='Y', align='MIN', order='LARGE_TO_S |
| average_islands_scale | bpy.ops.uv.average_islands_scale(scale_uv=False, shear=False) |
| copy | bpy.ops.uv.copy() |
| copy_mirrored_faces | bpy.ops.uv.copy_mirrored_faces(mesh_axis='POS_X', uv_axis='X', precision=3) |
| cube_project | bpy.ops.uv.cube_project(cube_size=1, correct_aspect=True, clip_to_bounds=False, scale_to_bounds=Fals |
| cursor_set | bpy.ops.uv.cursor_set(location=(0, 0)) |
| custom_region_set | bpy.ops.uv.custom_region_set(xmin=0, xmax=0, ymin=0, ymax=0, wait_for_input=True) |
| cylinder_project | bpy.ops.uv.cylinder_project(direction='VIEW_ON_EQUATOR', align='POLAR_ZX', pole='PINCH', seam=False, |
| export_layout | bpy.ops.uv.export_layout(filepath="", export_all=False, export_tiles='NONE', modified=False, mode='P |
| follow_active_quads | bpy.ops.uv.follow_active_quads(mode='LENGTH_AVERAGE') |
| hide | bpy.ops.uv.hide(unselected=False) |
| lightmap_pack | bpy.ops.uv.lightmap_pack(PREF_CONTEXT='SEL_FACES', PREF_PACK_IN_ONE=True, PREF_NEW_UVLAYER=False, PR |
| mark_seam | bpy.ops.uv.mark_seam(clear=False) |
| minimize_stretch | bpy.ops.uv.minimize_stretch(fill_holes=True, blend=0, iterations=0) |
| move_on_axis | bpy.ops.uv.move_on_axis(type='UDIM', axis='X', distance=1) |
| pack_islands | bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=True, rotate_method='ANY', scale=True, me |
| paste | bpy.ops.uv.paste() |
| pin | bpy.ops.uv.pin(clear=False, invert=False) |
| project_from_view | bpy.ops.uv.project_from_view(orthographic=False, camera_bounds=True, correct_aspect=True, clip_to_bo |
| randomize_uv_transform | bpy.ops.uv.randomize_uv_transform(random_seed=0, use_loc=True, loc=(0, 0), use_rot=True, rot=0, use_ |
| remove_doubles | bpy.ops.uv.remove_doubles(threshold=0.02, use_unselected=False, use_shared_vertex=False) |
| reset | bpy.ops.uv.reset() |
| reveal | bpy.ops.uv.reveal(select=True) |
| rip | bpy.ops.uv.rip(mirror=False, release_confirm=False, use_accurate=False, location=(0, 0)) |
| rip_move | bpy.ops.uv.rip_move(UV_OT_rip={"mirror":False, "release_confirm":False, "use_accurate":False, "locat |
| seams_from_islands | bpy.ops.uv.seams_from_islands(mark_seams=True, mark_sharp=False) |
| select | bpy.ops.uv.select(extend=False, deselect=False, toggle=False, deselect_all=False, select_passthrough |
| select_all | bpy.ops.uv.select_all(action='TOGGLE') |
| select_box | bpy.ops.uv.select_box(pinned=False, xmin=0, xmax=0, ymin=0, ymax=0, wait_for_input=True, mode='SET') |
| select_by_winding | bpy.ops.uv.select_by_winding(winding='NEGATIVE', extend=False) |
| select_circle | bpy.ops.uv.select_circle(x=0, y=0, radius=25, wait_for_input=True, mode='SET') |
| select_edge_ring | bpy.ops.uv.select_edge_ring(extend=False, location=(0, 0)) |
| select_lasso | bpy.ops.uv.select_lasso(path=[], use_smooth_stroke=False, smooth_stroke_factor=0.75, smooth_stroke_r |
| select_less | bpy.ops.uv.select_less() |
| select_linked | bpy.ops.uv.select_linked(delimit=set()) |
| select_linked_pick | bpy.ops.uv.select_linked_pick(extend=False, deselect=False, delimit=set(), location=(0, 0)) |
| select_loop | bpy.ops.uv.select_loop(extend=False, location=(0, 0)) |
| select_mode | bpy.ops.uv.select_mode(type='VERTEX') |
| select_more | bpy.ops.uv.select_more() |
| select_overlap | bpy.ops.uv.select_overlap(extend=False) |
| select_pinned | bpy.ops.uv.select_pinned() |
| select_similar | bpy.ops.uv.select_similar(type='PIN', compare='EQUAL', threshold=0) |
| select_split | bpy.ops.uv.select_split() |
| select_tile | bpy.ops.uv.select_tile(extend=False, tile=(0, 0)) |
| shortest_path_pick | bpy.ops.uv.shortest_path_pick(use_face_step=False, use_topology_distance=False, use_fill=False, skip |
| shortest_path_select | bpy.ops.uv.shortest_path_select(use_face_step=False, use_topology_distance=False, use_fill=False, sk |
| smart_project | bpy.ops.uv.smart_project(angle_limit=1.15192, margin_method='SCALED', rotate_method='AXIS_ALIGNED_Y' |
| snap_cursor | bpy.ops.uv.snap_cursor(target='PIXELS') |
| snap_selected | bpy.ops.uv.snap_selected(target='PIXELS') |
| sphere_project | bpy.ops.uv.sphere_project(direction='VIEW_ON_EQUATOR', align='POLAR_ZX', pole='PINCH', seam=False, c |
| stitch | bpy.ops.uv.stitch(use_limit=False, snap_islands=True, limit=0.01, static_island=0, active_object_ind |
| unwrap | bpy.ops.uv.unwrap(method='CONFORMAL', fill_holes=False, correct_aspect=True, use_subsurf_data=False, |
| weld | bpy.ops.uv.weld() |

## view3d（68） ⚠

| 操作符 | 说明 |
|---|---|
| bone_select_menu | bpy.ops.view3d.bone_select_menu(name='<UNKNOWN ENUM>', extend=False, deselect=False, toggle=False) |
| camera_background_image_add | bpy.ops.view3d.camera_background_image_add(filepath="", relative_path=True, name="", session_uid=0) |
| camera_background_image_remove | bpy.ops.view3d.camera_background_image_remove(index=0) |
| camera_to_view | bpy.ops.view3d.camera_to_view() |
| camera_to_view_selected | bpy.ops.view3d.camera_to_view_selected() |
| clear_render_border | bpy.ops.view3d.clear_render_border() |
| clip_border | bpy.ops.view3d.clip_border(xmin=0, xmax=0, ymin=0, ymax=0, wait_for_input=True) |
| copybuffer | bpy.ops.view3d.copybuffer() |
| cursor3d | bpy.ops.view3d.cursor3d(use_depth=True, orientation='VIEW') |
| dolly | bpy.ops.view3d.dolly(mx=0, my=0, delta=0, use_cursor_init=True) |
| drop_world | bpy.ops.view3d.drop_world(name="", session_uid=0) |
| edit_mesh_extrude_individual_move | bpy.ops.view3d.edit_mesh_extrude_individual_move() |
| edit_mesh_extrude_manifold_normal | bpy.ops.view3d.edit_mesh_extrude_manifold_normal() |
| edit_mesh_extrude_move_normal | bpy.ops.view3d.edit_mesh_extrude_move_normal(dissolve_and_intersect=False) |
| edit_mesh_extrude_move_shrink_fatten | bpy.ops.view3d.edit_mesh_extrude_move_shrink_fatten() |
| fly | bpy.ops.view3d.fly() |
| interactive_add | bpy.ops.view3d.interactive_add(primitive_type='CUBE', plane_origin_base='EDGE', plane_origin_depth=' |
| localview | bpy.ops.view3d.localview(frame_selected=True) |
| localview_remove_from | bpy.ops.view3d.localview_remove_from() |
| move | bpy.ops.view3d.move(use_cursor_init=True) |
| navigate | bpy.ops.view3d.navigate() |
| ndof_all | bpy.ops.view3d.ndof_all() |
| ndof_orbit | bpy.ops.view3d.ndof_orbit() |
| ndof_orbit_zoom | bpy.ops.view3d.ndof_orbit_zoom() |
| ndof_pan | bpy.ops.view3d.ndof_pan() |
| object_as_camera | bpy.ops.view3d.object_as_camera() |
| object_mode_pie_or_toggle | bpy.ops.view3d.object_mode_pie_or_toggle() |
| pastebuffer | bpy.ops.view3d.pastebuffer(autoselect=True, active_collection=True) |
| render_border | bpy.ops.view3d.render_border(xmin=0, xmax=0, ymin=0, ymax=0, wait_for_input=True) |
| rotate | bpy.ops.view3d.rotate(use_cursor_init=True) |
| ruler_add | bpy.ops.view3d.ruler_add() |
| ruler_remove | bpy.ops.view3d.ruler_remove() |
| select | bpy.ops.view3d.select(extend=False, deselect=False, toggle=False, deselect_all=False, select_passthr |
| select_box | bpy.ops.view3d.select_box(xmin=0, xmax=0, ymin=0, ymax=0, wait_for_input=True, mode='SET') |
| select_circle | bpy.ops.view3d.select_circle(x=0, y=0, radius=25, wait_for_input=True, mode='SET') |
| select_lasso | bpy.ops.view3d.select_lasso(path=[], use_smooth_stroke=False, smooth_stroke_factor=0.75, smooth_stro |
| select_menu | bpy.ops.view3d.select_menu(name='<UNKNOWN ENUM>', extend=False, deselect=False, toggle=False) |
| smoothview | bpy.ops.view3d.smoothview() |
| snap_cursor_to_active | bpy.ops.view3d.snap_cursor_to_active() |
| snap_cursor_to_center | bpy.ops.view3d.snap_cursor_to_center() |
| snap_cursor_to_grid | bpy.ops.view3d.snap_cursor_to_grid() |
| snap_cursor_to_selected | bpy.ops.view3d.snap_cursor_to_selected() |
| snap_selected_to_active | bpy.ops.view3d.snap_selected_to_active() |
| snap_selected_to_cursor | bpy.ops.view3d.snap_selected_to_cursor(use_offset=True, use_rotation=False) |
| snap_selected_to_grid | bpy.ops.view3d.snap_selected_to_grid() |
| toggle_matcap_flip | bpy.ops.view3d.toggle_matcap_flip() |
| toggle_shading | bpy.ops.view3d.toggle_shading(type='WIREFRAME') |
| toggle_xray | bpy.ops.view3d.toggle_xray() |
| transform_gizmo_set | bpy.ops.view3d.transform_gizmo_set(extend=False, type=set()) |
| view_all | bpy.ops.view3d.view_all(use_all_regions=False, center=False) |
| view_axis | bpy.ops.view3d.view_axis(type='LEFT', align_active=False, relative=False) |
| view_camera | bpy.ops.view3d.view_camera() |
| view_center_camera | bpy.ops.view3d.view_center_camera() |
| view_center_cursor | bpy.ops.view3d.view_center_cursor() |
| view_center_lock | bpy.ops.view3d.view_center_lock() |
| view_center_pick | bpy.ops.view3d.view_center_pick() |
| view_lock_clear | bpy.ops.view3d.view_lock_clear() |
| view_lock_to_active | bpy.ops.view3d.view_lock_to_active() |
| view_orbit | bpy.ops.view3d.view_orbit(angle=0, type='ORBITLEFT') |
| view_pan | bpy.ops.view3d.view_pan(type='PANLEFT') |
| view_persportho | bpy.ops.view3d.view_persportho() |
| view_roll | bpy.ops.view3d.view_roll(angle=0, type='ANGLE') |
| view_selected | bpy.ops.view3d.view_selected(use_all_regions=False) |
| vr_location_scouting_capture_review | bpy.ops.view3d.vr_location_scouting_capture_review() |
| walk | bpy.ops.view3d.walk() |
| zoom | bpy.ops.view3d.zoom(mx=0, my=0, delta=0, use_cursor_init=True) |
| zoom_border | bpy.ops.view3d.zoom_border(xmin=0, xmax=0, ymin=0, ymax=0, wait_for_input=True, zoom_out=False) |
| zoom_camera_1_to_1 | bpy.ops.view3d.zoom_camera_1_to_1() |

## wm（118）

| 操作符 | 说明 |
|---|---|
| alembic_export | bpy.ops.wm.alembic_export(filepath="", check_existing=True, filter_blender=False, filter_backup=Fals |
| alembic_import | bpy.ops.wm.alembic_import(filepath="", directory="", files=[], check_existing=False, filter_blender= |
| append | bpy.ops.wm.append(filepath="", directory="", filename="", files=[], check_existing=False, filter_ble |
| batch_rename | bpy.ops.wm.batch_rename(data_type='OBJECT', data_source='SELECT', actions=[]) |
| blend_strings_utf8_validate | bpy.ops.wm.blend_strings_utf8_validate() |
| call_asset_shelf_popover | bpy.ops.wm.call_asset_shelf_popover(name="") |
| call_menu | bpy.ops.wm.call_menu(name="") |
| call_menu_pie | bpy.ops.wm.call_menu_pie(name="") |
| call_panel | bpy.ops.wm.call_panel(name="", keep_open=True) |
| clear_recent_files | bpy.ops.wm.clear_recent_files(remove='ALL') |
| collection_export_all | bpy.ops.wm.collection_export_all() |
| console_toggle | bpy.ops.wm.console_toggle() |
| context_collection_boolean_set | bpy.ops.wm.context_collection_boolean_set(data_path_iter="", data_path_item="", type='TOGGLE') |
| context_cycle_array | bpy.ops.wm.context_cycle_array(data_path="", reverse=False) |
| context_cycle_enum | bpy.ops.wm.context_cycle_enum(data_path="", reverse=False, wrap=False) |
| context_cycle_int | bpy.ops.wm.context_cycle_int(data_path="", reverse=False, wrap=False) |
| context_menu_enum | bpy.ops.wm.context_menu_enum(data_path="") |
| context_modal_mouse | bpy.ops.wm.context_modal_mouse(data_path_iter="", data_path_item="", header_text="", input_scale=0.0 |
| context_pie_enum | bpy.ops.wm.context_pie_enum(data_path="") |
| context_scale_float | bpy.ops.wm.context_scale_float(data_path="", value=1) |
| context_scale_int | bpy.ops.wm.context_scale_int(data_path="", value=1, always_step=True) |
| context_set_boolean | bpy.ops.wm.context_set_boolean(data_path="", value=True) |
| context_set_enum | bpy.ops.wm.context_set_enum(data_path="", value="") |
| context_set_float | bpy.ops.wm.context_set_float(data_path="", value=0, relative=False) |
| context_set_id | bpy.ops.wm.context_set_id(data_path="", value="") |
| context_set_int | bpy.ops.wm.context_set_int(data_path="", value=0, relative=False) |
| context_set_string | bpy.ops.wm.context_set_string(data_path="", value="") |
| context_set_value | bpy.ops.wm.context_set_value(data_path="", value="") |
| context_toggle | bpy.ops.wm.context_toggle(data_path="", module="") |
| context_toggle_enum | bpy.ops.wm.context_toggle_enum(data_path="", value_1="", value_2="") |
| debug_menu | bpy.ops.wm.debug_menu(debug_value=0) |
| doc_view | bpy.ops.wm.doc_view(doc_id="") |
| doc_view_manual | bpy.ops.wm.doc_view_manual(doc_id="") |
| doc_view_manual_ui_context | bpy.ops.wm.doc_view_manual_ui_context() |
| drop_blend_file | bpy.ops.wm.drop_blend_file(filepath="", use_scripts=False) |
| drop_import_file | bpy.ops.wm.drop_import_file(directory="", files=[]) |
| fbx_import | bpy.ops.wm.fbx_import(filepath="", directory="", files=[], check_existing=False, filter_blender=Fals |
| grease_pencil_export_pdf | bpy.ops.wm.grease_pencil_export_pdf(filepath="", check_existing=True, filter_blender=False, filter_b |
| grease_pencil_export_svg | bpy.ops.wm.grease_pencil_export_svg(filepath="", check_existing=True, filter_blender=False, filter_b |
| grease_pencil_import_svg | bpy.ops.wm.grease_pencil_import_svg(filepath="", directory="", files=[], check_existing=False, filte |
| id_linked_relocate | bpy.ops.wm.id_linked_relocate(id_session_uid=0, filepath="", directory="", filename="", check_existi |
| interface_theme_preset_add | bpy.ops.wm.interface_theme_preset_add(name="", remove_name=False, remove_active=False) |
| interface_theme_preset_remove | bpy.ops.wm.interface_theme_preset_remove(name="", remove_name=False, remove_active=True) |
| interface_theme_preset_save | bpy.ops.wm.interface_theme_preset_save(name="", remove_name=False, remove_active=True) |
| keyconfig_preset_add | bpy.ops.wm.keyconfig_preset_add(name="", remove_name=False, remove_active=False) |
| keyconfig_preset_remove | bpy.ops.wm.keyconfig_preset_remove(name="", remove_name=False, remove_active=True) |
| lib_reload | bpy.ops.wm.lib_reload(library="", filepath="", directory="", filename="", hide_props_region=True, ch |
| lib_relocate | bpy.ops.wm.lib_relocate(library="", filepath="", directory="", filename="", files=[], hide_props_reg |
| link | bpy.ops.wm.link(filepath="", directory="", filename="", files=[], check_existing=False, filter_blend |
| memory_statistics | bpy.ops.wm.memory_statistics() |
| obj_export | bpy.ops.wm.obj_export(filepath="", check_existing=True, filter_blender=False, filter_backup=False, f |
| obj_import | bpy.ops.wm.obj_import(filepath="", directory="", files=[], check_existing=False, filter_blender=Fals |
| open_mainfile | bpy.ops.wm.open_mainfile(filepath="", hide_props_region=True, check_existing=False, filter_blender=T |
| operator_cheat_sheet | bpy.ops.wm.operator_cheat_sheet() |
| operator_defaults | bpy.ops.wm.operator_defaults() |
| operator_pie_enum | bpy.ops.wm.operator_pie_enum(data_path="", prop_string="") |
| operator_preset_add | bpy.ops.wm.operator_preset_add(name="", remove_name=False, remove_active=False, operator="") |
| operator_presets_cleanup | bpy.ops.wm.operator_presets_cleanup(operator="", properties=[]) |
| owner_disable | bpy.ops.wm.owner_disable(owner_id="") |
| owner_enable | bpy.ops.wm.owner_enable(owner_id="") |
| path_open | bpy.ops.wm.path_open(filepath="") |
| ply_export | bpy.ops.wm.ply_export(filepath="", check_existing=True, filter_blender=False, filter_backup=False, f |
| ply_import | bpy.ops.wm.ply_import(filepath="", directory="", files=[], check_existing=False, filter_blender=Fals |
| previews_batch_clear | bpy.ops.wm.previews_batch_clear(files=[], directory="", filter_blender=True, filter_folder=True, use |
| previews_batch_generate | bpy.ops.wm.previews_batch_generate(files=[], directory="", filter_blender=True, filter_folder=True,  |
| previews_clear | bpy.ops.wm.previews_clear(id_type=set()) |
| previews_ensure | bpy.ops.wm.previews_ensure() |
| properties_add | bpy.ops.wm.properties_add(data_path="") |
| properties_context_change | bpy.ops.wm.properties_context_change(context="") |
| properties_edit | bpy.ops.wm.properties_edit(data_path="", property_name="", property_type='FLOAT', is_overridable_lib |
| properties_edit_value | bpy.ops.wm.properties_edit_value(data_path="", property_name="", eval_string="") |
| properties_remove | bpy.ops.wm.properties_remove(data_path="", property_name="") |
| quit_blender | bpy.ops.wm.quit_blender() |
| radial_control | bpy.ops.wm.radial_control(data_path_primary="", data_path_secondary="", use_secondary="", rotation_p |
| read_factory_settings | bpy.ops.wm.read_factory_settings(use_factory_startup_app_template_only=False, app_template="Template |
| read_factory_userpref | bpy.ops.wm.read_factory_userpref(use_factory_startup_app_template_only=False) |
| read_history | bpy.ops.wm.read_history() |
| read_homefile | bpy.ops.wm.read_homefile(filepath="", load_ui=True, use_splash=False, use_factory_startup=False, use |
| read_userpref | bpy.ops.wm.read_userpref() |
| recover_auto_save | bpy.ops.wm.recover_auto_save(filepath="", hide_props_region=True, check_existing=False, filter_blend |
| recover_last_session | bpy.ops.wm.recover_last_session(use_scripts=False) |
| redraw_timer | bpy.ops.wm.redraw_timer(type='DRAW', iterations=10, time_limit=0) |
| revert_mainfile | bpy.ops.wm.revert_mainfile(use_scripts=False) |
| save_as_mainfile | bpy.ops.wm.save_as_mainfile(filepath="", hide_props_region=True, check_existing=True, filter_blender |
| save_auto_save | bpy.ops.wm.save_auto_save() |
| save_homefile | bpy.ops.wm.save_homefile() |
| save_mainfile | bpy.ops.wm.save_mainfile(filepath="", hide_props_region=True, check_existing=True, filter_blender=Tr |
| save_userpref | bpy.ops.wm.save_userpref() |
| search_menu | bpy.ops.wm.search_menu() |
| search_operator | bpy.ops.wm.search_operator() |
| search_single_menu | bpy.ops.wm.search_single_menu(menu_idname="", initial_query="") |
| set_stereo_3d | bpy.ops.wm.set_stereo_3d(display_mode='ANAGLYPH', anaglyph_type='RED_CYAN', interlace_type='ROW_INTE |
| set_working_color_space | bpy.ops.wm.set_working_color_space(convert_colors=True, working_space='<UNKNOWN ENUM>') |
| splash | bpy.ops.wm.splash() |
| splash_about | bpy.ops.wm.splash_about() |
| stl_export | bpy.ops.wm.stl_export(filepath="", check_existing=True, filter_blender=False, filter_backup=False, f |
| stl_import | bpy.ops.wm.stl_import(filepath="", directory="", files=[], check_existing=False, filter_blender=Fals |
| sysinfo | bpy.ops.wm.sysinfo(filepath="") |
| tool_set_by_brush_type | bpy.ops.wm.tool_set_by_brush_type(brush_type="", space_type='EMPTY') |
| tool_set_by_id | bpy.ops.wm.tool_set_by_id(name="", cycle=False, as_fallback=False, space_type='EMPTY') |
| tool_set_by_index | bpy.ops.wm.tool_set_by_index(index=0, cycle=False, expand=True, as_fallback=False, space_type='EMPTY |
| toolbar | bpy.ops.wm.toolbar() |
| toolbar_fallback_pie | bpy.ops.wm.toolbar_fallback_pie() |
| toolbar_prompt | bpy.ops.wm.toolbar_prompt() |
| url_open | bpy.ops.wm.url_open(url="") |
| url_open_preset | bpy.ops.wm.url_open_preset(type='BUG') |
| usd_export | bpy.ops.wm.usd_export(filepath="", check_existing=True, filter_blender=False, filter_backup=False, f |
| usd_import | bpy.ops.wm.usd_import(filepath="", check_existing=False, filter_blender=False, filter_backup=False,  |
| window_close | bpy.ops.wm.window_close() |
| window_fullscreen_toggle | bpy.ops.wm.window_fullscreen_toggle() |
| window_new | bpy.ops.wm.window_new() |
| window_new_main | bpy.ops.wm.window_new_main() |
| xr_navigation_fly | bpy.ops.wm.xr_navigation_fly(mode='VIEWER_FORWARD', snap_turn_threshold=0.95, lock_location_z=False, |
| xr_navigation_grab | bpy.ops.wm.xr_navigation_grab(lock_location=False, lock_location_z=False, lock_rotation=False, lock_ |
| xr_navigation_reset | bpy.ops.wm.xr_navigation_reset(location=True, rotation=True, scale=True) |
| xr_navigation_swap_hands | bpy.ops.wm.xr_navigation_swap_hands() |
| xr_navigation_teleport | bpy.ops.wm.xr_navigation_teleport(selectable_only=True, force=8.5, range=0.15, ray_line_width=6, des |
| xr_session_toggle | bpy.ops.wm.xr_session_toggle() |

## image（49）

| 操作符 | 说明 |
|---|---|
| add_render_slot | bpy.ops.image.add_render_slot() |
| change_frame | bpy.ops.image.change_frame(frame=0) |
| clear_render_border | bpy.ops.image.clear_render_border() |
| clear_render_slot | bpy.ops.image.clear_render_slot() |
| clipboard_copy | bpy.ops.image.clipboard_copy() |
| clipboard_paste | bpy.ops.image.clipboard_paste() |
| convert_to_mesh_plane | bpy.ops.image.convert_to_mesh_plane(interpolation='Linear', extension='CLIP', use_auto_refresh=True, |
| curves_point_set | bpy.ops.image.curves_point_set(point='BLACK_POINT', size=1) |
| cycle_render_slot | bpy.ops.image.cycle_render_slot(reverse=False) |
| external_edit | bpy.ops.image.external_edit(filepath="") |
| file_browse | bpy.ops.image.file_browse(filepath="", hide_props_region=True, check_existing=False, filter_blender= |
| flip | bpy.ops.image.flip(use_flip_x=False, use_flip_y=False) |
| import_as_mesh_planes | bpy.ops.image.import_as_mesh_planes(interpolation='Linear', extension='CLIP', use_auto_refresh=True, |
| invert | bpy.ops.image.invert(invert_r=False, invert_g=False, invert_b=False, invert_a=False) |
| match_movie_length | bpy.ops.image.match_movie_length() |
| new | bpy.ops.image.new(name="Untitled", width=1024, height=1024, color=(0, 0, 0, 1), alpha=True, generate |
| open | bpy.ops.image.open(allow_path_tokens=True, filepath="", directory="", files=[], hide_props_region=Tr |
| open_images | bpy.ops.image.open_images(directory="", files=[], relative_path=True, use_sequence_detection=True, u |
| pack | bpy.ops.image.pack() |
| project_apply | bpy.ops.image.project_apply() |
| project_edit | bpy.ops.image.project_edit() |
| read_viewlayers | bpy.ops.image.read_viewlayers() |
| reload | bpy.ops.image.reload() |
| remove_render_slot | bpy.ops.image.remove_render_slot() |
| render_border | bpy.ops.image.render_border(xmin=0, xmax=0, ymin=0, ymax=0, wait_for_input=True) |
| replace | bpy.ops.image.replace(filepath="", hide_props_region=True, check_existing=False, filter_blender=Fals |
| resize | bpy.ops.image.resize(size=(0, 0), all_udims=False) |
| rotate_orthogonal | bpy.ops.image.rotate_orthogonal(degrees='90') |
| sample | bpy.ops.image.sample(size=1) |
| sample_line | bpy.ops.image.sample_line(xstart=0, xend=0, ystart=0, yend=0, flip=False, cursor=5) |
| save | bpy.ops.image.save() |
| save_all_modified | bpy.ops.image.save_all_modified() |
| save_as | bpy.ops.image.save_as(save_as_render=False, copy=False, allow_path_tokens=True, filepath="", check_e |
| save_sequence | bpy.ops.image.save_sequence() |
| tile_add | bpy.ops.image.tile_add(number=1002, count=1, label="", fill=True, color=(0, 0, 0, 1), generated_type |
| tile_fill | bpy.ops.image.tile_fill(color=(0, 0, 0, 1), generated_type='BLANK', width=1024, height=1024, float=F |
| tile_remove | bpy.ops.image.tile_remove() |
| unpack | bpy.ops.image.unpack(method='USE_LOCAL', id="") |
| view_all | bpy.ops.image.view_all(fit_view=False) |
| view_center_cursor | bpy.ops.image.view_center_cursor() |
| view_cursor_center | bpy.ops.image.view_cursor_center(fit_view=False) |
| view_ndof | bpy.ops.image.view_ndof() |
| view_pan | bpy.ops.image.view_pan(offset=(0, 0)) |
| view_selected | bpy.ops.image.view_selected() |
| view_zoom | bpy.ops.image.view_zoom(factor=0, use_cursor_init=True) |
| view_zoom_border | bpy.ops.image.view_zoom_border(xmin=0, xmax=0, ymin=0, ymax=0, wait_for_input=True, zoom_out=False) |
| view_zoom_in | bpy.ops.image.view_zoom_in(location=(0, 0)) |
| view_zoom_out | bpy.ops.image.view_zoom_out(location=(0, 0)) |
| view_zoom_ratio | bpy.ops.image.view_zoom_ratio(ratio=0) |

## transform（27）

| 操作符 | 说明 |
|---|---|
| bbone_resize | bpy.ops.transform.bbone_resize(value=(1, 1, 1), orient_type='GLOBAL', orient_matrix=((0, 0, 0), (0,  |
| bend | bpy.ops.transform.bend(value=(0, ), mirror=False, use_proportional_edit=False, proportional_edit_fal |
| create_orientation | bpy.ops.transform.create_orientation(name="", use_view=False, use=False, overwrite=False) |
| delete_orientation | bpy.ops.transform.delete_orientation() |
| edge_bevelweight | bpy.ops.transform.edge_bevelweight(value=0, snap=False, release_confirm=False, use_accurate=False) |
| edge_crease | bpy.ops.transform.edge_crease(value=0, snap=False, release_confirm=False, use_accurate=False) |
| edge_slide | bpy.ops.transform.edge_slide(value=0, single_side=False, use_even=False, flipped=False, use_clamp=Tr |
| from_gizmo | bpy.ops.transform.from_gizmo() |
| mirror | bpy.ops.transform.mirror(orient_type='GLOBAL', orient_matrix=((0, 0, 0), (0, 0, 0), (0, 0, 0)), orie |
| push_pull | bpy.ops.transform.push_pull(value=0, mirror=False, use_proportional_edit=False, proportional_edit_fa |
| resize | bpy.ops.transform.resize(value=(1, 1, 1), mouse_dir_constraint=(0, 0, 0), orient_type='GLOBAL', orie |
| rotate | bpy.ops.transform.rotate(value=0, orient_axis='Z', orient_type='GLOBAL', orient_matrix=((0, 0, 0), ( |
| rotate_normal | bpy.ops.transform.rotate_normal(value=0, orient_axis='Z', orient_type='GLOBAL', orient_matrix=((0, 0 |
| select_orientation | bpy.ops.transform.select_orientation(orientation='GLOBAL') |
| seq_slide | bpy.ops.transform.seq_slide(value=(0, 0), use_restore_handle_selection=False, snap=False, texture_sp |
| shear | bpy.ops.transform.shear(angle=0, orient_axis='Z', orient_axis_ortho='X', orient_type='GLOBAL', orien |
| shrink_fatten | bpy.ops.transform.shrink_fatten(value=0, use_even_offset=False, mirror=False, use_proportional_edit= |
| skin_resize | bpy.ops.transform.skin_resize(value=(1, 1, 1), orient_type='GLOBAL', orient_matrix=((0, 0, 0), (0, 0 |
| tilt | bpy.ops.transform.tilt(value=0, mirror=False, use_proportional_edit=False, proportional_edit_falloff |
| tosphere | bpy.ops.transform.tosphere(value=0, mirror=False, use_proportional_edit=False, proportional_edit_fal |
| trackball | bpy.ops.transform.trackball(value=(0, 0), mirror=False, use_proportional_edit=False, proportional_ed |
| transform | bpy.ops.transform.transform(mode='TRANSLATION', value=(0, 0, 0, 0), orient_axis='Z', orient_type='GL |
| translate | bpy.ops.transform.translate(value=(0, 0, 0), orient_type='GLOBAL', orient_matrix=((0, 0, 0), (0, 0,  |
| vert_crease | bpy.ops.transform.vert_crease(value=0, snap=False, release_confirm=False, use_accurate=False) |
| vert_slide | bpy.ops.transform.vert_slide(value=0, use_even=False, flipped=False, use_clamp=True, direction=(0, 0 |
| vertex_random | bpy.ops.transform.vertex_random(offset=0, uniform=0, normal=0, seed=0, wait_for_input=True) |
| vertex_warp | bpy.ops.transform.vertex_warp(warp_angle=6.28319, offset_angle=0, min=-1, max=1, viewmat=((0, 0, 0,  |
