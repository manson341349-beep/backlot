# Backlot 片场 v1.4 · 反推母图机位
# 作者：Manson AIGC · 许可 CC BY 4.0
#
# 母图定版后，白模要照母图对齐。这一步最难的是反推"母图是站在哪、用多少焦距拍的"。
# 本脚本适用于"盒子房间"：母图里看得到一面远墙，和它两边的左墙、右墙（看得到其中一面也行）。
# 你在母图上量几个点的像素坐标，它算出相机位置、朝向、焦距和房间宽度，再把你点名的门窗、家具换算成米。
#
# 用法：
#   python3 solve_camera.py --example > 量点.json     先拿一份样例，照着填
#   python3 solve_camera.py 量点.json                 算
# 需要 numpy：pip install numpy
#
# 怎么量点：用任意看图软件读像素坐标（左上角是 0,0，x 往右、y 往下），按母图原始尺寸量。
# 必须给一个"已知真实尺寸"（known_sizes，比如门宽 0.9 米、双开门 1.7 米）。没有它，焦距定不住：
#   拉远相机、换长焦，墙角照样对得上（见 pitfalls.md 第 17 条）。脚本会按这个尺寸 ±10% 各算一次，报出焦距范围。
#   这个尺寸不能取在远墙上：远墙上的东西和层高是同一个比例，定不了进深。取在侧墙或地面上（窗宽、地上两件东西的间距）。
#   也别取在和相机差不多高的平面上（相机离地 1.2 米，就别用 0.8 米高的桌面）：视线贴着那个面擦过去，量偏一两个像素就差很多。
# 局限：母图是模型画的，透视不严格，残差有几十个像素是常事；算出来的只是初值，
#   搭好白模后一定在母图机位做描边叠图，再手调一两轮。
import json, math, sys
import numpy as np

EXAMPLE = {
    "说明": "像素坐标按母图原始尺寸量。points 里量得到几个填几个，至少三个墙角；known_sizes 至少一条。",
    "image": [2816, 1584],
    "height": 3.0,
    "far_wall": "east",
    "behind": 1.0,
    "points": {
        "far_left_top": [504, 406],
        "far_right_top": [1264, 410],
        "far_left_bottom": [504, 945],
        "left_top_line": [90, 0],
        "right_top_line": [2816, 90]
    },
    "known_sizes": [
        {"name": "双开门的宽", "on": "right_wall", "a": [1630, 520], "b": [1950, 520], "meters": 1.7}
    ],
    "locate": [
        {"name": "门左边框", "pixel": [1630, 520], "on": "right_wall"},
        {"name": "吊柜下沿", "pixel": [900, 595], "on": "far_wall"},
        {"name": "货架顶·远端", "pixel": [800, 775], "on": {"height": 1.45}},
        {"name": "第 1 排灯左端", "pixel": [440, 36], "on": "ceiling"}
    ],
    "字段": {
        "height": "层高（米）。不知道就按同类建筑的常见值填，别的尺寸都跟着它成比例",
        "far_wall": "母图里正对面那面远墙是哪面墙：east / west / north / south。只影响最后换算成场景坐标",
        "behind": "相机身后那面墙离相机多远（米）。母图里看不到，是假设，写进设定卡",
        "points": "far_left_top = 远墙和左墙、天花板交的那个角；far_right_top、far_left_bottom、far_right_bottom 同理；"
                  "left_top_line = 左墙顶线（左墙和天花板的交线）上任意一点，通常取它出画的地方；"
                  "right_top_line、left_bottom_line、right_bottom_line 同理",
        "known_sizes.on / locate.on": "这个点在哪个面上：left_wall / right_wall / far_wall / floor / ceiling，或 {\"height\": 离地几米}。known_sizes 至少有一条不在 far_wall 上"
    }
}

def basis(yaw, pitch):
    """相机自己的坐标：d 往远墙，l 往右，z 往上。yaw 往右转为正，pitch 往下为正。"""
    F = np.array([math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), -math.sin(pitch)])
    R = np.array([-math.sin(yaw), math.cos(yaw), 0.0]); U = np.cross(F, R)
    return F, R, U

