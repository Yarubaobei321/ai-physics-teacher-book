# -*- coding: utf-8 -*-
"""
HS-SR04P 超声波模块 · 修订 3 生成脚本
================================================
依据：本工作区“参考”中的两张自有实拍 + 同版商家尺寸图 + 说明.md。
本脚本不读取旧模型、零件库或其他项目，全部几何在本进程中从零生成。
修订 3 在修订2几何基础上集中提高外观一致性，不改变器件结构或相机位置。

修订 3 内容：
  1. 查询并修正修订2背面左上角的极细亮线（疑似反射/边缘描线），
     不靠压暗灯光掩盖，并在检查轮输出隔离诊断图。
  2. 安装孔、探头焊盘改为分层银灰金属；白色接口改为暖白；
     内部针脚改为暗色金属；PCB/芯片保持深黑。
  3. 探头外壳改为非镜面、带细微程序凹凸的银色表面；
     前压圈与侧壁使用不同粗糙度。GLB 使用合理的基础 PBR 参数。
  4. 防护网改为更密的横纵真实线网（约0.50 mm节距），减细线径、加深颜色；
     去除同心圆靶盘和中心规则突点，改为弧面反光层与偏置可见暗点。
  5. 丝印改用本机衬线字体（不安装字体），调整字号/间距；
     不添加照片中不可辨认的型号或数值。
  6. 保留 3 台原相机位置，另新增一台“教学斜视”透明背景相机。
  7. 保持板宽 45 mm、16 脚/16 焊盘、右侧纵向列 5 件、芯片下方 3 件、
     探头丝印圈在板内。

坐标与单位：
  - 建模局部坐标以毫米(mm)为单位，X=板宽，Y=板厚(前面为 -Y，背面为 +Y)，Z=板高。
  - 模型统一挂在“HS-SR04P_模型根节点”下，根节点缩放 0.001，
    使模型世界尺寸为米；scene.unit_settings.scale_length=1.0，length_unit=mm。
  - 主尺寸解释：板宽 45mm，孔径 3mm，孔距 9mm（标称）；
    26mm 解释为“板上沿到白色接口底部”的总体高度（解释值，仍保留不确定性）。
  - 其余未由资料给出的尺寸均为按照片的估测值，不把斜拍照片比例当作
    已校正透视的测量。

运行：
  HS_STAGE=check1      ... 第一轮低分辨率检查（640×480，不导出 GLB）
  HS_STAGE=check2      ... 必要时第二轮低分辨率检查
  HS_STAGE=final       ... 最终 1200×900 三视图、.blend 与 GLB
"""

import json
import math
import os
import struct
import sys
import time
from datetime import datetime
from pathlib import Path

import bpy
import bmesh
from mathutils import Matrix, Vector

# ---------------------------------------------------------------------------
# 路径与阶段
# ---------------------------------------------------------------------------
SCRIPT_PATH = Path(__file__).resolve()
ROOT_DIR = SCRIPT_PATH.parent

# 本机已有衬线字体；不安装任何字体，生成后文字转网格，交付文件不依赖该路径。
SERIF_FONT_PATH = Path("/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf")
_SERIF_FONT = None
_SERIF_FONT_USED = False
STAGE = os.environ.get("HS_STAGE", "final").strip().lower()
STAGES = {
    "check1": ("01_低分辨率检查", "检查1"),
    "check2": ("02_纠错检查", "检查2"),
}
IS_FINAL = STAGE == "final"

if IS_FINAL:
    OUTPUT_DIR = ROOT_DIR
    BLEND_PATH = ROOT_DIR / "HS-SR04P_修订3.blend"
    GLB_PATH = ROOT_DIR / "HS-SR04P_修订3.glb"
    RENDER_RECORD_PATH = ROOT_DIR / "核验记录.json"
    RENDER_SIZE = (1200, 900)
    RENDER_SAMPLES = 96
    VIEW_PREFIX = ""
else:
    folder, label = STAGES.get(STAGE, ("99_其他", STAGE))
    OUTPUT_DIR = ROOT_DIR / "_过程" / folder
    BLEND_PATH = OUTPUT_DIR / f"HS-SR04P_{label}.blend"
    GLB_PATH = None
    RENDER_RECORD_PATH = OUTPUT_DIR / "低分辨率检查记录.json"
    RENDER_SIZE = (640, 480)
    RENDER_SAMPLES = 20
    VIEW_PREFIX = "预览_"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def log(msg):
    print(f"[HS-SR04P/{STAGE}] {msg}", flush=True)


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"不是有效 PNG：{path}")
    return [int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")]


def png_color_type(path):
    with open(path, "rb") as f:
        head = f.read(26)
    if len(head) < 26 or head[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"不是有效 PNG：{path}")
    return head[25]


def file_size(path):
    return Path(path).stat().st_size if Path(path).is_file() else 0


# ---------------------------------------------------------------------------
# 通用工具
# ---------------------------------------------------------------------------
def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.images,
    ):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    # 1 BU = 1 m；模型世界宽度 0.045 BU，因此在 mm 单位下显示为 45 mm。
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.frame_start = 1
    scene.frame_end = 1
    return scene


def new_collection(name, parent=None):
    coll = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(coll)
    return coll


def make_empty(name, coll, parent=None, display_size=2.0):
    obj = bpy.data.objects.new(name, None)
    coll.objects.link(obj)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = display_size
    if parent is not None:
        obj.parent = parent
    return obj


def attach(obj, group, coll, name=None):
    if name:
        obj.name = name
        if obj.data is not None:
            obj.data.name = name
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)
    if group is not None:
        obj.parent = group
    return obj


def assign_material(obj, mat):
    if obj.data is None:
        return
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def add_bevel(obj, width=0.08, segments=2, angle=35.0):
    mod = obj.modifiers.new("倒角", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(angle)
    return mod


def apply_modifier(obj, mod):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)


def set_smooth_side_faces(obj):
    """圆柱侧面平滑、端盖平直。在对象局部空间判断法线。"""
    if obj.type != "MESH":
        return
    for poly in obj.data.polygons:
        poly.use_smooth = abs(poly.normal.z) < 0.6


def make_material(name, color, metallic=0.0, roughness=0.5,
                  clearcoat=0.0, emission=None, emission_strength=0.0,
                  specular=0.5):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1.0)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = specular
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = clearcoat
    if emission is not None:
        for key in ("Emission Color", "Emission"):
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = (*emission, 1.0)
                break
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat


def add_noise_bump(mat, scale=40.0, detail=4.0, strength=0.10, distance=0.01):
    """给材质增加细微程序凹凸；只连接 Normal，保留可直接导出的 PBR 基础参数。

    glTF 不支持该程序节点组合时，基础色/金属度/粗糙度仍会导出；
    程序细节只在 Blender 渲染中可见，这一点会在修改记录中注明。
    """
    if not mat.use_nodes:
        return
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    if bsdf is None:
        return
    if nodes.get("细节_对象坐标") is not None:
        return
    tex = nodes.new("ShaderNodeTexCoord")
    tex.name = "细节_对象坐标"
    tex.location = (-700, 200)
    noise = nodes.new("ShaderNodeTexNoise")
    noise.name = "细节_噪声"
    noise.location = (-500, 200)
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = detail
    noise.inputs["Roughness"].default_value = 0.62
    bump = nodes.new("ShaderNodeBump")
    bump.name = "细节_凹凸"
    bump.location = (-280, 120)
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = distance
    links.new(tex.outputs["Object"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


def add_box(name, dims, loc, mat, coll, group, bevel=0.0, segments=2):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.object
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign_material(obj, mat)
    attach(obj, group, coll, name)
    if bevel > 0:
        add_bevel(obj, bevel, segments)
    return obj


def add_cylinder(name, radius, depth, loc, rotation, mat, coll, group,
                 vertices=64, bevel=0.0, smooth=True):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=depth,
        location=loc, rotation=rotation,
    )
    obj = bpy.context.object
    assign_material(obj, mat)
    attach(obj, group, coll, name)
    if smooth:
        set_smooth_side_faces(obj)
    if bevel > 0:
        add_bevel(obj, bevel, 2)
    return obj


def add_cone(name, radius1, radius2, depth, loc, rotation, mat, coll, group,
             vertices=96, bevel=0.0):
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices, radius1=radius1, radius2=radius2, depth=depth,
        location=loc, rotation=rotation,
    )
    obj = bpy.context.object
    assign_material(obj, mat)
    attach(obj, group, coll, name)
    for poly in obj.data.polygons:
        poly.use_smooth = abs(poly.normal.z) < 0.7
    if bevel > 0:
        add_bevel(obj, bevel, 2)
    return obj


def add_uv_sphere(name, radius, loc, scale, mat, coll, group,
                  segments=32, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments, ring_count=rings, radius=radius, location=loc,
    )
    obj = bpy.context.object
    obj.scale = scale
    assign_material(obj, mat)
    attach(obj, group, coll, name)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def add_torus(name, major_radius, minor_radius, loc, rotation,
              mat, coll, group, major_segments=64, minor_segments=8):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius, minor_radius=minor_radius,
        major_segments=major_segments, minor_segments=minor_segments,
        location=loc, rotation=rotation,
    )
    obj = bpy.context.object
    assign_material(obj, mat)
    attach(obj, group, coll, name)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def add_annulus(name, x, z, outer_r, inner_r, thickness, y_center,
                mat, coll, group, segments=64):
    """在 XZ 平面、沿 Y 厚度的圆环/垫圈。"""
    verts = []
    faces = []
    y_front = y_center - thickness / 2.0
    y_back = y_center + thickness / 2.0
    for y in (y_front, y_back):
        for r in (outer_r, inner_r):
            for i in range(segments):
                a = 2.0 * math.pi * i / segments
                verts.append((x + r * math.cos(a), y, z + r * math.sin(a)))
    # rings: OF=0, IF=1, OB=2, IB=3
    for i in range(segments):
        j = (i + 1) % segments
        of_i, if_i = i, segments + i
        of_j, if_j = j, segments + j
        ob_i, ib_i = 2 * segments + i, 3 * segments + i
        ob_j, ib_j = 2 * segments + j, 3 * segments + j
        faces.append((of_i, if_i, if_j, of_j))
        faces.append((ob_i, ob_j, ib_j, ib_i))
        faces.append((of_i, of_j, ob_j, ob_i))
        faces.append((if_i, ib_i, ib_j, if_j))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    assign_material(obj, mat)
    attach(obj, group, coll, name)
    return obj


