# Backlot 片场 v1.4 · 生成单文件版
# 作者：Manson AIGC · 许可 CC BY 4.0
#
# 把 SKILL.md、references/ 里的说明、examples/ 里三个示例的说明和 scripts/ 里的脚本拼成一份 Markdown，
# 给豆包、扣子、ChatGPT 这些不能装技能文件夹的平台用。改了任何文件之后重跑一次，保持同步。
# 用法：python3 scripts/build_single_file.py   （在技能包根目录或任意位置运行都行）
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = "v1.4"
SIGN = "Backlot 片场 · Manson AIGC · CC BY 4.0（https://creativecommons.org/licenses/by/4.0/deed.zh-hans）"
OUT = os.path.join(ROOT, f"Backlot片场_{VERSION}_单文件版.md")

REFS = ["scene-card.md", "mother-image.md", "blender-whitebox.md", "derive-prompt.md",
        "qa-and-repair.md", "prop-swap.md", "model-notes.md", "pitfalls.md"]
SCRIPTS = ["whitebox_template.py", "solve_camera.py", "overlay.py", "pixel_diff.py", "patch_back.py"]
EXAMPLES = ["老办公室", "雨夜老街", "两层仓库"]   # 只收示例说明；示例的白模脚本和渲染图只在文件夹版里

def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()

def body(md):
    md = re.sub(r"^---\n.*?\n---\n", "", md, flags=re.S)            # 去掉 SKILL.md 的头信息
    md = re.sub(r"^> Backlot 片场 v[\d.]+ · .*\n\n?", "", md, flags=re.M)  # 去掉每份说明重复的署名行
    md = re.sub(r"\n---\n\nBacklot 片场 v[\d.]+ · [^\n]*\s*$", "", md)     # 去掉示例说明末尾重复的署名
    return md.strip()

def demote(md):
    """说明文件里的标题整体降一级，放进单文件版不和主文件抢层级；代码块（模板）里的内容不动。"""
    out, fence = [], False
    for line in md.split("\n"):
        if line.startswith("```"):
            fence = not fence
        elif not fence and re.match(r"#{1,5} ", line):
            line = "#" + line
        out.append(line)
    return "\n".join(out)

parts = [f"> {SIGN}",
         "> 单文件版：把这整份内容贴给你的智能体（或作为文件 / 知识库上传），说\"按这份技能帮我搭场景\"。",
         "> 文中提到 `references/xxx.md` 的，就是本文后面附录里同名的那一节；提到 `scripts/xxx.py` 的，在最后的附录脚本里。",
         "", body(read("SKILL.md")), "", "---", "", "# 附录：细节说明", ""]
for r in REFS:
    parts += [f"<!-- references/{r} -->", demote(body(read("references", r))), "", "---", ""]
parts += ["# 附录：示例", "",
          "三个示例的说明。示例里提到的白模脚本（build_雨夜老街_v1.py、build_两层仓库_v1.py）和白模渲染图只在文件夹版的 examples/ 里；单文件版里没有图，按说明里的数字也能自己搭。", ""]
for e in EXAMPLES:
    parts += [f"<!-- examples/{e}/示例说明.md -->", demote(body(read("examples", e, "示例说明.md"))), "", "---", ""]
parts += ["# 附录：脚本", "",
          "能跑 Python 的智能体或用户，把下面的代码存成同名文件再运行。"]
for s in SCRIPTS:
    parts += ["", f"## scripts/{s}", "", "```python", read("scripts", s).rstrip(), "```"]
parts += ["", "---", f"{SIGN}", ""]

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(parts))
print("已生成：", OUT, f"（{os.path.getsize(OUT)} 字节）")
