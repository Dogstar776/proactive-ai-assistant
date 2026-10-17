#!/usr/bin/env python3
"""md2tex.py — 将 paper/proactive-agi-theory.md 转换为 LaTeX (ctexart) 源码。

论文以 Markdown 为唯一权威源（GitHub 直接渲染），本脚本生成投稿级 .tex。
用法: python3 md2tex.py proactive-agi-theory.md -o proactive-agi-theory.tex
依赖: Python 3.8+，无第三方库。编译: xelatex proactive-agi-theory.tex
"""
import re
import sys
import argparse

# 文本中需要替换为数学模式的 Unicode 符号（仅处理非数学校本）
UNICODE_MATH_MAP = {
    "→": r"$\to$",
    "←": r"$\leftarrow$",
    "≈": r"$\approx$",
    "≤": r"$\le$",
    "≥": r"$\ge$",
    "×": r"$\times$",
    "·": r"$\cdot$",
    "∫": r"$\int$",
    "∑": r"$\sum$",
    "π": r"$\pi$",
    "Δ": r"$\Delta$",
    "∈": r"$\in$",
    "–": "--",  # en dash
}

LATEX_SPECIAL = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "#": r"\#",
    "_": r"\_",
    "$": r"\$",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def escape_text(s: str) -> str:
    for ch, repl in UNICODE_MATH_MAP.items():
        s = s.replace(ch, repl)
    out = []
    for ch in s:
        if ch in LATEX_SPECIAL:
            out.append(LATEX_SPECIAL[ch])
        else:
            out.append(ch)
    s = "".join(out)
    # 数学校本替换后再做会破坏 $...$，所以先替换特殊字符、后加粗是安全的：
    # 加粗标记 ** 不含特殊字符。
    s = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", s)
    return s