def add_curve(name, points, bevel_depth, mat, coll, group, cyclic=False,
              bevel_resolution=2):
    curve = bpy.data.curves.new(name, type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = bevel_resolution
    curve.use_fill_caps = True
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for p, (x, y, z) in zip(spline.points, points):
        p.co = (x, y, z, 1.0)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    coll.objects.link(obj)
    assign_material(obj, mat)
    attach(obj, group, coll, name)
    return obj


def arc_points_xz(cx, cz, r, a0, a1, steps=16):
    return [
        (cx + r * math.cos(a0 + (a1 - a0) * i / steps),
         cz + r * math.sin(a0 + (a1 - a0) * i / steps))
        for i in range(steps + 1)
    ]


FACE_FRONT = Matrix.Rotation(math.radians(90.0), 4, "X")
FACE_BACK = Matrix.Rotation(math.radians(180.0), 4, "Z") @ Matrix.Rotation(
    math.radians(90.0), 4, "X"
)


def add_text(name, body, size, x, z, y, face, mat, coll, group,
             angle=0.0, extrude=0.018, align_x="CENTER"):
    """平面丝印文字。面朝前(-Y)或后(+Y)，angle 为在平面内的附加旋转。"""
    global _SERIF_FONT, _SERIF_FONT_USED
    if _SERIF_FONT is None and SERIF_FONT_PATH.is_file():
        try:
            _SERIF_FONT = bpy.data.fonts.load(str(SERIF_FONT_PATH), check_existing=True)
            _SERIF_FONT_USED = True
            log(f"使用本机衬线字体：{SERIF_FONT_PATH.name}")
        except Exception as exc:
            log(f"衬线字体读取失败，回退 Blender 内置字体：{exc}")
    curve = bpy.data.curves.new(name, type="FONT")
    curve.body = body
    curve.align_x = align_x
    curve.align_y = "CENTER"
    curve.size = size
    curve.extrude = extrude
    curve.resolution_u = 2
    curve.offset = 0.0
    curve.space_character = 0.97
    if _SERIF_FONT is not None:
        curve.font = _SERIF_FONT
    obj = bpy.data.objects.new(name, curve)
    coll.objects.link(obj)
    assign_material(obj, mat)
    base = FACE_FRONT if face == "front" else FACE_BACK
    obj.matrix_basis = (
        Matrix.Translation((x, y, z))
        @ base
        @ Matrix.Rotation(angle, 4, "Z")
    )
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    attach(obj, group, coll, name)
    return obj


def join_objects(objects, name, coll, group):
    if not objects:
        raise RuntimeError(f"join_objects 收到空列表：{name}")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    active = objects[0]
    bpy.context.view_layer.objects.active = active
    if len(objects) > 1:
        bpy.ops.object.join()
    active = bpy.context.object
    attach(active, group, coll, name)
    return active


def make_via(x, z, mat_ring, mat_hole, coll, group, face="front", name="过孔"):
    y = -0.826 if face == "front" else 0.826
    sign = -1 if face == "front" else 1
    add_annulus(
        name + "_金属环", x, z, 0.55, 0.20, 0.06, y,
        mat_ring, coll, group, segments=32,
    )
    add_cylinder(
        name + "_孔", 0.20, 0.08, (x, y + sign * 0.01, z),
        (math.pi / 2, 0, 0), mat_hole, coll, group,
        vertices=24, smooth=False,
    )


# ---------------------------------------------------------------------------
# 场景 / 材质 / 分组
# ---------------------------------------------------------------------------
scene = clear_scene()

MODEL_COL = new_collection("HS-SR04P_模型")
C_PCB = new_collection("01_PCB主板", MODEL_COL)
C_PROBE_R = new_collection("02_探头_R", MODEL_COL)
C_PROBE_T = new_collection("03_探头_T", MODEL_COL)
C_BACK = new_collection("04_背面元件", MODEL_COL)
C_CONN = new_collection("05_白色四针接口", MODEL_COL)
C_SILK = new_collection("06_丝印与走线", MODEL_COL)
C_STUDIO = new_collection("07_摄影棚与相机", scene.collection)

ROOT = make_empty("HS-SR04P_模型根节点", MODEL_COL, display_size=3.0)
ROOT.scale = (0.001, 0.001, 0.001)

G_PCB = make_empty("组_PCB主板", C_PCB, ROOT, display_size=2.0)
G_R = make_empty("组_探头R", C_PROBE_R, ROOT, display_size=2.0)
G_T = make_empty("组_探头T", C_PROBE_T, ROOT, display_size=2.0)
G_BACK = make_empty("组_背面元件", C_BACK, ROOT, display_size=2.0)
G_CONN = make_empty("组_白色接口", C_CONN, ROOT, display_size=2.0)
G_SILK = make_empty("组_丝印与走线", C_SILK, ROOT, display_size=2.0)

# 材质：颜色按线性空间设置，用于 AgX 渲染。
# 金属件基础色/粗糙度保持为可导出的 Principled PBR；细节噪声仅用于 Blender 渲染。
M = {}
M["pcb"] = make_material(
    "M_PCB_黑色阻焊", (0.0012, 0.0014, 0.0014), 0.0, 0.62, 0.0,
    specular=0.0,
)
M["fr4"] = make_material("M_PCB_基材边缘", (0.17, 0.120, 0.050), 0.0, 0.80)
M["silver_pad"] = make_material(
    "M_焊盘_银灰", (0.28, 0.30, 0.29), 1.0, 0.43, 0.02, specular=0.5
)
M["silver_pad_dark"] = make_material(
    "M_焊盘_深银灰", (0.105, 0.115, 0.105), 1.0, 0.48
)
M["hole_wall"] = make_material(
    "M_孔壁_深褐灰", (0.050, 0.038, 0.026), 0.7, 0.52
)
M["solder"] = make_material("M_焊锡_银灰", (0.42, 0.44, 0.42), 1.0, 0.40)
M["tin"] = make_material("M_镀锡引脚_银灰", (0.36, 0.38, 0.36), 1.0, 0.44)
M["pin_dull"] = make_material("M_接口针脚_暗金属", (0.20, 0.18, 0.14), 0.85, 0.46)
M["aluminum_side"] = make_material(
    "M_探头_银色侧壁", (0.27, 0.29, 0.28), 1.0, 0.50, 0.0, specular=0.45
)
M["aluminum_ring"] = make_material(
    "M_探头_前压圈", (0.36, 0.38, 0.37), 1.0, 0.34, 0.02, specular=0.5
)
M["aluminum_dark"] = make_material(
    "M_探头_内腔暗金属", (0.055, 0.060, 0.058), 0.85, 0.48
)
M["reflector"] = make_material(
    "M_探头_弧面振膜", (0.090, 0.100, 0.096), 1.0, 0.30, 0.01, specular=0.4
)
M["mesh"] = make_material(
    "M_防护网_深黑", (0.0022, 0.0025, 0.0025), 0.05, 0.55, 0.0, specular=0.10
)
M["plastic"] = make_material(
    "M_塑料_暖象牙白", (0.43, 0.35, 0.235), 0.0, 0.57, 0.0, specular=0.28
)
M["plastic_dark"] = make_material("M_塑料_暗缝", (0.016, 0.012, 0.008), 0.0, 0.64)
M["connector_inner"] = make_material(
    "M_接口_内腔阴影", (0.13, 0.105, 0.070), 0.0, 0.72
)
M["chip"] = make_material(
    "M_芯片_黑塑封", (0.0008, 0.0010, 0.0009), 0.0, 0.60, 0.0, specular=0.035
)
M["chip_mark"] = make_material("M_芯片_一脚凹点", (0.025, 0.028, 0.025), 0.0, 0.60)
M["silk"] = make_material(
    "M_丝印_淡蓝灰", (0.40, 0.48, 0.48), 0.0, 0.60, 0.0, specular=0.30
)
M["silk_blue"] = make_material("M_丝印_浅蓝", (0.12, 0.26, 0.31), 0.0, 0.60)
M["trace_front"] = make_material(
    "M_正面走线_银灰", (0.33, 0.36, 0.34), 0.7, 0.40
)
M["metal_pkg_rim"] = make_material(
    "M_金属封装元件_金属边框", (0.24, 0.14, 0.055), 1.0, 0.40
)
M["metal_pkg_lid"] = make_material(
    "M_金属封装元件_灰色顶盖", (0.18, 0.18, 0.17), 0.75, 0.48
)
M["light_pkg"] = make_material(
    "M_浅色小封装_外壳", (0.50, 0.52, 0.42), 0.0, 0.50, 0.0, specular=0.30
)
M["light_pkg_mark"] = make_material(
    "M_浅色小封装_绿色标记", (0.08, 0.22, 0.11), 0.0, 0.48
)
M["beige_pkg"] = make_material(
    "M_米黄色小件_外壳", (0.32, 0.22, 0.10), 0.0, 0.56, 0.0, specular=0.30
)
M["black"] = make_material("M_黑色配件", (0.002, 0.002, 0.002), 0.0, 0.60)
M["floor"] = make_material("M_摄影背景地面", (0.10, 0.105, 0.10), 0.0, 0.88,
                           specular=0.15)

# 细微表面凹凸（Blender 渲染用；GLB 保留基础 PBR）。
add_noise_bump(M["pcb"], scale=120.0, detail=2.0, strength=0.025, distance=0.006)
add_noise_bump(M["chip"], scale=180.0, detail=2.0, strength=0.018, distance=0.004)
add_noise_bump(M["aluminum_side"], scale=52.0, detail=3.0, strength=0.065, distance=0.008)
add_noise_bump(M["aluminum_ring"], scale=120.0, detail=2.0, strength=0.025, distance=0.003)
add_noise_bump(M["reflector"], scale=65.0, detail=3.0, strength=0.035, distance=0.006)
add_noise_bump(M["silver_pad"], scale=160.0, detail=1.0, strength=0.018, distance=0.003)

# ---------------------------------------------------------------------------
# PCB 主板
# ---------------------------------------------------------------------------
BOARD_W = 45.0
BOARD_TOP = 8.4
BOARD_BOTTOM = -8.4
BOARD_TAB_BOTTOM = -12.6
BOARD_THICKNESS = 1.6
HOLE_D = 3.0
HOLE_TOP_Z = 4.4
HOLE_BOTTOM_Z = -4.6

PROBE_X = 14.3
PROBE_Z = 1.8
PROBE_R = 8.0


def board_outline():
    pts = []

    def add(p):
        if not pts or (Vector((p[0], 0, p[1])) - Vector((pts[-1][0], 0, pts[-1][1]))).length > 1e-6:
            pts.append(p)

    def arc(cx, cz, r, a0, a1, steps=16):
        for p in arc_points_xz(cx, cz, r, a0, a1, steps):
            add(p)

    # 顶部两角为与顶边、侧边相切的连续圆角（半径按实拍估计 3.8 mm），
    # 不再使用首版/修订1的直线斜切。总板宽、顶边高度和侧边位置不变。
    add((-18.7, BOARD_TOP))
    add((18.7, BOARD_TOP))
    arc(18.7, 4.6, 3.8, math.pi / 2, 0.0, 24)
    add((22.5, -5.8))
    arc(19.9, -5.8, 2.6, 0.0, -math.pi / 2, 16)
    add((10.5, BOARD_BOTTOM))
    arc(10.5, -10.6, 2.2, math.pi / 2, math.pi, 16)
    add((8.3, -11.1))
    arc(6.8, -11.1, 1.5, 0.0, -math.pi / 2, 16)
    add((-6.8, BOARD_TAB_BOTTOM))
    arc(-6.8, -11.1, 1.5, -math.pi / 2, -math.pi, 16)
    add((-8.3, -11.1))
    arc(-10.5, -10.6, 2.2, 0.0, math.pi / 2, 16)
    add((-19.9, BOARD_BOTTOM))
    arc(-19.9, -5.8, 2.6, -math.pi / 2, -math.pi, 16)
    add((-22.5, -5.8))
    add((-22.5, 4.6))
    arc(-18.7, 4.6, 3.8, math.pi, math.pi / 2, 24)
    # 最后一段圆弧的终点与首点重合；去掉重复点，避免退化边。
    if len(pts) > 1 and math.dist(pts[0], pts[-1]) < 1e-6:
        pts.pop()
    return pts


def make_board():
    outline = board_outline()
    verts = [(x, 0.0, z) for x, z in outline]
    mesh = bpy.data.meshes.new("PCB_主板")
    mesh.from_pydata(verts, [], [list(range(len(verts)))])
    mesh.validate()
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("PCB_主板", mesh)
    C_PCB.objects.link(obj)
    assign_material(obj, M["pcb"])
    obj.data.materials.append(M["fr4"])
    for poly in obj.data.polygons:
        poly.material_index = 0

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    solid = obj.modifiers.new("板厚", "SOLIDIFY")
    solid.thickness = BOARD_THICKNESS
    solid.offset = 0.0
    solid.use_even_offset = True
    solid.use_rim = True
    solid.use_rim_only = False
    solid.material_offset_rim = 1
    apply_modifier(obj, solid)

    # 两个安装孔：布尔切孔
    for z in (HOLE_TOP_Z, HOLE_BOTTOM_Z):
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=64, radius=HOLE_D / 2.0, depth=10.0,
            location=(0.0, 0.0, z), rotation=(math.pi / 2, 0, 0),
        )
        cutter = bpy.context.object
        cutter.name = "临时_安装孔切刀"
        boolean = obj.modifiers.new("安装孔", "BOOLEAN")
        boolean.operation = "DIFFERENCE"
        boolean.solver = "EXACT"
        boolean.object = cutter
        apply_modifier(obj, boolean)
        bpy.data.objects.remove(cutter, do_unlink=True)

    # 稍宽的 4 段倒角把上下两面的阻焊边缘与 FR4 侧壁连成自然过渡。
    bevel = add_bevel(obj, 0.20, 4, 30.0)
    apply_modifier(obj, bevel)
    obj.parent = G_PCB
    obj["标称板宽_mm"] = 45.0
    obj["估测PCB总高_mm"] = 21.0
    return obj


board = make_board()

# PCB 轮廓在 XZ 平面内的采样，用于裁切探头底部的板面丝印圈。
BOARD_POLY = board_outline()


def point_in_polygon_xz(x, z, poly):
    """XZ 平面射线法；poly 为 (x,z) 点列，首尾自动闭合。"""
    inside = False
    j = len(poly) - 1
    for i, (xi, zi) in enumerate(poly):
        xj, zj = poly[j]
        if (zi > z) != (zj > z):
            x_cross = (xj - xi) * (z - zi) / (zj - zi) + xi
            if x < x_cross:
                inside = not inside
        j = i
    return inside


def distance_point_to_segment_xz(px, pz, ax, az, bx, bz):
    vx, vz = bx - ax, bz - az
    wx, wz = px - ax, pz - az
    c1 = vx * wx + vz * wz
    if c1 <= 0.0:
        return math.hypot(px - ax, pz - az)
    c2 = vx * vx + vz * vz
    if c2 <= c1:
        return math.hypot(px - bx, pz - bz)
    t = c1 / c2
    return math.hypot(px - (ax + t * vx), pz - (az + t * vz))


