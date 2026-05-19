# -*- coding: utf-8 -*-
"""
Windows-only (Microsoft Word required):
1) Open docx
2) Repaginate + Update fields (TOC page numbers become correct)
3) Unlink TOC fields (freeze as plain text)
4) Rebuild each TOC entry as: <title><ellipsis chars><page>
   - Level1 title: 黑体 四号(14pt)
   - Level2/3: 宋体 小四(12pt)
   - Ellipsis & page number: 宋体 小四(12pt)
   - Ellipsis are real selectable characters: '…' (U+2026)
5) Save *_FINAL.docx and export *_FINAL.pdf using Word engine
"""

from __future__ import annotations

import sys
from pathlib import Path

import win32com.client as win32

# Word constants
WD_EXPORT_FORMAT_PDF = 17
WD_DO_NOT_SAVE_CHANGES = 0
WD_STATISTIC_LINES = 1  # wdStatisticLines


ELL = "…"


def _norm_title_for_toc_display(title: str) -> str:
    """School appendix: TOC shows 摘要 / ABSTRACT even if headings are 摘  要 / Abstract."""
    t = "".join(title.split())  # remove spaces
    if t in ("摘要", "摘要。", "摘 要", "摘要:", "摘要：", "摘要；", "摘要;") or t == "摘要":
        return "摘要"
    if t.lower() == "abstract":
        return "ABSTRACT"
    # Many theses use '摘 要' in body; treat it as 摘要 in TOC
    if t in ("摘要", "摘要", "摘要"):
        return "摘要"
    return title.strip()


def _set_range_font(rng, *, name: str, size_pt: float, bold=None, color_rgb=0):
    # color_rgb is int 0x00bbggrr? Word uses BGR; we'll just use 0 (black)
    rng.Font.Name = name
    rng.Font.Size = size_pt
    if bold is not None:
        rng.Font.Bold = bold
    rng.Font.Color = color_rgb
    rng.Font.Underline = 0


def _para_level_from_style(para) -> int:
    """Try to infer level from Word TOC styles."""
    try:
        s = para.Style.NameLocal
    except Exception:
        return 1
    # common: "TOC 1", "TOC 2", "TOC 3"
    for lvl in (1, 2, 3):
        if str(lvl) in s and "TOC" in s.upper():
            return lvl
    return 1


def _set_para_indent(para, level: int):
    fmt = para.Format
    fmt.SpaceBefore = 0
    fmt.SpaceAfter = 0
    fmt.LineSpacingRule = 0  # wdLineSpaceSingle? We'll use Multiple via LineSpacing
    # Word: for multiple line spacing, set LineSpacingRule=5 (wdLineSpaceMultiple) and LineSpacing=?? in points*20
    # Simpler: use 1.5 by setting LineSpacingRule=5 and LineSpacing=18? not stable. We'll use "Multiple" 1.5.
    try:
        fmt.LineSpacingRule = 5  # wdLineSpaceMultiple
        fmt.LineSpacing = 18  # 1.5 * 12pt = 18pt, Word stores in points
    except Exception:
        pass

    # From appendix sample:
    # L1: no indent
    # L2: first-line indent 18pt
    # L3: left indent 15.45pt + first-line indent 24pt
    if level == 1:
        fmt.LeftIndent = 0
        fmt.FirstLineIndent = 0
    elif level == 2:
        fmt.LeftIndent = 0
        fmt.FirstLineIndent = 18
    else:
        fmt.LeftIndent = 15.45
        fmt.FirstLineIndent = 24


def _build_line_no_wrap(doc, para, title: str, page: str, level: int) -> tuple[str, int]:
    """
    Find the maximum count of ELL that keeps the paragraph on a single line.
    Approach: exponential search to find upper bound that wraps, then binary search.
    """
    # Base text (no leader)
    base = f"{title}"
    page = page.strip()
    # minimal leader
    lo = 0
    hi = 32
    def set_text(cnt: int):
        para.Range.Text = f"{base}{ELL * cnt}{page}\r"
        _set_para_indent(para, level)

    set_text(hi)
    lines = para.Range.ComputeStatistics(WD_STATISTIC_LINES)
    while lines <= 1 and hi < 4096:
        lo = hi
        hi *= 2
        set_text(hi)
        lines = para.Range.ComputeStatistics(WD_STATISTIC_LINES)

    # If even a lot of leaders doesn't wrap, keep hi
    if lines <= 1:
        return f"{base}{ELL * hi}{page}", hi

    # Now binary search in (lo, hi)
    left = lo
    right = hi
    best = lo
    while left <= right:
        mid = (left + right) // 2
        set_text(mid)
        lines = para.Range.ComputeStatistics(WD_STATISTIC_LINES)
        if lines <= 1:
            best = mid
            left = mid + 1
        else:
            right = mid - 1

    # Restore best
    set_text(best)
    return f"{base}{ELL * best}{page}", best


