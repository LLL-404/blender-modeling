# 节点类型

端口从**真实节点实例**读取（`tree.nodes.new(type)` 后读 `inputs`/`outputs`），
格式 `` `名字:类型` ``，尾部 `*` 表示多输入口（可以接多条线）。
完整结构（含默认值）见 `api.json` → `nodes.detail`。

## ShaderNode（102，其中可实例化 99）

> node_tree：`shader`

| 节点 | 输入 | 输出 |
|---|---|---|
| ShaderNodeAddShader | `Shader:SHADER`, `Shader:SHADER` | `Shader:SHADER` |
| ShaderNodeAmbientOcclusion | `Color:RGBA`, `Distance:VALUE`, `Normal:VECTOR` | `Color:RGBA`, `AO:VALUE` |
| ShaderNodeAttribute | — | `Color:RGBA`, `Vector:VECTOR`, `Factor:VALUE`, `Alpha:VALUE` |
| ShaderNodeBackground | `Color:RGBA`, `Strength:VALUE`, `Weight:VALUE` | `Background:SHADER` |
| ShaderNodeBevel | `Radius:VALUE`, `Normal:VECTOR` | `Normal:VECTOR` |
| ShaderNodeBlackbody | `Temperature:VALUE` | `Color:RGBA` |
| ShaderNodeBrightContrast | `Color:RGBA`, `Brightness:VALUE`, `Contrast:VALUE` | `Color:RGBA` |
| ShaderNodeBsdfAnisotropic | `Color:RGBA`, `Roughness:VALUE`, `Anisotropy:VALUE`, `Rotation:VALUE`, `Normal:VECTOR`, `Tangent:VECTOR`, `Weight:VALUE` | `BSDF:SHADER` |
| ShaderNodeBsdfDiffuse | `Color:RGBA`, `Roughness:VALUE`, `Normal:VECTOR`, `Weight:VALUE` | `BSDF:SHADER` |
| ShaderNodeBsdfGlass | `Color:RGBA`, `Roughness:VALUE`, `IOR:VALUE`, `Normal:VECTOR`, `Weight:VALUE`, `Thin Film Thickness:VALUE`, `Thin Film IOR:VALUE` | `BSDF:SHADER` |
| ShaderNodeBsdfHair | `Color:RGBA`, `Offset:VALUE`, `RoughnessU:VALUE`, `RoughnessV:VALUE`, `Tangent:VECTOR`, `Weight:VALUE` | `BSDF:SHADER` |
| ShaderNodeBsdfHairPrincipled | `Color:RGBA`, `Melanin:VALUE`, `Melanin Redness:VALUE`, `Tint:RGBA`, `Absorption Coefficient:VECTOR`, `Aspect Ratio:VALUE`, `Roughness:VALUE`, `Radial Roughness:VALUE`, `Coat:VALUE`, `IOR:VALUE`, `Offset:VALUE`, `Random Color:VALUE`, `Random Roughness:VALUE`, `Random:VALUE`, `Weight:VALUE`, `Reflection:VALUE`, `Transmission:VALUE`, `Secondary Reflection:VALUE` | `BSDF:SHADER` |
| ShaderNodeBsdfMetallic | `Base Color:RGBA`, `Edge Tint:RGBA`, `IOR:VECTOR`, `Extinction:VECTOR`, `Roughness:VALUE`, `Anisotropy:VALUE`, `Rotation:VALUE`, `Normal:VECTOR`, `Tangent:VECTOR`, `Weight:VALUE`, `Thin Film Thickness:VALUE`, `Thin Film IOR:VALUE` | `BSDF:SHADER` |
| ShaderNodeBsdfPrincipled | `Base Color:RGBA`, `Metallic:VALUE`, `Roughness:VALUE`, `IOR:VALUE`, `Alpha:VALUE`, `Thin Wall:BOOLEAN`, `Normal:VECTOR`, `Weight:VALUE`, `Diffuse Roughness:VALUE`, `Subsurface Weight:VALUE`, `Subsurface Radius:VECTOR`, `Subsurface Scale:VALUE`, `Subsurface IOR:VALUE`, `Subsurface Anisotropy:VALUE`, `Specular IOR Level:VALUE`, `Specular Tint:RGBA`, `Anisotropic:VALUE`, `Anisotropic Rotation:VALUE`, `Tangent:VECTOR`, `Transmission Weight:VALUE`, `Coat Weight:VALUE`, `Coat Roughness:VALUE`, `Coat IOR:VALUE`, `Coat Tint:RGBA`, `Coat Normal:VECTOR`, `Sheen Weight:VALUE`, `Sheen Roughness:VALUE`, `Sheen Tint:RGBA`, `Emission Color:RGBA`, `Emission Strength:VALUE`, `Thin Film Thickness:VALUE`, `Thin Film IOR:VALUE` | `BSDF:SHADER` |
| ShaderNodeBsdfRayPortal | `Color:RGBA`, `Position:VECTOR`, `Direction:VECTOR`, `Weight:VALUE` | `BSDF:SHADER` |
| ShaderNodeBsdfRefraction | `Color:RGBA`, `Roughness:VALUE`, `IOR:VALUE`, `Normal:VECTOR`, `Weight:VALUE` | `BSDF:SHADER` |
| ShaderNodeBsdfSheen | `Color:RGBA`, `Roughness:VALUE`, `Normal:VECTOR`, `Weight:VALUE` | `BSDF:SHADER` |
| ShaderNodeBsdfToon | `Color:RGBA`, `Size:VALUE`, `Smooth:VALUE`, `Normal:VECTOR`, `Weight:VALUE` | `BSDF:SHADER` |
| ShaderNodeBsdfTranslucent | `Color:RGBA`, `Normal:VECTOR`, `Weight:VALUE` | `BSDF:SHADER` |
| ShaderNodeBsdfTransparent | `Color:RGBA`, `Weight:VALUE` | `BSDF:SHADER` |
| ShaderNodeBump | `Strength:VALUE`, `Distance:VALUE`, `Filter Width:VALUE`, `Height:VALUE`, `Normal:VECTOR` | `Normal:VECTOR` |
| ShaderNodeCameraData | — | `View Vector:VECTOR`, `View Z Depth:VALUE`, `View Distance:VALUE` |
| ShaderNodeClamp | `Value:VALUE`, `Min:VALUE`, `Max:VALUE` | `Result:VALUE` |
| ShaderNodeCombineColor | `Red:VALUE`, `Green:VALUE`, `Blue:VALUE` | `Color:RGBA` |
| ShaderNodeCombineXYZ | `X:VALUE`, `Y:VALUE`, `Z:VALUE` | `Vector:VECTOR` |
| ShaderNodeDisplacement | `Height:VALUE`, `Midlevel:VALUE`, `Scale:VALUE`, `Normal:VECTOR` | `Displacement:VECTOR` |
| ShaderNodeEeveeSpecular | `Base Color:RGBA`, `Specular:RGBA`, `Roughness:VALUE`, `Emissive Color:RGBA`, `Transparency:VALUE`, `Normal:VECTOR`, `Clear Coat:VALUE`, `Clear Coat Roughness:VALUE`, `Clear Coat Normal:VECTOR`, `Weight:VALUE` | `BSDF:SHADER` |
| ShaderNodeEmission | `Color:RGBA`, `Strength:VALUE`, `Weight:VALUE` | `Emission:SHADER` |
| ShaderNodeFloatCurve | `Factor:VALUE`, `Value:VALUE` | `Value:VALUE` |
| ShaderNodeFresnel | `IOR:VALUE`, `Normal:VECTOR` | `Factor:VALUE` |
| ShaderNodeGamma | `Color:RGBA`, `Gamma:VALUE` | `Color:RGBA` |
| ShaderNodeGroup | — | — |
| ShaderNodeHairInfo | — | `Is Strand:VALUE`, `Intercept:VALUE`, `Length:VALUE`, `Thickness:VALUE`, `Tangent Normal:VECTOR`, `Random:VALUE` |
| ShaderNodeHoldout | `Weight:VALUE` | `Holdout:SHADER` |
| ShaderNodeHueSaturation | `Hue:VALUE`, `Saturation:VALUE`, `Value:VALUE`, `Factor:VALUE`, `Color:RGBA` | `Color:RGBA` |
| ShaderNodeInvert | `Factor:VALUE`, `Color:RGBA` | `Color:RGBA` |
| ShaderNodeLayerWeight | `Blend:VALUE`, `Normal:VECTOR` | `Fresnel:VALUE`, `Facing:VALUE` |
| ShaderNodeLightFalloff | `Strength:VALUE`, `Smooth:VALUE` | `Quadratic:VALUE`, `Linear:VALUE`, `Constant:VALUE` |
| ShaderNodeLightPath | — | `Is Camera Ray:VALUE`, `Is Shadow Ray:VALUE`, `Is Diffuse Ray:VALUE`, `Is Glossy Ray:VALUE`, `Is Singular Ray:VALUE`, `Is Reflection Ray:VALUE`, `Is Transmission Ray:VALUE`, `Is Volume Scatter Ray:VALUE`, `Ray Length:VALUE`, `Ray Depth:VALUE`, `Diffuse Depth:VALUE`, `Glossy Depth:VALUE`, `Transparent Depth:VALUE`, `Transmission Depth:VALUE`, `Portal Depth:VALUE` |
| ShaderNodeMapRange | `Value:VALUE`, `From Min:VALUE`, `From Max:VALUE`, `To Min:VALUE`, `To Max:VALUE`, `Steps:VALUE`, `Vector:VECTOR`, `From Min:VECTOR`, `From Max:VECTOR`, `To Min:VECTOR`, `To Max:VECTOR`, `Steps:VECTOR` | `Result:VALUE`, `Vector:VECTOR` |
| ShaderNodeMapping | `Vector:VECTOR`, `Location:VECTOR`, `Rotation:VECTOR`, `Scale:VECTOR` | `Vector:VECTOR` |
| ShaderNodeMath | `Value:VALUE`, `Value:VALUE`, `Value:VALUE` | `Value:VALUE` |
| ShaderNodeMix | `Factor:VALUE`, `Factor:VECTOR`, `A:VALUE`, `B:VALUE`, `A:VECTOR`, `B:VECTOR`, `A:RGBA`, `B:RGBA`, `A:ROTATION`, `B:ROTATION` | `Result:VALUE`, `Result:VECTOR`, `Result:RGBA`, `Result:ROTATION` |
| ShaderNodeMixRGB | `Factor:VALUE`, `Color1:RGBA`, `Color2:RGBA` | `Color:RGBA` |
| ShaderNodeMixShader | `Factor:VALUE`, `Shader:SHADER`, `Shader:SHADER` | `Shader:SHADER` |
| ShaderNodeNewGeometry | — | `Position:VECTOR`, `Normal:VECTOR`, `Tangent:VECTOR`, `True Normal:VECTOR`, `Incoming:VECTOR`, `Parametric:VECTOR`, `Backfacing:VALUE`, `Pointiness:VALUE`, `Random Per Island:VALUE` |
| ShaderNodeNormal | `Normal:VECTOR` | `Normal:VECTOR`, `Dot:VALUE` |
| ShaderNodeNormalMap | `Strength:VALUE`, `Color:RGBA` | `Normal:VECTOR` |
| ShaderNodeObjectInfo | — | `Location:VECTOR`, `Color:RGBA`, `Alpha:VALUE`, `Object Index:VALUE`, `Material Index:VALUE`, `Random:VALUE` |
| ShaderNodeOutputAOV | `Color:RGBA`, `Value:VALUE` | — |
| ShaderNodeOutputLight | `Surface:SHADER` | — |
| ShaderNodeOutputLineStyle | `Color:RGBA`, `Color Fac:VALUE`, `Alpha:VALUE`, `Alpha Fac:VALUE` | — |
| ShaderNodeOutputMaterial | `Surface:SHADER`, `Volume:SHADER`, `Displacement:VECTOR`, `Thickness:VALUE` | — |
| ShaderNodeOutputWorld | `Surface:SHADER`, `Volume:SHADER` | — |
| ShaderNodeParticleInfo | — | `Index:VALUE`, `Random:VALUE`, `Age:VALUE`, `Lifetime:VALUE`, `Location:VECTOR`, `Size:VALUE`, `Velocity:VECTOR`, `Angular Velocity:VECTOR` |
| ShaderNodePointInfo | — | `Position:VECTOR`, `Radius:VALUE`, `Random:VALUE` |
| ShaderNodeRGB | — | `Color:RGBA` |
| ShaderNodeRGBCurve | `Factor:VALUE`, `Color:RGBA` | `Color:RGBA` |
| ShaderNodeRGBToBW | `Color:RGBA` | `Val:VALUE` |
| ShaderNodeRadialTiling | `Vector:VECTOR`, `Sides:VALUE`, `Roundness:VALUE` | `Segment Coordinates:VECTOR`, `Segment ID:VALUE`, `Segment Width:VALUE`, `Segment Rotation:VALUE` |
| ShaderNodeRaycast | `Position:VECTOR`, `Direction:VECTOR`, `Length:VALUE`, `:CUSTOM` | `Is Hit:VALUE`, `Self Hit:VALUE`, `Hit Distance:VALUE`, `Hit Position:VECTOR`, `Hit Normal:VECTOR`, `:CUSTOM` |
| ShaderNodeScript | — | — |
| ShaderNodeSeparateColor | `Color:RGBA` | `Red:VALUE`, `Green:VALUE`, `Blue:VALUE` |
| ShaderNodeSeparateXYZ | `Vector:VECTOR` | `X:VALUE`, `Y:VALUE`, `Z:VALUE` |
| ShaderNodeShaderToRGB | `Shader:SHADER` | `Color:RGBA`, `Alpha:VALUE` |
| ShaderNodeSqueeze | `Value:VALUE`, `Width:VALUE`, `Center:VALUE` | `Value:VALUE` |
| ShaderNodeSubsurfaceScattering | `Color:RGBA`, `Scale:VALUE`, `Radius:VECTOR`, `IOR:VALUE`, `Roughness:VALUE`, `Anisotropy:VALUE`, `Normal:VECTOR`, `Weight:VALUE` | `BSSRDF:SHADER` |
| ShaderNodeTangent | — | `Tangent:VECTOR` |
| ShaderNodeTexBrick | `Vector:VECTOR`, `Color1:RGBA`, `Color2:RGBA`, `Mortar:RGBA`, `Scale:VALUE`, `Mortar Size:VALUE`, `Mortar Smooth:VALUE`, `Bias:VALUE`, `Brick Width:VALUE`, `Row Height:VALUE` | `Color:RGBA`, `Factor:VALUE` |
| ShaderNodeTexChecker | `Vector:VECTOR`, `Color1:RGBA`, `Color2:RGBA`, `Scale:VALUE` | `Color:RGBA`, `Factor:VALUE` |
| ShaderNodeTexCoord | — | `Generated:VECTOR`, `Normal:VECTOR`, `UV:VECTOR`, `Object:VECTOR`, `Camera:VECTOR`, `Window:VECTOR`, `Reflection:VECTOR` |
| ShaderNodeTexEnvironment | `Vector:VECTOR` | `Color:RGBA` |
| ShaderNodeTexGabor | `Vector:VECTOR`, `Scale:VALUE`, `Frequency:VALUE`, `Anisotropy:VALUE`, `Orientation:VALUE`, `Orientation:VECTOR` | `Value:VALUE`, `Phase:VALUE`, `Intensity:VALUE` |
| ShaderNodeTexGradient | `Vector:VECTOR` | `Color:RGBA`, `Factor:VALUE` |
| ShaderNodeTexIES | `Vector:VECTOR`, `Strength:VALUE` | `Factor:VALUE` |
| ShaderNodeTexImage | `Vector:VECTOR` | `Color:RGBA`, `Alpha:VALUE` |
| ShaderNodeTexMagic | `Vector:VECTOR`, `Scale:VALUE`, `Distortion:VALUE` | `Color:RGBA`, `Factor:VALUE` |
| ShaderNodeTexNoise | `Vector:VECTOR`, `W:VALUE`, `Scale:VALUE`, `Detail:VALUE`, `Roughness:VALUE`, `Lacunarity:VALUE`, `Offset:VALUE`, `Gain:VALUE`, `Distortion:VALUE` | `Factor:VALUE`, `Color:RGBA` |
| ShaderNodeTexSky | `Vector:VECTOR` | `Color:RGBA` |
| ShaderNodeTexVoronoi | `Vector:VECTOR`, `W:VALUE`, `Scale:VALUE`, `Detail:VALUE`, `Roughness:VALUE`, `Lacunarity:VALUE`, `Smoothness:VALUE`, `Exponent:VALUE`, `Randomness:VALUE` | `Distance:VALUE`, `Color:RGBA`, `Position:VECTOR`, `W:VALUE`, `Radius:VALUE` |
| ShaderNodeTexWave | `Vector:VECTOR`, `Scale:VALUE`, `Distortion:VALUE`, `Detail:VALUE`, `Detail Scale:VALUE`, `Detail Roughness:VALUE`, `Phase Offset:VALUE` | `Color:RGBA`, `Factor:VALUE` |
| ShaderNodeTexWhiteNoise | `Vector:VECTOR`, `W:VALUE` | `Value:VALUE`, `Color:RGBA` |
| ShaderNodeUVAlongStroke | — | `UV:VECTOR` |
| ShaderNodeUVMap | — | `UV:VECTOR` |
| ShaderNodeValToRGB | `Factor:VALUE` | `Color:RGBA`, `Alpha:VALUE` |
| ShaderNodeValue | — | `Value:VALUE` |
| ShaderNodeVectorCurve | `Factor:VALUE`, `Vector:VECTOR` | `Vector:VECTOR` |
| ShaderNodeVectorDisplacement | `Vector:RGBA`, `Midlevel:VALUE`, `Scale:VALUE` | `Displacement:VECTOR` |
| ShaderNodeVectorMath | `Vector:VECTOR`, `Vector:VECTOR`, `Vector:VECTOR`, `Scale:VALUE` | `Vector:VECTOR`, `Value:VALUE` |
| ShaderNodeVectorRotate | `Vector:VECTOR`, `Center:VECTOR`, `Axis:VECTOR`, `Angle:VALUE`, `Rotation:VECTOR` | `Vector:VECTOR` |
| ShaderNodeVectorTransform | `Vector:VECTOR` | `Vector:VECTOR` |
| ShaderNodeVertexColor | — | `Color:RGBA`, `Alpha:VALUE` |
| ShaderNodeVolumeAbsorption | `Color:RGBA`, `Density:VALUE`, `Weight:VALUE` | `Volume:SHADER` |
| ShaderNodeVolumeCoefficients | `Weight:VALUE`, `Absorption Coefficients:VECTOR`, `Scatter Coefficients:VECTOR`, `Anisotropy:VALUE`, `IOR:VALUE`, `Backscatter:VALUE`, `Alpha:VALUE`, `Diameter:VALUE`, `Emission Coefficients:VECTOR` | `Volume:SHADER` |
| ShaderNodeVolumeInfo | — | `Color:RGBA`, `Density:VALUE`, `Flame:VALUE`, `Temperature:VALUE` |
| ShaderNodeVolumePrincipled | `Color:RGBA`, `Color Attribute:STRING`, `Density:VALUE`, `Density Attribute:STRING`, `Anisotropy:VALUE`, `Absorption Color:RGBA`, `Emission Strength:VALUE`, `Emission Color:RGBA`, `Blackbody Intensity:VALUE`, `Blackbody Tint:RGBA`, `Temperature:VALUE`, `Temperature Attribute:STRING`, `Weight:VALUE` | `Volume:SHADER` |
| ShaderNodeVolumeScatter | `Color:RGBA`, `Density:VALUE`, `Anisotropy:VALUE`, `IOR:VALUE`, `Backscatter:VALUE`, `Alpha:VALUE`, `Diameter:VALUE`, `Weight:VALUE` | `Volume:SHADER` |
| ShaderNodeWavelength | `Wavelength:VALUE` | `Color:RGBA` |
| ShaderNodeWireframe | `Size:VALUE` | `Factor:VALUE` |

