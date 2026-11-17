# Backlot 片场 v1.4 · 示例白模：雨夜老街（室外）
# 作者：Manson AIGC · 许可 CC BY 4.0（转发、修改请保留这一行署名）
#
# 用法（命令行，不开界面）：
#   blender -b --factory-startup -P build_雨夜老街_v1.py -- <输出文件夹>
# 也可以在 Blender 里新建一个空白文件，到 Scripting 面板粘贴运行：脚本会先清空这个文件里的东西再搭，
#   所以不要在有你自己作品的文件里跑。
#
# 场景：一条老城区的双车道老街，夜里下雨。数字和 examples/雨夜老街/示例说明.md 里的设定卡一致。
# 坐标：原点 = 街道中线南头的路面；X 往东（横穿街道），Y 往北（顺着街道），Z 往上；单位米。
# 和室内例子的不同：没有天花板；地面要铺得足够大，不然画面里会看到地面的边；
#   街道两头、远处的楼都要搭出体块，反打时身后才有东西。
import bpy, math, os, sys
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0]) if argv else (os.path.dirname(bpy.data.filepath)
                                              or os.path.join(os.path.expanduser("~"), "Backlot_白模输出"))
RENDERS = os.path.join(OUT, "renders"); os.makedirs(RENDERS, exist_ok=True)
NAME = "雨夜老街_白模_v1"

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

# 颜色只为在白模里读得清，生成时颜色按母图走
ROAD = (.20, .20, .22); WALK = (.32, .32, .33); WALL = (.34, .32, .30); WALL2 = (.28, .29, .31)
SHUT = (.17, .17, .18); LIT = (.85, .70, .45); SIGN = (.50, .48, .44); WIN = (.12, .13, .16)
METAL = (.35, .36, .38); LAMP = (.98, .97, .90); FAR = (.22, .23, .27); KIOSK = (.25, .38, .32)

# ================= 一、地面和街道 =================
ROAD_W, WALK_W = 7.0, 2.0                     # 双车道 7 米，两边人行道各 2 米
RX = ROAD_W / 2; SX = RX + WALK_W             # 路缘 X=±3.5，店面 X=±5.5
Y0, Y1 = -10.0, 50.0                          # 搭出来的这一段老街，南北 60 米
box("地面_远处", -300, 300, -300, 300, -.2, -.01, ROAD, "地面")     # 铺得足够大，画面里看不到地面的边
box("路面", -RX, RX, Y0 - 12, Y1 + 12, -.01, 0, ROAD, "地面")
box("西人行道", -SX, -RX, Y0, Y1, 0, .15, WALK, "地面")
box("东人行道", RX, SX, Y0, Y1, 0, .15, WALK, "地面")

# ================= 二、两侧店面（每间开间 4 米，两层楼） =================
SHOP_W, DEPTH = 4.0, 8.0
HEIGHTS = [7.0, 7.5, 6.5, 8.0, 7.0, 9.0, 7.0, 6.5, 7.5, 8.0, 7.0, 7.0, 8.5, 6.5, 7.5]   # 15 间，高低错开
LIT_E = {2, 7, 11}            # 东侧亮灯开着的店（从南往北数第 3、8、12 间），其余卷帘门拉下
LIT_W = {4, 9}                # 西侧亮灯的店（第 5、10 间）

def shop_row(side, lit):
    s = 1 if side == "东" else -1
    for i, h in enumerate(HEIGHTS if s > 0 else HEIGHTS[::-1]):
        y0, y1 = Y0 + i * SHOP_W, Y0 + (i + 1) * SHOP_W
        xa, xb = sorted([s * SX, s * (SX + DEPTH)])
        g = f"{side}侧店面"
        box(f"{side}{i+1}_楼体", xa, xb, y0, y1, 0, h, WALL if i % 2 == 0 else WALL2, g)
        f = s * SX                                         # 临街立面
        fx0, fx1 = sorted([f, f - s * .06])                # 往街道方向凸出 6 厘米
        box(f"{side}{i+1}_店门", fx0, fx1, y0 + .35, y1 - .35, .15, 2.9, LIT if i in lit else SHUT, g)
        sx0, sx1 = sorted([f, f - s * .18])
        box(f"{side}{i+1}_招牌板（空白）", sx0, sx1, y0 + .2, y1 - .2, 3.1, 3.8, SIGN, g)
        for k in range(2):                                  # 二楼两扇窗
            wy = y0 + .6 + k * 1.7
            box(f"{side}{i+1}_二楼窗{k+1}", fx0, fx1, wy, wy + 1.1, 4.4, 5.9, WIN, g)

