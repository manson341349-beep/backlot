# Backlot 片场 v1.4 · 白模模板脚本
# 作者：Manson AIGC · 许可 CC BY 4.0（转发、修改请保留这一行署名）
#
# 用法（命令行，不开界面）：
#   blender -b --factory-startup -P whitebox_template.py -- <输出文件夹> [母图路径]
# 也可以在 Blender 里新建一个空白文件，到 Scripting 面板粘贴运行：脚本会先清空这个文件里的东西再搭，
#   所以不要在有你自己作品的文件里跑。输出到 .blend 所在文件夹；文件没保存过，就输出到 主目录/Backlot_白模输出。
#
# 例子场景：九十年代老式办公室，5 × 4 米，层高 3 米（和 references/scene-card.md 的例子一致）。
# 改成你的场景：重写「一、房间」「二、构件」「三、相机」「四、要出哪些图」这四段（墙、构件、相机都要照设定卡重写，
#   不只是改几个数字）；这四段以外的工具函数和检查不用动。
# 坐标：原点 = 西南墙角地面；X 往东，Y 往北，Z 往上；单位米。
import bpy, math, os, sys
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0]) if argv else (os.path.dirname(bpy.data.filepath)
                                              or os.path.join(os.path.expanduser("~"), "Backlot_白模输出"))
MOTHER = argv[1] if len(argv) > 1 else ""          # 母图路径，可不填
RENDERS = os.path.join(OUT, "renders"); os.makedirs(RENDERS, exist_ok=True)
NAME = "老办公室_白模_v2"                            # 输出文件名前缀

if bpy.app.background:                             # 命令行：从空白开始
    bpy.ops.wm.read_factory_settings(use_empty=True)
else:                                              # 界面里粘贴运行：只清空当前文件里的物体和组
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections): bpy.data.collections.remove(c)
scene = bpy.context.scene
GROUPS = {}

def group(n):
    """每样东西放进一个组，某个角度可以整组隐藏（比如拆掉一面墙放相机）。"""
    if n not in GROUPS:
        c = bpy.data.collections.new(n); scene.collection.children.link(c); GROUPS[n] = c
    return GROUPS[n]