def cell_tex(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", escape_text(s))
    return s


TABLE_SPECS = {
    "对比维度": r"{p{1.6cm} p{3.4cm} p{4.1cm} p{4.4cm}}",
    "层": r"{p{1.7cm} p{4.3cm} p{0.8cm} p{5.0cm}}",
}


def convert(md: str) -> str:
    lines = md.splitlines()
    out = []
    i = 0
    title = None
    in_refs = False
    ref_items = []

    # 第一遍：取标题
    for ln in lines:
        if ln.startswith("# ") and title is None:
            title = ln[2:].strip()
            break

    out.append(r"% !TeX program = xelatex")
    out.append(r"% 本文件由 md2tex.py 自动生成，请勿手改；请修改 Markdown 源后重新生成。")
    out.append(r"\documentclass[11pt,a4paper]{ctexart}")
    out.append(r"\usepackage{geometry}")
    out.append(r"\geometry{margin=2.5cm}")
    out.append(r"\usepackage{booktabs}")
    out.append(r"\usepackage{amsmath,amssymb}")
    out.append(r"\usepackage{graphicx}")
    out.append(r"\usepackage{hyperref}")
    out.append(r"\hypersetup{colorlinks=true,linkcolor=black,urlcolor=blue}")
    out.append(r"\setlength{\parindent}{2em}")
    out.append(r"\linespread{1.3}")
    out.append(r"\begin{document}")
    if title:
        out.append(r"\title{" + escape_text(title) + "}")
        out.append(r"\author{}")
        out.append(r"\date{\today}")
        out.append(r"\maketitle")

    def flush_list(buf, ordered):
        if not buf:
            return
        env = "enumerate" if ordered else "itemize"
        out.append(r"\begin{" + env + "}")
        for it in buf:
            out.append(r"  \item " + it)
        out.append(r"\end{" + env + "}")

    list_buf, list_ordered = [], None

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()

        # 空行 / 分隔线
        if not stripped or stripped == "---":
            flush_list(list_buf, list_ordered)
            list_buf, list_ordered = [], None
            i += 1
            continue

        # 数学校本（$$...$$ 整行）
        if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
            flush_list(list_buf, list_ordered)
            list_buf, list_ordered = [], None
            out.append(r"\[" + stripped[2:-2].strip() + r"\]")
            i += 1
            continue

        # 表格
        if stripped.startswith("|") and i + 1 < len(lines) and re.match(
            r"^\|[\s:\-|]+\|$", lines[i + 1].strip()
        ):
            flush_list(list_buf, list_ordered)
            list_buf, list_ordered = [], None
            header = [c.strip() for c in stripped.strip("|").split("|")]
            spec = TABLE_SPECS.get(header[0], r"{p{2cm} p{4cm} p{4cm} p{4cm}}")
            out.append(r"\begin{center}")
            out.append(r"\begin{tabular}{" + spec + "}")
            out.append(r"\toprule")
            out.append(" & ".join(cell_tex(c) for c in header) + r" \\")
            out.append(r"\midrule")
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                out.append(" & ".join(cell_tex(c) for c in row) + r" \\")
                i += 1
            out.append(r"\bottomrule")
            out.append(r"\end{tabular}")
            out.append(r"\end{center}")
            continue

        # 标题
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            flush_list(list_buf, list_ordered)
            list_buf, list_ordered = [], None
            level, text = len(m.group(1)), escape_text(m.group(2))
            if level == 1:
                pass  # 标题已在 preamble 处理
            elif text == "摘要":
                out.append(r"\begin{abstract}")
            elif text == "参考文献":
                in_refs = True
            elif level == 2:
                out.append(r"\section{" + text + "}")
            elif level == 3:
                out.append(r"\subsection{" + text + "}")
            else:
                out.append(r"\subsubsection{" + text + "}")
            i += 1
            continue

        # 列表
        m = re.match(r"^-\s+(.*)$", stripped)
        if m:
            if list_ordered is not False and list_buf:
                flush_list(list_buf, list_ordered)
                list_buf = []
            list_ordered = False
            list_buf.append(escape_text(m.group(1)))
            i += 1
            continue
        m = re.match(r"^\d+\.\s+(.*)$", stripped)
        if m:
            if in_refs:
                flush_list(list_buf, list_ordered)
                list_buf, list_ordered = [], None
                ref_items.append(escape_text(m.group(1)))
                i += 1
                continue
            if list_ordered is not True and list_buf:
                flush_list(list_buf, list_ordered)
                list_buf = []
            list_ordered = True
            list_buf.append(escape_text(m.group(1)))
            i += 1
            continue

        # 普通段落
        flush_list(list_buf, list_ordered)
        list_buf, list_ordered = [], None
        para = escape_text(stripped)
        if in_refs:
            ref_items.append(para)
        elif para.startswith(r"\textbf{关键词"):
            out.append(r"\par\noindent " + para)
        else:
            out.append(para)
        i += 1

    flush_list(list_buf, list_ordered)

    if ref_items:
        out.append(r"\begin{thebibliography}{99}")
        for n, it in enumerate(ref_items, 1):
            out.append(r"\bibitem{ref%d} %s" % (n, it))
        out.append(r"\end{thebibliography}")

    # 摘要块收尾：在最后一个非空输出后、参考文献前关闭 abstract 不可靠，
    # 这里用括号配对思路不可行——改为在解析时遇到下一个 section 前关闭。
    tex = "\n\n".join(out) + "\n\n\\end{document}\n"
    return fix_abstract(tex)


def fix_abstract(tex: str) -> str:
    r"""\begin{abstract} 后若遇到 \section 仍未关闭，则补 \end{abstract}。"""
    marker = r"\begin{abstract}"
    if marker not in tex:
        return tex
    head, rest = tex.split(marker, 1)
    m = re.search(r"\\section\{", rest)
    if not m:
        return tex
    body, tail = rest[: m.start()], rest[m.start():]
    return head + marker + "\n" + body.rstrip() + "\n" + r"\end{abstract}" + "\n\n" + tail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()
    with open(args.input, encoding="utf-8") as f:
        md = f.read()
    tex = convert(md)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(tex)
    print("written:", args.output)


if __name__ == "__main__":
    main()
