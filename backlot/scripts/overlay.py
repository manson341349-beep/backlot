# Backlot 片场 v1.4.1 · 叠图检查
# 作者：Manson AIGC · 许可 CC BY 4.0
#
# 把成图和白模渲染图叠在一起，看布局对不对得上：
#   母图 vs 母图机位的白模渲染图（对位），或 派生成图 vs 这个角度的白模渲染图（自检）。
# 两种叠法：
#   默认：50% 半透明叠图，看整体偏没偏。
#   --edge：描边叠图，把图B（白模渲染图）的边线描成红线压在图A上。判断结构（门在哪面墙、
#           墙有没有转折）和量偏差用这个，半透明叠图线条混在一起容易看错（见 pitfalls.md 第 19 条）。
# 用法：python3 overlay.py <图A 成图> <图B 白模渲染图> <输出.png> [图A提亮倍数，默认 1.0] [--edge]
#   夜景、暗场景的成图可以把提亮倍数设成 2～2.5，暗处的墙角门框才看得清。
# 需要 Pillow：pip install pillow
import sys
from PIL import Image, ImageEnhance, ImageFilter

args = [x for x in sys.argv[1:] if x != "--edge"]
edge = "--edge" in sys.argv[1:]
if len(args) < 3:
    sys.exit("用法：python3 overlay.py <图A> <图B> <输出.png> [图A提亮倍数] [--edge]")
a = Image.open(args[0]).convert("RGB")
k = float(args[3]) if len(args) > 3 else 1.0
if k != 1.0:
    a = ImageEnhance.Brightness(a).enhance(k)
if edge:
    b = Image.open(args[1]).convert("L").resize(a.size, Image.LANCZOS)
    lines = b.filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v > 10 else 0)
    lines = lines.filter(ImageFilter.MaxFilter(3))          # 线加粗到约 3 像素，缩小看也看得见
    out = Image.composite(Image.new("RGB", a.size, (255, 40, 40)), a, lines)
else:
    b = Image.open(args[1]).convert("RGB").resize(a.size)
    out = Image.blend(a, b, 0.5)
out.save(args[2])
print("已保存：", args[2])