def board_edge_distance_xz(x, z, poly=None):
    poly = poly or BOARD_POLY
    return min(
        distance_point_to_segment_xz(
            x, z, poly[i][0], poly[i][1],
            poly[(i + 1) % len(poly)][0], poly[(i + 1) % len(poly)][1],
        )
        for i in range(len(poly))
    )


def add_trimmed_silk_circle(prefix, x, z, radius, margin=0.10, steps=720):
    """只保留 PCB 轮廓内的圆周段，管径外缘也留在板内。

    该函数不改变板宽、不移动探头，仅对丝印本身做轮廓内裁切。
    过短的边缘碎段会被丢弃，避免出现孤立的丝印小点。
    """
    pts = []
    valid = []
    for i in range(steps):
        a = 2.0 * math.pi * i / steps
        px = x + radius * math.cos(a)
        pz = z + radius * math.sin(a)
        pts.append((px, -0.827, pz))
        valid.append(
            point_in_polygon_xz(px, pz, BOARD_POLY)
            and board_edge_distance_xz(px, pz) >= margin
        )

    if all(valid):
        obj = add_curve(
            prefix + "_板面丝印圈", pts, 0.055,
            M["silk_blue"], C_SILK, G_SILK, cyclic=True,
        )
        obj["板内裁切"] = True
        obj["裁切余量_mm"] = margin
        return [obj.name]

    objects = []
    i = 0
    while i < steps:
        if valid[i] and not valid[i - 1]:
            run = []
            j = i
            while j < i + steps and valid[j % steps]:
                run.append(pts[j % steps])
                j += 1
            # 计算折线长度，丢弃极短边缘碎段
            length = sum(
                math.dist((run[k][0], run[k][2]), (run[k + 1][0], run[k + 1][2]))
                for k in range(len(run) - 1)
            ) if len(run) > 1 else 0.0
            # 板角圆角后会形成一小段 4 mm 左右的孤立贴边弧；
            # 实拍不足以确认这段碎弧，小于 6 mm 的边缘孤段不保留。
            if len(run) >= 2 and length >= 6.0:
                suffix = "" if len(objects) == 0 else f"_{len(objects) + 1}"
                name = prefix + "_板面丝印圈" + suffix
                obj = add_curve(
                    name, run, 0.055, M["silk_blue"], C_SILK, G_SILK,
                    cyclic=False,
                )
                obj["板内裁切"] = True
                obj["裁切余量_mm"] = margin
                obj["弧段长度_mm"] = round(length, 3)
                objects.append(obj.name)
            i = j
        else:
            i += 1
    if not objects:
        raise RuntimeError(f"{prefix} 板面丝印圈裁切后没有剩余弧段")
    return objects


def verify_probe_silk_inside_board():
    """对转换成网格后的丝印圈逐顶点核验：全部在板内且有余量。"""
    rings = [
        o for o in bpy.data.objects
        if o.type == "MESH" and "板面丝印圈" in o.name
    ]
    if len(rings) < 2:
        raise RuntimeError(f"探头丝印圈对象数量异常：{len(rings)}")
    worst = 1e9
    details = []
    for obj in rings:
        min_margin = 1e9
        outside = 0
        for v in obj.data.vertices:
            px, pz = v.co.x, v.co.z
            if not point_in_polygon_xz(px, pz, BOARD_POLY):
                outside += 1
            d = board_edge_distance_xz(px, pz)
            min_margin = min(min_margin, d)
            worst = min(worst, d)
        if outside:
            raise RuntimeError(f"{obj.name} 有 {outside} 个丝印顶点在 PCB 轮廓外")
        if min_margin < 0.03:
            raise RuntimeError(f"{obj.name} 丝印离板边过近：{min_margin:.4f} mm")
        details.append({
            "对象": obj.name,
            "顶点数": len(obj.data.vertices),
            "最小板边距_mm": round(min_margin, 4),
        })
    return {
        "丝印圈对象数": len(rings),
        "全体最小板边距_mm": round(worst, 4),
        "各对象": details,
    }


# 安装孔：外层银灰环 + 略高的深银灰内圈 + 深褐灰孔壁。
for z, tag in ((HOLE_TOP_Z, "上"), (HOLE_BOTTOM_Z, "下")):
    for y, face, sign in ((-0.86, "前", -1.0), (0.86, "后", 1.0)):
        add_annulus(
            f"PCB_安装孔{tag}_{face}_银环", 0.0, z, 2.65, 1.58, 0.12,
            y, M["silver_pad"], C_PCB, G_PCB, segments=64,
        )
        add_annulus(
            f"PCB_安装孔{tag}_{face}_深银内圈", 0.0, z, 2.03, 1.52, 0.040,
            y + sign * 0.055, M["silver_pad_dark"], C_PCB, G_PCB, segments=64,
        )
    add_annulus(
        f"PCB_安装孔{tag}_孔壁", 0.0, z, 1.56, 1.50, 1.62, 0.0,
        M["hole_wall"], C_PCB, G_PCB, segments=64,
    )

# 板边两条极细的加工边线，增强实物感
add_curve(
    "PCB_前侧边缘描线",
    [(x, -0.821, z) for x, z in board_outline()[1:]] + [(
        board_outline()[0][0], -0.821, board_outline()[0][1])],
    0.040, M["fr4"], C_PCB, G_PCB, cyclic=True,
)

# ---------------------------------------------------------------------------
# 探头 R / T
# ---------------------------------------------------------------------------
def make_mesh_grid(name, x, z, coll, group):
    """实际管线网格：横纵两族深色细线，带轻微前后错层以示意经纬交织。

    实拍网目约 0.5 mm 节距；线径明显小于网孔，确保旋转查看时能从孔中
    看到后方的弧面金属反光。几何本身可导出到 GLB。
    """
    verts = []
    faces = []
    aperture = 6.55
    spacing = 0.50
    wire_r = 0.045
    families = (
        (0.0, -11.40),                 # 接近水平的一族
        (math.pi / 2.0, -11.46),       # 与上一族相交的竖向一族
    )
    wire_count = 0

    def add_tube(p1, p2, radius, sides=7):
        axis = (Vector(p2) - Vector(p1)).normalized()
        ref = Vector((0, 1, 0))
        if abs(axis.dot(ref)) > 0.95:
            ref = Vector((1, 0, 0))
        n1 = axis.cross(ref).normalized()
        n2 = axis.cross(n1).normalized()
        base = len(verts)
        for p in (p1, p2):
            for k in range(sides):
                a = 2 * math.pi * k / sides
                verts.append(tuple(
                    Vector(p) + n1 * math.cos(a) * radius + n2 * math.sin(a) * radius
                ))
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((base + k, base + k2, base + sides + k2, base + sides + k))

    for angle, y_base in families:
        u = Vector((math.cos(angle), 0, math.sin(angle)))
        n = Vector((-math.sin(angle), 0, math.cos(angle)))
        s = -aperture + spacing / 2
        line_index = 0
        while s < aperture:
            h = math.sqrt(max(aperture * aperture - s * s, 0.0))
            center = n * s
            # 交替 ±0.018 mm 的层高，给交叉点一点上下穿插的感觉。
            y = y_base + (0.018 if line_index % 2 == 0 else -0.018)
            p1 = (x + center.x - u.x * h, y, z + center.z - u.z * h)
            p2 = (x + center.x + u.x * h, y, z + center.z + u.z * h)
            add_tube(p1, p2, wire_r)
            wire_count += 1
            s += spacing
            line_index += 1
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    assign_material(obj, M["mesh"])
    attach(obj, group, coll, name)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    obj["网目节距_mm"] = spacing
    obj["线径_mm"] = 2.0 * wire_r
    obj["网格段数"] = wire_count
    obj["结构"] = "横纵两族、交替高度、真实几何"
    log(f"{name}：{wire_count} 段，节距 {spacing} mm，线径 {2*wire_r:.3f} mm")
    return obj


def make_dished_disc(name, x, z, coll, group):
    """镜头后方的浅弧面反射层，不是对真实压电结构的复原。"""
    radius = 4.85
    y_rim = -10.86
    y_center = -10.34
    n_radial = 12
    n_angular = 96
    verts = []
    faces = []
    # 中心点
    verts.append((x, y_center, z))
    for ring in range(1, n_radial + 1):
        r = radius * ring / n_radial
        # 中心后退，边缘朝前，形成柔和凹面反光。
        y = y_rim + (y_center - y_rim) * (1.0 - (r / radius) ** 2)
        for k in range(n_angular):
            a = 2.0 * math.pi * k / n_angular
            verts.append((x + r * math.cos(a), y, z + r * math.sin(a)))
    # 中心到第一圈
    first = 1
    for k in range(n_angular):
        k2 = (k + 1) % n_angular
        faces.append((0, first + k, first + k2))
    for ring in range(1, n_radial):
        a0 = 1 + (ring - 1) * n_angular
        a1 = 1 + ring * n_angular
        for k in range(n_angular):
            k2 = (k + 1) % n_angular
            faces.append((a0 + k, a1 + k, a1 + k2, a0 + k2))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    assign_material(obj, M["reflector"])
    attach(obj, group, coll, name)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    obj["说明"] = "浅弧面反射层；内部结构不可见，为估计建模"
    return obj


def make_probe(tag, x, coll, group):
    prefix = f"探头{tag}"
    # 底圈：黑色衬圈
    add_annulus(
        prefix + "_底座密封圈", x, PROBE_Z, 8.28, 6.50, 0.22, -0.91,
        M["black"], coll, group, segments=96,
    )
    # 铝壳：空心中管；侧壁和前压圈使用不同的粗糙度
    shell = add_annulus(
        prefix + "_金属外壳", x, PROBE_Z, 8.03, 6.55, 11.30, -6.30,
        M["aluminum_side"], coll, group, segments=96,
    )
    for poly in shell.data.polygons:
        poly.use_smooth = abs(poly.normal.y) < 0.5
    # 前端压圈：更光洁，保留与侧壁的材质差异
    front_ring = add_annulus(
        prefix + "_前圈", x, PROBE_Z, 8.23, 6.60, 0.55, -12.17,
        M["aluminum_ring"], coll, group, segments=96,
    )
    for poly in front_ring.data.polygons:
        poly.use_smooth = abs(poly.normal.y) < 0.5
    # 内腔壁/深色底
    add_annulus(
        prefix + "_内腔壁", x, PROBE_Z, 6.62, 6.50, 1.38, -11.34,
        M["aluminum_dark"], coll, group, segments=96,
    )
    add_cylinder(
        prefix + "_内腔底", 6.52, 0.18, (x, -10.14, PROBE_Z),
        (math.pi / 2, 0, 0), M["black"], coll, group,
        vertices=96, smooth=False,
    )
    # 浅弧面反射层：不是同心靶盘，也不复原真实压电内部。
    make_dished_disc(prefix + "_振膜", x, PROBE_Z, coll, group)
    # 弧面外沿一圈极细暗金属收边
    add_torus(
        prefix + "_振膜外沿", 4.78, 0.028,
        (x, -10.845, PROBE_Z), (math.pi / 2, 0, 0),
        M["aluminum_dark"], coll, group,
        major_segments=72, minor_segments=6,
    )
    # 偏心暗点：只表达照片可见的一个非对称暗斑，不声称是中心孔。
    add_cylinder(
        prefix + "_振膜偏心暗点", 0.27, 0.020,
        (x + 0.95, -10.375, PROBE_Z + 0.60),
        (math.pi / 2, 0, 0), M["chip_mark"], coll, group,
        vertices=24, smooth=False,
    )
    obj = make_mesh_grid(prefix + "_防护网", x, PROBE_Z, coll, group)
    # 板面白色压圈丝印：按 PCB 轮廓裁切，避免伸出板外悬空
    add_trimmed_silk_circle(prefix, x, PROBE_Z, 8.52, margin=0.10, steps=720)
    return obj

make_probe("R", PROBE_X, C_PROBE_R, G_R)
make_probe("T", -PROBE_X, C_PROBE_T, G_T)

# ---------------------------------------------------------------------------
# 白色四针侧插接口
# ---------------------------------------------------------------------------
CONN_TOP = -11.9
CONN_BOTTOM = -17.7
CONN_CENTER_Y = 3.35
CONN_DEPTH = 5.2
CONN_W = 12.2
CONN_OPEN_W = 9.2
CONN_OPEN_Z0 = -13.05
CONN_OPEN_Z1 = -16.75


