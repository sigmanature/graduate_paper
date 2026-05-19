import re
import sys
from pathlib import Path

import win32com.client as win32
from win32com.client import constants

PT_PER_CM = 72.0 / 2.54
WD_STAT_LINES = 1
WD_EXPORT_PDF = 17

DOT_CHAR = "…"
FONT_SONG = "宋体"
FONT_HEI = "黑体"

# Adjustable layout knobs
LEVEL_INDENT_CM = {1: 0.0, 2: 0.74, 3: 1.48}
TITLE_SIZE_PT = {1: 14.0, 2: 12.0, 3: 12.0}
BODY_SIZE_PT = 12.0
MAX_DOTS = 80


def cm_to_pt(value_cm):
    return float(value_cm) * PT_PER_CM


def clean_text(text):
    if text is None:
        return ""
    return text.replace("\r", "").replace("\x07", "").strip()


def get_style_level(paragraph):
    try:
        name = str(paragraph.Range.Style.NameLocal)
    except Exception:
        try:
            name = str(paragraph.Style.NameLocal)
        except Exception:
            name = ""
    m = re.search(r"(\d+)", name)
    if m:
        return max(1, min(3, int(m.group(1))))
    return 1


def locate_markers(doc):
    start = None
    end = None
    for para in doc.Paragraphs:
        txt = clean_text(para.Range.Text)
        if txt == "[[TOC_BEGIN]]":
            start = para.Range.Start
        elif txt == "[[TOC_END]]":
            end = para.Range.End
    return start, end


def collect_toc_entries(doc):
    if doc.TablesOfContents.Count < 1:
        raise RuntimeError("No Word TOC field found in the document.")

    toc = doc.TablesOfContents(1)
    toc.Update()
    doc.Repaginate()
    toc = doc.TablesOfContents(1)
    toc_range = toc.Range.Duplicate
    toc_start = toc_range.Start
    toc_end = toc_range.End

    entries = []
    for para in toc_range.Paragraphs:
        text = clean_text(para.Range.Text)
        if not text or text == "目录":
            continue
        if "\t" not in text:
            continue
        parts = [p for p in text.split("\t") if p != ""]
        if len(parts) < 2:
            continue
        title = parts[0].strip()
        page = parts[-1].strip()
        if not title or not page:
            continue
        entries.append({
            "level": get_style_level(para),
            "title": title,
            "page": page,
        })

    if not entries:
        raise RuntimeError("TOC was found, but no TOC entries could be parsed after Word update.")

    return entries, toc_start, toc_end


def apply_font(rng, font_name, size_pt, bold=False):
    rng.Font.Name = font_name
    try:
        rng.Font.NameFarEast = font_name
    except Exception:
        pass
    rng.Font.Size = size_pt
    rng.Font.Bold = -1 if bold else 0


def style_toc_para(para, level):
    pf = para.Range.ParagraphFormat
    pf.LeftIndent = cm_to_pt(LEVEL_INDENT_CM.get(level, 0.0))
    pf.FirstLineIndent = 0
    pf.SpaceBefore = 0
    pf.SpaceAfter = 0
    pf.LineSpacingRule = constants.wdLineSpace1pt5
    para.Alignment = constants.wdAlignParagraphLeft


def set_entry_text_and_style(doc, para, entry, dot_count):
    title = entry["title"]
    dots = DOT_CHAR * dot_count
    page = entry["page"]
    full_text = f"{title}{dots}{page}"
    para.Range.Text = full_text
    style_toc_para(para, entry["level"])

    start = para.Range.Start
    title_rng = doc.Range(start, start + len(title))
    dots_rng = doc.Range(start + len(title), start + len(title) + len(dots))
    page_rng = doc.Range(start + len(title) + len(dots), start + len(full_text))

    # Base font: all directory text, dots, and page numbers use Songti small-four.
    apply_font(para.Range, FONT_SONG, BODY_SIZE_PT, False)
    apply_font(dots_rng, FONT_SONG, BODY_SIZE_PT, False)
    apply_font(page_rng, FONT_SONG, BODY_SIZE_PT, False)

    # Only the level-1 title text itself uses SimHei 14pt.
    if entry["level"] == 1:
        apply_font(title_rng, FONT_HEI, TITLE_SIZE_PT[1], False)
    else:
        apply_font(title_rng, FONT_SONG, TITLE_SIZE_PT.get(entry["level"], BODY_SIZE_PT), False)

    return full_text


