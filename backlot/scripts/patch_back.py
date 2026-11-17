# Backlot 片场 v1.4 · 换道具：把重画过的裁块贴回原图
# 作者：Manson AIGC · 许可 CC BY 4.0
#
# 用法见 references/prop-swap.md。流程：从原图裁出道具那一块 → 交给模型只重画道具 →
# 用本脚本把重画结果缩回裁块大小，只在"贴回区"里换上新内容（边缘羽化），贴回区外一个像素都不动。
#
#   python3 patch_back.py 原图.png 重画结果.png X0 Y0 X1 Y1 输出.png \
#       --area x0 y0 x1 y1 [--area ...] [--ellipse] [--feather 12]
#
#   X0 Y0 X1 Y1   当初裁块在原图里的位置（原图坐标）
#   --area        贴回区，原图坐标（右下角不含，和 pixel_diff.py 一样），可以给多个（一块里有两盏灯就给两个）；必须在裁块里面
#   --ellipse     贴回区按椭圆，不按矩形（灯罩、圆桌这类圆东西用）
#   --feather     羽化宽度（像素），默认 12；贴回区要比道具外扩出至少这么多
#
# 跑完会报告：贴回区外变了多少像素（应该是 0）；贴回区外圈一条环带里，重画结果和原图差多少
# （差得多说明模型把整块的颜色或位置也改了，贴回会有接缝，要先看接缝预览图）。
# 需要 Pillow：pip install pillow
import argparse
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

ap = argparse.ArgumentParser()
ap.add_argument("orig"); ap.add_argument("patch")
ap.add_argument("x0", type=int); ap.add_argument("y0", type=int)
ap.add_argument("x1", type=int); ap.add_argument("y1", type=int)
ap.add_argument("out")
ap.add_argument("--area", type=int, nargs=4, action="append", required=True)
ap.add_argument("--ellipse", action="store_true")
ap.add_argument("--feather", type=int, default=12)
a = ap.parse_args()

orig = Image.open(a.orig).convert("RGB")
box = (a.x0, a.y0, a.x1, a.y1)
cw, ch = a.x1 - a.x0, a.y1 - a.y0
patch = Image.open(a.patch).convert("RGB")
pw, ph = patch.size
if abs(pw / ph - cw / ch) > 0.02:
    print(f"注意：重画结果比例 {pw}x{ph} 和裁块 {cw}x{ch} 不一样，缩放会变形，先查模型是不是改了画幅")
patch = patch.resize((cw, ch), Image.LANCZOS)

# 贴回区蒙版（裁块坐标）
mask = Image.new("L", (cw, ch), 0)
d = ImageDraw.Draw(mask)
for x0, y0, x1, y1 in a.area:
    if not (a.x0 <= x0 < x1 <= a.x1 and a.y0 <= y0 < y1 <= a.y1):
        raise SystemExit(f"贴回区 {x0,y0,x1,y1} 不在裁块 {box} 里面")
    r = (x0 - a.x0, y0 - a.y0, x1 - a.x0 - 1, y1 - a.y0 - 1)  # 右下角不含，和裁块坐标一致
    (d.ellipse if a.ellipse else d.rectangle)(r, fill=255)
hard = mask.copy()
if a.feather > 0:
    # 先往里收再羽化，保证羽化后不超出给定的贴回区
    mask = mask.filter(ImageFilter.MinFilter(a.feather * 2 + 1 if a.feather * 2 + 1 <= 51 else 51))
    mask = mask.filter(ImageFilter.GaussianBlur(a.feather / 2))
    mask = ImageChops.multiply(mask, hard)

crop = orig.crop(box)
merged = Image.composite(patch, crop, mask)
out = orig.copy(); out.paste(merged, box[:2]); out.save(a.out)

# 自查 1：贴回区外有没有变
diff = ImageChops.difference(orig, out).convert("L").point(lambda v: 255 if v else 0)
full_hard = Image.new("L", orig.size, 0); full_hard.paste(hard, box[:2])
outside = ImageChops.multiply(diff, ImageChops.invert(full_hard))
n_out = sum(1 for v in outside.getdata() if v)
n_in = sum(1 for v in diff.getdata() if v) - n_out
print(f"贴回区里变了 {n_in} 个像素；贴回区外变了 {n_out} 个像素（应该是 0）")

# 自查 2：贴回区外圈 24 像素环带，模型结果和原图差多少（看有没有整体偏色或错位）
ring = hard.filter(ImageFilter.MaxFilter(49))
ring = ImageChops.subtract(ring, hard)
st = ImageStat.Stat(ImageChops.difference(crop, patch).convert("L"), ring)
print(f"贴回区外圈环带：重画结果和原图平均差 {st.mean[0]:.1f}（0–255；超过 8 左右多半有可见接缝，放大看预览）")

# 接缝预览：裁块范围放大 2 倍，贴回区边线描红
prev = merged.resize((cw * 2, ch * 2), Image.LANCZOS)
pd = ImageDraw.Draw(prev)
for x0, y0, x1, y1 in a.area:
    r = [(x0 - a.x0) * 2, (y0 - a.y0) * 2, (x1 - a.x0) * 2, (y1 - a.y0) * 2]
    (pd.ellipse if a.ellipse else pd.rectangle)(r, outline=(255, 0, 0), width=2)
pv = a.out.rsplit(".", 1)[0] + "_接缝预览.png"
prev.save(pv)
print(f"已存：{a.out}；接缝预览：{pv}")
