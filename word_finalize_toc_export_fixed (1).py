# -*- coding: utf-8 -*-
"""
Word 一键定稿脚本（更稳版）
- 打开 docx
- 更新所有域（尤其是 TOC）
- 将 TOC 域“冻结”为普通文本（避免后续 Update 覆盖你的规范点线）
- 把每条目录行改成：标题 + 可选中字符“…”若干 + [Tab] + 页码
  （页码右对齐；“…”是实际字符，可逐个选中，不是 Word 的 leader 点）
- 按规范设置字体字号（TOC 1: 黑体四号；TOC 2/3: 宋体小四；颜色黑；无下划线）
- 导出 PDF（Word 引擎）
"""

import sys
import time
from pathlib import Path

import win32com.client as win32

# Word 常量（用数字避免 constants 生成失败）
WD_EXPORT_FORMAT_PDF = 17          # wdExportFormatPDF
WD_STAT_LINES = 1                  # wdStatisticLines
WD_LINE_SPACE_1PT5 = 1             # wdLineSpace1pt5
WD_TAB_ALIGN_RIGHT = 2             # wdAlignTabRight
WD_COLOR_AUTOMATIC = 0             # wdColorAutomatic
WD_FIELD_TOC = 13                  # wdFieldTOC


def _ensure_real_fkey_hint():
    # 只是提示：无须在脚本里按 F9
    pass


def _get_toc_field(doc):
    """返回第一个 TOC Field（比 TablesOfContents 对象更不容易被 Word 更新时删除）。"""
    for f in doc.Fields:
        try:
            if int(f.Type) == WD_FIELD_TOC:
                return f
        except Exception:
            continue
    return None


def _set_font_range(rng, east_asia: str, ascii_font: str, size_pt: float, bold: bool):
    # 注意：Range.Font 的属性名在不同语言 Word 都一致
    rng.Font.NameFarEast = east_asia
    rng.Font.NameAscii = ascii_font
    rng.Font.NameOther = ascii_font
    rng.Font.Name = ascii_font
    rng.Font.Size = size_pt
    rng.Font.Bold = -1 if bold else 0
    rng.Font.Color = WD_COLOR_AUTOMATIC
    rng.Font.Underline = 0


def _para_text_no_mark(para):
    """取段落文本（去掉段落标记 \r）。"""
    t = para.Range.Text
    if t.endswith("\r"):
        t = t[:-1]
    return t


def _set_right_tabstop(para, usable_width_points: float):
    """给段落加一个“右对齐 TabStop”，位置在正文右边界。"""
    ts = para.TabStops
    ts.ClearAll()
    # Position 是“从左边距开始”的距离（points）
    ts.Add(Position=usable_width_points, Alignment=WD_TAB_ALIGN_RIGHT)


def _fits_single_line(para, candidate_text: str) -> bool:
    """把候选文本写入段落，判断是否仍为 1 行。"""
    rng = para.Range.Duplicate
    rng.End -= 1  # 不覆盖段落标记
    rng.Text = candidate_text
    # 让 Word 有时间重排（否则 ComputeStatistics 偶尔拿到旧值）
    para.Range.Document.Repaginate()
    lines = int(para.Range.ComputeStatistics(WD_STAT_LINES))
    return lines <= 1


def _max_dots_for_para(para, title: str, page: str, base_dots: str = "…") -> int:
    """
    找到不换行时 “…” 的最大数量。
    用指数扩展 + 二分，兼顾速度和稳定性。
    """
    # 小标题可能为空，直接返回 0
    title = title.strip()
    page = page.strip()
    if not title or not page:
        return 0

    # 先确保有一个右对齐 TabStop
    doc = para.Range.Document
    usable = float(doc.PageSetup.PageWidth - doc.PageSetup.LeftMargin - doc.PageSetup.RightMargin)
    _set_right_tabstop(para, usable)

    def cand(n: int) -> str:
        return f"{title}{base_dots * n}\t{page}"

    lo, hi = 0, 16
    # 指数扩展找上界
    while True:
        try:
            if _fits_single_line(para, cand(hi)):
                lo = hi
                hi *= 2
                if hi > 4096:
                    break
            else:
                break
        except Exception:
            # 出现 COM 抖动时，直接停止扩展
            break

    # 二分
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        try:
            if _fits_single_line(para, cand(mid)):
                lo = mid
            else:
                hi = mid
        except Exception:
            hi = mid
    return lo