_cube = bpy.data.meshes.new("unit_cube")
_cube.from_pydata([(x, y, z) for x in (-.5, .5) for y in (-.5, .5) for z in (-.5, .5)], [],
                  [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
_cube.update()

def box(n, x0, x1, y0, y1, z0, z1, col, g):
    """方块：给出 X、Y、Z 三个方向的起止坐标。"""
    o = bpy.data.objects.new(n, _cube)
    o.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    o.scale = (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))
    o.color = (*col, 1); group(g).objects.link(o); return o

def cyl(n, x, y, z0, z1, r, col, g, verts=24):
    """竖直圆柱：灯罩、柱子、人物占位。"""
    m = bpy.data.meshes.new(n + "_mesh")
    pts = [(r * math.cos(2 * math.pi * k / verts), r * math.sin(2 * math.pi * k / verts)) for k in range(verts)]
    vs = [(px, py, -.5) for px, py in pts] + [(px, py, .5) for px, py in pts]
    fs = [tuple(range(verts))[::-1], tuple(range(verts, 2 * verts))]
    fs += [(k, (k + 1) % verts, verts + (k + 1) % verts, verts + k) for k in range(verts)]
    m.from_pydata(vs, [], fs); m.update()
    o = bpy.data.objects.new(n, m); o.location = (x, y, (z0 + z1) / 2); o.scale = (1, 1, z1 - z0)
    o.color = (*col, 1); group(g).objects.link(o); return o

def table(n, cx, cy, w, d, h, col, g, top=.04, leg=.05):
    """有四条腿的桌子：中心 (cx, cy)，宽 w（X 向）、深 d（Y 向）、高 h。"""
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2
    box(n + "_桌面", x0, x1, y0, y1, h - top, h, col, g)
    for i, (lx, ly) in enumerate([(x0, y0), (x1 - leg, y0), (x0, y1 - leg), (x1 - leg, y1 - leg)]):
        box(f"{n}_腿{i+1}", lx, lx + leg, ly, ly + leg, 0, h - top, col, g)

def chair(n, cx, cy, facing, col, g, seat=.45, size=.46, back=.95, leg=.04):
    """有四条腿、有靠背的椅子。facing = 'N' / 'S' / 'E' / 'W'：坐的人面朝哪边。靠背在反方向。
    座板下面留空、看得见地面；后腿一直通到靠背顶当立柱。"""
    s = size / 2; x0, x1, y0, y1 = cx - s, cx + s, cy - s, cy + s
    box(n + "_座板", x0, x1, y0, y1, seat - .04, seat, col, g)
    back_side = {"N": "S", "S": "N", "E": "W", "W": "E"}[facing]
    corners = {"SW": (x0, y0), "SE": (x1 - leg, y0), "NW": (x0, y1 - leg), "NE": (x1 - leg, y1 - leg)}
    for k, (lx, ly) in corners.items():
        tall = back_side in k
        box(f"{n}_腿_{k}", lx, lx + leg, ly, ly + leg, 0, back if tall else seat - .04, col, g)
    t = .03
    if back_side == "S": box(n + "_靠背", x0 + leg, x1 - leg, y0, y0 + t, seat + .15, back - .03, col, g)
    if back_side == "N": box(n + "_靠背", x0 + leg, x1 - leg, y1 - t, y1, seat + .15, back - .03, col, g)
    if back_side == "W": box(n + "_靠背", x0, x0 + t, y0 + leg, y1 - leg, seat + .15, back - .03, col, g)
    if back_side == "E": box(n + "_靠背", x1 - t, x1, y0 + leg, y1 - leg, seat + .15, back - .03, col, g)

# 颜色只为在白模里读得清，生成时颜色按母图走。相邻的体块深浅拉开，前后几层才分得清；
# 一律用灰，不用带颜色倾向的色块（蓝色的"玻璃"会被照搬成一块蓝板）。
FLOOR = (.34, .34, .34); WALL = (.52, .52, .52); WOOD = (.26, .26, .26); DARK = (.14, .14, .14)
METAL = (.40, .40, .40); LAMP = (.95, .95, .95); GLASS = (.70, .70, .70); CEIL = (.20, .20, .20)

# ================= 一、房间 =================
ROOM = dict(X=5.0, Y=4.0, H=3.0)        # 东西长、南北宽、层高
X, Y, H, T = ROOM["X"], ROOM["Y"], ROOM["H"], .15   # T = 墙厚
box("地面", 0, X, 0, Y, -.1, 0, FLOOR, "地面")
box("天花板", 0, X, 0, Y, H, H + .1, CEIL, "天花板")
# 每面墙做成一整块，不用几块拼（拼缝会渲出竖线，被画成墙板缝）。门、窗做成贴在墙内侧的薄板。
box("西墙", -T, 0, 0, Y, 0, H, WALL, "西墙")
box("东墙", X, X + T, 0, Y, 0, H, WALL, "东墙")
box("南墙", -T, X + T, -T, 0, 0, H, WALL, "南墙")
box("北墙", -T, X + T, Y, Y + T, 0, H, WALL, "北墙")
# 南墙的门：X 0.6～1.5，高 2.1，关着
DOOR = (0.6, 1.5, 2.1)
box("门扇（关着，贴门框）", DOOR[0], DOOR[1], 0, .04, 0, DOOR[2], DARK, "门")
box("门扇_磨砂玻璃", DOOR[0] + .12, DOOR[1] - .12, .04, .045, 1.15, 1.95, GLASS, "门")
# 北墙三扇竖窗：X 1.5～4.5，窗台 0.9，窗顶 2.4
WIN_X0, WIN_X1, SILL, TOP = 1.5, 4.5, 0.9, 2.4
box("窗玻璃", WIN_X0, WIN_X1, Y - .02, Y, SILL, TOP, GLASS, "窗")
for i in range(4):                                     # 三扇窗 = 四根窗框竖梃
    mx = WIN_X0 + i * (WIN_X1 - WIN_X0) / 3
    box(f"窗框竖梃_{i}", mx - .04, mx + .04, Y - .06, Y - .02, SILL, TOP, DARK, "窗")

# ================= 二、构件 =================
table("办公桌", 2.5, 2.6, 1.6, 0.8, 0.76, WOOD, "家具")
chair("办公椅", 2.5, 3.2, "S", DARK, "家具")          # 坐的人面朝南（朝门）
chair("访客椅", 2.5, 1.8, "N", DARK, "家具")          # 面朝北，对着桌子
box("书柜", 0, .4, 1.2, 3.6, 0, 2.2, WOOD, "家具")
box("文件柜", 4.5, 5.0, .5, 1.0, 0, 1.3, METAL, "家具")
cyl("衣帽架", .3, .35, 0, 1.8, .03, DARK, "家具", verts=12)
cyl("台灯_灯罩", 3.1, 2.75, .95, 1.1, .1, METAL, "灯", verts=16)
for i, lx in enumerate([1.8, 3.4]):                   # 吊灯正好两盏
    cyl(f"吊灯{i+1}_灯罩", lx, 2.0, 2.5, 2.7, .22, LAMP, "灯")
    cyl(f"吊灯{i+1}_吊杆", lx, 2.0, 2.7, H, .01, METAL, "灯", verts=8)

# 人物占位：只在俯视图里显示
for n, px, py, h, col in [("坐着的主角", 2.5, 3.2, 1.25, (.85, .45, .6)), ("访客", 2.5, 1.8, 1.25, (.4, .6, .9))]:
    cyl("人物_" + n, px, py, 0, h, .22, col, "人物占位", verts=16)

# ================= 三、相机 =================
def camera(n, loc, target, lens):
    cd = bpy.data.cameras.new(n); cd.lens = lens; cd.sensor_width = 36; cd.sensor_fit = 'HORIZONTAL'; cd.clip_end = 500
    co = bpy.data.objects.new(n, cd); co.location = loc
    co.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    group("相机").objects.link(co); return co

CAMS = {   # 名字: (相机位置, 看向的点, 焦距 mm)。派生机位焦距尽量 20 毫米以上，超广角的透视模型会拉平
    # 母图：拆掉东墙（像影棚的"活动墙"），从东边稍高处往西看，门、窗、书柜、桌椅都在画面里
    # 相机偏南、比吊灯低、斜着看，两盏吊灯才不会前后叠成一盏
    "CAM_母图_东边往西":   ((7.4, 0.5, 1.7), (0.0, 2.7, 1.25), 20),
    "CAM_A_门口往北":      ((2.2, -3.0, 1.6), (1.50, 1.95, 1.43), 32),
    "CAM_B_窗边往南":      ((2.6, 6.8, 1.7), (1.73, 1.88, 1.53), 32),
}
cams = {k: camera(k, *v) for k, v in CAMS.items()}
top = camera("CAM_俯视布局", (X / 2, Y / 2, 30), (X / 2, Y / 2, 0), 50)
top.data.type = 'ORTHO'; top.data.ortho_scale = max(X, Y) * 1.15; top.rotation_euler = (0, 0, 0)
chk = camera("CAM_椅子检查", (3.6, .9, .5), (2.5, 1.8, .3), 28)   # 斜下方看访客椅：四条腿要都在、都着地
proof = camera("CAM_自证_正对东墙", (1.0, 2.0, 1.5), (5.0, 2.0, 1.5), 28)   # 只用来证明"未定墙面检查"会报出东西

# 每台相机必须完整拍到什么（角度清单里"画面里必须有什么"那一栏）。投影检查只查这里列的。
MUST = {
    "CAM_母图_东边往西": ["门扇（关着，贴门框）", "吊灯1_灯罩", "吊灯2_灯罩", "办公桌_桌面", "办公椅_座板", "访客椅_座板", "书柜", "窗玻璃"],
    "CAM_A_门口往北":    ["吊灯1_灯罩", "吊灯2_灯罩", "办公桌_桌面", "办公椅_座板", "窗玻璃"],
    "CAM_B_窗边往南":    ["门扇（关着，贴门框）", "衣帽架", "办公桌_桌面", "访客椅_座板", "吊灯1_灯罩", "吊灯2_灯罩"],
}
# 母图里看不到、没定的墙面（母图机位拆掉了东墙）。派生机位不能拍到它们。
UNSEEN = ["东墙"]

if MOTHER and os.path.exists(MOTHER):        # 母图挂到母图相机背景上，开界面时可以直接对位
    cd = cams["CAM_母图_东边往西"].data; cd.show_background_images = True
    bg = cd.background_images.new(); bg.image = bpy.data.images.load(MOTHER); bg.alpha = .5; bg.display_depth = 'FRONT'

# ================= 渲染设置（Workbench，灰模，快） =================
scene.render.engine = 'BLENDER_WORKBENCH'
sh = scene.display.shading; sh.light = 'STUDIO'; sh.color_type = 'OBJECT'
sh.show_cavity = True; sh.cavity_type = 'WORLD'; sh.show_shadows = False; sh.show_object_outline = True
# 有屋顶的室内关投影（开着会整片压黑）；室外场景把 show_shadows 改成 True，能看出前后关系
scene.display.light_direction = (.3, -.2, .9)
w = bpy.data.worlds.new("W"); scene.world = w; w.color = (.10, .10, .11)
scene.render.image_settings.file_format = 'PNG'

def show(**kw):
    for n, on in kw.items():
        if n in GROUPS: GROUPS[n].hide_render = not on

def project_check(cam_name):
    """把这台相机必须拍到的东西（MUST）投到画面里：打印它在画面中的范围（0～1），以及是否完整在画面内。"""
    bpy.context.view_layer.update()            # 相机挪过之后必须先刷新，不然读到的是旧位置
    cam = bpy.data.objects[cam_name]; need = MUST.get(cam_name, []); bad = 0
    print(f"--- 投影检查 {cam_name}（必须有 {len(need)} 样）---")
    for n in need:
        o = bpy.data.objects.get(n)
        if not o:
            print(f"  {n}: 【场景里没有这个名字，检查 MUST 里的拼写】"); bad += 1; continue
        if o.users_collection[0].hide_render:
            print(f"  {n}: 这个角度被隐藏了"); bad += 1; continue
        ps = [world_to_camera_view(scene, cam, o.matrix_world @ Vector(c)) for c in o.bound_box]
        xs, ys, zs = [p.x for p in ps], [p.y for p in ps], [p.z for p in ps]
        if max(zs) <= 0:
            print(f"  {n}: 在相机身后，不在画面里"); bad += 1; continue
        if min(zs) <= 0:                         # 一部分在相机身后，投影数字不可信
            print(f"  {n}: 有一部分在相机身后（被画框切到）"); bad += 1; continue
        inside = min(xs) >= 0 and max(xs) <= 1 and min(ys) >= 0 and max(ys) <= 1
        visible = max(xs) > 0 and min(xs) < 1 and max(ys) > 0 and min(ys) < 1
        state = "完整在画面内" if inside else ("被画框切到" if visible else "不在画面里")
        bad += 0 if inside else 1
        print(f"  {n}: 横 {min(xs):.2f}～{max(xs):.2f}  竖 {min(ys):.2f}～{max(ys):.2f}  {state}")
    if need:
        print("  结论：" + ("必须有的都完整在画面内" if not bad else f"【有 {bad} 样没完整入画：挪相机，或者改 MUST 并在卡上写明】"))

def _small_render(path, W, Hh):
    r = scene.render; keep = (r.resolution_x, r.resolution_y, r.filepath)
    r.resolution_x, r.resolution_y, r.resolution_percentage, r.filepath = max(W // 4, 64), max(Hh // 4, 64), 100, path
    bpy.ops.render.render(write_still=True); r.resolution_x, r.resolution_y, r.filepath = keep

def wall_check(cam_name, W, Hh, expect_seen=False):
    """未定墙面检查（给派生机位用，render(..., check_walls=True) 时自动跑）：母图里看不到的墙（UNSEEN）有没有进这台相机的画面。
    做法：同一台相机渲两张小图，第二张把那些墙换个颜色，逐像素比两张图差多少。
    不靠颜色阈值判断（渲出来的颜色会被灯光压暗，按"够不够红"去数会漏）。"""
    import numpy as np
    objs = [o for g in UNSEEN if g in GROUPS for o in GROUPS[g].objects]
    if not objs:
        print(f"--- 未定墙面检查 {cam_name}：UNSEEN 是空的，跳过 ---"); return 0.0
    scene.camera = bpy.data.objects[cam_name]
    pa, pb = os.path.join(RENDERS, "_检查a.png"), os.path.join(RENDERS, "_检查b.png")
    _small_render(pa, W, Hh)
    old = [tuple(o.color) for o in objs]
    for o in objs: o.color = (1, 0, 1, 1)
    _small_render(pb, W, Hh)
    for o, c in zip(objs, old): o.color = c
    ia, ib = bpy.data.images.load(pa), bpy.data.images.load(pb)
    a = np.array(ia.pixels[:]).reshape(-1, 4)[:, :3]; b = np.array(ib.pixels[:]).reshape(-1, 4)[:, :3]
    pct = float((np.abs(a - b).max(axis=1) > .03).mean() * 100)
    bpy.data.images.remove(ia); bpy.data.images.remove(ib); os.remove(pa); os.remove(pb)
    names = "、".join(UNSEEN)
    if expect_seen:
        print(f"--- 未定墙面检查·自证 {cam_name}：这台相机正对着{names}，应当大于 0 → {pct:.2f}% "
              + ("（检查有效）" if pct > 0 else "【报的是 0，检查本身坏了，先修检查】") + " ---")
    else:
        print(f"--- 未定墙面检查 {cam_name}：{names} 占画面 {pct:.2f}% "
              + ("（没入画，合格）" if pct == 0 else "【入画了：换站位或收朝向，只转镜头躲不开就挪相机】") + " ---")
    return pct

def void_check(cam_name, W, Hh):
    """露底检查（室内用）：画面里有没有露出房间外面的空背景。把背景换个颜色再渲一张，比两张图差多少。
    室外场景的天空本来就是背景，不用这项。"""
    import numpy as np
    scene.camera = bpy.data.objects[cam_name]
    pa, pb = os.path.join(RENDERS, "_检查a.png"), os.path.join(RENDERS, "_检查b.png")
    _small_render(pa, W, Hh); old = tuple(scene.world.color); scene.world.color = (1, 0, 1)
    _small_render(pb, W, Hh); scene.world.color = old
    ia, ib = bpy.data.images.load(pa), bpy.data.images.load(pb)
    a = np.array(ia.pixels[:]).reshape(-1, 4)[:, :3]; b = np.array(ib.pixels[:]).reshape(-1, 4)[:, :3]
    pct = float((np.abs(a - b).max(axis=1) > .03).mean() * 100)
    bpy.data.images.remove(ia); bpy.data.images.remove(ib); os.remove(pa); os.remove(pb)
    print(f"--- 露底检查 {cam_name}：露到房间外面的空背景占画面 {pct:.2f}% "
          + ("（没露，合格）" if pct == 0 else "【露了：模型会在那里自己画东西。收朝向、换长一点的焦距，或者把缺口补上】") + " ---")
    return pct

def render(cam_name, tag, W, Hh, check_walls=False):
    scene.camera = bpy.data.objects[cam_name]
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = W, Hh, 100
    project_check(cam_name)
    if check_walls: wall_check(cam_name, W, Hh); void_check(cam_name, W, Hh)
    path = os.path.join(RENDERS, f"{NAME}_{tag}.png")
    scene.render.resolution_x, scene.render.resolution_y = W, Hh
    scene.render.filepath = path; bpy.ops.render.render(write_still=True)
    print("  已渲染：", path, "存在" if os.path.exists(path) else "【没找到文件，检查输出路径】")

# ================= 四、要出哪些图 =================
W16, H16 = 1920, 1080                      # 画幅和母图、成片保持一致；21:9 用 2520×1080
show(人物占位=False)
wall_check("CAM_自证_正对东墙", W16, H16, expect_seen=True)        # 先证明检查会报，再信它报的 0
show(东墙=False); render("CAM_母图_东边往西", "母图机位_拆东墙", W16, H16); show(东墙=True)
# A 站在门外：把南墙和门隐藏（活动墙），相机才退得开；这面墙在相机身后，本来也不入画
show(南墙=False, 门=False); render("CAM_A_门口往北", "A_门口往北", W16, H16, check_walls=True); show(南墙=True, 门=True)
# B 站在窗外：把北墙和窗隐藏
show(北墙=False, 窗=False); render("CAM_B_窗边往南", "B_窗边往南", W16, H16, check_walls=True); show(北墙=True, 窗=True)
render("CAM_椅子检查", "椅子检查", 1600, 900)
show(天花板=False, 灯=False, 人物占位=True)
render("CAM_俯视布局", "俯视布局", 1600, int(1600 * Y / X))
show(天花板=True, 灯=True, 人物占位=False)

scene.camera = cams["CAM_母图_东边往西"]
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, NAME + ".blend"))
print("完成。渲染图在：", RENDERS)
