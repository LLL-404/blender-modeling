# bmesh 算子（83）

签名取自运行时 docstring，可能被截断；调用前用 `help(bmesh.ops.x)` 确认。

| 算子 | 签名首行 |
|---|---|
| average_vert_facedata | BMeshOpFunc bmesh.ops.average_vert_facedata(bmesh, verts=[]) |
| beautify_fill | BMeshOpFunc bmesh.ops.beautify_fill(bmesh, faces=[], edges=[], use_restrict_tag=False, method='AREA') |
| bevel | BMeshOpFunc bmesh.ops.bevel(bmesh, geom=[], offset=0.0, offset_type='OFFSET', profile_type='SUPERELLIPSE', segments=0, profile=0.0, affect='VERTICES', clamp_overlap=False, material=0, loop_slide=False |
| bisect_edges | BMeshOpFunc bmesh.ops.bisect_edges(bmesh, edges=[], cuts=0, edge_percents={}) |
| bisect_plane | BMeshOpFunc bmesh.ops.bisect_plane(bmesh, geom=[], dist=0.0, plane_co=Vector(), plane_no=Vector(), use_snap_center=False, clear_outer=False, clear_inner=False) |
| bmesh_to_mesh | BMeshOpFunc bmesh.ops.bmesh_to_mesh(bmesh, mesh=None, object=None) |
| bridge_loops | BMeshOpFunc bmesh.ops.bridge_loops(bmesh, edges=[], use_pairs=False, use_cyclic=False, use_merge=False, merge_factor=0.0, twist_offset=0) |
| circularize | BMeshOpFunc bmesh.ops.circularize(bmesh, geom=[], factor=0.0, custom_radius=0.0, angle=0.0, fit_method=0, flatten=0.0, regular=False, lock_x=False, lock_y=False, lock_z=False, mirror_x=False, mirror_y |
| collapse | BMeshOpFunc bmesh.ops.collapse(bmesh, edges=[], uvs=False) |
| collapse_uvs | BMeshOpFunc bmesh.ops.collapse_uvs(bmesh, edges=[]) |
| connect_vert_pair | BMeshOpFunc bmesh.ops.connect_vert_pair(bmesh, verts=[], verts_exclude=[], faces_exclude=[]) |
| connect_verts | BMeshOpFunc bmesh.ops.connect_verts(bmesh, verts=[], faces_exclude=[], check_degenerate=False) |
| connect_verts_concave | BMeshOpFunc bmesh.ops.connect_verts_concave(bmesh, faces=[]) |
| connect_verts_nonplanar | BMeshOpFunc bmesh.ops.connect_verts_nonplanar(bmesh, angle_limit=0.0, faces=[]) |
| contextual_create | BMeshOpFunc bmesh.ops.contextual_create(bmesh, geom=[], mat_nr=0, use_smooth=False) |
| convex_hull | BMeshOpFunc bmesh.ops.convex_hull(bmesh, input=[], use_existing_faces=False) |
| create_circle | BMeshOpFunc bmesh.ops.create_circle(bmesh, cap_ends=False, cap_tris=False, segments=0, radius=0.0, matrix=Matrix(), calc_uvs=False) |
| create_cone | BMeshOpFunc bmesh.ops.create_cone(bmesh, cap_ends=False, cap_tris=False, segments=0, radius1=0.0, radius2=0.0, depth=0.0, matrix=Matrix(), calc_uvs=False) |
| create_cube | BMeshOpFunc bmesh.ops.create_cube(bmesh, size=0.0, matrix=Matrix(), calc_uvs=False) |
| create_grid | BMeshOpFunc bmesh.ops.create_grid(bmesh, x_segments=0, y_segments=0, size=0.0, matrix=Matrix(), calc_uvs=False) |
| create_icosphere | BMeshOpFunc bmesh.ops.create_icosphere(bmesh, subdivisions=0, radius=0.0, matrix=Matrix(), calc_uvs=False) |
| create_monkey | BMeshOpFunc bmesh.ops.create_monkey(bmesh, matrix=Matrix(), calc_uvs=False) |
| create_uvsphere | BMeshOpFunc bmesh.ops.create_uvsphere(bmesh, u_segments=0, v_segments=0, radius=0.0, matrix=Matrix(), calc_uvs=False) |
| create_vert | BMeshOpFunc bmesh.ops.create_vert(bmesh, co=Vector()) |
| delete | BMeshOpFunc bmesh.ops.delete(bmesh, geom=[], context='VERTS') |
| dissolve_degenerate | BMeshOpFunc bmesh.ops.dissolve_degenerate(bmesh, dist=0.0, edges=[]) |
| dissolve_edges | BMeshOpFunc bmesh.ops.dissolve_edges(bmesh, edges=[], use_verts=False, use_face_split=False, angle_threshold=0.0, use_preserve_quads=False) |
| dissolve_faces | BMeshOpFunc bmesh.ops.dissolve_faces(bmesh, faces=[], use_verts=False) |
| dissolve_limit | BMeshOpFunc bmesh.ops.dissolve_limit(bmesh, angle_limit=0.0, use_dissolve_boundaries=False, verts=[], edges=[], delimit={}) |
| dissolve_verts | BMeshOpFunc bmesh.ops.dissolve_verts(bmesh, verts=[], use_face_split=False, use_boundary_tear=False) |
| duplicate | BMeshOpFunc bmesh.ops.duplicate(bmesh, geom=[], dest=None, use_select_history=False, use_edge_flip_from_face=False) |
| edgeloop_fill | BMeshOpFunc bmesh.ops.edgeloop_fill(bmesh, edges=[], mat_nr=0, use_smooth=False) |
| edgenet_fill | BMeshOpFunc bmesh.ops.edgenet_fill(bmesh, edges=[], mat_nr=0, use_smooth=False, sides=0) |
| edgenet_prepare | BMeshOpFunc bmesh.ops.edgenet_prepare(bmesh, edges=[]) |
| extrude_discrete_faces | BMeshOpFunc bmesh.ops.extrude_discrete_faces(bmesh, faces=[], use_normal_flip=False, use_select_history=False) |
| extrude_edge_only | BMeshOpFunc bmesh.ops.extrude_edge_only(bmesh, edges=[], use_normal_flip=False, use_select_history=False) |
| extrude_face_region | BMeshOpFunc bmesh.ops.extrude_face_region(bmesh, geom=[], edges_exclude={}, use_keep_orig=False, use_normal_flip=False, use_normal_from_adjacent=False, use_dissolve_ortho_edges=False, use_select_histo |
| extrude_vert_indiv | BMeshOpFunc bmesh.ops.extrude_vert_indiv(bmesh, verts=[], use_select_history=False) |
| face_attribute_fill | BMeshOpFunc bmesh.ops.face_attribute_fill(bmesh, faces=[], use_normals=False, use_data=False) |
| find_doubles | BMeshOpFunc bmesh.ops.find_doubles(bmesh, verts=[], keep_verts=[], use_connected=False, dist=0.0) |
| flatten | BMeshOpFunc bmesh.ops.flatten(bmesh, geom=[], factor=0.0, method=0, view_normal=Vector(), lock_x=False, lock_y=False, lock_z=False) |
| flip_quad_tessellation | BMeshOpFunc bmesh.ops.flip_quad_tessellation(bmesh, faces=[]) |
| grid_fill | BMeshOpFunc bmesh.ops.grid_fill(bmesh, edges=[], mat_nr=0, use_smooth=False, use_interp_simple=False) |
| holes_fill | BMeshOpFunc bmesh.ops.holes_fill(bmesh, edges=[], sides=0) |
| inset_individual | BMeshOpFunc bmesh.ops.inset_individual(bmesh, faces=[], thickness=0.0, depth=0.0, use_even_offset=False, use_interpolate=False, use_relative_offset=False) |
| inset_region | BMeshOpFunc bmesh.ops.inset_region(bmesh, faces=[], faces_exclude=[], use_boundary=False, use_even_offset=False, use_interpolate=False, use_relative_offset=False, use_edge_rail=False, thickness=0.0, d |
| join_triangles | BMeshOpFunc bmesh.ops.join_triangles(bmesh, faces=[], cmp_seam=False, cmp_sharp=False, cmp_uvs=False, cmp_vcols=False, cmp_materials=False, angle_face_threshold=0.0, angle_shape_threshold=0.0, topolog |
| mesh_to_bmesh | BMeshOpFunc bmesh.ops.mesh_to_bmesh(bmesh, mesh=None, object=None, use_shapekey=False) |
| mirror | BMeshOpFunc bmesh.ops.mirror(bmesh, geom=[], matrix=Matrix(), merge_dist=0.0, axis='X', mirror_u=False, mirror_v=False, mirror_udim=False, use_shapekey=False) |
| object_load_bmesh | BMeshOpFunc bmesh.ops.object_load_bmesh(bmesh, scene=None, object=None) |
| offset_edgeloops | BMeshOpFunc bmesh.ops.offset_edgeloops(bmesh, edges=[], use_cap_endpoint=False) |
| planar_faces | BMeshOpFunc bmesh.ops.planar_faces(bmesh, faces=[], iterations=0, factor=0.0) |
| pointmerge | BMeshOpFunc bmesh.ops.pointmerge(bmesh, verts=[], merge_co=Vector(), vert_target=None) |
| pointmerge_facedata | BMeshOpFunc bmesh.ops.pointmerge_facedata(bmesh, verts=[], vert_target=None) |
| poke | BMeshOpFunc bmesh.ops.poke(bmesh, faces=[], offset=0.0, center_mode='MEAN_WEIGHTED', use_relative_offset=False) |
| recalc_face_normals | BMeshOpFunc bmesh.ops.recalc_face_normals(bmesh, faces=[]) |
| region_extend | BMeshOpFunc bmesh.ops.region_extend(bmesh, geom=[], use_contract=False, use_faces=False, use_face_step=False) |
| remove_doubles | BMeshOpFunc bmesh.ops.remove_doubles(bmesh, verts=[], use_connected=False, dist=0.0) |
| reverse_colors | BMeshOpFunc bmesh.ops.reverse_colors(bmesh, faces=[], color_index=0) |
| reverse_faces | BMeshOpFunc bmesh.ops.reverse_faces(bmesh, faces=[], flip_multires=False) |
| reverse_uvs | BMeshOpFunc bmesh.ops.reverse_uvs(bmesh, faces=[]) |
| rotate | BMeshOpFunc bmesh.ops.rotate(bmesh, cent=Vector(), matrix=Matrix(), verts=[], space=Matrix(), use_shapekey=False) |
| rotate_colors | BMeshOpFunc bmesh.ops.rotate_colors(bmesh, faces=[], use_ccw=False, color_index=0) |
| rotate_edges | BMeshOpFunc bmesh.ops.rotate_edges(bmesh, edges=[], use_ccw=False) |
| rotate_uvs | BMeshOpFunc bmesh.ops.rotate_uvs(bmesh, faces=[], use_ccw=False) |
| scale | BMeshOpFunc bmesh.ops.scale(bmesh, vec=Vector(), space=Matrix(), verts=[], use_shapekey=False) |
| smooth_laplacian_vert | BMeshOpFunc bmesh.ops.smooth_laplacian_vert(bmesh, verts=[], lambda_factor=0.0, lambda_border=0.0, use_x=False, use_y=False, use_z=False, preserve_volume=False) |
| smooth_vert | BMeshOpFunc bmesh.ops.smooth_vert(bmesh, verts=[], factor=0.0, mirror_clip_x=False, mirror_clip_y=False, mirror_clip_z=False, clip_dist=0.0, use_axis_x=False, use_axis_y=False, use_axis_z=False) |
| solidify | BMeshOpFunc bmesh.ops.solidify(bmesh, geom=[], thickness=0.0) |
| space_edge_loops_evenly | BMeshOpFunc bmesh.ops.space_edge_loops_evenly(bmesh, geom=[], interpolation='CUBIC', factor=0.0, lock_x=False, lock_y=False, lock_z=False) |
| spin | BMeshOpFunc bmesh.ops.spin(bmesh, geom=[], cent=Vector(), axis=Vector(), dvec=Vector(), angle=0.0, space=Matrix(), steps=0, use_merge=False, use_normal_flip=False, use_duplicate=False) |
| split | BMeshOpFunc bmesh.ops.split(bmesh, geom=[], dest=None, use_only_faces=False) |
| split_edges | BMeshOpFunc bmesh.ops.split_edges(bmesh, edges=[], verts=[], use_verts=False) |
| subdivide_edgering | BMeshOpFunc bmesh.ops.subdivide_edgering(bmesh, edges=[], interp_mode='LINEAR', smooth=0.0, cuts=0, profile_shape='SMOOTH', profile_shape_factor=0.0) |
| subdivide_edges | BMeshOpFunc bmesh.ops.subdivide_edges(bmesh, edges=[], smooth=0.0, smooth_falloff='SMOOTH', fractal=0.0, along_normal=0.0, cuts=0, seed=0, custom_patterns={}, edge_percents={}, quad_corner_type='STRAI |
| symmetrize | BMeshOpFunc bmesh.ops.symmetrize(bmesh, input=[], direction='-X', dist=0.0, use_shapekey=False) |
| transform | BMeshOpFunc bmesh.ops.transform(bmesh, matrix=Matrix(), space=Matrix(), verts=[], use_shapekey=False) |
| translate | BMeshOpFunc bmesh.ops.translate(bmesh, vec=Vector(), space=Matrix(), verts=[], use_shapekey=False) |
| triangle_fill | BMeshOpFunc bmesh.ops.triangle_fill(bmesh, use_beauty=False, use_dissolve=False, edges=[], normal=Vector()) |
| triangulate | BMeshOpFunc bmesh.ops.triangulate(bmesh, faces=[], quad_method='BEAUTY', ngon_method='BEAUTY') |
| unsubdivide | BMeshOpFunc bmesh.ops.unsubdivide(bmesh, verts=[], iterations=0) |
| weld_verts | BMeshOpFunc bmesh.ops.weld_verts(bmesh, targetmap={}, use_centroid=False, average_vert_data=False) |
| wireframe | BMeshOpFunc bmesh.ops.wireframe(bmesh, faces=[], thickness=0.0, offset=0.0, use_replace=False, use_boundary=False, use_even_offset=False, use_crease=False, crease_weight=0.0, use_relative_offset=False |