def _rewrite_toc_range(doc, toc_range):
    """
    把 TOC 结果区里的每条目录行改成规范格式：
    - 保留段落结构
    - 目录 1：黑体四号（14pt）
    - 目录 2/3：宋体小四（12pt）
    - 使用 '…' 实际字符 + 右对齐 TabStop + 页码
    """
    # 目录结果里通常包含很多段落；我们逐段处理
    paras = list(toc_range.Paragraphs)
    for para in paras:
        txt = _para_text_no_mark(para).strip()
        if not txt:
            continue

        # 目录标题“目 录”一般不含 tab，不处理
        if "\t" not in txt:
            continue

        parts = txt.split("\t")
        # 取最后一段为页码，中间可能有多个 tab
        page = parts[-1].strip()
        title = "".join(parts[:-1]).strip()

        # 判定目录级别：优先根据样式名（中文 Word 常见“目录 1/2/3”，英文为“TOC 1/2/3”）
        style_name = ""
        try:
            style_name = str(para.Range.Style.NameLocal)
        except Exception:
            try:
                style_name = str(para.Range.Style.Name)
            except Exception:
                style_name = ""

        level = None
        for k in (1, 2, 3):
            if f"{k}" in style_name and ("TOC" in style_name.upper() or "目录" in style_name):
                level = k
                break
        if level is None:
            # 兜底：根据标题是否像“第一章/第X章”判为 1 级
            if title.startswith("第") and "章" in title[:6]:
                level = 1
            else:
                level = 2

        # 生成候选文本（先把段落清空，再写回）
        # 注意：为了二分测试，我们会多次写入，所以先把段落范围拿出来
        # 先重置为最小文本，避免旧 tabstop/格式影响
        rng0 = para.Range.Duplicate
        rng0.End -= 1
        rng0.Text = f"{title}\t{page}"
        doc.Repaginate()

        # 计算“…”个数
        dots_n = _max_dots_for_para(para, title, page, base_dots="…")
        final_text = f"{title}{'…' * dots_n}\t{page}"

        # 写回最终文本
        rng = para.Range.Duplicate
        rng.End -= 1
        rng.Text = final_text

        # 段落格式：1.5 倍行距（其他缩进你如果要严格对齐模板，再告诉我具体数值）
        try:
            para.Format.LineSpacingRule = WD_LINE_SPACE_1PT5
        except Exception:
            pass

        # 字体字号
        if level == 1:
            _set_font_range(para.Range, east_asia="黑体", ascii_font="Times New Roman", size_pt=14, bold=False)
        else:
            _set_font_range(para.Range, east_asia="宋体", ascii_font="Times New Roman", size_pt=12, bold=False)


def finalize(docx_path: Path, out_docx: Path | None = None, out_pdf: Path | None = None):
    docx_path = docx_path.resolve()
    if out_docx is None:
        out_docx = docx_path.with_name(docx_path.stem + "_FINAL.docx")
    else:
        out_docx = out_docx.resolve()
    if out_pdf is None:
        out_pdf = out_docx.with_suffix(".pdf")
    else:
        out_pdf = out_pdf.resolve()

    if not docx_path.exists():
        raise FileNotFoundError(f"docx not found: {docx_path}")

    word = win32.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0

    doc = None
    try:
        # 如果你电脑上 Word 有“受保护视图”弹窗，建议先手动打开一次并点“启用编辑”
        doc = word.Documents.Open(str(docx_path), ReadOnly=False, AddToRecentFiles=False)

        # 更新域 + 分页
        doc.Repaginate()
        doc.Fields.Update()

        # 重新抓 TOC field（避免旧对象被 Word 更新时删掉）
        toc_field = _get_toc_field(doc)
        if toc_field is None:
            raise RuntimeError("在该文档中没有找到 TOC 域（目录字段）。请确认 docx 里确实插入了 TOC。")

        # 确保 TOC 自己也更新
        try:
            toc_field.Update()
        except Exception:
            pass

        doc.Repaginate()
        time.sleep(0.1)

        # 用书签锁定 TOC 结果范围（避免 Field/TOC 对象失效）
        toc_result = toc_field.Result.Duplicate
        bm = "__TOC_RESULT__"
        # 如果书签已存在，先删
        try:
            if doc.Bookmarks.Exists(bm):
                doc.Bookmarks(bm).Delete()
        except Exception:
            pass
        doc.Bookmarks.Add(bm, toc_result)

        # 冻结目录：Unlink 后它就变成普通文本（之后不会再被 Update 覆盖）
        toc_field.Unlink()

        # 取回 TOC 范围
        toc_range = doc.Bookmarks(bm).Range

        # 改目录为规范“可选中…点”
        _rewrite_toc_range(doc, toc_range)

        # 保存定稿 docx
        doc.SaveAs2(str(out_docx))

        # 导出 PDF
        doc.ExportAsFixedFormat(
            OutputFileName=str(out_pdf),
            ExportFormat=WD_EXPORT_FORMAT_PDF,
            OpenAfterExport=False,
            OptimizeFor=0,   # 0=Print
            Range=0,         # 0=All
            Item=0,          # 0=DocumentContent
            IncludeDocProps=True,
            KeepIRM=True,
            CreateBookmarks=1,  # 1=Headings
            DocStructureTags=True,
            BitmapMissingFonts=True,
            UseISO19005_1=False,
        )

        print(f"[OK] FINAL DOCX: {out_docx}")
        print(f"[OK] FINAL PDF : {out_pdf}")

    finally:
        if doc is not None:
            # 1 表示保存更改；0 不保存
            try:
                doc.Close(SaveChanges=0)
            except Exception:
                pass
        try:
            word.Quit()
        except Exception:
            pass


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python word_finalize_toc_export_fixed.py <path_to_docx> [out_docx] [out_pdf]")
        raise SystemExit(1)

    docx = Path(sys.argv[1])
    out_docx = Path(sys.argv[2]) if len(sys.argv) >= 3 else None
    out_pdf = Path(sys.argv[3]) if len(sys.argv) >= 4 else None
    finalize(docx, out_docx, out_pdf)