def make_connector():
    # 外壳：先做圆角外盒，再布尔挖出朝后的插口
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, CONN_CENTER_Y, (CONN_TOP + CONN_BOTTOM) / 2),
    )
    body = bpy.context.object
    body.name = "接口_白色壳体"
    body.dimensions = (CONN_W, CONN_DEPTH, CONN_TOP - CONN_BOTTOM)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign_material(body, M["plastic"])
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    bevel = add_bevel(body, 0.28, 3, 30.0)
    apply_modifier(body, bevel)

    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0.0, (2.30 + CONN_CENTER_Y + CONN_DEPTH / 2 + 0.8) / 2,
                  (CONN_OPEN_Z0 + CONN_OPEN_Z1) / 2),
    )
    cutter = bpy.context.object
    cutter.name = "临时_接口开口切刀"
    cutter.dimensions = (CONN_OPEN_W, CONN_CENTER_Y + CONN_DEPTH / 2 + 0.8 - 2.30,
                         CONN_OPEN_Z1 - CONN_OPEN_Z0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    boolean = body.modifiers.new("侧插开口", "BOOLEAN")
    boolean.operation = "DIFFERENCE"
    boolean.solver = "EXACT"
    boolean.object = cutter
    apply_modifier(body, boolean)
    bpy.data.objects.remove(cutter, do_unlink=True)
    bevel = add_bevel(body, 0.07, 2, 30.0)
    apply_modifier(body, bevel)
    attach(body, G_CONN, C_CONN, "接口_白色壳体")

    # 插口内衬：给开口建立可读的深度和阴影，内部针脚仍然独立建模
    add_box(
        "接口_内腔背板", (8.95, 0.08, 3.52),
        (0.0, 2.39, -14.90), M["connector_inner"],
        C_CONN, G_CONN, bevel=0.01,
    )
    for sign, tag in ((-1, "左"), (1, "右")):
        add_box(
            f"接口_内腔侧壁_{tag}", (0.08, 3.35, 3.50),
            (sign * 4.56, 4.22, -14.90), M["connector_inner"],
            C_CONN, G_CONN, bevel=0.005,
        )
    add_box(
        "接口_内腔顶阴影", (9.00, 3.35, 0.07),
        (0.0, 4.22, -13.10), M["connector_inner"], C_CONN, G_CONN,
    )
    add_box(
        "接口_内腔底阴影", (9.00, 3.35, 0.07),
        (0.0, 4.22, -16.70), M["connector_inner"], C_CONN, G_CONN,
    )

    # 内部四个扁平针脚
    pins = []
    for x in (-3.0, -1.0, 1.0, 3.0):
        pin = add_box(
            f"临时_内部针脚_{x:+.1f}", (0.48, 0.22, 2.62),
            (x, 4.62, -14.48), M["pin_dull"], C_CONN, G_CONN, bevel=0.04,
        )
        pins.append(pin)
    join_objects(pins, "接口_内部针脚_4P", C_CONN, G_CONN)

    # 开口上沿的四个引脚槽
    for x in (-3.0, -1.0, 1.0, 3.0):
        add_box(
            f"接口_针槽_{x:+.1f}", (0.62, 0.06, 0.92),
            (x, 5.93, -12.55), M["plastic_dark"],
            C_CONN, G_CONN, bevel=0.01,
        )

    # 插口外唇：四条细边框，让开口从背面看具有真实的厚度
    add_box(
        "接口_开口上唇", (10.55, 0.28, 0.44),
        (0.0, 6.02, -12.84), M["plastic"], C_CONN, G_CONN,
        bevel=0.06, segments=2,
    )
    add_box(
        "接口_开口下唇", (10.55, 0.28, 0.42),
        (0.0, 6.02, -16.96), M["plastic"], C_CONN, G_CONN,
        bevel=0.06, segments=2,
    )
    for sign, tag in ((-1, "左"), (1, "右")):
        add_box(
            f"接口_开口侧唇_{tag}", (0.42, 0.28, 4.42),
            (sign * 5.08, 6.02, -14.90), M["plastic"],
            C_CONN, G_CONN, bevel=0.06, segments=2,
        )
    add_box(
        "接口_下唇中央缺口", (1.55, 0.05, 0.30),
        (0.0, 6.175, -16.76), M["plastic_dark"],
        C_CONN, G_CONN, bevel=0.01,
    )

    # 侧卡扣
    for sign, tag in ((-1, "左"), (1, "右")):
        add_box(
            f"接口_侧卡扣_{tag}", (0.8, 1.8, 2.5),
            (sign * 6.45, 4.45, -14.7), M["plastic"],
            C_CONN, G_CONN, bevel=0.10, segments=2,
        )
        # 侧面暗色卡窗
        add_box(
            f"接口_侧卡窗_{tag}", (0.06, 1.25, 1.55),
            (sign * 6.87, 4.45, -14.7), M["plastic_dark"],
            C_CONN, G_CONN, bevel=0.01,
        )

    # 正面（朝前）两个可见卡窗
    for x in (-3.8, 3.8):
        add_box(
            f"接口_前卡窗_{x:+.1f}", (0.72, 0.04, 1.85),
            (x, 0.735, -14.8), M["plastic_dark"],
            C_CONN, G_CONN, bevel=0.005,
        )

    # 穿板 U 形镀锡引脚 + 焊盘/焊点
    for x in (-3.0, -1.0, 1.0, 3.0):
        pts = [
            (x - 0.44, 1.08, -12.02),
            (x - 0.44, 1.08, -10.86),
            (x - 0.22, 1.08, -10.45),
            (x + 0.22, 1.08, -10.45),
            (x + 0.44, 1.08, -10.86),
            (x + 0.44, 1.08, -12.02),
        ]
        add_curve(
            f"接口_穿板引脚_{x:+.1f}", pts, 0.16,
            M["tin"], C_CONN, G_CONN, cyclic=False, bevel_resolution=2,
        )
        add_annulus(
            f"接口_焊盘_{x:+.1f}", x, -11.95, 0.68, 0.32, 0.07, 0.826,
            M["silver_pad"], C_CONN, G_CONN, segments=32,
        )
        add_uv_sphere(
            f"接口_焊点_{x:+.1f}", 0.56, (x, 0.96, -11.92),
            (1.0, 0.55, 0.75), M["solder"], C_CONN, G_CONN,
            segments=20, rings=10,
        )

    # 接口上方的一段横向分模线
    add_box(
        "接口_分模线", (11.5, 0.035, 0.08),
        (0.0, 5.965, -13.15), M["plastic_dark"], C_CONN, G_CONN,
    )


make_connector()

# ---------------------------------------------------------------------------
# 背面芯片 / 无源小件 / 焊点
# ---------------------------------------------------------------------------
def make_soic():
    """背面双列 16 脚贴片芯片。

    实拍每侧可见 8 个焊脚，共 16 脚。具体型号和芯片表面字迹不可辨，
    因此不在模型上编造型号或大片装饰标记，只保留实拍可见的黑色本体
    与一个极小的 1 脚凹点。
    """
    cx, cz = 7.95, 0.35
    body_y = 1.58
    body_len = 9.8
    body = add_box(
        "背_IC_U1_本体", (4.2, 1.5, body_len), (cx, body_y, cz),
        M["chip"], C_BACK, G_BACK, bevel=0.12, segments=2,
    )
    body["封装备注"] = "双列16脚贴片封装；每侧8脚，按实拍计数；具体型号未核实"
    body["引脚数"] = 16

    # 1 脚标记：仅一个小凹点，不添加任何无依据的丝印或型号文字。
    add_cylinder(
        "背_IC_U1_一脚标记", 0.20, 0.035,
        (cx - 1.35, body_y + 0.765, cz + 4.45),
        (math.pi / 2, 0, 0), M["chip_mark"], C_BACK, G_BACK,
        vertices=20, smooth=False,
    )

    # 每侧 8 个焊脚，共 16 个。间距按 1.27 mm 的贴片封装节距估计。
    leads = []
    for i in range(8):
        z = cz + (i - 3.5) * 1.27
        for sign in (-1, 1):
            x_outer = cx + sign * 2.1
            leads.append(add_box(
                f"临时_IC脚_{i:02d}_{sign:+d}_上段", (0.92, 0.30, 0.50),
                (x_outer + sign * 0.38, 1.55, z),
                M["tin"], C_BACK, G_BACK,
            ))
            leads.append(add_box(
                f"临时_IC脚_{i:02d}_{sign:+d}_落板", (0.36, 0.58, 0.50),
                (x_outer + sign * 0.82, 1.12, z),
                M["tin"], C_BACK, G_BACK,
            ))
    if len(leads) != 32:  # 16 脚 × 每脚两段
        raise RuntimeError(f"芯片引脚段数异常：{len(leads)}")
    joined = join_objects(leads, "背_IC_U1_引脚", C_BACK, G_BACK)
    add_bevel(joined, 0.035, 2, 35.0)
    joined["引脚数量"] = 16
    joined["封装备注"] = "每侧8脚，共16脚；具体型号未核实"

    # 16 个焊盘
    pads = []
    for i in range(8):
        z = cz + (i - 3.5) * 1.27
        for sign in (-1, 1):
            x = cx + sign * 2.92
            pads.append(add_box(
                f"临时_IC焊盘_{i:02d}_{sign:+d}", (0.82, 0.035, 0.60),
                (x, 0.835, z), M["silver_pad"], C_BACK, G_BACK,
            ))
    if len(pads) != 16:
        raise RuntimeError(f"芯片焊盘数量异常：{len(pads)}")
    pad_obj = join_objects(pads, "背_IC_U1_焊盘", C_BACK, G_BACK)
    pad_obj["焊盘数量"] = 16
    log("芯片核验：每侧8脚，共16脚；焊盘16个")

def make_smd_piece(name, x, z, body_x, body_z, body_mat,
                    orientation="horizontal", depth=0.62, cap=0.30,
                    group=None, visible_note=""):
    """按可见外形制作一个贴片小件，不写入数值、型号或电气功能。

    orientation='horizontal'：长轴沿 X，金属端在左右；
    orientation='vertical'：长轴沿 Z，金属端在上下。
    本体与端部金属合并为一个可编辑对象。
    """
    body = add_box(
        name + "_本体", (body_x, depth, body_z), (x, 1.19, z),
        body_mat, C_BACK, G_BACK,
    )
    caps = []
    if orientation == "horizontal":
        for sign, tag in ((-1, "左"), (1, "右")):
            caps.append(add_box(
                name + f"_端部金属_{tag}",
                (cap, depth + 0.04, body_z + 0.04),
                (x + sign * (body_x / 2 - cap / 2), 1.19, z),
                M["tin"], C_BACK, G_BACK,
            ))
    elif orientation == "vertical":
        for sign, tag in ((-1, "下"), (1, "上")):
            caps.append(add_box(
                name + f"_端部金属_{tag}",
                (body_x + 0.04, depth + 0.04, cap),
                (x, 1.19, z + sign * (body_z / 2 - cap / 2)),
                M["tin"], C_BACK, G_BACK,
            ))
    else:
        raise ValueError(orientation)
    cap_obj = join_objects(caps, name + "_端部金属", C_BACK, G_BACK)
    comp = join_objects([body, cap_obj], name, C_BACK, G_BACK)
    add_bevel(comp, 0.045, 2, 35.0)
    if group:
        comp["元件组"] = group
        comp["元件母体"] = True
    if visible_note:
        comp["可见外形备注"] = visible_note
    return comp


def make_metal_top_package():
    """右侧纵向列第4件：带金属顶盖的封装元件，类型未核实。"""
    prefix = "背_纵向列_04_金属顶盖件"
    metal_pkg = add_box(
        prefix + "_本体", (2.55, 1.20, 2.45),
        (-7.05, 1.42, 0.20), M["chip"], C_BACK, G_BACK,
        bevel=0.14, segments=2,
    )
    metal_pkg["类型备注"] = "金属封装元件；类型未核实，不做电气功能推断"
    metal_pkg["元件组"] = "纵向列"
    metal_pkg["元件母体"] = True
    metal_pkg["可见外形备注"] = "深色本体、铜色边框、灰色金属顶盖、端部金属"
    for sign, tag in ((-1, "下"), (1, "上")):
        add_box(
            f"{prefix}_端部金属{tag}",
            (2.42, 1.28, 0.30), (-7.05, 1.42, 0.20 + sign * 1.05),
            M["tin"], C_BACK, G_BACK,
        )
    add_box(
        prefix + "_金属边框", (2.50, 0.06, 2.36),
        (-7.05, 2.055, 0.20), M["metal_pkg_rim"], C_BACK, G_BACK,
        bevel=0.04, segments=2,
    )
    add_box(
        prefix + "_灰色顶盖", (2.06, 0.10, 1.92),
        (-7.05, 2.115, 0.20), M["metal_pkg_lid"], C_BACK, G_BACK,
        bevel=0.08, segments=2,
    )


def make_back_column():
    """右侧纵向元件列：照片中从上到下共 5 件，按可见外形编号。"""
    # 01 顶端浅色小封装；保留可见的绿色标记，不命名为 LED，不推断功能。
    top = make_smd_piece(
        "背_纵向列_01_浅色小封装", -7.05, 5.75, 1.85, 1.05,
        M["light_pkg"], orientation="horizontal", depth=0.72, cap=0.28,
        group="纵向列", visible_note="浅色本体、左右金属端、绿色小标记",
    )
    add_box(
        "背_纵向列_01_浅色小封装_绿色标记", (0.52, 0.05, 0.32),
        (-7.25, 1.55, 5.79), M["light_pkg_mark"], C_BACK, G_BACK,
        bevel=0.03,
    )

    # 02 黑色小件：长轴沿 X；不复制不可靠的数值。
    make_smd_piece(
        "背_纵向列_02_黑色小件", -7.05, 3.75, 2.15, 0.95,
        M["chip"], orientation="horizontal", depth=0.62, cap=0.30,
        group="纵向列", visible_note="黑色横向本体、左右金属端",
    )
    # 03 中间米黄色小件。
    make_smd_piece(
        "背_纵向列_03_米黄色小件", -7.05, 2.35, 1.95, 0.98,
        M["beige_pkg"], orientation="horizontal", depth=0.66, cap=0.32,
        group="纵向列", visible_note="米黄色横向本体、左右金属端",
    )
    # 04 金属顶盖件。
    make_metal_top_package()
    # 05 底端米黄色小件，替换首版/修订1的竖向黑色错误外观。
    make_smd_piece(
        "背_纵向列_05_米黄色小件", -7.05, -3.00, 2.25, 1.05,
        M["beige_pkg"], orientation="horizontal", depth=0.70, cap=0.34,
        group="纵向列", visible_note="米黄色横向本体、左右金属端",
    )


def make_under_chip_components():
    """芯片下方实拍 3 件：左竖黑，右上米黄，右下黑。"""
    make_smd_piece(
        "背_芯片下_01_竖向黑色件", 5.35, -5.80, 0.95, 1.85,
        M["chip"], orientation="vertical", depth=0.62, cap=0.30,
        group="芯片下方", visible_note="竖向黑色本体、上下金属端",
    )
    make_smd_piece(
        "背_芯片下_02_米黄色件", 3.00, -5.15, 1.80, 0.92,
        M["beige_pkg"], orientation="horizontal", depth=0.66, cap=0.30,
        group="芯片下方", visible_note="米黄色横向本体、左右金属端",
    )
    make_smd_piece(
        "背_芯片下_03_黑色件", 3.00, -6.35, 1.80, 0.92,
        M["chip"], orientation="horizontal", depth=0.62, cap=0.30,
        group="芯片下方", visible_note="黑色横向本体、左右金属端",
    )


def make_soic_and_smd():
    make_soic()
    make_back_column()
    make_under_chip_components()


make_soic_and_smd()

# 探头焊点（每只探头两个穿孔焊点）
for tag, x in (("R", PROBE_X), ("T", -PROBE_X)):
    for idx, dz in enumerate((4.05, -4.05)):
        z = PROBE_Z + dz
        add_annulus(
            f"背_焊盘_探头{tag}_{idx+1}_银外圈", x, z, 1.10, 0.50, 0.075, 0.826,
            M["silver_pad"], C_BACK, G_BACK, segments=40,
        )
        add_annulus(
            f"背_焊盘_探头{tag}_{idx+1}_深银内圈", x, z, 0.80, 0.43, 0.035, 0.875,
            M["silver_pad_dark"], C_BACK, G_BACK, segments=40,
        )
        add_uv_sphere(
            f"背_焊点_探头{tag}_{idx+1}", 0.92,
            (x, 0.97, z), (1.0, 0.50, 0.82),
            M["solder"], C_BACK, G_BACK, segments=24, rings=12,
        )

# ---------------------------------------------------------------------------
# 丝印、天线符号、走线、过孔
# ---------------------------------------------------------------------------
# 正面主标题
add_text(
    "丝印_正面_Ultrasonic_distance", "Ultrasonic distance", 2.20,
    0.0, -8.15, -0.815, "front", M["silk"], C_SILK, G_SILK,
)
add_text(
    "丝印_正面_measuring_module", "measuring module", 2.20,
    0.0, -10.15, -0.815, "front", M["silk"], C_SILK, G_SILK,
)

# 背面型号/丝印
add_text(
    "丝印_背面_HS-SR04P", "HS-SR04P", 2.65,
    19.28, 0.35, 0.815, "back", M["silk"], C_SILK, G_SILK,
    angle=math.pi / 2,
)
add_text(
    "丝印_背面_CS100A", "CS100A", 1.15,
    17.18, -0.45, 0.815, "back", M["silk"], C_SILK, G_SILK,
    angle=math.pi / 2,
)
add_text(
    "丝印_背面_R", "R", 2.90,
    11.75, -1.35, 0.815, "back", M["silk"], C_SILK, G_SILK,
)
add_text(
    "丝印_背面_T", "T", 2.90,
    -11.75, -1.35, 0.815, "back", M["silk"], C_SILK, G_SILK,
)
add_text(
    "丝印_背面_Power", "Power", 1.95,
    -7.05, 7.15, 0.815, "back", M["silk"], C_SILK, G_SILK,
)
add_text(
    "丝印_背面_VCC_Trig_Echo_GND", "VCC|Trig|Echo|GND", 1.22,
    0.0, -8.05, 0.815, "back", M["silk"], C_SILK, G_SILK,
)

# 天线符号：三层弧 + 圆点（正反面各一组）
def antenna_symbol(face):
    y = -0.828 if face == "front" else 0.828
    for idx, r in enumerate((0.85, 1.55, 2.25)):
        pts = [
            (r * math.cos(a), y, -0.10 + r * math.sin(a))
            for a in [math.radians(55 + 70 * i / 24) for i in range(25)]
        ]
        add_curve(
            f"丝印_{face}_天线_{idx+1}", pts, 0.10,
            M["silk"], C_SILK, G_SILK,
        )
    add_uv_sphere(
        f"丝印_{face}_天线点", 0.24, (0.0, y, -1.26),
        (1.0, 0.18, 1.0), M["silk"], C_SILK, G_SILK,
        segments=16, rings=8,
    )


antenna_symbol("front")
antenna_symbol("back")

# 背面元件丝印框
def silk_rect(name, x0, x1, z0, z1, y=0.828, bevel=0.045):
    pts = [
        (x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1),
    ]
    add_curve(name, pts, bevel, M["silk_blue"], C_SILK, G_SILK, cyclic=True)


# 芯片外框只保留照片中可见的一圈浅蓝色丝印，缩短下缘以让出芯片下方元件位置。
silk_rect("丝印_背_IC边框", 4.70, 11.12, -4.72, 5.55)
# 右侧纵向列 5 件的丝印框
silk_rect("丝印_背_纵向列01框", -8.25, -5.85, 5.08, 6.35)
silk_rect("丝印_背_纵向列02框", -8.25, -5.85, 3.12, 4.38)
silk_rect("丝印_背_纵向列03框", -8.20, -5.90, 1.70, 2.95)
silk_rect("丝印_背_纵向列04框", -8.55, -5.55, -1.25, 1.65)
silk_rect("丝印_背_纵向列05框", -8.30, -5.80, -3.70, -2.35)
# 芯片下方 3 件的丝印框，均低于芯片引脚并避开 VCC 文字
silk_rect("丝印_背_芯片下01框", 4.72, 6.00, -6.90, -4.82)
silk_rect("丝印_背_芯片下02框", 1.95, 4.05, -5.72, -4.55)
silk_rect("丝印_背_芯片下03框", 1.95, 4.05, -6.93, -5.73)

# 背面只能在实拍中看到少量被阻焊覆盖的弱线路，无法逐条确认走向。
# 本轮不再为“丰富细节”添加背面走线或过孔，只保留焊盘、元件轮廓和可读丝印。
# 正面下方：照片能确认文字附近有一段可见短线；仅保留这一段和两个小过孔，
# 不据此推导或宣称真实电气连接。
front_trace_pts = [
    (-4.0, -0.824, -11.45), (4.2, -0.824, -11.45),
]
add_curve(
    "走线_正面_可见段", front_trace_pts, 0.052,
    M["trace_front"], C_SILK, G_SILK,
)
for x, z, tag in ((-4.0, -11.45, "左"), (4.2, -11.45, "右")):
    make_via(
        x, z, M["silver_pad_dark"], M["black"], C_SILK, G_SILK, "front",
        name=f"正面过孔_{tag}",
    )

# 少量板面灰尘/微小标记不建模，避免装饰性虚构。

# ---------------------------------------------------------------------------
# 摄影棚：世界、地面、灯光、三台相机
# ---------------------------------------------------------------------------
world = bpy.data.worlds.new("HS-SR04P_摄影世界")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
bg.inputs["Color"].default_value = (0.58, 0.60, 0.61, 1.0)
bg.inputs["Strength"].default_value = 0.52

# 地面只用于斜视图，正/背视图隐藏
bpy.ops.mesh.primitive_plane_add(size=0.8, location=(0.0, 0.0, -0.0222))
floor = bpy.context.object
floor.name = "摄影_地面"
assign_material(floor, M["floor"])
for c in list(floor.users_collection):
    c.objects.unlink(floor)
C_STUDIO.objects.link(floor)
floor.hide_render = True


def add_area(name, loc, energy, size, color=(1.0, 1.0, 1.0), shape="DISK"):
    data = bpy.data.lights.new(name, type="AREA")
    data.energy = energy
    data.shape = shape
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    C_STUDIO.objects.link(obj)
    obj.location = loc
    direction = Vector((0.0, 0.0, -0.004)) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return obj


add_area("灯光_前主光", (-0.15, -0.23, 0.19), 11.0, 0.14, (1.0, 0.955, 0.90))
add_area("灯光_前补光", (0.17, -0.16, 0.035), 3.8, 0.13, (0.84, 0.92, 1.0))
add_area("灯光_背主光", (0.11, 0.24, 0.17), 9.0, 0.14, (1.0, 0.965, 0.92))
add_area("灯光_背补光", (-0.18, 0.15, 0.045), 3.4, 0.12, (0.85, 0.91, 1.0))
add_area("灯光_顶光", (0.0, 0.01, 0.30), 6.0, 0.20, (1.0, 1.0, 1.0))


def add_camera(name, loc, rot=None, ortho=False, ortho_scale=0.052, lens=70.0,
               target=None):
    data = bpy.data.cameras.new(name)
    data.type = "ORTHO" if ortho else "PERSP"
    if ortho:
        data.ortho_scale = ortho_scale
    else:
        data.lens = lens
    data.sensor_width = 36.0
    data.clip_start = 0.0001
    data.clip_end = 10.0
    obj = bpy.data.objects.new(name, data)
    C_STUDIO.objects.link(obj)
    obj.location = loc
    if rot is not None:
        obj.rotation_euler = rot
    elif target is not None:
        direction = Vector(target) - obj.location
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return obj


cam_front = add_camera(
    "相机_正面", (0.0, -0.20, -0.00385),
    rot=(math.pi / 2, 0.0, 0.0), ortho=True, ortho_scale=0.052,
)
cam_back = add_camera(
    "相机_背面", (0.0, 0.20, -0.00385),
    rot=(math.pi / 2, 0.0, math.pi), ortho=True, ortho_scale=0.052,
)
cam_oblique = add_camera(
    "相机_斜视", (0.055, -0.095, 0.040),
    lens=72.0, target=(0.0, 0.0005, -0.0045),
)
# 课件用第四台相机；前三台相机的位置完全不变。
cam_teaching = add_camera(
    "相机_教学斜视", (0.042, -0.112, 0.016),
    lens=70.0, target=(0.0, 0.0005, -0.0048),
)

# 渲染设置
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = RENDER_SIZE
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.image_settings.color_depth = "8"
scene.render.image_settings.compression = 15
scene.render.film_transparent = False
scene.render.use_file_extension = True
scene.render.threads_mode = "FIXED"
scene.render.threads = 4
scene.frame_start = 1
scene.frame_end = 1
try:
    scene.eevee.taa_render_samples = RENDER_SAMPLES
except Exception:
    pass
try:
    scene.eevee.use_raytracing = True
    scene.eevee.ray_tracing_options.use_denoise = True
except Exception:
    pass
try:
    scene.eevee.use_shadows = True
except Exception:
    pass
try:
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
except Exception:
    pass
scene.view_settings.exposure = 0.0

# 保存时默认显示正面相机、隐藏地面
scene.camera = cam_front
floor.hide_render = True


# ---------------------------------------------------------------------------
# 输出前处理 / 渲染 / 导出 / 重开核验
# ---------------------------------------------------------------------------
def convert_all_curves():
    for obj in list(bpy.data.objects):
        if obj.type == "CURVE":
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.convert(target="MESH")
    for obj in list(bpy.data.objects):
        if obj.type == "FONT":
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.convert(target="MESH")


def configure_render(width, height, samples):
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    try:
        scene.eevee.taa_render_samples = samples
    except Exception:
        pass


def render_view(view, filepath, width, height, samples):
    cam = {"front": cam_front, "back": cam_back, "oblique": cam_oblique}[view]
    scene.camera = cam
    floor.hide_render = view != "oblique"
    configure_render(width, height, samples)
    scene.render.filepath = str(filepath)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    elapsed = round(time.time() - t0, 2)
    if not Path(filepath).is_file():
        raise RuntimeError(f"渲染未生成文件：{filepath}")
    size = png_size(filepath)
    if size != [width, height]:
        raise RuntimeError(f"渲染尺寸异常：{size}，期望 {width}×{height}")
    log(f"渲染 {view} -> {Path(filepath).name} ({size[0]}×{size[1]}, {elapsed}s)")
    return {"view": view, "path": str(filepath), "size": size, "seconds": elapsed}


def object_world_width_mm(obj, scale_m_per_bu):
    """用求值后的世界几何测量对象 X 宽度；返回 BU 与按场景比例换算的 mm。"""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(depsgraph)
    mesh = ev.to_mesh()
    try:
        xs = [(ev.matrix_world @ v.co).x for v in mesh.vertices]
        width_bu = max(xs) - min(xs)
    finally:
        ev.to_mesh_clear()
    return {
        "宽度_BU": width_bu,
        "scale_length_m_per_BU": scale_m_per_bu,
        "显示宽度_mm": width_bu * scale_m_per_bu * 1000.0,
    }


def count_mesh_islands(mesh):
    """统计网格连通块数量，用于验证 16 个独立焊盘。"""
    n = len(mesh.vertices)
    if n == 0:
        return 0
    adj = [[] for _ in range(n)]
    for e in mesh.edges:
        a, b = e.vertices
        adj[a].append(b)
        adj[b].append(a)
    seen = [False] * n
    count = 0
    for start in range(n):
        if seen[start]:
            continue
        count += 1
        stack = [start]
        seen[start] = True
        while stack:
            v = stack.pop()
            for w in adj[v]:
                if not seen[w]:
                    seen[w] = True
                    stack.append(w)
    return count


def _cluster_1d(values, gap):
    vals = sorted(set(values))
    if not vals:
        return []
    groups = [[vals[0]]]
    for v in vals[1:]:
        if v - groups[-1][-1] > gap:
            groups.append([v])
        else:
            groups[-1].append(v)
    return [sum(g) / len(g) for g in groups]


def count_glb_grid_slots(obj, x_gap=0.65, z_gap=0.65):
    """按顶点世界坐标的 X/Z 空间槽位统计引脚或焊盘数量。

    glTF 重导入会按法线拆分顶点，因此不能再用网格连通块数量。
    这里只依赖实际空间位置：16 个焊盘/引脚应形成 2 列 × 8 行槽位。
    """
    points = []
    for v in obj.data.vertices:
        p = obj.matrix_world @ v.co
        points.append((p.x * 1000.0, p.z * 1000.0))
    xs = _cluster_1d([p[0] for p in points], x_gap)
    zs = _cluster_1d([p[1] for p in points], z_gap)
    cells = set()
    for x, z in points:
        xi = min(range(len(xs)), key=lambda i: abs(x - xs[i]))
        zi = min(range(len(zs)), key=lambda i: abs(z - zs[i]))
        cells.add((xi, zi))
    return {
        "X槽位数": len(xs),
        "Z槽位数": len(zs),
        "空间槽位总数": len(cells),
        "X中心_mm": [round(v, 3) for v in xs],
        "Z中心_mm": [round(v, 3) for v in zs],
    }


def verify_board_shape():
    """用轮廓采样核验 45 mm 板宽与两个连续圆角。"""
    pts = list(BOARD_POLY)
    width = max(p[0] for p in pts) - min(p[0] for p in pts)
    if abs(width - 45.0) > 0.001:
        raise RuntimeError(f"PCB轮廓宽度不是45 mm：{width:.6f}")
    if abs(max(p[1] for p in pts) - BOARD_TOP) > 1e-6:
        raise RuntimeError("PCB顶边高度发生变化")
    corner_checks = []
    for side, cx in (("右", 18.7), ("左", -18.7)):
        if side == "右":
            corner = [(x, z) for x, z in pts
                      if x > cx + 1e-6 and z > 4.6 + 1e-6]
        else:
            corner = [(x, z) for x, z in pts
                      if x < cx - 1e-6 and z > 4.6 + 1e-6]
        radii = [math.hypot(x - cx, z - 4.6) for x, z in corner]
        if len(radii) < 5:
            raise RuntimeError(f"{side}上角圆弧采样点不足")
        dev = max(abs(r - 3.8) for r in radii)
        if dev > 0.002:
            raise RuntimeError(f"{side}上角不是半径3.8 mm的连续圆弧：{dev:.5f}")
        corner_checks.append({
            "角": side + "上角",
            "圆弧半径_mm": 3.8,
            "采样点数": len(radii),
            "半径最大偏差_mm": round(dev, 6),
        })
    result = {
        "板宽_mm": round(width, 6),
        "顶边高度_mm": BOARD_TOP,
        "两上角": corner_checks,
        "直线斜切": "已移除",
        "板边倒角_mm": 0.20,
        "板边倒角段数": 4,
    }
    log("板形核验：" + json.dumps(result, ensure_ascii=False))
    return result


def verify_chip_geometry():
    """核验 16 脚：16 个引脚位置、16 个焊盘、无顶面装饰、无编造型号。"""
    lead_obj = bpy.data.objects.get("背_IC_U1_引脚")
    pad_obj = bpy.data.objects.get("背_IC_U1_焊盘")
    body_obj = bpy.data.objects.get("背_IC_U1_本体")
    if not all((lead_obj, pad_obj, body_obj)):
        raise RuntimeError("芯片本体/引脚/焊盘对象缺失")
    if int(lead_obj.get("引脚数量", -1)) != 16:
        raise RuntimeError("芯片引脚数量属性不是 16")
    if int(pad_obj.get("焊盘数量", -1)) != 16:
        raise RuntimeError("芯片焊盘数量属性不是 16")
    pad_islands = count_mesh_islands(pad_obj.data)
    if pad_islands != 16:
        raise RuntimeError(f"芯片焊盘网格连通块数量不是 16：{pad_islands}")
    if "背_IC_U1_顶面凹槽" in bpy.data.objects:
        raise RuntimeError("仍存在无依据的芯片顶面装饰区")
    decorative = [
        o.name for o in bpy.data.objects
        if o.name.startswith("背_IC_U1_") and o.type == "FONT"
    ]
    if decorative:
        raise RuntimeError("芯片上仍有额外文字对象：" + "、".join(decorative))
    lead_islands = count_mesh_islands(lead_obj.data)
    result = {
        "每侧引脚数": 8,
        "总引脚数": 16,
        "焊盘数": 16,
        "焊盘网格连通块数": pad_islands,
        "引脚网格段连通块数": lead_islands,
        "顶面装饰区已移除": True,
        "芯片型号": "未核实，未在模型上编造",
    }
    log("芯片核验：" + json.dumps(result, ensure_ascii=False))
    return result


def object_local_z_range(obj):
    zs = [v[2] for v in obj.bound_box]
    return obj.location.z + min(zs), obj.location.z + max(zs)


def verify_silk_inside_board():
    """检查所有丝印对象（文字/框线）在 PCB 轮廓内。"""
    silk = [
        o for o in bpy.data.objects
        if o.type == "MESH" and o.name.startswith("丝印_")
    ]
    if not silk:
        raise RuntimeError("没有找到丝印对象")
    outside = 0
    min_margin = 1e9
    for obj in silk:
        for v in obj.data.vertices:
            x, z = v.co.x, v.co.z
            if not point_in_polygon_xz(x, z, BOARD_POLY):
                outside += 1
            min_margin = min(min_margin, board_edge_distance_xz(x, z))
    if outside:
        raise RuntimeError(f"有 {outside} 个丝印顶点落在 PCB 轮廓外")
    result = {
        "丝印对象数": len(silk),
        "越界顶点数": outside,
        "最小板边距_mm": round(min_margin, 4),
    }
    log("丝印板内核验：" + json.dumps(result, ensure_ascii=False))
    return result


def verify_probe_appearance():
    """核验真实网罩几何、弧面反射层与衬线文字转换。"""
    grids = [bpy.data.objects.get("探头R_防护网"), bpy.data.objects.get("探头T_防护网")]
    if not all(grids):
        raise RuntimeError("探头防护网对象缺失")
    for grid in grids:
        if abs(float(grid.get("网目节距_mm", -1)) - 0.50) > 1e-6:
            raise RuntimeError(f"{grid.name} 网目节距不是0.50mm")
        if abs(float(grid.get("线径_mm", -1)) - 0.09) > 1e-5:
            raise RuntimeError(f"{grid.name} 线径不是0.09mm")
        if int(grid.get("网格段数", 0)) < 45:
            raise RuntimeError(f"{grid.name} 网格段数不足")
    old_rings = [o.name for o in bpy.data.objects if "振膜环" in o.name or "振膜中心" in o.name]
    if old_rings:
        raise RuntimeError("仍存在旧同心环/中心突点：" + "、".join(old_rings))
    dishes = [bpy.data.objects.get("探头R_振膜"), bpy.data.objects.get("探头T_振膜")]
    if not all(dishes):
        raise RuntimeError("探头弧面反射层缺失")
    font_objects = [o.name for o in bpy.data.objects if o.type == "FONT"]
    if font_objects:
        raise RuntimeError("仍有未转网格的文字：" + "、".join(font_objects))
    result = {
        "防护网对象": [g.name for g in grids],
        "网目节距_mm": 0.50,
        "线径_mm": 0.09,
        "网格段数": [int(g.get("网格段数", 0)) for g in grids],
        "旧同心环/中心突点": "已移除",
        "弧面反射层": [d.name for d in dishes],
        "文字对象": "均转换为网格",
        "衬线字体": SERIF_FONT_PATH.name if _SERIF_FONT_USED else "内置字体回退",
    }
    log("探头外观核验：" + json.dumps(result, ensure_ascii=False))
    return result


def verify_back_layout():
    """核验右侧纵向列 5 件、芯片下方 3 件，并清除无依据装饰。"""
    column = sorted(
        [o for o in bpy.data.objects
         if o.get("元件母体") and o.get("元件组") == "纵向列"],
        key=lambda o: o.location.z, reverse=True,
    )
    under_chip = sorted(
        [o for o in bpy.data.objects
         if o.get("元件母体") and o.get("元件组") == "芯片下方"],
        key=lambda o: o.location.z, reverse=True,
    )
    expected_column = [
        "背_纵向列_01_浅色小封装",
        "背_纵向列_02_黑色小件",
        "背_纵向列_03_米黄色小件",
        "背_纵向列_04_金属顶盖件_本体",
        "背_纵向列_05_米黄色小件",
    ]
    expected_under = {
        "背_芯片下_01_竖向黑色件",
        "背_芯片下_02_米黄色件",
        "背_芯片下_03_黑色件",
    }
    if [o.name for o in column] != expected_column:
        raise RuntimeError(
            "右侧纵向列不足/顺序不对："
            + "、".join(f"{o.name}@{o.location.z:.2f}" for o in column)
        )
    if len(column) != 5:
        raise RuntimeError(f"右侧纵向列数量不是 5：{len(column)}")
    if {o.name for o in under_chip} != expected_under or len(under_chip) != 3:
        raise RuntimeError(f"芯片下方元件数量/名称不对：{[o.name for o in under_chip]}")

    # 芯片下方小件都要低于芯片本体下缘，并明显高于 VCC 丝印。
    chip_body = bpy.data.objects.get("背_IC_U1_本体")
    if chip_body is None:
        raise RuntimeError("找不到芯片本体")
    chip_bottom = object_local_z_range(chip_body)[0]
    for obj in under_chip:
        zmin, zmax = object_local_z_range(obj)
        if zmax >= chip_bottom:
            raise RuntimeError(f"{obj.name} 与芯片/引脚发生高度交叠：{zmax:.2f} vs {chip_bottom:.2f}")
        if zmin <= -7.30:
            raise RuntimeError(f"{obj.name} 延伸到 VCC 文字区域：{zmin:.2f}")

    # 背面不得再出现无依据的过孔、长走线或元件数值。
    forbidden_prefixes = ("走线_背面", "背面过孔", "背_R1", "背_R2", "背_R3",
                          "背_R4", "背_LED", "背_C1", "背_金属封装元件_01")
    hits = [o.name for o in bpy.data.objects if o.name.startswith(forbidden_prefixes)]
    if hits:
        raise RuntimeError("仍存在已删除的背面装饰/旧命名：" + "、".join(hits))
    value_hits = [
        o.name for o in bpy.data.objects
        if any(t in o.name for t in ("310", "226", "000"))
    ]
    if value_hits:
        raise RuntimeError("仍存在不可靠的元件数值：" + "、".join(value_hits))
    if any("顶面凹槽" in o.name for o in bpy.data.objects):
        raise RuntimeError("仍存在芯片顶面装饰区")

    front_traces = [
        o.name for o in bpy.data.objects if o.name.startswith("走线_正面")
    ]
    if front_traces != ["走线_正面_可见段"]:
        raise RuntimeError("正面走线对象数量异常：" + "、".join(front_traces))
    frames = [o.name for o in bpy.data.objects if o.name.startswith("丝印_背_纵向列")]
    under_frames = [o.name for o in bpy.data.objects if o.name.startswith("丝印_背_芯片下")]
    if len(frames) != 5 or len(under_frames) != 3:
        raise RuntimeError(f"元件丝印框数量异常：纵向列{len(frames)}，芯片下{len(under_frames)}")

    result = {
        "右侧纵向列数量": len(column),
        "右侧纵向列顺序": [o.name for o in column],
        "右侧纵向列Z_mm": [round(o.location.z, 3) for o in column],
        "芯片下方数量": len(under_chip),
        "芯片下方对象": [o.name for o in under_chip],
        "芯片下缘Z_mm": round(chip_bottom, 3),
        "芯片下方均低于芯片": True,
        "背面走线/过孔": "已删除",
        "不可靠元件数值": "已删除",
        "正面可见走线": front_traces,
        "纵向列丝印框": len(frames),
        "芯片下丝印框": len(under_frames),
    }
    log("背面布局核验：" + json.dumps(result, ensure_ascii=False))
    return result


def verify_no_type_claims():
    """确保对象和材质命名不把可见外形说成未核实的电气类型。"""
    forbidden = ("钽", "tantalum", "C1", "LED", "电容", "电阻", "发光二极管")
    hits = []
    for obj in bpy.data.objects:
        for token in forbidden:
            if token in obj.name:
                hits.append(f"对象:{obj.name}")
    for mat in bpy.data.materials:
        for token in forbidden:
            if token in mat.name:
                hits.append(f"材质:{mat.name}")
    if hits:
        raise RuntimeError("仍存在未核实类型命名：" + "；".join(hits))
    body = bpy.data.objects.get("背_纵向列_04_金属顶盖件_本体")
    lid = bpy.data.objects.get("背_纵向列_04_金属顶盖件_灰色顶盖")
    if body is None or lid is None:
        raise RuntimeError("金属顶盖件对象缺失")
    note = body.get("类型备注", "")
    if "未核实" not in note:
        raise RuntimeError("金属顶盖件缺少类型未核实备注")
    result = {
        "命名": "金属顶盖件（纵向列第4件）",
        "类型": "未核实",
        "对象": [body.name, lid.name],
        "电气功能推断": "无",
    }
    log("金属顶盖件核验：" + json.dumps(result, ensure_ascii=False))
    return result

def verify_scene_scale(scene):
    """重新打开工程后，用实际 PCB 世界包围盒核验 45 mm。"""
    pcb = bpy.data.objects.get("PCB_主板")
    if pcb is None:
        raise RuntimeError("核验尺度时找不到 PCB_主板")
    scale = scene.unit_settings.scale_length
    data = object_world_width_mm(pcb, scale)
    if abs(data["显示宽度_mm"] - 45.0) > 0.01:
        raise RuntimeError(
            "PCB 工程宽度不是 45 mm："
            f"{data['显示宽度_mm']:.9f} mm（{data['宽度_BU']:.9f} BU，"
            f"scale_length={scale}）"
        )
    data.update({
        "长度单位": scene.unit_settings.length_unit,
        "scale_length_m_per_BU": scale,
        "判定": "通过",
    })
    log("工程尺度核验：" + json.dumps(data, ensure_ascii=False))
    return data


def render_teaching_transparent(filepath, width, height, samples):
    """透明背景教学斜视：同时看到网罩、板上文字与下方接口。"""
    floor.hide_render = True
    scene.camera = cam_teaching
    configure_render(width, height, samples)
    old_transparent = scene.render.film_transparent
    old_mode = scene.render.image_settings.color_mode
    scene.render.film_transparent = True
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = str(filepath)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    elapsed = round(time.time() - t0, 2)
    scene.render.film_transparent = old_transparent
    scene.render.image_settings.color_mode = old_mode
    if not Path(filepath).is_file():
        raise RuntimeError(f"教学斜视未生成：{filepath}")
    size = png_size(filepath)
    color_type = png_color_type(filepath)
    if size != [width, height] or color_type != 6:
        raise RuntimeError(
            f"教学斜视格式异常：size={size}, color_type={color_type}, 期望 RGBA"
        )
    log(f"渲染 教学斜视_透明 -> {Path(filepath).name} ({size[0]}×{size[1]}, RGBA, {elapsed}s)")
    return {
        "view": "teaching_transparent",
        "path": str(filepath),
        "size": size,
        "color_type": color_type,
        "alpha": True,
        "seconds": elapsed,
    }


def render_line_diagnostics():
    """仅检查轮：隔离背面左上细亮线的来源，不用于最终交付图。"""
    if IS_FINAL:
        return {}
    diag_dir = ROOT_DIR / "_工作" / "亮线诊断"
    diag_dir.mkdir(parents=True, exist_ok=True)
    scene.camera = cam_back
    floor.hide_render = True
    configure_render(640, 480, 20)
    edge = bpy.data.objects.get("PCB_前侧边缘描线")
    rings = [o for o in bpy.data.objects if "板面丝印圈" in o.name]
    old_edge_hide = edge.hide_render if edge else None
    old_ring_hide = {o.name: o.hide_render for o in rings}
    old_ray = None
    try:
        old_ray = scene.eevee.use_raytracing
    except Exception:
        pass

    def shoot(tag):
        path = diag_dir / f"亮线诊断_{tag}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        return str(path)

    results = {}
    if edge is not None:
        edge.hide_render = True
        results["B_隐藏边缘描线"] = shoot("B_隐藏边缘描线")
        edge.hide_render = old_edge_hide
    for obj in rings:
        obj.hide_render = True
    results["C_隐藏探头丝印圈"] = shoot("C_隐藏探头丝印圈")
    for obj in rings:
        obj.hide_render = old_ring_hide[obj.name]
    if old_ray is not None:
        try:
            scene.eevee.use_raytracing = False
            results["D_关闭光线追踪"] = shoot("D_关闭光线追踪")
        finally:
            scene.eevee.use_raytracing = old_ray
    if edge is not None:
        edge.hide_render = True
    for obj in rings:
        obj.hide_render = True
    results["E_隐藏边缘与丝印"] = shoot("E_隐藏边缘与丝印")
    if edge is not None:
        edge.hide_render = old_edge_hide
    for obj in rings:
        obj.hide_render = old_ring_hide[obj.name]

    # F：临时换回修订2的高光板材质，验证细亮线是否来自PCB镜面反射。
    board = bpy.data.objects.get("PCB_主板")
    old_board_mat = None
    diag_mat = None
    if board is not None and len(board.data.materials) > 0:
        old_board_mat = board.data.materials[0]
        diag_mat = make_material(
            "M_诊断_旧高光板", (0.003, 0.0034, 0.0034), 0.0, 0.58, 0.05,
            specular=0.10,
        )
        board.data.materials[0] = diag_mat
        results["F_旧高光板材质"] = shoot("F_旧高光板材质")
        board.data.materials[0] = old_board_mat
        bpy.data.materials.remove(diag_mat)

    floor.hide_render = True
    log("亮线诊断图：" + json.dumps(results, ensure_ascii=False))
    return results


def strip_procedural_normals_for_glb():
    """GLB 不能携带这些程序节点；导出前去除 Normal 链接，保留基础 PBR。"""
    removed = 0
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf is None or "Normal" not in bsdf.inputs:
            continue
        for link in list(bsdf.inputs["Normal"].links):
            mat.node_tree.links.remove(link)
            removed += 1
    log(f"GLB 导出前移除程序法线链接：{removed} 条（.blend 中仍保留）")


# 场景说明写入 .blend
notes = bpy.data.texts.new("模型说明_HS-SR04P_修订3")
notes.write(
    "HS-SR04P 超声波模块 · 修订3\n"
    "依据：本工作区两张自有实拍 + 同版商家尺寸图 + 说明.md。\n"
    "标称值：板宽45mm、孔直径3mm、两孔中心距9mm。\n"
    "解释值：26mm按“板上沿到白色侧插接口底部”的总体高度处理；\n"
    "PCB本体约45×21mm（主体高16.8mm、下凸舌4.2mm），板厚1.6mm。\n"
    "照片估测值：探头外径16mm、探头前伸约11.6mm；接口约12.2×5.2×5.8mm。\n"
    "板形：顶部两角为半径约3.8mm、与顶边和侧边相切的连续圆角；\n"
    "板边采用4段倒角，露出FR4侧壁。板宽、孔位、板高、探头位置不变。\n"
    "外观修订：\n"
    "  安装孔为银灰外环 + 深银内圈 + 深褐灰孔壁；\n"
    "  探头焊盘为银灰外圈 + 深银内圈；白色接口为暖象牙白；\n"
    "  接口内部针脚改为暗色金属，不再做亮金色条；\n"
    "  PCB和芯片使用接近黑色的低反射基色；\n"
    "  探头侧壁粗糙度高于前压圈，并有极细微程序凹凸；\n"
    "  防护网为真实横纵线网，约0.50mm节距、0.09mm线径；\n"
    "  网后为浅弧面反射层与一个可见偏心暗点，不声称还原压电内部。\n"
    "丝印：本机 Times New Roman Bold，文字已转网格；不添加不可辨认型号/数值。\n"
    "亮线诊断：修订2左上细线只在旧高光板材质下复现，来自亮安装孔在高光阻焊面上的\n"
    "屏幕空间镜面反射；修订3将PCB阻焊镜面设为0、粗糙度0.62，1200像素复核后消失，未调整灯光。\n"
    "程序凹凸只在Blender中存在；GLB导出基础PBR颜色/金属度/粗糙度。\n"
    "背面右侧纵向列5件、芯片下方3件、16脚/16焊盘、板内丝印均保留。\n"
    "场景尺度：1 BU = 1 m（scale_length=1.0），PCB宽度0.045 BU显示45mm；\n"
    "GLB重导入测量同为45mm。相机：原正面/背面/斜视三台位置不变，\n"
    "另设第四台“相机_教学斜视”用于透明教学图。\n"
    "本模型为教学配图/旋转查看用途，不作为精密装配或电气连接依据。\n"
    "照片斜拍比例未做透视校正，除标称值外的尺寸均为估测。\n"
)
notes.write("\n主要集合：01_PCB主板、02_探头_R、03_探头_T、04_背面元件、05_白色四针接口、06_丝印与走线、07_摄影棚与相机。\n")
notes.write("\n生成脚本：HS-SR04P_修订3_生成脚本.py\n")
notes.write("修订记录：修订记录.md\n")

scene["模型名称"] = "HS-SR04P 超声波模块（修订3）"
scene["模型用途"] = "教材配图与旋转查看"
scene["尺寸解释"] = "26mm按板上沿到接口底部总体高度解释；其余照片估测，斜拍比例未作透视校正"
scene["标称尺寸"] = "板宽45mm；孔径3mm；孔距9mm"
scene["工程尺度"] = "1 BU = 1 m；scale_length=1.0；PCB宽度0.045 BU，按毫米显示45mm"
scene["板角"] = "顶部半径约3.8mm连续圆角，与顶边和侧边相切"
scene["IC引脚数"] = 16
scene["背面纵向列元件数"] = 5
scene["芯片下方元件数"] = 3
scene["外观修订"] = "银灰分层焊盘、哑光黑色PCB/芯片、暖白接口、粗糙度分层铝壳、加密真实线网"
scene["防护网"] = "约0.50mm节距、0.09mm线径、横纵两族、轻微错层"
scene["丝印字体"] = "Times New Roman Bold（本机字体；文字已转网格）"
scene["程序纹理备注"] = "细节凹凸仅在Blender中；GLB导出基础PBR，不含程序纹理"
scene["教学相机"] = "相机_教学斜视（透明背景）"
scene["制作阶段"] = STAGE

convert_all_curves()
bpy.context.view_layer.update()

# 保存前的结构核验；任何一项失败都直接中止，不产生“看似完成”的交付。
BOARD_CHECK = verify_board_shape()
CHIP_CHECK = verify_chip_geometry()
PROBE_APPEARANCE_CHECK = verify_probe_appearance()
SILK_CHECK = verify_probe_silk_inside_board()
SILK_ALL_CHECK = verify_silk_inside_board()
BACK_CHECK = verify_back_layout()
TYPE_CHECK = verify_no_type_claims()
PRE_SAVE_SCALE = verify_scene_scale(scene)

log(f"场景对象数：{len(scene.objects)}；集合数：{len(bpy.data.collections)}")
log(f"保存工程：{BLEND_PATH}")
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), compress=True)
log(f"工程大小：{file_size(BLEND_PATH)} bytes")

