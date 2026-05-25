#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import tempfile
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Callable

from lxml import etree


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
XML = "http://www.w3.org/XML/1998/namespace"

NS = {"w": W, "r": R}
REL_NS = {"rel": REL}
CT_NS = {"ct": CT}

SCHOOL_HEADER = "南京工业大学本科毕业设计（论文）"


def qn(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


def body_text(p: etree._Element) -> str:
    return "".join(p.xpath(".//w:t/text()", namespaces=NS)).strip()


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def is_page_break_only(p: etree._Element) -> bool:
    txt = body_text(p)
    has_page_break = bool(p.xpath(".//w:br[@w:type='page']", namespaces=NS))
    non_break_text = compact(txt)
    return has_page_break and not non_break_text


def ensure_child(parent: etree._Element, child_tag: str) -> etree._Element:
    child = parent.find(qn(W, child_tag))
    if child is None:
        child = etree.SubElement(parent, qn(W, child_tag))
    return child


def clear_paragraph_content(p: etree._Element) -> None:
    for child in list(p):
        if child.tag != qn(W, "pPr"):
            p.remove(child)


def set_jc(p: etree._Element, value: str) -> None:
    p_pr = ensure_child(p, "pPr")
    jc = p_pr.find(qn(W, "jc"))
    if jc is None:
        jc = etree.SubElement(p_pr, qn(W, "jc"))
    jc.set(qn(W, "val"), value)


def get_style_id(p: etree._Element) -> str | None:
    vals = p.xpath("./w:pPr/w:pStyle/@w:val", namespaces=NS)
    return vals[0] if vals else None


def is_heading_or_special(text: str, style_id: str | None) -> bool:
    c = compact(text)
    if not c:
        return True
    if style_id in {"3", "4", "5"}:
        return True
    if c in {"摘要", "ABSTRACT", "目录", "参考文献", "致谢"}:
        return True
    if re.match(r"^第[一二三四五六七八九十]+章", c):
        return True
    if re.match(r"^\d+(\.\d+)+", c):
        return True
    if re.match(r"^(图|表|代码)\s*\d", text.strip()):
        return True
    if text.strip().startswith(("关键词", "Key Words", "Key words")):
        return True
    return False


def add_run_text(p: etree._Element, text: str, font: str = "宋体", size_half_points: str = "21") -> None:
    r = etree.SubElement(p, qn(W, "r"))
    r_pr = etree.SubElement(r, qn(W, "rPr"))
    r_fonts = etree.SubElement(r_pr, qn(W, "rFonts"))
    r_fonts.set(qn(W, "ascii"), font)
    r_fonts.set(qn(W, "hAnsi"), font)
    r_fonts.set(qn(W, "eastAsia"), font)
    sz = etree.SubElement(r_pr, qn(W, "sz"))
    sz.set(qn(W, "val"), size_half_points)
    sz_cs = etree.SubElement(r_pr, qn(W, "szCs"))
    sz_cs.set(qn(W, "val"), size_half_points)
    t = etree.SubElement(r, qn(W, "t"))
    t.text = text


def add_field(
    p: etree._Element,
    instr: str,
    placeholder: str = "",
    font: str = "Times New Roman",
    size_half_points: str = "21",
) -> None:
    def add_r() -> etree._Element:
        r = etree.SubElement(p, qn(W, "r"))
        r_pr = etree.SubElement(r, qn(W, "rPr"))
        r_fonts = etree.SubElement(r_pr, qn(W, "rFonts"))
        r_fonts.set(qn(W, "ascii"), font)
        r_fonts.set(qn(W, "hAnsi"), font)
        r_fonts.set(qn(W, "eastAsia"), font)
        sz = etree.SubElement(r_pr, qn(W, "sz"))
        sz.set(qn(W, "val"), size_half_points)
        sz_cs = etree.SubElement(r_pr, qn(W, "szCs"))
        sz_cs.set(qn(W, "val"), size_half_points)
        return r

    r = add_r()
    fld = etree.SubElement(r, qn(W, "fldChar"))
    fld.set(qn(W, "fldCharType"), "begin")

    r = add_r()
    instr_el = etree.SubElement(r, qn(W, "instrText"))
    instr_el.set(qn(XML, "space"), "preserve")
    instr_el.text = instr

    r = add_r()
    fld = etree.SubElement(r, qn(W, "fldChar"))
    fld.set(qn(W, "fldCharType"), "separate")

    if placeholder:
        add_run_text(p, placeholder, font=font, size_half_points=size_half_points)

    r = add_r()
    fld = etree.SubElement(r, qn(W, "fldChar"))
    fld.set(qn(W, "fldCharType"), "end")


def make_header_xml(kind: str, title: str | None = None) -> bytes:
    root = etree.Element(qn(W, "hdr"), nsmap={"w": W, "r": R})
    p = etree.SubElement(root, qn(W, "p"))
    p_pr = etree.SubElement(p, qn(W, "pPr"))
    jc = etree.SubElement(p_pr, qn(W, "jc"))
    jc.set(qn(W, "val"), "center")
    p_bdr = etree.SubElement(p_pr, qn(W, "pBdr"))
    bottom = etree.SubElement(p_bdr, qn(W, "bottom"))
    bottom.set(qn(W, "val"), "single")
    bottom.set(qn(W, "color"), "auto")
    bottom.set(qn(W, "sz"), "6")
    bottom.set(qn(W, "space"), "1")
    if kind == "odd":
        add_run_text(p, SCHOOL_HEADER, font="宋体", size_half_points="21")
    else:
        add_run_text(p, title or "", font="宋体", size_half_points="21")
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def make_footer_xml() -> bytes:
    root = etree.Element(qn(W, "ftr"), nsmap={"w": W, "r": R})
    p = etree.SubElement(root, qn(W, "p"))
    p_pr = etree.SubElement(p, qn(W, "pPr"))
    jc = etree.SubElement(p_pr, qn(W, "jc"))
    jc.set(qn(W, "val"), "center")
    add_field(p, " PAGE  \\* MERGEFORMAT ", placeholder="1", font="Times New Roman", size_half_points="21")
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def strip_null_relationships(rels_root: etree._Element) -> int:
    removed = 0
    for rel in list(rels_root):
        target = rel.get("Target", "")
        if "NULL" in target:
            rels_root.remove(rel)
            removed += 1
    return removed


def next_rid(rels_root: etree._Element) -> str:
    max_id = 0
    for rel in rels_root:
        rid = rel.get("Id", "")
        m = re.match(r"rId(\d+)$", rid)
        if m:
            max_id = max(max_id, int(m.group(1)))
    return f"rId{max_id + 1}"


def add_relationship(rels_root: etree._Element, rel_type: str, target: str) -> str:
    rid = next_rid(rels_root)
    rel = etree.SubElement(rels_root, qn(REL, "Relationship"))
    rel.set("Id", rid)
    rel.set("Type", rel_type)
    rel.set("Target", target)
    return rid


def ensure_content_type(ct_root: etree._Element, part_name: str, content_type: str) -> None:
    existing = ct_root.xpath(f"./ct:Override[@PartName='{part_name}']", namespaces=CT_NS)
    if existing:
        existing[0].set("ContentType", content_type)
        return
    override = etree.SubElement(ct_root, qn(CT, "Override"))
    override.set("PartName", part_name)
    override.set("ContentType", content_type)


def clean_sect_pr(base: etree._Element) -> etree._Element:
    sect = deepcopy(base)
    for child in list(sect):
        if child.tag in {
            qn(W, "headerReference"),
            qn(W, "footerReference"),
            qn(W, "pgNumType"),
            qn(W, "titlePg"),
            qn(W, "type"),
        }:
            sect.remove(child)
    return sect


def prepend_section_refs(
    sect: etree._Element,
    *,
    odd_header_rid: str | None = None,
    even_header_rid: str | None = None,
    footer_rid: str | None = None,
    fmt: str | None = None,
    start: int | None = None,
    next_page: bool = True,
) -> etree._Element:
    insert_at = 0
    if odd_header_rid:
        h = etree.Element(qn(W, "headerReference"))
        h.set(qn(W, "type"), "default")
        h.set(qn(R, "id"), odd_header_rid)
        sect.insert(insert_at, h)
        insert_at += 1
    if even_header_rid:
        h = etree.Element(qn(W, "headerReference"))
        h.set(qn(W, "type"), "even")
        h.set(qn(R, "id"), even_header_rid)
        sect.insert(insert_at, h)
        insert_at += 1
    if footer_rid:
        f = etree.Element(qn(W, "footerReference"))
        f.set(qn(W, "type"), "default")
        f.set(qn(R, "id"), footer_rid)
        sect.insert(insert_at, f)
        insert_at += 1
        f = etree.Element(qn(W, "footerReference"))
        f.set(qn(W, "type"), "even")
        f.set(qn(R, "id"), footer_rid)
        sect.insert(insert_at, f)
        insert_at += 1
    if next_page:
        typ = etree.Element(qn(W, "type"))
        typ.set(qn(W, "val"), "nextPage")
        sect.insert(insert_at, typ)
        insert_at += 1
    if fmt or start is not None:
        pg = etree.Element(qn(W, "pgNumType"))
        if fmt:
            pg.set(qn(W, "fmt"), fmt)
        if start is not None:
            pg.set(qn(W, "start"), str(start))
        # Word accepts pgNumType after page margins; place it before cols/docGrid if possible.
        cols_idx = next((i for i, c in enumerate(sect) if c.tag == qn(W, "cols")), len(sect))
        sect.insert(cols_idx, pg)
    return sect


def make_section_break_paragraph(sect_pr: etree._Element) -> etree._Element:
    p = etree.Element(qn(W, "p"))
    p_pr = etree.SubElement(p, qn(W, "pPr"))
    p_pr.append(sect_pr)
    return p


def replace_with_section_break(p: etree._Element, sect_pr: etree._Element) -> None:
    clear_paragraph_content(p)
    p_pr = ensure_child(p, "pPr")
    for old in list(p_pr):
        if old.tag == qn(W, "sectPr"):
            p_pr.remove(old)
    p_pr.append(sect_pr)


def make_toc_field_paragraph() -> etree._Element:
    p = etree.Element(qn(W, "p"))
    p_pr = etree.SubElement(p, qn(W, "pPr"))
    spacing = etree.SubElement(p_pr, qn(W, "spacing"))
    spacing.set(qn(W, "line"), "360")
    spacing.set(qn(W, "lineRule"), "auto")
    fld = etree.SubElement(p, qn(W, "fldSimple"))
    fld.set(qn(W, "instr"), 'TOC \\o "1-3" \\h \\z \\u')
    r = etree.SubElement(fld, qn(W, "r"))
    t = etree.SubElement(r, qn(W, "t"))
    t.text = "目录待 Word 更新"
    return p


def ensure_even_and_odd(settings_root: etree._Element) -> None:
    if not settings_root.xpath("./w:evenAndOddHeaders", namespaces=NS):
        node = etree.Element(qn(W, "evenAndOddHeaders"))
        node.set(qn(W, "val"), "1")
        settings_root.insert(0, node)


def find_paragraphs(root: etree._Element) -> tuple[etree._Element, list[etree._Element]]:
    body = root.xpath("//w:body", namespaces=NS)[0]
    return body, [child for child in body if child.tag == qn(W, "p")]


def find_indexes(paras: list[etree._Element]) -> tuple[int, int, int]:
    abstract_idx = None
    toc_idx = None
    body_idx = None
    for i, p in enumerate(paras):
        text = body_text(p)
        c = compact(text)
        if abstract_idx is None and c == "摘要":
            abstract_idx = i
        if toc_idx is None and c == "目录":
            toc_idx = i
        if toc_idx is not None and body_idx is None and get_style_id(p) == "3" and re.match(r"^第一章", c):
            body_idx = i
            break
    missing = []
    if abstract_idx is None:
        missing.append("摘要")
    if toc_idx is None:
        missing.append("目录")
    if body_idx is None:
        missing.append("正文第一章")
    if missing:
        raise RuntimeError(f"missing required paragraph(s): {', '.join(missing)}")
    return abstract_idx, toc_idx, body_idx


def normalized_header_title(text: str) -> str:
    c = compact(text)
    if c == "摘要":
        return "摘要"
    if c.upper() == "ABSTRACT":
        return "ABSTRACT"
    if c == "目录":
        return "目录"
    return re.sub(r"\s+", " ", text).strip()


def section_page_start(paras: list[etree._Element], heading_idx: int) -> etree._Element:
    """Use the visible thesis title line before abstract headings when it belongs to the same page."""
    if heading_idx >= 2:
        prev = paras[heading_idx - 1]
        prev_prev = paras[heading_idx - 2]
        if body_text(prev) and is_page_break_only(prev_prev):
            return prev
    return paras[heading_idx]


def ensure_break_before(
    body: etree._Element,
    start_element: etree._Element,
    sect_pr: etree._Element,
) -> None:
    children = list(body)
    idx = children.index(start_element)
    if idx > 0 and children[idx - 1].tag == qn(W, "p") and is_page_break_only(children[idx - 1]):
        replace_with_section_break(children[idx - 1], sect_pr)
        return
    body.insert(idx, make_section_break_paragraph(sect_pr))


def collect_section_starts(document_root: etree._Element) -> list[dict[str, object]]:
    body, paras = find_paragraphs(document_root)
    abstract_idx, toc_idx, _first_body_idx = find_indexes(paras)
    abstract_start = section_page_start(paras, abstract_idx)

    abstract_en_idx = None
    for i, p in enumerate(paras):
        if compact(body_text(p)).upper() == "ABSTRACT":
            abstract_en_idx = i
            break
    if abstract_en_idx is None:
        raise RuntimeError("missing ABSTRACT heading")
    abstract_en_start = section_page_start(paras, abstract_en_idx)

    starts: list[dict[str, object]] = [
        {"element": abstract_start, "title": "摘要", "fmt": "upperRoman", "start": 1},
        {"element": abstract_en_start, "title": "ABSTRACT", "fmt": "upperRoman", "start": None},
        {"element": paras[toc_idx], "title": "目录", "fmt": "upperRoman", "start": None},
    ]

    after_toc = False
    first_body = True
    for p in paras:
        if p is paras[toc_idx]:
            after_toc = True
            continue
        if not after_toc:
            continue
        text = body_text(p)
        if get_style_id(p) != "3" or not text:
            continue
        c = compact(text)
        if c in {"摘要", "ABSTRACT"}:
            continue
        if re.match(r"^第一章", c) or re.match(r"^第[一二三四五六七八九十]+章", c) or c in {"参考文献", "致谢"}:
            if c in {"参考文献", "致谢"}:
                continue
            starts.append(
                {
                    "element": p,
                    "title": normalized_header_title(text),
                    "fmt": "decimal",
                    "start": 1 if first_body else None,
                }
            )
            first_body = False
    return starts


def normalize_toc_and_sections(
    document_root: etree._Element,
    *,
    odd_header_rid: str,
    footer_rid: str,
    even_header_for: Callable[[str], str],
) -> tuple[int, int]:
    body, paras = find_paragraphs(document_root)
    abstract_idx, toc_idx, first_body_idx = find_indexes(paras)
    final_sect = body.find(qn(W, "sectPr"))
    if final_sect is None:
        raise RuntimeError("document has no final sectPr")
    base = clean_sect_pr(final_sect)

    # Start the Roman-numbered section at the page containing the Chinese abstract.
    abstract_page_start = max(0, abstract_idx - 1)
    section_break_source = None
    for j in range(abstract_page_start - 1, max(-1, abstract_page_start - 6), -1):
        if is_page_break_only(paras[j]):
            section_break_source = paras[j]
            break
    front_sect = prepend_section_refs(clean_sect_pr(base), next_page=True)
    if section_break_source is not None:
        replace_with_section_break(section_break_source, front_sect)
    else:
        idx = body.index(paras[abstract_page_start])
        body.insert(idx, make_section_break_paragraph(front_sect))

    body, paras = find_paragraphs(document_root)
    abstract_idx, toc_idx, first_body_idx = find_indexes(paras)
    toc_title = paras[toc_idx]
    first_body = paras[first_body_idx]

    # Replace the old rendered/manual TOC with a real Word TOC field.
    for p in paras[toc_idx + 1 : first_body_idx]:
        body.remove(p)
    toc_field = make_toc_field_paragraph()
    body.insert(body.index(toc_title) + 1, toc_field)

    # End the Roman section immediately before the body.
    # Split every top-level thesis part into its own section, matching the reference
    # document's static even-page running headers.
    section_starts = collect_section_starts(document_root)
    if len(section_starts) < 4:
        raise RuntimeError("expected abstract, ABSTRACT, TOC, and at least one body section")

    body, _paras = find_paragraphs(document_root)
    for idx, current in enumerate(section_starts[:-1]):
        next_start = section_starts[idx + 1]["element"]
        even_rid = even_header_for(str(current["title"]))
        sect = prepend_section_refs(
            clean_sect_pr(base),
            odd_header_rid=odd_header_rid,
            even_header_rid=even_rid,
            footer_rid=footer_rid,
            fmt=str(current["fmt"]),
            start=current["start"],
            next_page=True,
        )
        ensure_break_before(body, next_start, sect)

    # The last section runs to document end.
    last = section_starts[-1]
    even_rid = even_header_for(str(last["title"]))
    body_final_sect = prepend_section_refs(
        clean_sect_pr(base),
        odd_header_rid=odd_header_rid,
        even_header_rid=even_rid,
        footer_rid=footer_rid,
        fmt=str(last["fmt"]),
        start=last["start"],
        next_page=False,
    )
    body.remove(final_sect)
    body.append(body_final_sect)

    return toc_idx, first_body_idx


def justify_body_paragraphs(document_root: etree._Element) -> tuple[int, list[tuple[int, str, str | None, str | None]]]:
    _body, paras = find_paragraphs(document_root)
    _abstract_idx, toc_idx, first_body_idx = find_indexes(paras)
    adjusted = 0
    leftovers: list[tuple[int, str, str | None, str | None]] = []
    in_toc_block = False
    for i, p in enumerate(paras):
        text = body_text(p)
        c = compact(text)
        if c == "目录":
            in_toc_block = True
        if i >= first_body_idx:
            in_toc_block = False
        if in_toc_block:
            continue
        style_id = get_style_id(p)
        if is_heading_or_special(text, style_id):
            continue
        jc_vals = p.xpath("./w:pPr/w:jc/@w:val", namespaces=NS)
        old = jc_vals[0] if jc_vals else None
        if old != "both":
            set_jc(p, "both")
            adjusted += 1
        jc_vals = p.xpath("./w:pPr/w:jc/@w:val", namespaces=NS)
        now = jc_vals[0] if jc_vals else None
        if now != "both":
            leftovers.append((i, text[:80], style_id, now))
    return adjusted, leftovers


def process_docx(input_docx: Path, output_docx: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        with zipfile.ZipFile(input_docx) as zin:
            zin.extractall(work)

        document_xml = work / "word" / "document.xml"
        settings_xml = work / "word" / "settings.xml"
        rels_xml = work / "word" / "_rels" / "document.xml.rels"
        content_types_xml = work / "[Content_Types].xml"

        parser = etree.XMLParser(remove_blank_text=False)
        document_root = etree.parse(str(document_xml), parser).getroot()
        settings_root = etree.parse(str(settings_xml), parser).getroot()
        rels_root = etree.parse(str(rels_xml), parser).getroot()
        ct_root = etree.parse(str(content_types_xml), parser).getroot()

        removed_null = strip_null_relationships(rels_root)
        odd_header_rid = add_relationship(
            rels_root,
            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/header",
            "header_thesis_odd.xml",
        )
        footer_rid = add_relationship(
            rels_root,
            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer",
            "footer_thesis_page.xml",
        )
        generated_headers: dict[str, bytes] = {"header_thesis_odd.xml": make_header_xml("odd")}

        def even_header_for(title: str) -> str:
            safe_idx = len(generated_headers)
            part_name = f"header_thesis_even_{safe_idx}.xml"
            rid = add_relationship(
                rels_root,
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/header",
                part_name,
            )
            ensure_content_type(
                ct_root,
                f"/word/{part_name}",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml",
            )
            generated_headers[part_name] = make_header_xml("even", title=title)
            return rid

        ensure_content_type(
            ct_root,
            "/word/header_thesis_odd.xml",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml",
        )
        ensure_content_type(
            ct_root,
            "/word/footer_thesis_page.xml",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml",
        )

        ensure_even_and_odd(settings_root)
        normalize_toc_and_sections(
            document_root,
            odd_header_rid=odd_header_rid,
            footer_rid=footer_rid,
            even_header_for=even_header_for,
        )
        justified, leftovers = justify_body_paragraphs(document_root)

        for header_name, header_xml in generated_headers.items():
            (work / "word" / header_name).write_bytes(header_xml)
        (work / "word" / "footer_thesis_page.xml").write_bytes(make_footer_xml())
        document_xml.write_bytes(etree.tostring(document_root, xml_declaration=True, encoding="UTF-8", standalone=True))
        settings_xml.write_bytes(etree.tostring(settings_root, xml_declaration=True, encoding="UTF-8", standalone=True))
        rels_xml.write_bytes(etree.tostring(rels_root, xml_declaration=True, encoding="UTF-8", standalone=True))
        content_types_xml.write_bytes(etree.tostring(ct_root, xml_declaration=True, encoding="UTF-8", standalone=True))

        output_docx.parent.mkdir(parents=True, exist_ok=True)
        if output_docx.exists():
            output_docx.unlink()
        with zipfile.ZipFile(output_docx, "w", zipfile.ZIP_DEFLATED) as zout:
            for path in sorted(work.rglob("*")):
                if path.is_file():
                    zout.write(path, path.relative_to(work).as_posix())

    return {
        "output": str(output_docx),
        "removed_null_relationships": removed_null,
        "justified_paragraphs": justified,
        "nonjustified_leftovers": leftovers,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_docx", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.input_docx.exists():
        raise FileNotFoundError(args.input_docx)

    result = process_docx(args.input_docx, args.output)
    print(f"output: {result['output']}")
    print(f"removed_null_relationships: {result['removed_null_relationships']}")
    print(f"justified_paragraphs: {result['justified_paragraphs']}")
    leftovers = result["nonjustified_leftovers"]
    print(f"nonjustified_leftovers: {len(leftovers)}")
    for idx, text, style_id, jc in leftovers[:20]:
        print(f"  leftover idx={idx} style={style_id} jc={jc} text={text!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