## GeometryNode（274，其中可实例化 264）

> node_tree：`geometry`

| 节点 | 输入 | 输出 |
|---|---|---|
| GeometryNodeAccumulateField | `Value:VALUE`, `Group ID:INT` | `Leading:VALUE`, `Trailing:VALUE`, `Total:VALUE` |
| GeometryNodeAttributeDomainSize | `Geometry:GEOMETRY` | `Point Count:INT`, `Edge Count:INT`, `Face Count:INT`, `Face Corner Count:INT`, `Spline Count:INT`, `Instance Count:INT`, `Layer Count:INT` |
| GeometryNodeAttributeStatistic | `Geometry:GEOMETRY`, `Selection:BOOLEAN`, `Attribute:VALUE` | `Mean:VALUE`, `Median:VALUE`, `Sum:VALUE`, `Min:VALUE`, `Max:VALUE`, `Range:VALUE`, `Standard Deviation:VALUE`, `Variance:VALUE` |
| GeometryNodeBake | `:CUSTOM` | `:CUSTOM` |
| GeometryNodeBlurAttribute | `Value:VALUE`, `Iterations:INT`, `Weight:VALUE` | `Value:VALUE` |
| GeometryNodeBoneInfo | `Armature:OBJECT`, `Bone Name:STRING` | `Pose:MATRIX`, `Local Pose:MATRIX`, `Transform Pose:MATRIX`, `Rest Pose:MATRIX`, `Rest Length:VALUE`, `Exists:BOOLEAN` |
| GeometryNodeBoundBox | `Geometry:GEOMETRY`, `Use Radius:BOOLEAN` | `Bounding Box:GEOMETRY`, `Min:VECTOR`, `Max:VECTOR` |
| GeometryNodeCameraInfo | `Camera:OBJECT` | `Projection Matrix:MATRIX`, `Focal Length:VALUE`, `Sensor:VECTOR`, `Shift:VECTOR`, `Clip Start:VALUE`, `Clip End:VALUE`, `Focus Distance:VALUE`, `Is Orthographic:BOOLEAN`, `Orthographic Scale:VALUE` |
| GeometryNodeCaptureAttribute | `Geometry:GEOMETRY`, `Selection:BOOLEAN`, `:CUSTOM` | `Geometry:GEOMETRY`, `Selection:BOOLEAN`, `:CUSTOM` |
| GeometryNodeClosureToList | `Count:INT`, `Closure:CLOSURE` | `:CUSTOM` |
| GeometryNodeClusterByConnected | `Selection:BOOLEAN`, `Position:VECTOR`, `Distance:VALUE` | `Cluster ID:INT` |
| GeometryNodeClusterByDistance | `Selection:BOOLEAN`, `Group ID:INT`, `Position:VECTOR`, `Distance:VALUE` | `Cluster ID:INT` |
| GeometryNodeCollectionChildren | `Collection:COLLECTION`, `Recursive:BOOLEAN` | `Collections:COLLECTION`, `Objects:OBJECT` |
| GeometryNodeCollectionInfo | `Collection:COLLECTION`, `Separate Children:BOOLEAN`, `Reset Children:BOOLEAN` | `Instances:GEOMETRY` |
| GeometryNodeConvexHull | `Geometry:GEOMETRY` | `Convex Hull:GEOMETRY` |
| GeometryNodeCornersOfEdge | `Edge Index:INT`, `Weights:VALUE`, `Sort Index:INT` | `Corner Index:INT`, `Total:INT` |
| GeometryNodeCornersOfFace | `Face Index:INT`, `Weights:VALUE`, `Sort Index:INT` | `Corner Index:INT`, `Total:INT` |
| GeometryNodeCornersOfVertex | `Vertex Index:INT`, `Weights:VALUE`, `Sort Index:INT` | `Corner Index:INT`, `Total:INT` |
| GeometryNodeCubeGridTopology | `Bounds Min:VECTOR`, `Bounds Max:VECTOR`, `Resolution X:INT`, `Resolution Y:INT`, `Resolution Z:INT`, `Min X:INT`, `Min Y:INT`, `Min Z:INT` | `Topology:BOOLEAN` |
| GeometryNodeCurveArc | `Resolution:INT`, `Start:VECTOR`, `Middle:VECTOR`, `End:VECTOR`, `Radius:VALUE`, `Start Angle:VALUE`, `Sweep Angle:VALUE`, `Offset Angle:VALUE`, `Connect Center:BOOLEAN`, `Invert Arc:BOOLEAN` | `Curve:GEOMETRY`, `Center:VECTOR`, `Normal:VECTOR`, `Radius:VALUE` |
| GeometryNodeCurveEndpointSelection | `Start Size:INT`, `End Size:INT` | `Selection:BOOLEAN` |
| GeometryNodeCurveHandleTypeSelection | — | `Selection:BOOLEAN` |
| GeometryNodeCurveLength | `Curve:GEOMETRY` | `Length:VALUE` |
| GeometryNodeCurveOfPoint | `Point Index:INT` | `Curve Index:INT`, `Index in Curve:INT` |
| GeometryNodeCurvePrimitiveBezierSegment | `Resolution:INT`, `Start:VECTOR`, `Start Handle:VECTOR`, `End Handle:VECTOR`, `End:VECTOR` | `Curve:GEOMETRY` |
| GeometryNodeCurvePrimitiveCircle | `Resolution:INT`, `Point 1:VECTOR`, `Point 2:VECTOR`, `Point 3:VECTOR`, `Radius:VALUE` | `Curve:GEOMETRY`, `Center:VECTOR` |
| GeometryNodeCurvePrimitiveLine | `Start:VECTOR`, `End:VECTOR`, `Direction:VECTOR`, `Length:VALUE` | `Curve:GEOMETRY` |
| GeometryNodeCurvePrimitiveQuadrilateral | `Width:VALUE`, `Height:VALUE`, `Bottom Width:VALUE`, `Top Width:VALUE`, `Offset:VALUE`, `Bottom Height:VALUE`, `Top Height:VALUE`, `Point 1:VECTOR`, `Point 2:VECTOR`, `Point 3:VECTOR`, `Point 4:VECTOR` | `Curve:GEOMETRY` |
| GeometryNodeCurveQuadraticBezier | `Resolution:INT`, `Start:VECTOR`, `Middle:VECTOR`, `End:VECTOR` | `Curve:GEOMETRY` |
| GeometryNodeCurveSetHandles | `Curve:GEOMETRY`, `Selection:BOOLEAN` | `Curve:GEOMETRY` |
| GeometryNodeCurveSpiral | `Resolution:INT`, `Rotations:VALUE`, `Start Radius:VALUE`, `End Radius:VALUE`, `Height:VALUE`, `Reverse:BOOLEAN` | `Curve:GEOMETRY` |
| GeometryNodeCurveSplineType | `Curve:GEOMETRY`, `Selection:BOOLEAN` | `Curve:GEOMETRY` |
| GeometryNodeCurveStar | `Points:INT`, `Inner Radius:VALUE`, `Outer Radius:VALUE`, `Twist:VALUE` | `Curve:GEOMETRY`, `Outer Points:BOOLEAN` |
| GeometryNodeCurveToMesh | `Curve:GEOMETRY`, `Profile Curve:GEOMETRY`, `Scale:VALUE`, `Fill Caps:BOOLEAN` | `Mesh:GEOMETRY` |
| GeometryNodeCurveToPoints | `Curve:GEOMETRY`, `Count:INT`, `Length:VALUE` | `Points:GEOMETRY`, `Tangent:VECTOR`, `Normal:VECTOR`, `Rotation:ROTATION` |
| GeometryNodeCurvesToGreasePencil | `Curves:GEOMETRY`, `Selection:BOOLEAN`, `Instances as Layers:BOOLEAN` | `Grease Pencil:GEOMETRY` |
| GeometryNodeDeformCurvesOnSurface | `Curves:GEOMETRY` | `Curves:GEOMETRY` |
| GeometryNodeDeleteGeometry | `Geometry:GEOMETRY`, `Selection:BOOLEAN` | `Geometry:GEOMETRY` |
| GeometryNodeDistributePointsInGrid | `Grid:VALUE`, `Density:VALUE`, `Seed:INT`, `Spacing:VECTOR`, `Threshold:VALUE` | `Points:GEOMETRY` |
| GeometryNodeDistributePointsInVolume | `Volume:GEOMETRY`, `Mode:MENU`, `Density:VALUE`, `Seed:INT`, `Spacing:VECTOR`, `Threshold:VALUE` | `Points:GEOMETRY` |
| GeometryNodeDistributePointsOnFaces | `Mesh:GEOMETRY`, `Selection:BOOLEAN`, `Distance Min:VALUE`, `Density Max:VALUE`, `Density:VALUE`, `Density Factor:VALUE`, `Seed:INT` | `Points:GEOMETRY`, `Normal:VECTOR`, `Rotation:ROTATION` |
| GeometryNodeDualMesh | `Mesh:GEOMETRY`, `Keep Boundaries:BOOLEAN` | `Dual Mesh:GEOMETRY` |
| GeometryNodeDuplicateElements | `Geometry:GEOMETRY`, `Selection:BOOLEAN`, `Amount:INT` | `Geometry:GEOMETRY`, `Duplicate Index:INT` |
| GeometryNodeEdgePathsToCurves | `Mesh:GEOMETRY`, `Start Vertices:BOOLEAN`, `Next Vertex Index:INT` | `Curves:GEOMETRY` |
| GeometryNodeEdgePathsToSelection | `Start Vertices:BOOLEAN`, `Next Vertex Index:INT` | `Selection:BOOLEAN` |
| GeometryNodeEdgesOfCorner | `Corner Index:INT` | `Next Edge Index:INT`, `Previous Edge Index:INT` |
| GeometryNodeEdgesOfVertex | `Vertex Index:INT`, `Weights:VALUE`, `Sort Index:INT` | `Edge Index:INT`, `Total:INT` |
| GeometryNodeEdgesToFaceGroups | `Boundary Edges:BOOLEAN` | `Face Group ID:INT` |
| GeometryNodeExtrudeMesh | `Mesh:GEOMETRY`, `Selection:BOOLEAN`, `Offset:VECTOR`, `Offset Scale:VALUE`, `Individual:BOOLEAN` | `Mesh:GEOMETRY`, `Top:BOOLEAN`, `Side:BOOLEAN` |
| GeometryNodeFaceOfCorner | `Corner Index:INT` | `Face Index:INT`, `Index in Face:INT` |
| GeometryNodeFieldAtIndex | `Value:VALUE`, `Index:INT` | `Value:VALUE` |
| GeometryNodeFieldAverage | `Value:VALUE`, `Group ID:INT` | `Mean:VALUE`, `Median:VALUE` |
| GeometryNodeFieldMinAndMax | `Value:VALUE`, `Group ID:INT` | `Min:VALUE`, `Max:VALUE` |
| GeometryNodeFieldOnDomain | `Value:VALUE` | `Value:VALUE` |
| GeometryNodeFieldToGrid | `Topology:VALUE`, `:CUSTOM` | `:CUSTOM` |
| GeometryNodeFieldToList | `Count:INT`, `:CUSTOM` | `:CUSTOM` |
| GeometryNodeFieldVariance | `Value:VALUE`, `Group ID:INT` | `Standard Deviation:VALUE`, `Variance:VALUE` |
| GeometryNodeFillCurve | `Curve:GEOMETRY`, `Group ID:INT`, `Mode:MENU`, `Fill Rule:MENU` | `Mesh:GEOMETRY` |
| GeometryNodeFilletCurve | `Curve:GEOMETRY`, `Radius:VALUE`, `Limit Radius:BOOLEAN`, `Mode:MENU`, `Count:INT` | `Curve:GEOMETRY` |
| GeometryNodeFilterList | `List:VALUE`, `Selection:BOOLEAN` | `Selection:VALUE`, `Inverted:VALUE` |
| GeometryNodeFlipFaces | `Mesh:GEOMETRY`, `Selection:BOOLEAN` | `Mesh:GEOMETRY` |
| GeometryNodeForeachGeometryElementInput | `Geometry:GEOMETRY`, `Selection:BOOLEAN`, `:CUSTOM` | `Index:INT`, `Element:GEOMETRY`, `:CUSTOM` |
| GeometryNodeForeachGeometryElementOutput | `:CUSTOM`, `Geometry:GEOMETRY`, `:CUSTOM` | `Geometry:GEOMETRY`, `:CUSTOM`, `Geometry:GEOMETRY`, `:CUSTOM` |
| GeometryNodeGeometryToInstance | `Geometry:GEOMETRY`* | `Instances:GEOMETRY` |
| GeometryNodeGetAttributeNames | `Geometry:GEOMETRY`, `Filter Data Type:BOOLEAN`, `Data Type:MENU`, `Filter Domain:BOOLEAN`, `Domain:MENU` | `Names:STRING` |
| GeometryNodeGetGeometryBundle | `Geometry:GEOMETRY`, `Remove:BOOLEAN` | `Geometry:GEOMETRY`, `Bundle:BUNDLE` |
| GeometryNodeGetGeometryComponent | `Geometry:GEOMETRY`, `Type:MENU`, `Remove:BOOLEAN` | `Geometry:GEOMETRY`, `Component:GEOMETRY`, `Exists:BOOLEAN` |
| GeometryNodeGetNamedGrid | `Volume:GEOMETRY`, `Name:STRING`, `Remove:BOOLEAN` | `Volume:GEOMETRY`, `Grid:VALUE` |
| GeometryNodeGizmoDial | `Value:VALUE`*, `Position:VECTOR`, `Up:VECTOR`, `Screen Space:BOOLEAN`, `Radius:VALUE` | `Transform:GEOMETRY` |
| GeometryNodeGizmoLinear | `Value:VALUE`*, `Position:VECTOR`, `Direction:VECTOR` | `Transform:GEOMETRY` |
| GeometryNodeGizmoTransform | `Value:MATRIX`*, `Position:VECTOR`, `Rotation:ROTATION` | `Transform:GEOMETRY` |
| GeometryNodeGreasePencilToCurves | `Grease Pencil:GEOMETRY`, `Selection:BOOLEAN`, `Layers as Instances:BOOLEAN` | `Curves:GEOMETRY` |
| GeometryNodeGridAdvect | `Grid:VALUE`, `Velocity:VECTOR`, `Time Step:VALUE`, `Integration Scheme:MENU`, `Limiter:MENU` | `Grid:VALUE` |
| GeometryNodeGridClip | `Grid:VALUE`, `Min X:INT`, `Min Y:INT`, `Min Z:INT`, `Max X:INT`, `Max Y:INT`, `Max Z:INT` | `Grid:VALUE` |
| GeometryNodeGridCurl | `Grid:VECTOR` | `Curl:VECTOR` |
| GeometryNodeGridDilateAndErode | `Grid:VALUE`, `Connectivity:MENU`, `Tiles:MENU`, `Steps:INT` | `Grid:VALUE` |
| GeometryNodeGridDivergence | `Grid:VECTOR` | `Divergence:VALUE` |
| GeometryNodeGridGradient | `Grid:VALUE` | `Gradient:VECTOR` |
| GeometryNodeGridInfo | `Grid:VALUE` | `Transform:MATRIX`, `Background Value:VALUE` |
| GeometryNodeGridLaplacian | `Grid:VALUE` | `Laplacian:VALUE` |
| GeometryNodeGridMean | `Grid:VALUE`, `Width:INT`, `Iterations:INT` | `Grid:VALUE` |
| GeometryNodeGridMedian | `Grid:VALUE`, `Width:INT`, `Iterations:INT` | `Grid:VALUE` |
| GeometryNodeGridPrune | `Grid:VALUE`, `Mode:MENU`, `Threshold:VALUE` | `Grid:VALUE` |
| GeometryNodeGridToMesh | `Grid:VALUE`, `Threshold:VALUE`, `Adaptivity:VALUE` | `Mesh:GEOMETRY` |
| GeometryNodeGridToPoints | `Grid:VALUE` | `Points:GEOMETRY`, `Value:VALUE`, `X:INT`, `Y:INT`, `Z:INT`, `Is Tile:BOOLEAN`, `Extent:INT` |
| GeometryNodeGridVoxelize | `Grid:VALUE` | `Grid:VALUE` |
| GeometryNodeGroup | — | — |
| GeometryNodeImageInfo | `Image:IMAGE`, `Frame:INT` | `Width:INT`, `Height:INT`, `Has Alpha:BOOLEAN`, `Frame Count:INT`, `FPS:VALUE` |
| GeometryNodeImageTexture | `Image:IMAGE`, `Vector:VECTOR`, `Frame:INT` | `Color:RGBA`, `Alpha:VALUE` |
| GeometryNodeImportCSV | `Path:STRING`, `Delimiter:STRING` | `Point Cloud:GEOMETRY` |
| GeometryNodeImportOBJ | `Path:STRING` | `Instances:GEOMETRY` |
| GeometryNodeImportPLY | `Path:STRING` | `Mesh:GEOMETRY` |
| GeometryNodeImportSTL | `Path:STRING` | `Mesh:GEOMETRY` |
| GeometryNodeImportText | `Path:STRING` | `String:STRING` |
| GeometryNodeImportVDB | `Path:STRING` | `Volume:GEOMETRY` |
| GeometryNodeIndexOfNearest | `Position:VECTOR`, `Group ID:INT` | `Index:INT`, `Has Neighbor:BOOLEAN` |
| GeometryNodeIndexSwitch | `Index:INT`, `0:VALUE`, `1:VALUE`, `:CUSTOM` | `Output:VALUE` |
| GeometryNodeInputActiveCamera | — | `Active Camera:OBJECT` |
| GeometryNodeInputCollection | — | `Collection:COLLECTION` |
| GeometryNodeInputCurveHandlePositions | `Relative:BOOLEAN` | `Left:VECTOR`, `Right:VECTOR` |
| GeometryNodeInputCurveTilt | — | `Tilt:VALUE` |
| GeometryNodeInputEdgeSmooth | — | `Smooth:BOOLEAN` |
| GeometryNodeInputFont | — | `Font:FONT` |
| GeometryNodeInputID | — | `ID:INT` |
| GeometryNodeInputImage | — | `Image:IMAGE` |
| GeometryNodeInputIndex | — | `Index:INT` |
| GeometryNodeInputInstanceBounds | `Use Radius:BOOLEAN` | `Min:VECTOR`, `Max:VECTOR` |
| GeometryNodeInputInstanceReference | — | `Reference Index:INT` |
| GeometryNodeInputInstanceRotation | — | `Rotation:ROTATION` |
| GeometryNodeInputInstanceScale | — | `Scale:VECTOR` |
| GeometryNodeInputMaterial | — | `Material:MATERIAL` |
| GeometryNodeInputMaterialIndex | — | `Material Index:INT` |
| GeometryNodeInputMeshEdgeAngle | — | `Unsigned Angle:VALUE`, `Signed Angle:VALUE` |
| GeometryNodeInputMeshEdgeNeighbors | — | `Face Count:INT` |
| GeometryNodeInputMeshEdgeVertices | — | `Vertex Index 1:INT`, `Vertex Index 2:INT`, `Position 1:VECTOR`, `Position 2:VECTOR` |
| GeometryNodeInputMeshFaceArea | — | `Area:VALUE` |
| GeometryNodeInputMeshFaceIsPlanar | `Threshold:VALUE` | `Planar:BOOLEAN` |
| GeometryNodeInputMeshFaceNeighbors | — | `Vertex Count:INT`, `Face Count:INT` |
| GeometryNodeInputMeshIsland | — | `Island Index:INT`, `Island Count:INT` |
| GeometryNodeInputMeshVertexNeighbors | — | `Vertex Count:INT`, `Face Count:INT` |
| GeometryNodeInputNamedAttribute | `Name:STRING` | `Attribute:VALUE`, `Exists:BOOLEAN` |
| GeometryNodeInputNamedLayerSelection | `Name:STRING` | `Selection:BOOLEAN` |
| GeometryNodeInputNormal | — | `Normal:VECTOR`, `True Normal:VECTOR` |
| GeometryNodeInputObject | — | `Object:OBJECT` |
| GeometryNodeInputPosition | — | `Position:VECTOR` |
| GeometryNodeInputRadius | — | `Radius:VALUE` |
| GeometryNodeInputSceneTime | — | `Seconds:VALUE`, `Frame:VALUE` |
| GeometryNodeInputShadeSmooth | — | `Smooth:BOOLEAN` |
| GeometryNodeInputShortestEdgePaths | `End Vertex:BOOLEAN`, `Edge Cost:VALUE` | `Next Vertex Index:INT`, `Total Cost:VALUE` |
| GeometryNodeInputSplineCyclic | — | `Cyclic:BOOLEAN` |
| GeometryNodeInputSplineResolution | — | `Resolution:INT` |
| GeometryNodeInputTangent | — | `Tangent:VECTOR` |
| GeometryNodeInputVoxelIndex | — | `X:INT`, `Y:INT`, `Z:INT`, `Is Tile:BOOLEAN`, `Extent X:INT`, `Extent Y:INT`, `Extent Z:INT` |
| GeometryNodeInstanceOnPoints | `Points:GEOMETRY`, `Selection:BOOLEAN`, `Instance:GEOMETRY`, `Pick Instance:BOOLEAN`, `Instance Index:INT`, `Rotation:ROTATION`, `Scale:VECTOR` | `Instances:GEOMETRY` |
| GeometryNodeInstanceTransform | — | `Transform:MATRIX` |
| GeometryNodeInstancesToPoints | `Instances:GEOMETRY`, `Selection:BOOLEAN`, `Position:VECTOR`, `Radius:VALUE` | `Points:GEOMETRY` |
| GeometryNodeInterpolateCurves | `Guide Curves:GEOMETRY`, `Guide Up:VECTOR`, `Guide Group ID:INT`, `Points:GEOMETRY`, `Point Up:VECTOR`, `Point Group ID:INT`, `Max Neighbors:INT` | `Curves:GEOMETRY`, `Closest Index:INT`, `Closest Weight:VALUE` |
| GeometryNodeIsViewport | — | `Is Viewport:BOOLEAN` |
| GeometryNodeJoinGeometry | `Geometry:GEOMETRY`* | `Geometry:GEOMETRY` |
| GeometryNodeListGetItem | `List:VALUE`, `Index:INT` | `Value:VALUE` |
| GeometryNodeListLength | `List:VALUE` | `Length:INT` |
| GeometryNodeMaterialSelection | `Material:MATERIAL` | `Selection:BOOLEAN` |
| GeometryNodeMenuSwitch | `Menu:MENU`, `A:GEOMETRY`, `B:GEOMETRY`, `:CUSTOM` | `Output:GEOMETRY`, `A:BOOLEAN`, `B:BOOLEAN` |
| GeometryNodeMergeByDistance | `Geometry:GEOMETRY`, `Selection:BOOLEAN`, `Mode:MENU`, `Distance:VALUE` | `Geometry:GEOMETRY` |
| GeometryNodeMergeLayers | `Grease Pencil:GEOMETRY`, `Selection:BOOLEAN`, `Group ID:INT` | `Grease Pencil:GEOMETRY` |
| GeometryNodeMergePoints | `Geometry:GEOMETRY`, `Selection:BOOLEAN`, `Merge ID:INT` | `Geometry:GEOMETRY` |
| GeometryNodeMeshBevel | `Mesh:GEOMETRY`, `Selection:BOOLEAN`, `Affect Kind:MENU`, `Start Left Offset:VALUE`, `Start Right Offset:VALUE`, `End Left Offset:VALUE`, `End Right Offset:VALUE`, `Offset:VALUE`, `Miter:BOOLEAN`, `Spread:VALUE`, `Segments:INT`, `Shape:VALUE`, `Profile:GEOMETRY` | `Mesh:GEOMETRY`, `Vertex Face:BOOLEAN`, `Edge Face:BOOLEAN`, `Outer Edge:BOOLEAN`, `Mid Edge:BOOLEAN` |
| GeometryNodeMeshBoolean | `Mesh 1:GEOMETRY`, `Mesh 2:GEOMETRY`*, `Self Intersection:BOOLEAN`, `Hole Tolerant:BOOLEAN` | `Mesh:GEOMETRY`, `Intersecting Edges:BOOLEAN` |
| GeometryNodeMeshCircle | `Vertices:INT`, `Radius:VALUE` | `Mesh:GEOMETRY` |
| GeometryNodeMeshCone | `Vertices:INT`, `Side Segments:INT`, `Fill Segments:INT`, `Radius Top:VALUE`, `Radius Bottom:VALUE`, `Depth:VALUE` | `Mesh:GEOMETRY`, `Top:BOOLEAN`, `Bottom:BOOLEAN`, `Side:BOOLEAN`, `UV Map:VECTOR` |
| GeometryNodeMeshCube | `Size:VECTOR`, `Vertices X:INT`, `Vertices Y:INT`, `Vertices Z:INT` | `Mesh:GEOMETRY`, `UV Map:VECTOR` |
| GeometryNodeMeshCylinder | `Vertices:INT`, `Side Segments:INT`, `Fill Segments:INT`, `Radius:VALUE`, `Depth:VALUE` | `Mesh:GEOMETRY`, `Top:BOOLEAN`, `Side:BOOLEAN`, `Bottom:BOOLEAN`, `UV Map:VECTOR` |
| GeometryNodeMeshFaceSetBoundaries | `Face Group ID:INT` | `Boundary Edges:BOOLEAN` |
| GeometryNodeMeshGrid | `Size X:VALUE`, `Size Y:VALUE`, `Vertices X:INT`, `Vertices Y:INT` | `Mesh:GEOMETRY`, `UV Map:VECTOR` |
| GeometryNodeMeshIcoSphere | `Radius:VALUE`, `Subdivisions:INT` | `Mesh:GEOMETRY`, `UV Map:VECTOR` |
| GeometryNodeMeshLine | `Count:INT`, `Resolution:VALUE`, `Start Location:VECTOR`, `Offset:VECTOR` | `Mesh:GEOMETRY` |
| GeometryNodeMeshToCurve | `Mesh:GEOMETRY`, `Selection:BOOLEAN` | `Curve:GEOMETRY` |
| GeometryNodeMeshToDensityGrid | `Mesh:GEOMETRY`, `Density:VALUE`, `Voxel Size:VALUE`, `Gradient Width:VALUE` | `Density Grid:VALUE` |
| GeometryNodeMeshToPoints | `Mesh:GEOMETRY`, `Selection:BOOLEAN`, `Position:VECTOR`, `Radius:VALUE` | `Points:GEOMETRY` |
| GeometryNodeMeshToSDFGrid | `Mesh:GEOMETRY`, `Voxel Size:VALUE`, `Band Width:INT` | `SDF Grid:VALUE` |
| GeometryNodeMeshToVolume | `Mesh:GEOMETRY`, `Density:VALUE`, `Resolution Mode:MENU`, `Voxel Size:VALUE`, `Voxel Amount:VALUE`, `Interior Band Width:VALUE` | `Volume:GEOMETRY` |
| GeometryNodeMeshUVSphere | `Segments:INT`, `Rings:INT`, `Radius:VALUE` | `Mesh:GEOMETRY`, `UV Map:VECTOR` |
| GeometryNodeObjectInfo | `Object:OBJECT`, `As Instance:BOOLEAN` | `Transform:MATRIX`, `Location:VECTOR`, `Rotation:ROTATION`, `Scale:VECTOR`, `Geometry:GEOMETRY` |
| GeometryNodeOffsetCornerInFace | `Corner Index:INT`, `Offset:INT` | `Corner Index:INT` |
| GeometryNodeOffsetPointInCurve | `Point Index:INT`, `Offset:INT` | `Is Valid Offset:BOOLEAN`, `Point Index:INT` |
| GeometryNodePoints | `Count:INT`, `Position:VECTOR`, `Radius:VALUE` | `Points:GEOMETRY` |
| GeometryNodePointsOfCurve | `Curve Index:INT`, `Weights:VALUE`, `Sort Index:INT` | `Point Index:INT`, `Total:INT` |
| GeometryNodePointsToCurves | `Points:GEOMETRY`, `Curve Group ID:INT`, `Weight:VALUE` | `Curves:GEOMETRY` |
| GeometryNodePointsToSDFGrid | `Points:GEOMETRY`, `Radius:VALUE`, `Voxel Size:VALUE` | `SDF Grid:VALUE` |
| GeometryNodePointsToVertices | `Points:GEOMETRY`, `Selection:BOOLEAN` | `Mesh:GEOMETRY` |
| GeometryNodePointsToVolume | `Points:GEOMETRY`, `Density:VALUE`, `Resolution Mode:MENU`, `Voxel Size:VALUE`, `Voxel Amount:VALUE`, `Radius:VALUE` | `Volume:GEOMETRY` |
| GeometryNodeProximity | `Geometry:GEOMETRY`, `Group ID:INT`, `Sample Position:VECTOR`, `Sample Group ID:INT` | `Position:VECTOR`, `Distance:VALUE`, `Is Valid:BOOLEAN` |
| GeometryNodeRaycast | `Target Geometry:GEOMETRY`, `Attribute:VALUE`, `Interpolation:MENU`, `Source Position:VECTOR`, `Ray Direction:VECTOR`, `Ray Length:VALUE` | `Is Hit:BOOLEAN`, `Hit Position:VECTOR`, `Hit Normal:VECTOR`, `Hit Distance:VALUE`, `Attribute:VALUE` |
| GeometryNodeRealizeInstances | `Geometry:GEOMETRY`, `Selection:BOOLEAN`, `Realize All:BOOLEAN`, `Depth:INT` | `Geometry:GEOMETRY` |
| GeometryNodeRemoveAttribute | `Geometry:GEOMETRY`, `Pattern Mode:MENU`, `Name:STRING` | `Geometry:GEOMETRY` |
| GeometryNodeRenameAttribute | `Geometry:GEOMETRY`, `Mode:MENU`, `Old:STRING`, `New:STRING`, `Overwrite:BOOLEAN` | `Geometry:GEOMETRY` |
| GeometryNodeRepeatInput | `Iterations:INT`, `:CUSTOM` | `Iteration:INT`, `:CUSTOM` |
| GeometryNodeRepeatOutput | `Geometry:GEOMETRY`, `:CUSTOM` | `Geometry:GEOMETRY`, `:CUSTOM` |
| GeometryNodeReplaceMaterial | `Geometry:GEOMETRY`, `Old:MATERIAL`, `New:MATERIAL` | `Geometry:GEOMETRY` |
| GeometryNodeResampleCurve | `Curve:GEOMETRY`, `Selection:BOOLEAN`, `Mode:MENU`, `Count:INT`, `Length:VALUE` | `Curve:GEOMETRY` |
| GeometryNodeReverseCurve | `Curve:GEOMETRY`, `Selection:BOOLEAN` | `Curve:GEOMETRY` |
| GeometryNodeRotateInstances | `Instances:GEOMETRY`, `Selection:BOOLEAN`, `Rotation:ROTATION`, `Pivot Point:VECTOR`, `Local Space:BOOLEAN` | `Instances:GEOMETRY` |
| GeometryNodeSDFGridBoolean | `Grid 1:VALUE`, `Grid 2:VALUE`* | `Grid:VALUE` |
| GeometryNodeSDFGridFillet | `Grid:VALUE`, `Iterations:INT` | `Grid:VALUE` |
| GeometryNodeSDFGridLaplacian | `Grid:VALUE`, `Iterations:INT` | `Grid:VALUE` |
| GeometryNodeSDFGridMean | `Grid:VALUE`, `Width:INT`, `Iterations:INT` | `Grid:VALUE` |
| GeometryNodeSDFGridMeanCurvature | `Grid:VALUE`, `Iterations:INT` | `Grid:VALUE` |
| GeometryNodeSDFGridMedian | `Grid:VALUE`, `Width:INT`, `Iterations:INT` | `Grid:VALUE` |
| GeometryNodeSDFGridOffset | `Grid:VALUE`, `Distance:VALUE` | `Grid:VALUE` |
| GeometryNodeSampleCurve | `Curves:GEOMETRY`, `Value:VALUE`, `Factor:VALUE`, `Length:VALUE`, `Curve Index:INT` | `Value:VALUE`, `Position:VECTOR`, `Tangent:VECTOR`, `Normal:VECTOR` |
| GeometryNodeSampleGrid | `Grid:VALUE`, `Position:VECTOR`, `Interpolation:MENU` | `Value:VALUE` |
| GeometryNodeSampleGridIndex | `Grid:VALUE`, `X:INT`, `Y:INT`, `Z:INT` | `Value:VALUE` |
| GeometryNodeSampleIndex | `Geometry:GEOMETRY`, `Value:VALUE`, `Index:INT` | `Value:VALUE` |
| GeometryNodeSampleNearest | `Geometry:GEOMETRY`, `Sample Position:VECTOR` | `Index:INT` |
| GeometryNodeSampleNearestSurface | `Mesh:GEOMETRY`, `Value:VALUE`, `Group ID:INT`, `Sample Position:VECTOR`, `Sample Group ID:INT` | `Value:VALUE`, `Is Valid:BOOLEAN` |
| GeometryNodeSampleSoundFrequencies | `Sound:SOUND`, `Time:VALUE`, `All Channels:BOOLEAN`, `Channel:INT`, `Low:VALUE`, `High:VALUE`, `FFT Size:MENU`, `Window Function:MENU` | `Amplitude:VALUE` |
| GeometryNodeSampleUVSurface | `Mesh:GEOMETRY`, `Value:VALUE`, `UV Map:VECTOR`, `Sample UV:VECTOR` | `Value:VALUE`, `Is Valid:BOOLEAN` |
| GeometryNodeScaleElements | `Geometry:GEOMETRY`, `Selection:BOOLEAN`, `Scale:VALUE`, `Center:VECTOR`, `Scale Mode:MENU`, `Axis:VECTOR` | `Geometry:GEOMETRY` |
| GeometryNodeScaleInstances | `Instances:GEOMETRY`, `Selection:BOOLEAN`, `Scale:VECTOR`, `Center:VECTOR`, `Local Space:BOOLEAN` | `Instances:GEOMETRY` |
| GeometryNodeSelfObject | — | `Self Object:OBJECT` |
| GeometryNodeSeparateComponents | `Geometry:GEOMETRY` | `Mesh:GEOMETRY`, `Curve:GEOMETRY`, `Grease Pencil:GEOMETRY`, `Point Cloud:GEOMETRY`, `Volume:GEOMETRY`, `Instances:GEOMETRY` |
| GeometryNodeSeparateGeometry | `Geometry:GEOMETRY`, `Selection:BOOLEAN` | `Selection:GEOMETRY`, `Inverted:GEOMETRY` |
| GeometryNodeSetCurveHandlePositions | `Curve:GEOMETRY`, `Selection:BOOLEAN`, `Position:VECTOR`, `Offset:VECTOR` | `Curve:GEOMETRY` |
| GeometryNodeSetCurveNormal | `Curve:GEOMETRY`, `Selection:BOOLEAN`, `Mode:MENU`, `Normal:VECTOR` | `Curve:GEOMETRY` |
| GeometryNodeSetCurveRadius | `Curve:GEOMETRY`, `Selection:BOOLEAN`, `Radius:VALUE` | `Curve:GEOMETRY` |
| GeometryNodeSetCurveTilt | `Curve:GEOMETRY`, `Selection:BOOLEAN`, `Tilt:VALUE` | `Curve:GEOMETRY` |
| GeometryNodeSetGeometryBundle | `Geometry:GEOMETRY`, `Bundle:BUNDLE` | `Geometry:GEOMETRY` |
| GeometryNodeSetGeometryName | `Geometry:GEOMETRY`, `Name:STRING` | `Geometry:GEOMETRY` |
| GeometryNodeSetGreasePencilColor | `Grease Pencil:GEOMETRY`, `Selection:BOOLEAN`, `Color:RGBA`, `Opacity:VALUE` | `Grease Pencil:GEOMETRY` |
| GeometryNodeSetGreasePencilDepth | `Grease Pencil:GEOMETRY` | `Grease Pencil:GEOMETRY` |
| GeometryNodeSetGreasePencilSoftness | `Grease Pencil:GEOMETRY`, `Selection:BOOLEAN`, `Softness:VALUE` | `Grease Pencil:GEOMETRY` |
| GeometryNodeSetGridBackground | `Grid:VALUE`, `Background:VALUE`, `Update Inactive:BOOLEAN` | `Grid:VALUE` |
| GeometryNodeSetGridTransform | `Grid:VALUE`, `Transform:MATRIX` | `Is Valid:BOOLEAN`, `Grid:VALUE` |
| GeometryNodeSetID | `Geometry:GEOMETRY`, `Selection:BOOLEAN`, `ID:INT` | `Geometry:GEOMETRY` |
| GeometryNodeSetInstanceTransform | `Instances:GEOMETRY`, `Selection:BOOLEAN`, `Transform:MATRIX` | `Instances:GEOMETRY` |
| GeometryNodeSetMaterial | `Geometry:GEOMETRY`, `Selection:BOOLEAN`, `Material:MATERIAL` | `Geometry:GEOMETRY` |
| GeometryNodeSetMaterialIndex | `Geometry:GEOMETRY`, `Selection:BOOLEAN`, `Material Index:INT` | `Geometry:GEOMETRY` |
| GeometryNodeSetMeshNormal | `Mesh:GEOMETRY`, `Remove Custom:BOOLEAN`, `Edge Sharpness:BOOLEAN`, `Face Sharpness:BOOLEAN` | `Mesh:GEOMETRY` |
| GeometryNodeSetNURBSOrder | `Curves:GEOMETRY`, `Selection:BOOLEAN`, `Order:INT` | `Curves:GEOMETRY` |
| GeometryNodeSetNURBSWeight | `Curves:GEOMETRY`, `Selection:BOOLEAN`, `Weight:VALUE` | `Curves:GEOMETRY` |
| GeometryNodeSetPointRadius | `Points:GEOMETRY`, `Selection:BOOLEAN`, `Radius:VALUE` | `Points:GEOMETRY` |
| GeometryNodeSetPosition | `Geometry:GEOMETRY`, `Selection:BOOLEAN`, `Position:VECTOR`, `Offset:VECTOR` | `Geometry:GEOMETRY` |
| GeometryNodeSetShadeSmooth | `Mesh:GEOMETRY`, `Selection:BOOLEAN`, `Shade Smooth:BOOLEAN` | `Mesh:GEOMETRY` |
| GeometryNodeSetSplineCyclic | `Curve:GEOMETRY`, `Selection:BOOLEAN`, `Cyclic:BOOLEAN` | `Curve:GEOMETRY` |
| GeometryNodeSetSplineResolution | `Curve:GEOMETRY`, `Selection:BOOLEAN`, `Resolution:INT` | `Curve:GEOMETRY` |
| GeometryNodeSimulationInput | — | `Delta Time:VALUE` |
| GeometryNodeSimulationOutput | `Skip:BOOLEAN`, `Geometry:GEOMETRY`, `:CUSTOM` | `Geometry:GEOMETRY`, `:CUSTOM` |
| GeometryNodeSortElements | `Geometry:GEOMETRY`, `Selection:BOOLEAN`, `Group ID:INT`, `Sort Weight:VALUE` | `Geometry:GEOMETRY` |
| GeometryNodeSortList | `List:VALUE`, `Selection:BOOLEAN`, `Group ID:INT`, `Sort Weight:VALUE` | `List:VALUE` |
| GeometryNodeSplineLength | — | `Length:VALUE`, `Point Count:INT` |
| GeometryNodeSplineParameter | — | `Factor:VALUE`, `Length:VALUE`, `Index:INT` |
| GeometryNodeSplitEdges | `Mesh:GEOMETRY`, `Selection:BOOLEAN` | `Mesh:GEOMETRY` |
| GeometryNodeSplitToInstances | `Geometry:GEOMETRY`, `Selection:BOOLEAN`, `Group ID:INT` | `Instances:GEOMETRY`, `Group ID:INT` |
| GeometryNodeStoreNamedAttribute | `Geometry:GEOMETRY`, `Selection:BOOLEAN`, `Name:STRING`, `Value:VALUE` | `Geometry:GEOMETRY` |
| GeometryNodeStoreNamedGrid | `Volume:GEOMETRY`, `Name:STRING`, `Grid:VALUE` | `Volume:GEOMETRY` |
| GeometryNodeStringJoin | `Delimiter:STRING`, `Strings:STRING`* | `String:STRING` |
| GeometryNodeStringToCurves | `String:STRING`, `Size:VALUE`, `Font:FONT`, `Align X:MENU`, `Align Y:MENU`, `Pivot Point:MENU`, `Character Spacing:VALUE`, `Word Spacing:VALUE`, `Line Spacing:VALUE`, `Overflow:MENU`, `Text Box Width:VALUE`, `Text Box Height:VALUE` | `Curve Instances:GEOMETRY`, `Remainder:STRING`, `Line:INT`, `Word:INT`, `Pivot Point:VECTOR` |
| GeometryNodeSubdivideCurve | `Curve:GEOMETRY`, `Cuts:INT` | `Curve:GEOMETRY` |
| GeometryNodeSubdivideMesh | `Mesh:GEOMETRY`, `Level:INT` | `Mesh:GEOMETRY` |
| GeometryNodeSubdivisionSurface | `Mesh:GEOMETRY`, `Level:INT`, `Edge Crease:VALUE`, `Vertex Crease:VALUE`, `Limit Surface:BOOLEAN`, `Quality:INT`, `UV Smooth:MENU`, `Boundary Smooth:MENU` | `Mesh:GEOMETRY` |
| GeometryNodeSwitch | `Switch:BOOLEAN`, `False:VALUE`, `True:VALUE` | `Output:VALUE` |
| GeometryNodeTagFilter | `Tag Filter:STRING`, `Tags:STRING` | `Match:BOOLEAN` |
| GeometryNodeTool3DCursor | — | `Location:VECTOR`, `Rotation:ROTATION` |
| GeometryNodeToolActiveElement | — | `Index:INT`, `Exists:BOOLEAN` |
| GeometryNodeToolFaceSet | — | `Face Set:INT`, `Exists:BOOLEAN` |
| GeometryNodeToolMousePosition | — | `Mouse X:INT`, `Mouse Y:INT`, `Region Width:INT`, `Region Height:INT` |
| GeometryNodeToolSelection | — | `Boolean:BOOLEAN`, `Float:VALUE` |
| GeometryNodeToolSetFaceSet | `Mesh:GEOMETRY`, `Selection:BOOLEAN`, `Face Set:INT` | `Mesh:GEOMETRY` |
| GeometryNodeToolSetSelection | `Geometry:GEOMETRY`, `Selection:BOOLEAN` | `Geometry:GEOMETRY` |
| GeometryNodeTransferAttributes | `Target:GEOMETRY`, `Target Point ID:INT`, `Target Edge ID:INT`, `Target Face ID:INT`, `Target Corner ID:INT`, `Target Curve ID:INT`, `Target Instance ID:INT`, `Source:GEOMETRY`, `Source Point ID:INT`, `Source Edge ID:INT`, `Source Face ID:INT`, `Source Corner ID:INT`, `Source Curve ID:INT`, `Source Instance ID:INT`, `Pattern Mode:MENU`, `Attribute Names:STRING`, `Exclude Names:BOOLEAN` | `Target:GEOMETRY`, `Transferred Names:STRING` |
| GeometryNodeTransform | `Geometry:GEOMETRY`, `Mode:MENU`, `Translation:VECTOR`, `Rotation:ROTATION`, `Scale:VECTOR`, `Transform:MATRIX` | `Geometry:GEOMETRY` |
| GeometryNodeTranslateInstances | `Instances:GEOMETRY`, `Selection:BOOLEAN`, `Translation:VECTOR`, `Local Space:BOOLEAN` | `Instances:GEOMETRY` |
| GeometryNodeTriangulate | `Mesh:GEOMETRY`, `Selection:BOOLEAN`, `Quad Method:MENU`, `N-gon Method:MENU` | `Mesh:GEOMETRY` |
| GeometryNodeTrimCurve | `Curve:GEOMETRY`, `Selection:BOOLEAN`, `Start:VALUE`, `End:VALUE`, `Start:VALUE`, `End:VALUE` | `Curve:GEOMETRY` |
| GeometryNodeUVPackIslands | `UV:VECTOR`, `Selection:BOOLEAN`, `Margin:VALUE`, `Rotate:BOOLEAN`, `Method:MENU`, `Bottom Left:VECTOR`, `Top Right:VECTOR` | `UV:VECTOR` |
| GeometryNodeUVTangent | `Method:MENU`, `UV:VECTOR` | `Tangent:VECTOR` |
| GeometryNodeUVUnwrap | `Selection:BOOLEAN`, `Seam:BOOLEAN`, `Margin:VALUE`, `Fill Holes:BOOLEAN`, `Method:MENU`, `Iterations:INT`, `No Flip:BOOLEAN` | `UV:VECTOR` |
| GeometryNodeVertexOfCorner | `Corner Index:INT` | `Vertex Index:INT` |
| GeometryNodeViewer | `:CUSTOM` | — |
| GeometryNodeViewportTransform | — | `Projection:MATRIX`, `View:MATRIX`, `Is Orthographic:BOOLEAN` |
| GeometryNodeVolumeCube | `Density:VALUE`, `Background:VALUE`, `Min:VECTOR`, `Max:VECTOR`, `Resolution X:INT`, `Resolution Y:INT`, `Resolution Z:INT` | `Volume:GEOMETRY` |
| GeometryNodeVolumeToMesh | `Volume:GEOMETRY`, `Resolution Mode:MENU`, `Voxel Size:VALUE`, `Voxel Amount:VALUE`, `Threshold:VALUE`, `Adaptivity:VALUE` | `Mesh:GEOMETRY` |
| GeometryNodeWarning | `Show:BOOLEAN`, `Message:STRING` | `Show:BOOLEAN` |
| GeometryNodeXPBDSolver | `World:BUNDLE`, `Delta Time:VALUE`, `Filter:STRING`, `Simulation to World:MATRIX`, `Substeps:INT`, `Constraint Iterations:INT`, `Solver Path:STRING`, `Begin:VALUE`, `End:VALUE` | `World:BUNDLE` |