record = {
    "阶段": STAGE,
    "时间": datetime.now().astimezone().isoformat(timespec="seconds"),
    "Blender版本": bpy.app.version_string,
    "工程文件": str(BLEND_PATH),
    "物体总数": len(scene.objects),
    "集合": [c.name for c in bpy.data.collections],
    "保存前核验": {
        "板形": BOARD_CHECK,
        "芯片": CHIP_CHECK,
        "探头外观": PROBE_APPEARANCE_CHECK,
        "探头丝印": SILK_CHECK,
        "全部丝印": SILK_ALL_CHECK,
        "背面元件布局": BACK_CHECK,
        "类型命名": TYPE_CHECK,
        "工程尺度": PRE_SAVE_SCALE,
    },
    "渲染": [],
    "亮线诊断": {
        "结论": "修订2背面左上细线为亮安装孔在高光PCB阻焊面上的屏幕空间镜面反射；非板形拼接、重叠面、边缘描线或残留丝印",
        "依据": "检查轮F旧高光板材质复现；B隐藏边缘描线、C隐藏探头丝印圈、D关闭光线追踪、E隐藏边缘与丝印的新材质图中均无该线",
        "修正": "PCB阻焊镜面反射设为0、粗糙度0.62；灯光位置与功率未改",
    },
}

