# Backlot 片场 v1.4.1 · 示例白模：两层旧仓库（有高低差）
# 作者：Manson AIGC · 许可 CC BY 4.0（转发、修改请保留这一行署名）
#
# 用法（命令行，不开界面）：
#   blender -b --factory-startup -P build_两层仓库_v1.py -- <输出文件夹>
# 也可以在 Blender 里新建一个空白文件，到 Scripting 面板粘贴运行：脚本会先清空这个文件里的东西再搭，
#   所以不要在有你自己作品的文件里跑。
#
# 场景：一座旧仓库，一楼是挑高的大厅，北墙一侧有一条二层走廊（夹层），西墙边一道钢楼梯上去。
# 数字和 examples/两层仓库/示例说明.md 里的设定卡一致。
# 坐标：原点 = 西南墙角地面；X 往东，Y 往北，Z 往上；单位米。
# 和单层房间的不同：楼上楼下两个机位要用"对视点"对上；俯视图看不出高度，要多出一张剖面图。
import bpy, math, os, sys
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0]) if argv else (os.path.dirname(bpy.data.filepath)
                                              or os.path.join(os.path.expanduser("~"), "Backlot_白模输出"))
RENDERS = os.path.join(OUT, "renders"); os.makedirs(RENDERS, exist_ok=True)
NAME = "两层仓库_白模_v1"

if bpy.app.background:
    bpy.ops.wm.read_factory_settings(use_empty=True)
else:
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections): bpy.data.collections.remove(c)
scene = bpy.context.scene
GROUPS = {}

def group(n):
    if n not in GROUPS:
        c = bpy.data.collections.new(n); scene.collection.children.link(c); GROUPS[n] = c
    return GROUPS[n]

