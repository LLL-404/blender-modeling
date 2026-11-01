extends SceneTree

func _initialize() -> void:
	for p in ["res://core_jade.glb", "res://tower_ballista.glb"]:
		var ps = load(p)
		print("=== ", p, " loaded=", ps != null)
		if ps == null:
			continue
		var inst = ps.instantiate()
		var anims: Array = []
		var skel = null
		var meshes: Array = []
		var stack: Array = [inst]
		while not stack.is_empty():
			var n = stack.pop_back()
			if n is AnimationPlayer:
				anims = n.get_animation_list()
			if n is Skeleton3D:
				skel = n
			if n is MeshInstance3D:
				meshes.append(n.name)
			for c in n.get_children():
				stack.append(c)
		print("  anims=", anims)
		print("  bones=", skel.get_bone_count() if skel != null else -1)
		print("  meshes=", meshes)
		var mi: MeshInstance3D = null
		stack = [inst]
		while not stack.is_empty():
			var n2 = stack.pop_back()
			if n2 is MeshInstance3D and String(n2.name).to_lower().begins_with("lod0"):
				mi = n2
			for c2 in n2.get_children():
				stack.append(c2)
		if mi != null:
			var aabb = mi.mesh.get_aabb()
			print("  lod0 aabb size=", aabb.size, " pos=", aabb.position)
		inst.free()
	quit()