## CompositorNode（92，其中可实例化 88）

> node_tree：`compositor`

| 节点 | 输入 | 输出 |
|---|---|---|
| CompositorNodeAlphaOver | `Background:RGBA`, `Foreground:RGBA`, `Factor:VALUE`, `Type:MENU`, `Straight Alpha:BOOLEAN` | `Image:RGBA` |
| CompositorNodeAntiAliasing | `Image:RGBA`, `Threshold:VALUE`, `Contrast Limit:VALUE`, `Corner Rounding:VALUE` | `Image:RGBA` |
| CompositorNodeBilateralblur | `Image:RGBA`, `Determinator:RGBA`, `Size:INT`, `Threshold:VALUE` | `Image:RGBA` |
| CompositorNodeBlankImage | `Color:RGBA`, `Size:INT_VECTOR` | `Image:RGBA` |
| CompositorNodeBlur | `Image:RGBA`, `Size:VECTOR`, `Type:MENU`, `Extend Bounds:BOOLEAN`, `Separable:BOOLEAN` | `Image:RGBA` |
| CompositorNodeBokehBlur | `Image:RGBA`, `Bokeh:RGBA`, `Size:VALUE`, `Mask:VALUE`, `Extend Bounds:BOOLEAN` | `Image:RGBA` |
| CompositorNodeBokehImage | `Flaps:INT`, `Angle:VALUE`, `Roundness:VALUE`, `Catadioptric Size:VALUE`, `Color Shift:VALUE` | `Image:RGBA` |
| CompositorNodeBoxMask | `Operation:MENU`, `Mask:VALUE`, `Value:VALUE`, `Position:VECTOR`, `Size:VECTOR`, `Rotation:VALUE` | `Mask:VALUE` |
| CompositorNodeBrightContrast | `Image:RGBA`, `Brightness:VALUE`, `Contrast:VALUE` | `Image:RGBA` |
| CompositorNodeChannelMatte | `Image:RGBA`, `Minimum:VALUE`, `Maximum:VALUE`, `Color Space:MENU`, `RGB Key Channel:MENU`, `HSV Key Channel:MENU`, `YUV Key Channel:MENU`, `YCbCr Key Channel:MENU`, `Limit Method:MENU`, `RGB Limit Channel:MENU`, `HSV Limit Channel:MENU`, `YUV Limit Channel:MENU`, `YCbCr Limit Channel:MENU` | `Image:RGBA`, `Matte:VALUE` |
| CompositorNodeChromaMatte | `Image:RGBA`, `Key Color:RGBA`, `Minimum:VALUE`, `Maximum:VALUE`, `Falloff:VALUE` | `Image:RGBA`, `Matte:VALUE` |
| CompositorNodeColorBalance | `Image:RGBA`, `Factor:VALUE`, `Type:MENU`, `Lift:VALUE`, `Lift:RGBA`, `Gamma:VALUE`, `Gamma:RGBA`, `Gain:VALUE`, `Gain:RGBA`, `Offset:VALUE`, `Offset:RGBA`, `Power:VALUE`, `Power:RGBA`, `Slope:VALUE`, `Slope:RGBA`, `Temperature:VALUE`, `Tint:VALUE`, `Temperature:VALUE`, `Tint:VALUE` | `Image:RGBA` |
| CompositorNodeColorCorrection | `Image:RGBA`, `Mask:VALUE`, `Saturation:VALUE`, `Contrast:VALUE`, `Gamma:VALUE`, `Gain:VALUE`, `Offset:VALUE`, `Saturation:VALUE`, `Contrast:VALUE`, `Gamma:VALUE`, `Gain:VALUE`, `Offset:VALUE`, `Saturation:VALUE`, `Contrast:VALUE`, `Gamma:VALUE`, `Gain:VALUE`, `Offset:VALUE`, `Saturation:VALUE`, `Contrast:VALUE`, `Gamma:VALUE`, `Gain:VALUE`, `Offset:VALUE`, `Midtones Start:VALUE`, `Midtones End:VALUE`, `Red:BOOLEAN`, `Green:BOOLEAN`, `Blue:BOOLEAN` | `Image:RGBA` |
| CompositorNodeColorMatte | `Image:RGBA`, `Key Color:RGBA`, `Hue:VALUE`, `Saturation:VALUE`, `Value:VALUE` | `Image:RGBA`, `Matte:VALUE` |
| CompositorNodeColorSpill | `Image:RGBA`, `Factor:VALUE`, `Spill Channel:MENU`, `Limit Method:MENU`, `Limit Channel:MENU`, `Limit Strength:VALUE`, `Use Spill Strength:BOOLEAN`, `Strength:RGBA` | `Image:RGBA` |
| CompositorNodeCombineColor | `Red:VALUE`, `Green:VALUE`, `Blue:VALUE`, `Alpha:VALUE` | `Image:RGBA` |
| CompositorNodeConvertColorSpace | `Image:RGBA` | `Image:RGBA` |
| CompositorNodeConvertToDisplay | `Image:RGBA`, `Invert:BOOLEAN` | `Image:RGBA` |
| CompositorNodeConvolve | `Image:RGBA`, `Kernel Data Type:MENU`, `Kernel:VALUE`, `Kernel:RGBA`, `Normalize Kernel:BOOLEAN` | `Image:RGBA` |
| CompositorNodeCornerPin | `Image:RGBA`, `Upper Left:VECTOR`, `Upper Right:VECTOR`, `Lower Left:VECTOR`, `Lower Right:VECTOR`, `Interpolation:MENU`, `Extension X:MENU`, `Extension Y:MENU` | `Image:RGBA`, `Plane:VALUE` |
| CompositorNodeCrop | `Image:RGBA`, `X:INT`, `Y:INT`, `Width:INT`, `Height:INT`, `Alpha Crop:BOOLEAN` | `Image:RGBA` |
| CompositorNodeCryptomatte | `Image:RGBA`, `Crypto 00:RGBA`, `Crypto 01:RGBA`, `Crypto 02:RGBA` | `Image:RGBA`, `Matte:VALUE`, `Pick:RGBA` |
| CompositorNodeCryptomatteV2 | `Image:RGBA` | `Image:RGBA`, `Matte:VALUE`, `Pick:RGBA` |
| CompositorNodeCurveRGB | `Image:RGBA`, `Factor:VALUE`, `Black Level:RGBA`, `White Level:RGBA` | `Image:RGBA` |
| CompositorNodeDBlur | `Image:RGBA`, `Samples:INT`, `Center:VECTOR`, `Rotation:VALUE`, `Scale:VALUE`, `Amount:VALUE`, `Direction:VALUE` | `Image:RGBA` |
| CompositorNodeDefocus | `Image:RGBA`, `Z:VALUE` | `Image:RGBA` |
| CompositorNodeDenoise | `Image:RGBA`, `Albedo:RGBA`, `Normal:VECTOR`, `HDR:BOOLEAN`, `Prefilter:MENU`, `Quality:MENU` | `Image:RGBA` |
| CompositorNodeDespeckle | `Image:RGBA`, `Factor:VALUE`, `Color Threshold:VALUE`, `Neighbor Threshold:VALUE` | `Image:RGBA` |
| CompositorNodeDiffMatte | `Image 1:RGBA`, `Image 2:RGBA`, `Tolerance:VALUE`, `Falloff:VALUE` | `Image:RGBA`, `Matte:VALUE` |
| CompositorNodeDilateErode | `Mask:VALUE`, `Size:INT`, `Type:MENU`, `Falloff Size:VALUE`, `Falloff:MENU` | `Mask:VALUE` |
| CompositorNodeDisplace | `Image:RGBA`, `Displacement:VECTOR`, `Interpolation:MENU`, `Extension X:MENU`, `Extension Y:MENU` | `Image:RGBA` |
| CompositorNodeDistanceMatte | `Image:RGBA`, `Key Color:RGBA`, `Color Space:MENU`, `Tolerance:VALUE`, `Falloff:VALUE` | `Image:RGBA`, `Matte:VALUE` |
| CompositorNodeDoubleEdgeMask | `Outer Mask:VALUE`, `Inner Mask:VALUE`, `Image Edges:BOOLEAN`, `Only Inside Outer:BOOLEAN` | `Mask:VALUE` |
| CompositorNodeEllipseMask | `Operation:MENU`, `Mask:VALUE`, `Value:VALUE`, `Position:VECTOR`, `Size:VECTOR`, `Rotation:VALUE` | `Mask:VALUE` |
| CompositorNodeExposure | `Image:RGBA`, `Exposure:VALUE` | `Image:RGBA` |
| CompositorNodeFilter | `Image:RGBA`, `Factor:VALUE`, `Type:MENU` | `Image:RGBA` |
| CompositorNodeFlip | `Image:RGBA`, `Flip X:BOOLEAN`, `Flip Y:BOOLEAN` | `Image:RGBA` |
| CompositorNodeGlare | `Image:RGBA`, `Type:MENU`, `Quality:MENU`, `Threshold:VALUE`, `Smoothness:VALUE`, `Clamp:BOOLEAN`, `Maximum:VALUE`, `Strength:VALUE`, `Saturation:VALUE`, `Tint:RGBA`, `Size:VALUE`, `Streaks:INT`, `Streaks Angle:VALUE`, `Iterations:INT`, `Fade:VALUE`, `Color Modulation:VALUE`, `Diagonal:BOOLEAN`, `Sun Position:VECTOR`, `Jitter:VALUE`, `Kernel Data Type:MENU`, `Kernel:VALUE`, `Kernel:RGBA` | `Image:RGBA`, `Glare:RGBA`, `Highlights:RGBA` |
| CompositorNodeGroup | — | — |
| CompositorNodeHueCorrect | `Image:RGBA`, `Factor:VALUE` | `Image:RGBA` |
| CompositorNodeHueSat | `Image:RGBA`, `Hue:VALUE`, `Saturation:VALUE`, `Value:VALUE`, `Factor:VALUE` | `Image:RGBA` |
| CompositorNodeIDMask | `ID value:VALUE`, `Index:INT`, `Anti-Alias:BOOLEAN` | `Alpha:VALUE` |
| CompositorNodeImage | — | `Image:RGBA`, `Alpha:VALUE` |
| CompositorNodeImageCoordinates | `Image:RGBA` | `Uniform:VECTOR`, `Normalized:VECTOR`, `Pixel:INT_VECTOR` |
| CompositorNodeImageInfo | `Image:RGBA` | `Dimensions:INT_VECTOR`, `Resolution:INT_VECTOR`, `Location:VECTOR`, `Rotation:VALUE`, `Scale:VECTOR` |
| CompositorNodeInpaint | `Image:RGBA`, `Size:INT` | `Image:RGBA` |
| CompositorNodeInvert | `Color:RGBA`, `Factor:VALUE`, `Invert Color:BOOLEAN`, `Invert Alpha:BOOLEAN` | `Color:RGBA` |
| CompositorNodeKeying | `Image:RGBA`, `Key Color:RGBA`, `Blur Size:INT`, `Balance:VALUE`, `Black Level:VALUE`, `White Level:VALUE`, `Size:INT`, `Tolerance:VALUE`, `Garbage Matte:VALUE`, `Core Matte:VALUE`, `Blur Size:INT`, `Dilate Size:INT`, `Feather Size:INT`, `Feather Falloff:MENU`, `Strength:VALUE`, `Balance:VALUE` | `Image:RGBA`, `Matte:VALUE`, `Edges:VALUE` |
| CompositorNodeKeyingScreen | `Smoothness:VALUE` | `Screen:RGBA` |
| CompositorNodeKuwahara | `Image:RGBA`, `Size:VALUE`, `Type:MENU`, `Uniformity:INT`, `Sharpness:VALUE`, `Eccentricity:VALUE`, `High Precision:BOOLEAN` | `Image:RGBA` |
| CompositorNodeLensdist | `Image:RGBA`, `Type:MENU`, `Distortion:VALUE`, `Dispersion:VALUE`, `Jitter:BOOLEAN`, `Fit:BOOLEAN` | `Image:RGBA` |
| CompositorNodeLevels | `Image:RGBA`, `Channel:MENU` | `Mean:VALUE`, `Standard Deviation:VALUE`, `Minimum:VALUE`, `Maximum:VALUE` |
| CompositorNodeLumaMatte | `Image:RGBA`, `Minimum:VALUE`, `Maximum:VALUE` | `Image:RGBA`, `Matte:VALUE` |
| CompositorNodeMapUV | `Image:RGBA`, `UV:VECTOR`, `Interpolation:MENU`, `Extension X:MENU`, `Extension Y:MENU` | `Image:RGBA` |
| CompositorNodeMask | `Size Source:MENU`, `Size X:INT`, `Size Y:INT`, `Feather:BOOLEAN`, `Motion Blur:BOOLEAN`, `Samples:INT`, `Shutter:VALUE` | `Mask:VALUE` |
| CompositorNodeMaskToSDF | `Mask:BOOLEAN` | `SDF:VALUE`, `Nearest Pixel:INT_VECTOR` |
| CompositorNodeMovieClip | — | `Image:RGBA`, `Alpha:VALUE`, `Offset X:VALUE`, `Offset Y:VALUE`, `Scale:VALUE`, `Angle:VALUE` |
| CompositorNodeMovieDistortion | `Image:RGBA`, `Type:MENU` | `Image:RGBA` |
| CompositorNodeNormal | — | `Normal:VECTOR` |
| CompositorNodeNormalize | `Value:VALUE` | `Value:VALUE` |
| CompositorNodeOutputFile | `:CUSTOM` | — |
| CompositorNodePixelate | `Color:RGBA`, `Size:INT` | `Color:RGBA` |
| CompositorNodePlaneTrackDeform | `Image:RGBA`, `Motion Blur:BOOLEAN`, `Samples:INT`, `Shutter:VALUE` | `Image:RGBA`, `Plane:VALUE` |
| CompositorNodePosterize | `Image:RGBA`, `Steps:VALUE` | `Image:RGBA` |
| CompositorNodePremulKey | `Image:RGBA`, `Type:MENU` | `Image:RGBA` |
| CompositorNodeRGB | — | `Color:RGBA` |
| CompositorNodeRGBToBW | `Image:RGBA` | `Val:VALUE` |
| CompositorNodeRLayers | — | `Image:RGBA`, `Alpha:VALUE` |
| CompositorNodeRelativeToPixel | `Value:VECTOR`, `Value:VALUE`, `Image:RGBA` | `Value:VALUE`, `Value:VECTOR` |
| CompositorNodeRotate | `Image:RGBA`, `Angle:VALUE`, `Interpolation:MENU`, `Extension X:MENU`, `Extension Y:MENU` | `Image:RGBA` |
| CompositorNodeScale | `Image:RGBA`, `Type:MENU`, `X:VALUE`, `Y:VALUE`, `Frame Type:MENU`, `Interpolation:MENU`, `Extension X:MENU`, `Extension Y:MENU` | `Image:RGBA` |
| CompositorNodeSceneTime | — | `Seconds:VALUE`, `Frame:VALUE` |
| CompositorNodeSeparateColor | `Image:RGBA` | `Red:VALUE`, `Green:VALUE`, `Blue:VALUE`, `Alpha:VALUE` |
| CompositorNodeSequencerStripInfo | — | `Start Frame:INT`, `End Frame:INT`, `Location:VECTOR`, `Rotation:VALUE`, `Scale:VECTOR` |
| CompositorNodeSetAlpha | `Image:RGBA`, `Alpha:VALUE`, `Type:MENU` | `Image:RGBA` |
| CompositorNodeSplit | `Position:VECTOR`, `Rotation:VALUE`, `Image:RGBA`, `Image:RGBA` | `Image:RGBA` |
| CompositorNodeStabilize | `Image:RGBA`, `Frame:INT`, `Invert:BOOLEAN`, `Interpolation:MENU`, `Extension X:MENU`, `Extension Y:MENU` | `Image:RGBA` |
| CompositorNodeStringToImage | `String:STRING`, `Font:FONT`, `Size:VALUE`, `Horizontal Alignment:MENU`, `Vertical Alignment:MENU`, `Wrap:BOOLEAN`, `Width:INT` | `Image:VALUE` |
| CompositorNodeSwitch | `Switch:BOOLEAN`, `Off:RGBA`, `On:RGBA` | `Image:RGBA` |
| CompositorNodeSwitchView | `left:RGBA`, `right:RGBA` | `Image:RGBA` |
| CompositorNodeTime | `Start Frame:INT`, `End Frame:INT` | `Factor:VALUE` |
| CompositorNodeTonemap | `Image:RGBA`, `Type:MENU`, `Key:VALUE`, `Balance:VALUE`, `Gamma:VALUE`, `Intensity:VALUE`, `Contrast:VALUE`, `Light Adaptation:VALUE`, `Chromatic Adaptation:VALUE` | `Image:RGBA` |
| CompositorNodeTrackPos | `Mode:MENU`, `Frame:INT` | `X:VALUE`, `Y:VALUE`, `Speed:VECTOR` |
| CompositorNodeTransform | `Image:RGBA`, `X:VALUE`, `Y:VALUE`, `Angle:VALUE`, `Scale:VALUE`, `Interpolation:MENU`, `Extension X:MENU`, `Extension Y:MENU` | `Image:RGBA` |
| CompositorNodeTranslate | `Image:RGBA`, `X:VALUE`, `Y:VALUE`, `Interpolation:MENU`, `Extension X:MENU`, `Extension Y:MENU` | `Image:RGBA` |
| CompositorNodeVecBlur | `Image:RGBA`, `Speed:VECTOR`, `Depth:VALUE`, `Samples:INT`, `Shutter:VALUE` | `Image:RGBA` |
| CompositorNodeViewer | `Image:RGBA` | — |
| CompositorNodeZcombine | `A:RGBA`, `Depth A:VALUE`, `B:RGBA`, `Depth B:VALUE`, `Use Alpha:BOOLEAN`, `Anti-Alias:BOOLEAN` | `Result:RGBA`, `Depth:VALUE` |

