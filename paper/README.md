# paper/ — 理论论文资产

本目录存放项目的理论基石：《主动式AGI的理论框架与落地约束：概念界定、持续认知闭环架构与开放研究问题》。

## 文件

| 文件 | 说明 |
|---|---|
| `proactive-agi-theory.md` | **权威源**。全文 Markdown，GitHub 直接渲染阅读 |
| `proactive-agi-theory.tex` | 投稿级 LaTeX 源码，由 `md2tex.py` 从 Markdown 生成 |
| `md2tex.py` | Markdown → LaTeX 转换器（Python 3.8+，无第三方依赖） |

## 编译 PDF

方式一（推荐，无需本地环境）：将 `proactive-agi-theory.tex` 导入 [Overleaf](https://www.overleaf.com)，编译器选择 **XeLaTeX**（ctex 宏包需要）。

方式二（本地）：

```bash
# 需要 TeX Live / MiKTeX，含 ctex、booktabs、amsmath、hyperref 宏包
xelatex proactive-agi-theory.tex
xelatex proactive-agi-theory.tex   # 第二遍解决交叉引用
```

## 修改论文的流程

Markdown 是唯一权威源，**不要手改 .tex**：

```bash
# 1. 编辑 proactive-agi-theory.md
# 2. 重新生成 tex
python3 md2tex.py proactive-agi-theory.md -o proactive-agi-theory.tex
```

转换器约定：`#` 一级标题=论文标题；`##`=章；`###`=节；`####`=小节；`$$...$$`=显示公式；GFM 表格=LaTeX 表格；编号列表在"参考文献"章内自动转为 `thebibliography`。

## 引用

```bibtex
@article{wu2026proactive,
  title   = {主动式AGI的理论框架与落地约束：概念界定、持续认知闭环架构与开放研究问题},
  author  = {吴子健},
  year    = {2026},
  note    = {开源项目 proactive-ai-assistant 随附论文},
  url     = {https://github.com/Dogstar776/proactive-ai-assistant}
}
```

## 版权

论文内容采用 CC BY 4.0（署名即可使用、修改、商用，欢迎批评与引用）。