shop_row("东", LIT_E)
shop_row("西", LIT_W)

# 街道两头：横街对面的一排楼，挡住视线尽头（反打时身后也要有东西）
box("北头_横街对面楼", -30, 30, Y1 + 7, Y1 + 15, 0, 10, WALL2, "街道两头")
box("南头_横街对面楼", -30, 30, Y0 - 15, Y0 - 7, 0, 9, WALL2, "街道两头")
# 远景：只放大体块，不做细节。比老街高很多，离得很远
FAR_BLOCKS = [(-55, 105, 16, 30), (-25, 120, 14, 42), (8, 112, 18, 26), (40, 125, 16, 38), (70, 108, 20, 24),
              (-60, -95, 18, 28), (-20, -110, 16, 36), (15, -100, 14, 30), (50, -115, 20, 40)]
for i, (cx, cy, w, h) in enumerate(FAR_BLOCKS):
    box(f"远景楼{i+1}", cx - w / 2, cx + w / 2, cy - 8, cy + 8, 0, h, FAR, "远景")

# ================= 三、固定陈设 =================
LAMP_Y = [2.0, 14.0, 26.0, 38.0]               # 路灯正好四盏，都在东侧人行道
for i, ly in enumerate(LAMP_Y):
    cyl(f"路灯{i+1}_灯杆", 4.9, ly, 0, 6.0, .08, METAL, "路灯", verts=10)
    box(f"路灯{i+1}_灯臂", 3.7, 4.9, ly - .04, ly + .04, 5.92, 6.0, METAL, "路灯")
    box(f"路灯{i+1}_灯头", 3.3, 3.9, ly - .14, ly + .14, 5.78, 5.92, LAMP, "路灯")
box("报刊亭（卷帘拉下）", -5.3, -3.9, 17.0, 19.5, .15, 2.6, KIOSK, "陈设")
box("报刊亭_顶檐", -5.45, -3.75, 16.85, 19.65, 2.6, 2.75, METAL, "陈设")

# 人物占位：只在俯视图里显示
for n, px, py in [("走在街心的人", -.6, 20.0), ("人行道上的人", -4.5, 15.0)]:
    cyl("人物_" + n, px, py, 0, 1.7, .35, (.85, .45, .6), "人物占位")

KEY = ["路灯1_灯头", "路灯2_灯头", "路灯3_灯头", "路灯4_灯头", "报刊亭（卷帘拉下）",
       "北头_横街对面楼", "南头_横街对面楼", "东3_店门", "东8_店门", "东12_店门"]

# ================= 四、相机 =================
def camera(n, loc, target, lens):
    cd = bpy.data.cameras.new(n); cd.lens = lens; cd.sensor_width = 36; cd.sensor_fit = 'HORIZONTAL'; cd.clip_end = 1000
    co = bpy.data.objects.new(n, cd); co.location = loc
    co.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    group("相机").objects.link(co); return co

CAMS = {   # 名字: (相机位置, 看向的点, 焦距 mm)
    # 母图：站在街南头、二楼高度往北看，两排店面、四盏路灯、报刊亭、远景都在画面里
    "CAM_母图_南头高处往北": ((.5, -8.0, 5.5), (0.0, 30.0, 2.0), 22),
    # A：人眼高度站在街心往北看（主角度）。站在 1 号路灯旁边，2～4 号路灯完整在画面里，
    #    不会有一盏灯头被画面上沿切掉（站到 Y=6 时 2 号灯头会出画，成图里容易变形）
    "CAM_A_街心往北":        ((-1.2, 0.0, 1.6), (.3, 45.0, 2.4), 28),
    # B：A 的反打，站在 4 号路灯旁边往南看，看到 3、2、1 号路灯，和 A 对称
    "CAM_B_街心往南":        ((1.2, 40.0, 1.6), (-.3, -5.0, 2.4), 28),
    # C：站在西侧人行道上横着往东看，看清街有多宽、对面店面和路灯
    "CAM_C_西人行道往东":    ((-4.8, 23.0, 1.75), (6.0, 21.0, 3.0), 20),
}
cams = {k: camera(k, *v) for k, v in CAMS.items()}
# 机位标记：只在俯视图里显示。三角形尖头 = 相机朝向，颜色区分机位（母图白、A 红、B 蓝、C 绿）
MARK = {"CAM_母图_南头高处往北": (.95, .95, .95), "CAM_A_街心往北": (.90, .25, .20),
        "CAM_B_街心往南": (.25, .45, .95), "CAM_C_西人行道往东": (.30, .80, .35)}