class Model:
    def __init__(self, cfg):
        self.W, self.Hh = cfg["image"]; self.H = float(cfg["height"]); self.cfg = cfg
    def unpack(self, p):
        return dict(D=math.exp(p[0]), cz=math.exp(p[1]), f=math.exp(p[2]), Lw=p[3], Rw=p[4], yaw=p[5], pitch=p[6])
    def proj(self, q, P):
        F, R, U = basis(q["yaw"], q["pitch"]); d = np.array(P, float) - np.array([0, 0, q["cz"]]); z = d @ F
        z = z if abs(z) > 1e-6 else 1e-6
        return np.array([self.W / 2 + q["f"] * (d @ R) / z, self.Hh / 2 - q["f"] * (d @ U) / z])
    def ray(self, q, u, v, on):
        F, R, U = basis(q["yaw"], q["pitch"]); C = np.array([0, 0, q["cz"]])
        d = F * q["f"] + R * (u - self.W / 2) - U * (v - self.Hh / 2)
        if isinstance(on, dict): axis, val = 2, float(on["height"])
        else: axis, val = {"left_wall": (1, -q["Lw"]), "right_wall": (1, q["Rw"]), "far_wall": (0, q["D"]),
                           "floor": (2, 0.0), "ceiling": (2, self.H)}[on]
        t = (val - C[axis]) / (d[axis] if abs(d[axis]) > 1e-9 else 1e-9)
        return C + t * d
    def corner(self, q, name):
        side, lvl = name.split("_")[1], name.split("_")[2]
        return (q["D"], -q["Lw"] if side == "left" else q["Rw"], self.H if lvl == "top" else 0.0)
    def residual(self, p):
        q = self.unpack(p); r = []; pts = self.cfg.get("points", {})
        for name, uv in pts.items():
            if name.startswith("far_"):
                r += list(self.proj(q, self.corner(q, name)) - np.array(uv, float))
            elif name.endswith("_line"):                      # 点到投影直线的距离
                side, lvl = name.split("_")[0], name.split("_")[1]
                l = -q["Lw"] if side == "left" else q["Rw"]; z = self.H if lvl == "top" else 0.0
                a, b = self.proj(q, (q["D"], l, z)), self.proj(q, (q["D"] * .4, l, z))
                n = np.array([-(b - a)[1], (b - a)[0]]); n = n / (np.linalg.norm(n) + 1e-9)
                r.append(float((np.array(uv, float) - a) @ n))
        for k in self.cfg.get("known_sizes", []):
            a, b = self.ray(q, *k["a"], k["on"]), self.ray(q, *k["b"], k["on"])
            r.append((np.linalg.norm(a - b) - self.scale * k["meters"]) * 300.0)
        return np.array(r, float)
    scale = 1.0

def lm(fun, p, iters=300):
    lam = 1e-2; r = fun(p); c = r @ r
    for _ in range(iters):
        J = np.zeros((len(r), len(p)))
        for i in range(len(p)):
            dp = np.zeros(len(p)); dp[i] = 1e-6 * max(1.0, abs(p[i])); J[:, i] = (fun(p + dp) - r) / dp[i]
        A, g = J.T @ J, J.T @ r; step = None
        while lam < 1e12:
            try: s = np.linalg.solve(A + lam * (np.diag(np.diag(A)) + 1e-9 * np.eye(len(p))), -g)
            except np.linalg.LinAlgError: lam *= 10; continue
            r2 = fun(p + s); c2 = r2 @ r2
            if np.isfinite(c2) and c2 < c: p, r, c, step = p + s, r2, c2, s; lam = max(lam / 3, 1e-9); break
            lam *= 4
        if step is None or np.linalg.norm(step) < 1e-10: break
    return p, r

def solve(m):
    best = None; pts = m.cfg.get("points", {})
    us = [uv[0] for n, uv in pts.items() if n.startswith("far_")]
    for f0 in (.45, .6, .8, 1.1):
        for D0 in (3.0, 6.0, 10.0, 16.0):
            f = f0 * m.W; yaw0 = math.atan((m.W / 2 - (sum(us) / len(us) if us else m.W / 2)) / f)
            p0 = np.array([math.log(D0), math.log(1.6), math.log(f), 2.0, 2.0, yaw0, .08])
            try: p, r = lm(m.residual, p0)
            except Exception: continue
            q = m.unpack(p)
            if q["Lw"] + q["Rw"] <= 0.3: continue           # 左右墙挤在一起，不是真解
            if best is None or r @ r < best[1] @ best[1]: best = (p, r)
    return best

def to_scene(cfg, q, P):
    """相机坐标 (d, l, z) → 场景坐标（原点 = 西南墙角地面，X 往东，Y 往北）。"""
    d, l, z = P; b = float(cfg.get("behind", 1.0)); far = cfg.get("far_wall", "east")
    if far == "east":  return (b + d, q["Rw"] - l, z)
    if far == "west":  return (q["D"] - d, q["Lw"] + l, z)
    if far == "north": return (q["Lw"] + l, b + d, z)
    if far == "south": return (q["Rw"] - l, q["D"] - d, z)
    raise SystemExit("far_wall 只能是 east / west / north / south")