## FunctionNode（56，其中可实例化 55）

> node_tree：`geometry` / `shader`

| 节点 | 输入 | 输出 |
|---|---|---|
| FunctionNodeAlignEulerToVector | `Rotation:VECTOR`, `Factor:VALUE`, `Vector:VECTOR` | `Rotation:VECTOR` |
| FunctionNodeAlignRotationToVector | `Rotation:ROTATION`, `Factor:VALUE`, `Vector:VECTOR` | `Rotation:ROTATION` |
| FunctionNodeAxesToRotation | `Primary Axis:VECTOR`, `Secondary Axis:VECTOR` | `Rotation:ROTATION` |
| FunctionNodeAxisAngleToRotation | `Axis:VECTOR`, `Angle:VALUE` | `Rotation:ROTATION` |
| FunctionNodeBitMath | `A:INT`, `B:INT`, `Shift:INT` | `Value:INT` |
| FunctionNodeBooleanMath | `Boolean:BOOLEAN`, `Boolean:BOOLEAN` | `Boolean:BOOLEAN` |
| FunctionNodeCombineColor | `Red:VALUE`, `Green:VALUE`, `Blue:VALUE`, `Alpha:VALUE` | `Color:RGBA` |
| FunctionNodeCombineMatrix | `Column 1 Row 1:VALUE`, `Column 1 Row 2:VALUE`, `Column 1 Row 3:VALUE`, `Column 1 Row 4:VALUE`, `Column 2 Row 1:VALUE`, `Column 2 Row 2:VALUE`, `Column 2 Row 3:VALUE`, `Column 2 Row 4:VALUE`, `Column 3 Row 1:VALUE`, `Column 3 Row 2:VALUE`, `Column 3 Row 3:VALUE`, `Column 3 Row 4:VALUE`, `Column 4 Row 1:VALUE`, `Column 4 Row 2:VALUE`, `Column 4 Row 3:VALUE`, `Column 4 Row 4:VALUE` | `Matrix:MATRIX` |
| FunctionNodeCombineTransform | `Translation:VECTOR`, `Rotation:ROTATION`, `Scale:VECTOR` | `Transform:MATRIX` |
| FunctionNodeCompare | `A:VALUE`, `B:VALUE` | `Result:BOOLEAN` |
| FunctionNodeEulerToRotation | `Euler:VECTOR` | `Rotation:ROTATION` |
| FunctionNodeFindInString | `String:STRING`, `Search:STRING`, `Mode:MENU` | `First Found:INT`, `Count:INT` |
| FunctionNodeFloatToInt | `Float:VALUE` | `Integer:INT` |
| FunctionNodeFormatString | `Format:STRING`, `:CUSTOM` | `String:STRING` |
| FunctionNodeHashValue | `Value:INT`, `Seed:INT` | `Hash:INT` |
| FunctionNodeInputBool | — | `Boolean:BOOLEAN` |
| FunctionNodeInputColor | — | `Color:RGBA` |
| FunctionNodeInputInt | — | `Integer:INT` |
| FunctionNodeInputIntVector | — | `Vector:INT_VECTOR` |
| FunctionNodeInputMenu | — | `Menu:MENU` |
| FunctionNodeInputRotation | — | `Rotation:ROTATION` |
| FunctionNodeInputSpecialCharacters | — | `Line Break:STRING`, `Tab:STRING` |
| FunctionNodeInputString | — | `String:STRING` |
| FunctionNodeInputVector | — | `Vector:VECTOR` |
| FunctionNodeIntegerMath | `Value:INT`, `Value:INT`, `Value:INT` | `Value:INT` |
| FunctionNodeInvertMatrix | `Matrix:MATRIX` | `Matrix:MATRIX`, `Invertible:BOOLEAN` |
| FunctionNodeInvertRotation | `Rotation:ROTATION` | `Rotation:ROTATION` |
| FunctionNodeMatchString | `String:STRING`, `Operation:MENU`, `Key:STRING` | `Result:BOOLEAN` |
| FunctionNodeMatrixDeterminant | `Matrix:MATRIX` | `Determinant:VALUE` |
| FunctionNodeMatrixMultiply | `Matrix:MATRIX`, `Matrix:MATRIX` | `Matrix:MATRIX` |
| FunctionNodeMatrixSVD | `Matrix:MATRIX` | `U:MATRIX`, `S:VECTOR`, `V:MATRIX` |
| FunctionNodeProjectPoint | `Vector:VECTOR`, `Transform:MATRIX` | `Vector:VECTOR` |
| FunctionNodeQuaternionToRotation | `W:VALUE`, `X:VALUE`, `Y:VALUE`, `Z:VALUE` | `Rotation:ROTATION` |
| FunctionNodeRandomValue | `Min:VALUE`, `Max:VALUE`, `ID:INT`, `Seed:INT` | `Value:VALUE` |
| FunctionNodeReplaceString | `String:STRING`, `Find:STRING`, `Replace:STRING` | `String:STRING` |
| FunctionNodeReverseString | `String:STRING` | `String:STRING` |
| FunctionNodeRotateEuler | `Rotation:VECTOR`, `Rotate By:VECTOR` | `Rotation:VECTOR` |
| FunctionNodeRotateRotation | `Rotation:ROTATION`, `Rotate By:ROTATION` | `Rotation:ROTATION` |
| FunctionNodeRotateVector | `Vector:VECTOR`, `Rotation:ROTATION` | `Vector:VECTOR` |
| FunctionNodeRotationToAxisAngle | `Rotation:ROTATION` | `Axis:VECTOR`, `Angle:VALUE` |
| FunctionNodeRotationToEuler | `Rotation:ROTATION` | `Euler:VECTOR` |
| FunctionNodeRotationToQuaternion | `Rotation:ROTATION` | `W:VALUE`, `X:VALUE`, `Y:VALUE`, `Z:VALUE` |
| FunctionNodeSeparateColor | `Color:RGBA` | `Red:VALUE`, `Green:VALUE`, `Blue:VALUE`, `Alpha:VALUE` |
| FunctionNodeSeparateMatrix | `Matrix:MATRIX` | `Column 1 Row 1:VALUE`, `Column 1 Row 2:VALUE`, `Column 1 Row 3:VALUE`, `Column 1 Row 4:VALUE`, `Column 2 Row 1:VALUE`, `Column 2 Row 2:VALUE`, `Column 2 Row 3:VALUE`, `Column 2 Row 4:VALUE`, `Column 3 Row 1:VALUE`, `Column 3 Row 2:VALUE`, `Column 3 Row 3:VALUE`, `Column 3 Row 4:VALUE`, `Column 4 Row 1:VALUE`, `Column 4 Row 2:VALUE`, `Column 4 Row 3:VALUE`, `Column 4 Row 4:VALUE` |
| FunctionNodeSeparateTransform | `Transform:MATRIX` | `Translation:VECTOR`, `Rotation:ROTATION`, `Scale:VECTOR` |
| FunctionNodeSetStringCase | `String:STRING`, `Case:MENU` | `String:STRING` |
| FunctionNodeSliceString | `String:STRING`, `Position:INT`, `Length:INT` | `String:STRING` |
| FunctionNodeSplitString | `String:STRING`, `Separator:STRING` | `List:STRING` |
| FunctionNodeStringLength | `String:STRING` | `Length:INT` |
| FunctionNodeStringToValue | `String:STRING`, `Base:INT` | `Value:VALUE`, `Length:INT` |
| FunctionNodeTransformDirection | `Direction:VECTOR`, `Transform:MATRIX` | `Direction:VECTOR` |
| FunctionNodeTransformPoint | `Vector:VECTOR`, `Transform:MATRIX` | `Vector:VECTOR` |
| FunctionNodeTransposeMatrix | `Matrix:MATRIX` | `Matrix:MATRIX` |
| FunctionNodeTrimString | `String:STRING`, `Characters:STRING`, `Whitespace:BOOLEAN`, `Start:BOOLEAN`, `End:BOOLEAN` | `String:STRING` |
| FunctionNodeValueToString | `Value:VALUE`, `Decimals:INT`, `Base:INT`, `Padding:INT` | `String:STRING` |

