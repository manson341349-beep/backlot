# Backlot 片场 v1.4.1 · 像素对比
# 作者：Manson AIGC · 许可 CC BY 4.0
#
# 两个用处：
#   1. 局部修图后，确认圈外一个像素都没变：python3 pixel_diff.py 原图.png 修过.png [x0 y0 x1 y1]
#      给了圈选框，就分别报告框内、框外变了多少像素；框外应该是 0。
#   2. 判断两张渲染图是不是真的一样（md5 不能用，见 qa-and-repair.md）：python3 pixel_diff.py A.png B.png
# 需要 Pillow：pip install pillow
import sys
from PIL import Image, ImageChops

if len(sys.argv) not in (3, 7):
    sys.exit("用法：python3 pixel_diff.py <图A> <图B> [x0 y0 x1 y1]")
a = Image.open(sys.argv[1]).convert("RGB")
b = Image.open(sys.argv[2]).convert("RGB")
if a.size != b.size:
    sys.exit(f"两张图尺寸不同：{a.size} 和 {b.size}，不能逐像素比")
diff = ImageChops.difference(a, b).convert("L").point(lambda v: 255 if v else 0)
total = sum(1 for v in diff.getdata() if v)
print(f"一共 {total} 个像素不同；不同的区域：{diff.getbbox() or '无'}")
if len(sys.argv) == 7:
    x0, y0, x1, y1 = map(int, sys.argv[3:7])
    inside = sum(1 for v in diff.crop((x0, y0, x1, y1)).getdata() if v)
    print(f"圈选框内变了 {inside} 个像素，框外变了 {total - inside} 个像素", "（框外没动，合格）" if total == inside else "（框外有改动，不合格）")