if IS_FINAL:
    # 保存后的 .blend 保留程序凹凸；GLB 只带可移植的基础 PBR。
    strip_procedural_normals_for_glb()
    # 仅选择模型层级导出 GLB，排除灯光/相机/地面
    bpy.ops.object.select_all(action="DESELECT")
    for coll in MODEL_COL.children_recursive:
        for obj in coll.objects:
            obj.select_set(True)
    ROOT.select_set(True)
    bpy.context.view_layer.objects.active = ROOT
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_animations=False,
        export_cameras=False,
        export_lights=False,
        export_yup=True,
    )
    if not GLB_PATH.is_file():
        raise RuntimeError(f"GLB 未生成：{GLB_PATH}")
    with open(GLB_PATH, "rb") as f:
        header = f.read(12)
    if header[:4] != b"glTF":
        raise RuntimeError("GLB 文件头不正确")
    log(f"已导出 GLB：{GLB_PATH} ({file_size(GLB_PATH)} bytes)")

    # 重新打开工程，核验可读性、相机与集合
    log("重新打开工程进行核验")
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
    scene = bpy.context.scene

    required_collections = {
        "01_PCB主板", "02_探头_R", "03_探头_T", "04_背面元件",
        "05_白色四针接口", "06_丝印与走线",
    }
    actual_collections = {c.name for c in bpy.data.collections}
    missing = required_collections.difference(actual_collections)
    if missing:
        raise RuntimeError("重开后缺少集合：" + "、".join(sorted(missing)))
    required_objects = {
        "PCB_主板", "探头R_金属外壳", "探头R_防护网",
        "探头T_金属外壳", "探头T_防护网", "接口_白色壳体",
        "接口_内部针脚_4P", "背_IC_U1_本体", "背_IC_U1_引脚",
        "背_IC_U1_焊盘", "背_纵向列_01_浅色小封装",
        "背_纵向列_02_黑色小件", "背_纵向列_03_米黄色小件",
        "背_纵向列_04_金属顶盖件_本体", "背_纵向列_04_金属顶盖件_灰色顶盖",
        "背_纵向列_05_米黄色小件", "背_芯片下_01_竖向黑色件",
        "背_芯片下_02_米黄色件", "背_芯片下_03_黑色件",
        "走线_正面_可见段", "丝印_背面_HS-SR04P",
    }
    object_names = {o.name for o in scene.objects}
    missing_objects = required_objects.difference(object_names)
    if missing_objects:
        raise RuntimeError("重开后缺少对象：" + "、".join(sorted(missing_objects)))
    # 重新打开后原 Python 数据块引用会失效，因此统一按名称重新获取。
    for cam_name in ("相机_正面", "相机_背面", "相机_斜视", "相机_教学斜视"):
        if cam_name not in object_names:
            raise RuntimeError("重开后缺少相机：" + cam_name)

    cam_front = bpy.data.objects["相机_正面"]
    cam_back = bpy.data.objects["相机_背面"]
    cam_oblique = bpy.data.objects["相机_斜视"]
    cam_teaching = bpy.data.objects["相机_教学斜视"]
    floor = bpy.data.objects["摄影_地面"]
    floor.hide_render = True
    scene.camera = cam_front
    configure_render(RENDER_SIZE[0], RENDER_SIZE[1], RENDER_SAMPLES)

    bpy.context.view_layer.update()
    REOPEN_BOARD_CHECK = verify_board_shape()
    REOPEN_CHIP_CHECK = verify_chip_geometry()
    REOPEN_PROBE_APPEARANCE = verify_probe_appearance()
    REOPEN_SILK_CHECK = verify_probe_silk_inside_board()
    REOPEN_SILK_ALL = verify_silk_inside_board()
    REOPEN_BACK_CHECK = verify_back_layout()
    REOPEN_TYPE_CHECK = verify_no_type_claims()
    REOPEN_SCALE = verify_scene_scale(scene)
    record.update({
        "重新打开成功": True,
        "重开后物体数": len(scene.objects),
        "重开后集合": sorted(actual_collections),
        "重开后相机": ["相机_正面", "相机_背面", "相机_斜视", "相机_教学斜视"],
        "重开后渲染分辨率": [scene.render.resolution_x, scene.render.resolution_y],
        "重开后核验": {
            "板形": REOPEN_BOARD_CHECK,
            "芯片": REOPEN_CHIP_CHECK,
            "探头外观": REOPEN_PROBE_APPEARANCE,
            "探头丝印": REOPEN_SILK_CHECK,
            "全部丝印": REOPEN_SILK_ALL,
            "背面元件布局": REOPEN_BACK_CHECK,
            "类型命名": REOPEN_TYPE_CHECK,
            "工程尺度": REOPEN_SCALE,
        },
    })
    log("工程重新打开并通过结构核验")

    views = (("front", "正面"), ("back", "背面"), ("oblique", "斜视"))
    for view, label in views:
        path = ROOT_DIR / f"{label}_1200.png"
        record["渲染"].append(
            render_view(view, path, 1200, 900, 96)
        )

    # 课件用手透明斜视图：保留三个原视图之后另出一张，不替换三视图。
    teaching_path = ROOT_DIR / "教学斜视_透明.png"
    record["教学斜视_透明"] = render_teaching_transparent(
        teaching_path, 1200, 900, 96
    )

    # ------------------------------------------------------------------
    # GLB 独立重导入核验（仍在同一个 Blender 进程内，完成后再退出）
    # 先清空当前内存场景；已保存的 .blend 不会被改写。
    # ------------------------------------------------------------------
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    bpy.ops.import_scene.gltf(filepath=str(GLB_PATH))
    bpy.context.view_layer.update()
    imported_objs = list(bpy.context.scene.objects)
    imported_meshes = [o for o in imported_objs if o.type == "MESH"]
    pcb_imported = next(
        (o for o in imported_meshes if o.name.startswith("PCB_主板")), None
    )
    if pcb_imported is None:
        raise RuntimeError("GLB 重导入后找不到 PCB_主板")
    glb_width = object_world_width_mm(pcb_imported, 1.0)
    glb_width_m = glb_width["宽度_BU"]
    glb_width_mm = glb_width_m * 1000.0
    if abs(glb_width_mm - 45.0) > 0.01:
        raise RuntimeError(f"GLB 重导入 PCB 宽度不是 45 mm：{glb_width_mm:.9f} mm")
    if len(bpy.data.actions) != 0:
        raise RuntimeError("GLB 重导入后发现动画数据")
    imported_names = {o.name for o in imported_objs}
    glb_column = [
        n for n in (
            "背_纵向列_01_浅色小封装",
            "背_纵向列_02_黑色小件",
            "背_纵向列_03_米黄色小件",
            "背_纵向列_04_金属顶盖件_本体",
            "背_纵向列_05_米黄色小件",
        ) if n in imported_names
    ]
    glb_under = [
        n for n in (
            "背_芯片下_01_竖向黑色件",
            "背_芯片下_02_米黄色件",
            "背_芯片下_03_黑色件",
        ) if n in imported_names
    ]
    if len(glb_column) != 5 or len(glb_under) != 3:
        raise RuntimeError(
            f"GLB 重导入元件数量异常：纵向列{len(glb_column)}、芯片下{len(glb_under)}"
        )
    glb_lead = next((o for o in imported_meshes if o.name == "背_IC_U1_引脚"), None)
    glb_pad = next((o for o in imported_meshes if o.name == "背_IC_U1_焊盘"), None)
    if glb_lead is None or glb_pad is None:
        raise RuntimeError("GLB 重导入后缺少芯片引脚/焊盘网格")
    # glTF 会按法线拆点，不能使用网格连通块计数；改按世界坐标空间槽位计数。
    glb_lead_slots = count_glb_grid_slots(glb_lead, x_gap=0.75, z_gap=0.75)
    # 焊盘单侧宽度 0.82 mm，X 阈值需大于 0.82；行间空隙约 0.67 mm。
    glb_pad_slots = count_glb_grid_slots(glb_pad, x_gap=0.90, z_gap=0.64)
    if glb_lead_slots["空间槽位总数"] != 16:
        raise RuntimeError(f"GLB 引脚空间槽位不是16：{glb_lead_slots}")
    if glb_pad_slots["空间槽位总数"] != 16:
        raise RuntimeError(f"GLB 焊盘空间槽位不是16：{glb_pad_slots}")
    glb_decor_hits = [
        n for n in imported_names
        if n.startswith(("走线_背面", "背面过孔"))
        or any(t in n for t in ("310", "226", "000"))
    ]
    if glb_decor_hits:
        raise RuntimeError("GLB 中仍有无依据的背面装饰/数值：" + "、".join(glb_decor_hits))
    glb_check = {
        "重导入成功": True,
        "PCB宽度_m": glb_width_m,
        "PCB宽度_mm": glb_width_mm,
        "对象数": len(imported_objs),
        "网格数": len(imported_meshes),
        "动画数": len(bpy.data.actions),
        "纵向列元件": glb_column,
        "芯片下方元件": glb_under,
        "芯片引脚空间槽位": glb_lead_slots,
        "芯片焊盘空间槽位": glb_pad_slots,
        "无依据背面装饰": "无",
        "判定": "通过",
    }
    log("GLB 独立重导入核验：" + json.dumps(glb_check, ensure_ascii=False))

    # 最终尺寸与文件核验
    record.update({
        "GLB": str(GLB_PATH),
        "GLB大小字节": file_size(GLB_PATH),
        "GLB文件头": "glTF",
        "GLB重导入验证": glb_check,
        "预览图最长边": 1200,
        "状态": "完成",
    })
else:
    views = (("front", "正面"), ("back", "背面"), ("oblique", "斜视"))
    for view, label in views:
        path = OUTPUT_DIR / f"{VIEW_PREFIX}{label}_{RENDER_SIZE[0]}.png"
        record["渲染"].append(
            render_view(view, path, RENDER_SIZE[0], RENDER_SIZE[1], RENDER_SAMPLES)
        )
    teaching_preview = OUTPUT_DIR / f"{VIEW_PREFIX}教学斜视_透明_{RENDER_SIZE[0]}.png"
    record["教学斜视_透明"] = render_teaching_transparent(
        teaching_preview, RENDER_SIZE[0], RENDER_SIZE[1], RENDER_SAMPLES
    )
    record["亮线诊断"] = render_line_diagnostics()
    record.update({
        "状态": "低分辨率检查图已生成",
        "说明": "本阶段不导出 GLB；包含透明教学视角与亮线隔离诊断。",
    })

RENDER_RECORD_PATH.write_text(
    json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
)
log("记录：" + str(RENDER_RECORD_PATH))
log("完成")