_cube = bpy.data.meshes.new("unit_cube")
_cube.from_pydata([(x, y, z) for x in (-.5, .5) for y in (-.5, .5) for z in (-.5, .5)], [],
                  [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
_cube.update()

def box(n, x0, x1, y0, y1, z0, z1, col, g):
    o = bpy.data.objects.new(n, _cube)
    o.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    o.scale = (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))
    o.color = (*col, 1); group(g).objects.link(o); return o

def cyl(n, x, y, z0, z1, r, col, g, verts=16):
    m = bpy.data.meshes.new(n + "_mesh")
    pts = [(r * math.cos(2 * math.pi * k / verts), r * math.sin(2 * math.pi * k / verts)) for k in range(verts)]
    vs = [(px, py, -.5) for px, py in pts] + [(px, py, .5) for px, py in pts]
    fs = [tuple(range(verts))[::-1], tuple(range(verts, 2 * verts))]
    fs += [(k, (k + 1) % verts, verts + (k + 1) % verts, verts + k) for k in range(verts)]
    m.from_pydata(vs, [], fs); m.update()
    o = bpy.data.objects.new(n, m); o.location = (x, y, (z0 + z1) / 2); o.scale = (1, 1, z1 - z0)
    o.color = (*col, 1); group(g).objects.link(o); return o

def slab_yz(n, x0, x1, yz, col, g):
    """斜的长条（楼梯斜梁、斜扶手）：在 Y-Z 平面上给四个角 (y, z)，沿 X 方向从 x0 拉到 x1。"""
    m = bpy.data.meshes.new(n + "_mesh")
    vs = [(x0, y, z) for y, z in yz] + [(x1, y, z) for y, z in yz]
    fs = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    m.from_pydata(vs, [], fs); m.update()
    o = bpy.data.objects.new(n, m); o.color = (*col, 1); group(g).objects.link(o); return o

# 颜色只为在白模里读得清，生成时颜色按母图走
FLOOR = (.30, .30, .31); WALL = (.30, .28, .26); STEEL = (.22, .24, .27); DARK = (.16, .15, .14)
GLASS = (.55, .62, .70); WOOD = (.40, .30, .20); LAMP = (.85, .85, .80); ROOF = (.18, .18, .19)

# ================= 一、厂房 =================
X, Y, H, T = 24.0, 12.0, 9.0, .25            # 东西 24 米，南北 12 米，檐口高 9 米，墙厚
box("地面", -1, X + 1, -1, Y + 1, -.1, 0, FLOOR, "地面")
box("屋面", -T, X + T, -T, Y + T, H, H + .2, ROOF, "屋顶")
for i, bx in enumerate([2, 6, 10, 14, 18, 22]):               # 屋顶下正好六道钢梁，南北走向
    box(f"屋架钢梁{i+1}", bx - .15, bx + .15, 0, Y, H - .6, H, STEEL, "屋顶")
box("西墙", -T, 0, 0, Y, 0, H, WALL, "西墙")
# 东墙：一扇小门，Y 3～4，高 2.1，关着
box("东墙_门南", X, X + T, 0, 3.0, 0, H, WALL, "东墙")
box("东墙_门北", X, X + T, 4.0, Y, 0, H, WALL, "东墙")
box("东墙_门上", X, X + T, 3.0, 4.0, 2.1, H, WALL, "东墙")
box("东墙小门（关着）", X - .05, X, 3.0, 4.0, 0, 2.1, DARK, "东墙")
# 南墙：大货门 X 9～14、高 5 米，关着；上面一排六扇高窗，窗台 6 米、窗顶 8 米
def wall_with_holes(n, axis_y, ys, holes, col, g):
    """一面东西向的墙（在 Y=axis_y，厚度 ys），按洞口 [(x0, x1, z0, z1)] 切成块。"""
    y0, y1 = ys
    xs = sorted({-T, X + T} | {h[0] for h in holes} | {h[1] for h in holes})
    for a, b in zip(xs, xs[1:]):
        zs = [(h[2], h[3]) for h in holes if h[0] <= a and h[1] >= b]
        cuts = sorted(zs); z = 0; k = 0
        for z0, z1 in cuts:
            if z0 > z: box(f"{n}_{a:.1f}_{k}", a, b, y0, y1, z, z0, col, g); k += 1
            z = max(z, z1)
        if z < H: box(f"{n}_{a:.1f}_{k}", a, b, y0, y1, z, H, col, g)
S_WIN = [(c - 1.1, c + 1.1, 6.0, 8.0) for c in [2, 6, 10, 14, 18, 22]]
wall_with_holes("南墙", 0, (-T, 0), S_WIN + [(9.0, 14.0, 0, 5.0)], WALL, "南墙")
box("大货门（关着）", 9.0, 14.0, -.12, -.05, 0, 5.0, DARK, "南墙")
for i, (a, b, z0, z1) in enumerate(S_WIN):
    box(f"南高窗{i+1}_玻璃", a, b, -.15, -.13, z0, z1, GLASS, "南墙")
# 北墙：二层走廊里三扇窗，X 中心 6、12、18，宽 2 米，窗台 5.6、窗顶 7.4
N_WIN = [(c - 1.0, c + 1.0, 5.6, 7.4) for c in [6, 12, 18]]
wall_with_holes("北墙", Y, (Y, Y + T), N_WIN, WALL, "北墙")
for i, (a, b, z0, z1) in enumerate(N_WIN):
    box(f"北窗{i+1}_玻璃", a, b, Y + .12, Y + .14, z0, z1, GLASS, "北墙")

# ================= 二、二层走廊（夹层）和楼梯 =================
MZ_Y, MZ_Z = 9.5, 4.2                        # 走廊前沿 Y=9.5，走廊地面高 4.2 米，进深 2.5 米
box("二层楼板", 0, X, MZ_Y, Y, MZ_Z - .25, MZ_Z, STEEL, "二层")
box("二层前沿边梁", 0, X, MZ_Y - .01, MZ_Y + .2, MZ_Z - .55, MZ_Z - .01, STEEL, "二层")
# ↑ 边梁比楼板往外凸 1 厘米、顶面低 1 厘米：两个面叠在同一位置，渲染出来会是一片碎斑
for i, cx in enumerate([4, 10, 16, 22]):                        # 走廊下正好四根钢柱
    box(f"走廊钢柱{i+1}", cx - .15, cx + .15, MZ_Y + .02, MZ_Y + .32, 0, MZ_Z - .55, STEEL, "钢柱")   # 柱子落地，一楼平面要看得到
RAIL_X0 = 1.2                                                   # 楼梯在 X 0～1.2 上来，那一段不装栏杆
RAIL_TOP = MZ_Z + 1.05
posts = [RAIL_X0 + 2 * k for k in range(12)] + [X - .05]       # 立柱每 2 米一根
for i, px in enumerate(posts):
    box(f"栏杆立柱{i+1}", px - .03, px + .03, MZ_Y + .05, MZ_Y + .11, MZ_Z, RAIL_TOP - .01, STEEL, "二层")
box("栏杆扶手", RAIL_X0 - .03, X, MZ_Y + .04, MZ_Y + .12, RAIL_TOP - .05, RAIL_TOP, STEEL, "二层")
box("栏杆中横杆", RAIL_X0 - .03, X, MZ_Y + .06, MZ_Y + .10, MZ_Z + .5, MZ_Z + .54, STEEL, "二层")
box("走廊长工作台_台面", 8.0, 11.0, 10.6, 11.4, .86, .9, WOOD, "一楼陈设")   # 在走廊下面、一楼
for i, (lx, ly) in enumerate([(8.0, 10.6), (10.95, 10.6), (8.0, 11.35), (10.95, 11.35)]):
    box(f"走廊长工作台_腿{i+1}", lx, lx + .05, ly, ly + .05, 0, .86, WOOD, "一楼陈设")

# 钢楼梯：贴西墙，X 0～1.2，从 Y=2.5 地面起步往北上，到 Y=9.5 接走廊；21 级，每级高 0.2、深 0.35，镂空踏板
ST_X0, ST_X1, ST_Y0, STEP_H, STEP_D, N = 0.0, 1.2, 2.5, .2, .35, 20
for i in range(N):
    y0 = ST_Y0 + i * STEP_D; zt = (i + 1) * STEP_H
    box(f"楼梯踏板{i+1:02d}", ST_X0 + .05, ST_X1 - .05, y0, y0 + STEP_D, zt - .04, zt, STEEL, "楼梯")
top_y = ST_Y0 + N * STEP_D                                     # = 9.5，最后一步跨上走廊
for side, (a, b) in (("西", (ST_X0, ST_X0 + .05)), ("东", (ST_X1 - .05, ST_X1))):
    slab_yz(f"楼梯斜梁_{side}", a, b, [(ST_Y0, 0), (top_y, MZ_Z - .25), (top_y, MZ_Z), (ST_Y0, .25)], STEEL, "楼梯")
# 楼梯扶手只装在开敞的东侧：斜扶手比踏板前沿高 0.9 米
slab_yz("楼梯扶手", ST_X1 - .04, ST_X1 + .02,
        [(ST_Y0, .9 + STEP_H - .04), (top_y, MZ_Z + .9 - .04), (top_y, MZ_Z + .9), (ST_Y0, .9 + STEP_H)], STEEL, "楼梯")
for i, yy in enumerate([ST_Y0 + .1, (ST_Y0 + top_y) / 2, top_y - .1]):
    zf = STEP_H * (1 + int((yy - ST_Y0) / STEP_D))
    box(f"楼梯扶手立柱{i+1}", ST_X1 - .04, ST_X1 + .02, yy - .03, yy + .03, zf, zf + .9, STEEL, "楼梯")

# ================= 三、一楼陈设和灯 =================
def crates(n, x0, y0, nx, ny, nz, s=1.2, g="一楼陈设"):
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                box(f"{n}_{i}{j}{k}", x0 + i * s + .02, x0 + (i + 1) * s - .02, y0 + j * s + .02,
                    y0 + (j + 1) * s - .02, k * s, (k + 1) * s - .02, WOOD, g)
crates("木箱堆1", 4.0, 0.3, 2, 1, 2)           # 靠南墙、货门西边：两列一排两层，共 4 只
crates("木箱堆2", 18.0, 6.5, 1, 2, 2)          # 大厅东半边：一列两排两层，共 4 只
# 箱子的位置是试过机位后定的：最早放在大厅中间、东堆三层高，母图机位里两堆箱子把楼梯和走廊东段都挡住了
for i, lx in enumerate([6.0, 12.0, 18.0]):     # 大厅上空正好三盏工矿罩灯，白天不亮
    cyl(f"工矿灯{i+1}_灯罩", lx, 4.0, 6.6, 7.0, .35, LAMP, "灯")
    cyl(f"工矿灯{i+1}_吊杆", lx, 4.0, 7.0, H - .6, .015, STEEL, "灯", verts=8)
# 灯原来挂在 Y=5，A 机位仰拍时 1 号灯正好卡在画面左上角、只露半个；挪到 Y=4 后 A 里三盏都不入画

# 人物占位：只在俯视和剖面里显示。两人就是 A、B 两个机位的"对视点"
UP = (8.0, 9.95)      # 楼上的人：站在走廊栏杆后，离扶手约 0.3 米
DN = (12.3, 4.6)      # 楼下的人：站在大厅里
cyl("人物_楼上的人", UP[0], UP[1], MZ_Z, MZ_Z + 1.7, .25, (.85, .45, .6), "人物占位")
cyl("人物_楼下的人", DN[0], DN[1], 0, 1.7, .25, (.4, .6, .9), "人物占位")

KEY = ["栏杆扶手", "二层前沿边梁", "楼梯踏板01", "楼梯踏板20", "走廊钢柱1", "走廊钢柱2", "走廊钢柱3", "走廊钢柱4",
       "工矿灯1_灯罩", "工矿灯2_灯罩", "工矿灯3_灯罩", "大货门（关着）", "北窗1_玻璃", "北窗2_玻璃", "北窗3_玻璃"]

# ================= 四、相机 =================
def camera(n, loc, target, lens):
    cd = bpy.data.cameras.new(n); cd.lens = lens; cd.sensor_width = 36; cd.sensor_fit = 'HORIZONTAL'; cd.clip_end = 500
    co = bpy.data.objects.new(n, cd); co.location = loc
    co.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    group("相机").objects.link(co); return co

EYE = 1.6
CAMS = {   # 名字: (相机位置, 看向的点, 焦距 mm)
    # 母图：站在东南角地面往西北看，楼梯、走廊、栏杆、钢柱、北窗、屋架、灯都在画面里
    "CAM_母图_东南角往西北": ((22.5, 1.0, 1.7), (6.0, 10.0, 4.0), 18),
    # A：楼下的人抬头看楼上的人（仰拍）。相机 = 楼下的人的眼睛，看向 = 楼上的人的脸
    "CAM_A_一楼仰看走廊":   ((DN[0], DN[1], EYE), (UP[0], UP[1], MZ_Z + EYE), 28),
    # B：A 的反打，楼上的人低头看楼下的人（俯拍）。相机 = 楼上的人的眼睛，看向 = 楼下的人
    "CAM_B_走廊俯看一楼":   ((UP[0], UP[1], MZ_Z + EYE), (DN[0], DN[1], 1.0), 20),
    # C：站在楼梯脚边往北看楼梯上到走廊
    "CAM_C_楼梯脚往上":     ((3.0, 1.0, 1.5), (0.6, 9.5, 4.4), 20),
}
cams = {k: camera(k, *v) for k, v in CAMS.items()}
# 机位标记和走廊投影线：只在一楼平面里显示。三角形尖头 = 相机朝向（母图白、A 红、B 蓝、C 绿）
MARK = {"CAM_母图_东南角往西北": (.95, .95, .95), "CAM_A_一楼仰看走廊": (.90, .25, .20),
        "CAM_B_走廊俯看一楼": (.25, .45, .95), "CAM_C_楼梯脚往上": (.30, .80, .35)}
def cam_marker(n, loc, target, col, z=.05, L=1.4, W=.7):
    d = Vector((target[0] - loc[0], target[1] - loc[1], 0)).normalized(); q = Vector((-d.y, d.x, 0))
    p0 = Vector((loc[0], loc[1], z))
    m = bpy.data.meshes.new(n + "_mesh")
    m.from_pydata([tuple(p0 + d * L), tuple(p0 + q * W / 2), tuple(p0 - q * W / 2)], [], [(0, 1, 2)]); m.update()
    o = bpy.data.objects.new(n, m); o.color = (*col, 1); group("机位标记").objects.link(o)
for k, (loc, tgt, _) in CAMS.items():
    cam_marker("标记_" + k, loc, tgt, MARK[k])
box("标记_二层走廊前沿投影线", 0, X, MZ_Y - .04, MZ_Y + .04, .01, .03, (.85, .75, .30), "机位标记")
top = camera("CAM_俯视_一楼平面", (X / 2, Y / 2, 40), (X / 2, Y / 2, 0), 50)
top.data.type = 'ORTHO'; top.data.ortho_scale = X * 1.1; top.rotation_euler = (0, 0, 0)
sec = camera("CAM_剖面_东往西", (60, Y / 2, H / 2), (0, Y / 2, H / 2), 50)   # 拆掉东墙，正交往西看：看高度
sec.data.type = 'ORTHO'; sec.data.ortho_scale = Y * 1.25

# ================= 渲染设置 =================
scene.render.engine = 'BLENDER_WORKBENCH'
sh = scene.display.shading; sh.light = 'STUDIO'; sh.color_type = 'OBJECT'
sh.show_cavity = True; sh.cavity_type = 'WORLD'; sh.show_object_outline = True
sh.show_shadows = False   # 有屋顶的室内：开投影会把整个室内压黑，还在楼板上留下一块块斑点，这一例关掉
scene.display.light_direction = (.3, -.2, .9)
w = bpy.data.worlds.new("W"); scene.world = w; w.color = (.10, .10, .11)
scene.render.image_settings.file_format = 'PNG'

def show(**kw):
    for n, on in kw.items():
        if n in GROUPS: GROUPS[n].hide_render = not on

def project_check(cam_name):
    bpy.context.view_layer.update()
    cam = bpy.data.objects[cam_name]
    print(f"--- 投影检查 {cam_name} ---")
    for n in KEY:
        o = bpy.data.objects.get(n)
        if not o or o.users_collection[0].hide_render: continue
        ps = [world_to_camera_view(scene, cam, o.matrix_world @ Vector(c)) for c in o.bound_box]
        xs, ys, zs = [p.x for p in ps], [p.y for p in ps], [p.z for p in ps]
        if max(zs) <= 0:
            print(f"  {n}: 在相机身后，不在画面里"); continue
        if min(zs) <= 0:
            print(f"  {n}: 有一部分在相机身后（被画框切到）"); continue
        inside = min(xs) >= 0 and max(xs) <= 1 and min(ys) >= 0 and max(ys) <= 1
        visible = max(xs) > 0 and min(xs) < 1 and max(ys) > 0 and min(ys) < 1
        state = "完整在画面内" if inside else ("被画框切到" if visible else "不在画面里")
        print(f"  {n}: 横 {min(xs):.2f}～{max(xs):.2f}  竖 {min(ys):.2f}～{max(ys):.2f}  {state}")

def render(cam_name, tag, W, Hh):
    scene.camera = bpy.data.objects[cam_name]
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = W, Hh, 100
    project_check(cam_name)
    path = os.path.join(RENDERS, f"{NAME}_{tag}.png")
    scene.render.filepath = path; bpy.ops.render.render(write_still=True)
    print("  已渲染：", path, "存在" if os.path.exists(path) else "【没找到文件，检查输出路径】")

# ================= 五、要出哪些图 =================
W16, H16 = 1920, 1080
show(人物占位=False, 机位标记=False)
render("CAM_母图_东南角往西北", "母图机位_东南角往西北", W16, H16)
render("CAM_A_一楼仰看走廊", "A_一楼仰看走廊", W16, H16)
render("CAM_B_走廊俯看一楼", "B_走廊俯看一楼", W16, H16)
render("CAM_C_楼梯脚往上", "C_楼梯脚往上", W16, H16)
show(屋顶=False, 灯=False, 二层=False, 人物占位=True, 机位标记=True)            # 一楼平面：掀掉屋顶和走廊楼板，看一楼和楼梯
render("CAM_俯视_一楼平面", "俯视_一楼平面", 2000, int(2000 * Y / X * 1.0))
show(屋顶=True, 灯=True, 二层=True, 东墙=False, 机位标记=False)                  # 剖面：拆掉东墙，看楼上楼下的高度关系
render("CAM_剖面_东往西", "剖面_东往西", 1500, 1200)
show(东墙=True, 人物占位=False)

scene.camera = cams["CAM_母图_东南角往西北"]
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, NAME + ".blend"))
print("完成。渲染图在：", RENDERS)