def cam_marker(n, loc, target, col, z=.4, L=2.2, W=1.0):
    d = Vector((target[0] - loc[0], target[1] - loc[1], 0)).normalized(); q = Vector((-d.y, d.x, 0))
    p0 = Vector((loc[0], loc[1], z))
    vs = [tuple(p0 + d * L), tuple(p0 + q * W / 2), tuple(p0 - q * W / 2)]
    m = bpy.data.meshes.new(n + "_mesh"); m.from_pydata(vs, [], [(0, 1, 2)]); m.update()
    o = bpy.data.objects.new(n, m); o.color = (*col, 1); group("机位标记").objects.link(o)
for k, (loc, tgt, _) in CAMS.items():
    cam_marker("标记_" + k, loc, tgt, MARK[k])
for i, ly in enumerate(LAMP_Y):                   # 俯视里灯头太小，给每盏路灯加一个黄色圆点
    cyl(f"标记_路灯{i+1}", 4.9, ly, .3, .35, .45, (.95, .85, .25), "机位标记")
top = camera("CAM_俯视布局", (0, 20, 80), (0, 20, 0), 50)
top.data.type = 'ORTHO'; top.data.ortho_scale = 46; top.rotation_euler = (0, 0, 0)
# ↑ 相机按横向取景：宽 46 米，竖图 1:2 所以高 92 米，南北两头横街对面的楼都在画内

# ================= 渲染设置 =================
scene.render.engine = 'BLENDER_WORKBENCH'
sh = scene.display.shading; sh.light = 'STUDIO'; sh.color_type = 'OBJECT'
sh.show_cavity = True; sh.cavity_type = 'WORLD'; sh.show_shadows = True; sh.show_object_outline = True
scene.display.light_direction = (.3, -.2, .9)
w = bpy.data.worlds.new("W"); scene.world = w; w.color = (.16, .18, .22)     # 夜空，白模里只是一块底色
scene.render.image_settings.file_format = 'PNG'

def show(**kw):
    for n, on in kw.items():
        if n in GROUPS: GROUPS[n].hide_render = not on

def project_check(cam_name):
    bpy.context.view_layer.update()
    cam = bpy.data.objects[cam_name]
    print(f"--- 投影检查 {cam_name} ---")
    if cam.data.type == 'PERSP':        # 地平线：远处和相机一样高的点落在画面哪里（0 = 底，1 = 顶）
        cx, cy = cam.location.x, cam.location.y
        d = (cam.matrix_world.to_quaternion() @ Vector((0, 0, -1))); d.z = 0; d.normalize()
        hp = world_to_camera_view(scene, cam, Vector((cx + d.x * 5000, cy + d.y * 5000, cam.location.z)))
        print(f"  地平线：画面竖向 {hp.y:.2f}（相机离地 {cam.location.z:.2f} 米）")
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
render("CAM_母图_南头高处往北", "母图机位_南头高处往北", W16, H16)
render("CAM_A_街心往北", "A_街心往北", W16, H16)
render("CAM_B_街心往南", "B_街心往南", W16, H16)
render("CAM_C_西人行道往东", "C_西人行道往东", W16, H16)
show(人物占位=True, 机位标记=True, 远景=False)
render("CAM_俯视布局", "俯视布局", 1000, 2000)
show(人物占位=False, 机位标记=False, 远景=True)

scene.camera = cams["CAM_母图_南头高处往北"]
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, NAME + ".blend"))
print("完成。渲染图在：", RENDERS)