def paragraph_is_one_line(para):
    try:
        return para.Range.ComputeStatistics(WD_STAT_LINES) <= 1
    except Exception:
        return True


def find_best_dot_count(doc, para, entry):
    # First try zero dots.
    set_entry_text_and_style(doc, para, entry, 0)
    if not paragraph_is_one_line(para):
        return 0

    lo = 0
    hi = 1
    while hi <= MAX_DOTS:
        set_entry_text_and_style(doc, para, entry, hi)
        if paragraph_is_one_line(para):
            lo = hi
            hi *= 2
        else:
            break
    hi = min(hi, MAX_DOTS)

    while lo < hi:
        mid = (lo + hi + 1) // 2
        set_entry_text_and_style(doc, para, entry, mid)
        if paragraph_is_one_line(para):
            lo = mid
        else:
            hi = mid - 1

    set_entry_text_and_style(doc, para, entry, lo)
    return lo


def find_toc_title_end(doc, toc_start):
    begin_pos, end_pos = locate_markers(doc)
    if begin_pos is not None:
        return begin_pos, end_pos

    prev_text = clean_text(doc.Range(max(0, toc_start - 120), toc_start).Text)
    if TOC_TITLE in prev_text:
        return toc_start, toc_start
    return toc_start, toc_start


def insert_paragraph_at(doc, pos):
    rng = doc.Range(pos, pos)
    para = doc.Paragraphs.Add(rng)
    return para


TOC_TITLE = "目录"


def rebuild_manual_toc(doc, entries, toc_start, toc_end):
    marker_start, marker_end = locate_markers(doc)

    if marker_start is not None and marker_end is not None:
        delete_start = marker_start
        delete_end = marker_end
    else:
        delete_start = toc_start
        delete_end = toc_end

    doc.Range(delete_start, delete_end).Delete()

    insert_at = delete_start
    for entry in entries:
        para = insert_paragraph_at(doc, insert_at)
        find_best_dot_count(doc, para, entry)
        insert_at = para.Range.End


def finalize(docx_path, pdf_path=None):
    word = win32.gencache.EnsureDispatch("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0

    doc = None
    try:
        doc = word.Documents.Open(str(docx_path.resolve()))
        doc.Repaginate()
        doc.Fields.Update()
        if doc.TablesOfContents.Count >= 1:
            for i in range(1, doc.TablesOfContents.Count + 1):
                doc.TablesOfContents(i).Update()
        doc.Repaginate()

        entries, toc_start, toc_end = collect_toc_entries(doc)
        rebuild_manual_toc(doc, entries, toc_start, toc_end)
        doc.Repaginate()

        final_docx = docx_path.with_name(docx_path.stem + "_FINAL.docx")
        doc.SaveAs(str(final_docx.resolve()))

        final_pdf = pdf_path or docx_path.with_name(docx_path.stem + "_FINAL.pdf")
        doc.ExportAsFixedFormat(str(Path(final_pdf).resolve()), WD_EXPORT_PDF)
        print(f"[OK] wrote {final_docx}")
        print(f"[OK] wrote {final_pdf}")
    finally:
        if doc is not None:
            try:
                doc.Close(False)
            except Exception:
                pass
        try:
            word.Quit()
        except Exception:
            pass


def main():
    if len(sys.argv) < 2:
        print("Usage: python word_toc_finalize_stage2.py <docx_path> [pdf_path]")
        raise SystemExit(2)

    docx_path = Path(sys.argv[1])
    if not docx_path.exists():
        raise FileNotFoundError(f"Input DOCX not found: {docx_path}")
    pdf_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else None
    finalize(docx_path, pdf_path)


if __name__ == "__main__":
    main()