def _format_toc_paragraph(doc, para):
    raw = para.Range.Text
    # raw ends with '\r' and sometimes '\x07'
    raw = raw.replace("\r", "").replace("\x07", "")
    if not raw.strip():
        return

    # Most Word TOC entries are "title\tpage"
    if "\t" in raw:
        parts = raw.split("\t")
        title = parts[0].strip()
        page = parts[-1].strip()
    else:
        # already flattened (or some weird case)
        # try last whitespace separated token as page
        toks = raw.strip().split()
        if len(toks) < 2:
            return
        title = " ".join(toks[:-1])
        page = toks[-1]

    level = _para_level_from_style(para)

    title_disp = _norm_title_for_toc_display(title)
    line, cnt = _build_line_no_wrap(doc, para, title_disp, page, level)

    # Apply font formatting by ranges (title vs leader+page)
    # After setting text, para.Range now contains line + '\r'
    rng = para.Range
    txt = rng.Text.replace("\r", "").replace("\x07", "")
    # Locate page start by finding the last occurrence of page
    page_pos = txt.rfind(page)
    if page_pos == -1:
        page_pos = len(txt) - len(page)

    # Title part ends right before leader start:
    # leader start is after title_disp length
    title_end = len(title_disp)

    # Set whole line default to 宋体 12
    _set_range_font(rng, name="SimSun", size_pt=12, bold=False, color_rgb=0)

    # Level 1 title in 黑体 14
    if level == 1:
        r_title = doc.Range(rng.Start, rng.Start + title_end)
        _set_range_font(r_title, name="SimHei", size_pt=14, bold=False, color_rgb=0)

    # Ensure leader+page are SimSun 12 (already), but we keep it explicit
    r_tail = doc.Range(rng.Start + title_end, rng.End - 1)  # exclude paragraph mark
    _set_range_font(r_tail, name="SimSun", size_pt=12, bold=False, color_rgb=0)


def finalize(docx_path: Path):
    docx_path = docx_path.resolve()
    if not docx_path.exists():
        raise FileNotFoundError(docx_path)

    out_docx = docx_path.with_name(docx_path.stem + "_FINAL.docx")
    out_pdf = docx_path.with_name(docx_path.stem + "_FINAL.pdf")

    word = win32.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0

    doc = None
    try:
        doc = word.Documents.Open(str(docx_path), ReadOnly=False, AddToRecentFiles=False)

        # Update pagination + fields (critical)
        doc.Repaginate()
        doc.Fields.Update()

        if doc.TablesOfContents.Count >= 1:
            toc = doc.TablesOfContents(1)
            toc.Update()

            # Freeze TOC fields -> plain text
            try:
                toc.Range.Fields.Unlink()
            except Exception:
                pass

            # Iterate paragraphs within TOC range
            start = toc.Range.Start
            end = toc.Range.End
            for para in doc.Range(start, end).Paragraphs:
                # Skip the TOC title "目 录" if included
                t = para.Range.Text.replace("\r", "").replace("\x07", "").strip()
                if t in ("目 录", "目录", "目  录"):
                    continue
                _format_toc_paragraph(doc, para)

        # Save final docx
        doc.SaveAs2(str(out_docx))

        # Export PDF
        doc.ExportAsFixedFormat(
            OutputFileName=str(out_pdf),
            ExportFormat=WD_EXPORT_FORMAT_PDF,
            OpenAfterExport=False,
            OptimizeFor=0,  # print
            Range=0,        # all
            Item=0,         # document content
            IncludeDocProps=True,
            KeepIRM=True,
            CreateBookmarks=1,  # headings
            DocStructureTags=True,
            BitmapMissingFonts=True,
            UseISO19005_1=False
        )

        print(f"[OK] FINAL DOCX: {out_docx}")
        print(f"[OK] FINAL PDF : {out_pdf}")

    finally:
        if doc is not None:
            doc.Close(SaveChanges=WD_DO_NOT_SAVE_CHANGES)
        word.Quit()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python word_finalize_toc_export.py <path_to_docx>")
        sys.exit(1)
    finalize(Path(sys.argv[1]))