def main():
    if len(sys.argv) < 2: sys.exit("用法：python3 solve_camera.py 量点.json    （样例：python3 solve_camera.py --example）")
    if sys.argv[1] == "--example": print(json.dumps(EXAMPLE, ensure_ascii=False, indent=2)); return
    cfg = json.load(open(sys.argv[1], encoding="utf-8")); m = Model(cfg)
    n_corner = sum(1 for n in cfg.get("points", {}) if n.startswith("far_"))
    if n_corner < 3: sys.exit("至少要量三个远墙的墙角（far_left_top / far_right_top / far_left_bottom / far_right_bottom）")
    if not cfg.get("known_sizes"):
        sys.exit("没有 known_sizes：只靠墙角定不住焦距（pitfalls.md 第 17 条）。量一样真实尺寸已知的东西，比如门宽。")
    if all(k.get("on") == "far_wall" for k in cfg["known_sizes"]):
        sys.exit("known_sizes 全都取在远墙上：远墙上的尺寸和层高是同一个比例，定不了进深。换一样在侧墙或地面上的（窗宽、地上两件东西的间距）。")
    best = solve(m)
    if best is None: sys.exit("没算出来：检查量的点是不是填错了角（左右、上下）")
    p, r = best; q = m.unpack(p); mm = lambda f: f / m.W * 36
    print("=== 残差（像素；几十个像素以内算正常，母图的透视本来就不严格）===")
    i = 0
    for name in cfg.get("points", {}):
        if name.startswith("far_"): print(f"  {name}: 横 {r[i]:+.0f}  竖 {r[i+1]:+.0f}"); i += 2
        else: print(f"  {name}: 离线 {r[i]:+.0f}"); i += 1
    for k in cfg["known_sizes"]: print(f"  {k.get('name', '已知尺寸')}: 差 {r[i] / 300:+.2f} 米"); i += 1
    print("=== 相机和房间（相机自己的坐标）===")
    print(f"  相机离远墙 {q['D']:.2f} 米，离左墙 {q['Lw']:.2f} 米，离右墙 {q['Rw']:.2f} 米，离地 {q['cz']:.2f} 米")
    print(f"  房间宽（左墙到右墙）{q['Lw'] + q['Rw']:.2f} 米；层高按 {m.H} 米")
    print(f"  朝向：比正对远墙往{'右' if q['yaw'] > 0 else '左'}偏 {abs(math.degrees(q['yaw'])):.1f}°，"
          f"往{'下' if q['pitch'] > 0 else '上'}俯仰 {abs(math.degrees(q['pitch'])):.1f}°")
    print(f"  焦距 {mm(q['f']):.1f} 毫米（按 36 毫米宽的画幅）")
    rng = []
    for s in (.9, 1.1):                                        # 已知尺寸 ±10%，看焦距跟着变多少
        m.scale = s; b2 = solve(m)
        if b2: rng.append(mm(m.unpack(b2[0])["f"]))
    m.scale = 1.0
    if len(rng) == 2:
        print(f"  已知尺寸差 ±10% 时，焦距在 {min(rng):.1f}～{max(rng):.1f} 毫米之间都对得上。把这个范围写进设定卡。")
    F, R, U = basis(q["yaw"], q["pitch"]); C = np.array([0, 0, q["cz"]])
    loc = to_scene(cfg, q, C); tgt = to_scene(cfg, q, C + F * 5)
    b = float(cfg.get("behind", 1.0)); far = cfg.get("far_wall", "east")
    length, width = q["D"] + b, q["Lw"] + q["Rw"]
    print(f"=== 换算成场景坐标（原点 = 西南墙角地面；远墙 = {far} 墙；相机身后的墙按 {b} 米假设）===")
    print(f"  房间：东西 {length if far in ('east', 'west') else width:.2f} 米，南北 {width if far in ('east', 'west') else length:.2f} 米")
    print(f"  白模脚本里这样写：\"CAM_母图\": (({loc[0]:.2f}, {loc[1]:.2f}, {loc[2]:.2f}), ({tgt[0]:.2f}, {tgt[1]:.2f}, {tgt[2]:.2f}), {mm(q['f']):.1f}),")
    if cfg.get("locate"):
        print("=== 点名的位置（场景坐标，米）===")
        for k in cfg["locate"]:
            P = to_scene(cfg, q, m.ray(q, *k["pixel"], k["on"]))
            print(f"  {k['name']}: X={P[0]:.2f}  Y={P[1]:.2f}  Z={P[2]:.2f}")

if __name__ == "__main__":
    main()