## TextureNode（38，其中可实例化 34）

> node_tree：`texture`

| 节点 | 输入 | 输出 |
|---|---|---|
| TextureNodeAt | `Texture:RGBA`, `Coordinates:VECTOR` | `Texture:RGBA` |
| TextureNodeBricks | `Bricks 1:RGBA`, `Bricks 2:RGBA`, `Mortar:RGBA`, `Thickness:VALUE`, `Bias:VALUE`, `Brick Width:VALUE`, `Row Height:VALUE` | `Color:RGBA` |
| TextureNodeChecker | `Color1:RGBA`, `Color2:RGBA`, `Size:VALUE` | `Color:RGBA` |
| TextureNodeCombineColor | `Red:VALUE`, `Green:VALUE`, `Blue:VALUE`, `Alpha:VALUE` | `Color:RGBA` |
| TextureNodeCoordinates | — | `Coordinates:VECTOR` |
| TextureNodeCurveRGB | `Color:RGBA` | `Color:RGBA` |
| TextureNodeCurveTime | — | `Value:VALUE` |
| TextureNodeDistance | `Coordinate 1:VECTOR`, `Coordinate 2:VECTOR` | `Value:VALUE` |
| TextureNodeGroup | — | — |
| TextureNodeHueSaturation | `Hue:VALUE`, `Saturation:VALUE`, `Value:VALUE`, `Factor:VALUE`, `Color:RGBA` | `Color:RGBA` |
| TextureNodeImage | — | `Image:RGBA` |
| TextureNodeInvert | `Color:RGBA` | `Color:RGBA` |
| TextureNodeMath | `Value:VALUE`, `Value:VALUE`, `Value:VALUE` | `Value:VALUE` |
| TextureNodeMixRGB | `Factor:VALUE`, `Color1:RGBA`, `Color2:RGBA` | `Color:RGBA` |
| TextureNodeOutput | `Color:RGBA` | — |
| TextureNodeRGBToBW | `Color:RGBA` | `Val:VALUE` |
| TextureNodeRotate | `Color:RGBA`, `Turns:VALUE`, `Axis:VECTOR` | `Color:RGBA` |
| TextureNodeScale | `Color:RGBA`, `Scale:VECTOR` | `Color:RGBA` |
| TextureNodeSeparateColor | `Color:RGBA` | `Red:VALUE`, `Green:VALUE`, `Blue:VALUE`, `Alpha:VALUE` |
| TextureNodeTexBlend | `Color 1:RGBA`, `Color 2:RGBA` | `Color:RGBA` |
| TextureNodeTexClouds | `Color 1:RGBA`, `Color 2:RGBA`, `Size:VALUE` | `Color:RGBA` |
| TextureNodeTexDistNoise | `Color 1:RGBA`, `Color 2:RGBA`, `Size:VALUE`, `Distortion:VALUE` | `Color:RGBA` |
| TextureNodeTexMagic | `Color 1:RGBA`, `Color 2:RGBA`, `Turbulence:VALUE` | `Color:RGBA` |
| TextureNodeTexMarble | `Color 1:RGBA`, `Color 2:RGBA`, `Size:VALUE`, `Turbulence:VALUE` | `Color:RGBA` |
| TextureNodeTexMusgrave | `Color 1:RGBA`, `Color 2:RGBA`, `H:VALUE`, `Lacunarity:VALUE`, `Octaves:VALUE`, `iScale:VALUE`, `Size:VALUE` | `Color:RGBA` |
| TextureNodeTexNoise | `Color 1:RGBA`, `Color 2:RGBA` | `Color:RGBA` |
| TextureNodeTexStucci | `Color 1:RGBA`, `Color 2:RGBA`, `Size:VALUE`, `Turbulence:VALUE` | `Color:RGBA` |
| TextureNodeTexVoronoi | `Color 1:RGBA`, `Color 2:RGBA`, `W1:VALUE`, `W2:VALUE`, `W3:VALUE`, `W4:VALUE`, `iScale:VALUE`, `Size:VALUE` | `Color:RGBA` |
| TextureNodeTexWood | `Color 1:RGBA`, `Color 2:RGBA`, `Size:VALUE`, `Turbulence:VALUE` | `Color:RGBA` |
| TextureNodeTexture | `Color1:RGBA`, `Color2:RGBA` | `Color:RGBA` |
| TextureNodeTranslate | `Color:RGBA`, `Offset:VECTOR` | `Color:RGBA` |
| TextureNodeValToNor | `Val:VALUE`, `Nabla:VALUE` | `Normal:VECTOR` |
| TextureNodeValToRGB | `Fac:VALUE` | `Color:RGBA` |
| TextureNodeViewer | `Color:RGBA` | — |

## 不可实例化（22）

这些类型 `nodes.new()` 会报 `Node type … undefined`，不是扫描失败——
它们是**基类 / node_tree 类型 / 自定义组 / 已删除节点**，本来就没有实例。

| 节点 | nodes.new 报错 |
|---|---|
| ShaderNode | shader:RuntimeError |
| ShaderNodeCustomGroup | shader:RuntimeError |
| ShaderNodeTree | shader:RuntimeError |
| GeometryNode | geometry:RuntimeError |
| GeometryNodeApplySimulatedData | geometry:RuntimeError |
| GeometryNodeClosureToListItem | geometry:RuntimeError |
| GeometryNodeClosureToListItems | geometry:RuntimeError |
| GeometryNodeCustomGroup | geometry:RuntimeError |
| GeometryNodeFieldToGridItem | geometry:RuntimeError |
| GeometryNodeFieldToGridItems | geometry:RuntimeError |
| GeometryNodeFieldToListItem | geometry:RuntimeError |
| GeometryNodeFieldToListItems | geometry:RuntimeError |
| GeometryNodeTree | geometry:RuntimeError |
| CompositorNode | compositor:RuntimeError |
| CompositorNodeCustomGroup | compositor:RuntimeError |
| CompositorNodeGamma | compositor:RuntimeError |
| CompositorNodeTree | compositor:RuntimeError |
| FunctionNode | shader:RuntimeError |
| TextureNode | texture:RuntimeError |
| TextureNodeCompose | texture:RuntimeError |
| TextureNodeDecompose | texture:RuntimeError |
| TextureNodeTree | texture:RuntimeError |
