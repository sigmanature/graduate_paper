#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the thesis .docx from the rewritten Markdown sources.

This script intentionally does not import the legacy thesis.py content builder.
The legacy file is used only as the formatting contract:
- A4 with 2.54 cm margins
- Heading 1: Songti 16 pt, centered
- Heading 2: Songti 14 pt, bold, left
- Heading 3: Songti 12 pt, left
- Body: Songti / Times New Roman 12 pt, first-line indent 24 pt, 1.5 line spacing
- Figure/table captions: Songti 10.5 pt, centered

The generated intermediate docx keeps algorithm placeholders. Run the bundled
word-thesis-pseudocode inserter afterwards to replace them with editable
algorithm tables.
"""

from __future__ import annotations

import copy
import html
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image


BASE = Path(__file__).resolve().parent
SOURCE_DOCX = BASE / "赵南哲毕业论文暂时初稿_1-20260512.docx"
REFERENCE_DOCX = Path("/home/nzzhao/Downloads/毕业论文_参考 (1).docx")
INTERMEDIATE = BASE / "赵南哲毕业论文_重写正文_算法占位.docx"
OUTPUT = BASE / "赵南哲毕业论文_重写正文_待Word更新目录.docx"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
W14_NS = "http://schemas.microsoft.com/office/word/2010/wordml"
W15_NS = "http://schemas.microsoft.com/office/word/2012/wordml"
WP14_NS = "http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing"
WPC_NS = "http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"
WPG_NS = "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup"
WPI_NS = "http://schemas.microsoft.com/office/word/2010/wordprocessingInk"
WPS_NS = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
W10_NS = "urn:schemas-microsoft-com:office:word"
WNE_NS = "http://schemas.microsoft.com/office/word/2006/wordml"
O_NS = "urn:schemas-microsoft-com:office:office"
V_NS = "urn:schemas-microsoft-com:vml"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"

NS = {"w": W_NS, "r": R_NS, "wp": WP_NS, "a": A_NS, "pic": PIC_NS}
for prefix, uri in [
    ("wpc", WPC_NS),
    ("mc", MC_NS),
    ("o", O_NS),
    ("w", W_NS),
    ("r", R_NS),
    ("m", M_NS),
    ("v", V_NS),
    ("wp14", WP14_NS),
    ("wp", WP_NS),
    ("w10", W10_NS),
    ("w14", W14_NS),
    ("w15", W15_NS),
    ("wpg", WPG_NS),
    ("wpi", WPI_NS),
    ("wne", WNE_NS),
    ("wps", WPS_NS),
    ("a", A_NS),
    ("pic", PIC_NS),
]:
    ET.register_namespace(prefix, uri)
ET.register_namespace("", REL_NS)


def qn(ns: str, tag: str) -> str:
    table = {
        "w": W_NS,
        "r": R_NS,
        "wp": WP_NS,
        "a": A_NS,
        "pic": PIC_NS,
        "rel": REL_NS,
        "ct": CT_NS,
        "mc": MC_NS,
    }
    return f"{{{table[ns]}}}{tag}"


def el(tag: str, attrs: dict[str, str] | None = None, text: str | None = None) -> ET.Element:
    prefix, name = tag.split(":", 1)
    node = ET.Element(qn(prefix, name), attrs or {})
    if text is not None:
        node.text = text
    return node


def append(parent: ET.Element, *children: ET.Element) -> ET.Element:
    for child in children:
        parent.append(child)
    return parent


def paragraph_text(p: ET.Element) -> str:
    return "".join(t.text or "" for t in p.findall(".//w:t", NS))


def make_rpr(
    *,
    size_half_pt: int,
    east_asia: str = "宋体",
    ascii_font: str = "Times New Roman",
    bold: bool = False,
    color: str = "000000",
    underline: bool = False,
    superscript: bool = False,
) -> ET.Element:
    rpr = el("w:rPr")
    fonts = el(
        "w:rFonts",
        {
            qn("w", "eastAsia"): east_asia,
            qn("w", "ascii"): ascii_font,
            qn("w", "hAnsi"): ascii_font,
        },
    )
    rpr.append(fonts)
    if bold:
        rpr.append(el("w:b"))
    if underline:
        rpr.append(el("w:u", {qn("w", "val"): "single"}))
    if superscript:
        rpr.append(el("w:vertAlign", {qn("w", "val"): "superscript"}))
    rpr.append(el("w:color", {qn("w", "val"): color}))
    rpr.append(el("w:sz", {qn("w", "val"): str(size_half_pt)}))
    rpr.append(el("w:szCs", {qn("w", "val"): str(size_half_pt)}))
    return rpr


def make_run(text: str, **rpr_kwargs) -> ET.Element:
    r = el("w:r")
    r.append(make_rpr(**rpr_kwargs))
    t = el("w:t", text=text)
    if text[:1].isspace() or text[-1:].isspace():
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    r.append(t)
    return r


def add_spacing(ppr: ET.Element, line: str = "360", before: str = "0", after: str = "0"):
    ppr.append(
        el(
            "w:spacing",
            {
                qn("w", "before"): before,
                qn("w", "after"): after,
                qn("w", "line"): line,
                qn("w", "lineRule"): "auto",
            },
        )
    )


def make_paragraph(
    text: str = "",
    *,
    kind: str = "body",
    style: str | None = None,
    align: str | None = None,
    first_line_twips: int | None = None,
    left_twips: int | None = None,
) -> ET.Element:
    p = el("w:p")
    ppr = el("w:pPr")
    if style:
        ppr.append(el("w:pStyle", {qn("w", "val"): style}))

    if kind == "h1":
        align = align or "center"
        add_spacing(ppr)
        rpr = dict(size_half_pt=32, east_asia="宋体", ascii_font="Times New Roman", bold=False)
    elif kind == "h2":
        align = align or "left"
        add_spacing(ppr)
        rpr = dict(size_half_pt=28, east_asia="宋体", ascii_font="Times New Roman", bold=True)
    elif kind == "h3":
        align = align or "left"
        add_spacing(ppr)
        rpr = dict(size_half_pt=24, east_asia="宋体", ascii_font="Times New Roman", bold=False)
    elif kind == "caption":
        align = align or "center"
        add_spacing(ppr)
        rpr = dict(size_half_pt=21, east_asia="宋体", ascii_font="Times New Roman", bold=False)
    elif kind == "toc_title":
        align = align or "center"
        add_spacing(ppr)
        rpr = dict(size_half_pt=32, east_asia="宋体", ascii_font="Times New Roman", bold=False)
    elif kind == "abstract_title":
        align = align or "center"
        add_spacing(ppr)
        rpr = dict(size_half_pt=30, east_asia="宋体", ascii_font="Times New Roman", bold=False)
    elif kind == "reference":
        align = align or "left"
        add_spacing(ppr, line="360")
        first_line_twips = first_line_twips if first_line_twips is not None else 0
        rpr = dict(size_half_pt=24, east_asia="宋体", ascii_font="Times New Roman", bold=False)
    else:
        align = align or "left"
        add_spacing(ppr, line="360")
        first_line_twips = first_line_twips if first_line_twips is not None else 480
        rpr = dict(size_half_pt=24, east_asia="宋体", ascii_font="Times New Roman", bold=False)

    if align:
        ppr.append(el("w:jc", {qn("w", "val"): align}))
    if first_line_twips is not None or left_twips is not None:
        attrs = {}
        if first_line_twips is not None:
            attrs[qn("w", "firstLine")] = str(first_line_twips)
        if left_twips is not None:
            attrs[qn("w", "left")] = str(left_twips)
        ppr.append(el("w:ind", attrs))
    p.append(ppr)
    if text:
        add_inline_runs(p, text, base_rpr=rpr, superscript_citations=(kind != "reference"))
    return p


SUPERSCRIPT_CITATION_RE = re.compile(r"(?:[\[［]\s*\d+(?:\s*(?:[-－–,，、]\s*\d+))*\s*[\]］])+")


def add_inline_runs(p: ET.Element, text: str, *, base_rpr: dict, superscript_citations: bool = True):
    """Add text with minimal Markdown inline cleanup, preserving code names."""
    # Remove bold markers but keep text. Inline code is rendered as regular thesis text.
    text = text.replace("**", "").replace("`", "")
    text = text.replace("–", "-")
    if not superscript_citations:
        p.append(make_run(text, **base_rpr))
        return
    pos = 0
    for match in SUPERSCRIPT_CITATION_RE.finditer(text):
        if match.start() > pos:
            p.append(make_run(text[pos : match.start()], **base_rpr))
        citation_rpr = dict(base_rpr)
        citation_rpr["superscript"] = True
        p.append(make_run(match.group(0), **citation_rpr))
        pos = match.end()
    if pos < len(text):
        p.append(make_run(text[pos:], **base_rpr))


def make_heading(text: str, level: int) -> ET.Element:
    if level == 1:
        return make_paragraph(text, kind="h1", style="1")
    if level == 2:
        return make_paragraph(text, kind="h2", style="21")
    return make_paragraph(text, kind="h3", style="31")


def make_page_break() -> ET.Element:
    p = el("w:p")
    r = el("w:r")
    r.append(el("w:br", {qn("w", "type"): "page"}))
    p.append(r)
    return p


def make_toc_field() -> ET.Element:
    p = el("w:p")
    fld = el("w:fldSimple", {qn("w", "instr"): 'TOC \\o "1-3" \\z \\u'})
    r = el("w:r")
    r.append(make_rpr(size_half_pt=24))
    r.append(el("w:t", text="目录待 Word 更新"))
    fld.append(r)
    p.append(fld)
    return p


IMAGE_MAP = {
    "fig_2_1_f2fs_inode_tree": ("imgs/元数据.jpg", "图 2-1 F2FS 索引节点与数据块映射结构"),
    "fig_2_4_64kb_read_path": ("imgs/page_bio.png", "图 2-2 一次 64KB 缓冲读的完整路径"),
    "fig_2_5_f2fs_layout": ("imgs/布局图.jpg", "图 2-3 F2FS 磁盘布局与冷热数据分区"),
    "fig_2_6_outplace_update": ("imgs/outplace.png", "图 2-4 F2FS 异地更新过程示意"),
    "fig_2_7_buffer_head_model": ("drawios/buffer_head_vs_iomap_layers.png", "图 2-5 buffer_head 与 iomap 映射模型对比"),
    "fig_2_8_iomap_arch": ("imgs/iomap架构图.png", "图 2-6 iomap 框架路径组织结构"),
    "fig_2_9_iomap_folio_state": ("imgs/ifs.png", "图 2-7 iomap 动态大页状态对象中的逐块位图与 pending 计数"),
    "fig_3_1_compress_cluster_cross": ("drawios/cross_modified.png", "图 3-1 动态大页跨越多个压缩簇的生命周期冲突"),
    "fig_4_1_all_arch": ("imgs/all_arch.png", "图 4-1 F2FS 动态大页缓冲 I/O 总体架构"),
    "fig_4_2_f2fs_ifs_layout": ("imgs/f2fs_ifs.png", "图 4-2 F2FS 扩展型动态大页状态对象布局"),
    "fig_4_3_private_strategy": ("imgs/multi_strategy.png", "图 4-3 F2FS private 字段兼容策略"),
    "fig_4_4_compress_read_cross": ("drawios/cross_modified.png", "图 4-4 压缩路径中动态大页跨簇子区间示意"),
    "fig_4_5_compress_buffered_write": ("imgs/compress_write.png", "图 4-5 压缩文件缓冲写的 head/middle/tail 簇处理"),
    "fig_4_6_compress_write_iomap": ("imgs/compress_write.png", "图 4-6 压缩写路径中的簇对齐与 iomap 区间处理"),
    "fig_4_7_read_pending": ("imgs/read_pending.png", "图 4-6 未完成读字节计数的偏置等待机制"),
    "fig_4_8_write_cache_folios": ("imgs/write_cache_folios.png", "图 4-7 动态大页脏区间写回路径"),
    "fig_5_1_qemu_bandwidth_normal": ("imgs/qemu/bandwidth_normal.png", "图 5-1 QEMU 平台普通文件顺序 I/O 带宽对比"),
    "fig_5_2_qemu_bandwidth_hole": ("imgs/qemu/bandwidth_hole.png", "图 5-2 QEMU 平台稀疏文件顺序 I/O 带宽对比"),
    "fig_5_3_qemu_bandwidth_com": ("imgs/qemu/bandwidth_com.png", "图 5-3 QEMU 平台压缩文件顺序 I/O 带宽对比"),
    "fig_5_4_pi_bandwidth_normal": ("imgs/pi/bandwidth_normal.png", "图 5-4 树莓派 5 平台普通文件顺序 I/O 带宽对比"),
    "fig_5_5_pi_bandwidth_hole": ("imgs/pi/bandwidth_hole.png", "图 5-5 树莓派 5 平台稀疏文件顺序 I/O 带宽对比"),
    "fig_5_6_pi_bandwidth_com": ("imgs/pi/bandwidth_com.png", "图 5-6 树莓派 5 平台压缩文件顺序 I/O 带宽对比"),
    "fig_5_7_qemu_stability_normal": ("imgs/qemu/bandwidth_stability_normal.png", "图 5-7 QEMU 平台普通文件带宽稳定性对比"),
    "fig_5_8_qemu_stability_hole": ("imgs/qemu/bandwidth_stability_hole.png", "图 5-8 QEMU 平台稀疏文件带宽稳定性对比"),
    "fig_5_9_qemu_stability_com": ("imgs/qemu/bandwidth_stability_com.png", "图 5-9 QEMU 平台压缩文件带宽稳定性对比"),
    "fig_5_10_pi_stability_normal": ("imgs/pi/bandwidth_stability_normal.png", "图 5-10 树莓派 5 平台普通文件带宽稳定性对比"),
    "fig_5_11_pi_stability_hole": ("imgs/pi/bandwidth_stability_hole.png", "图 5-11 树莓派 5 平台稀疏文件带宽稳定性对比"),
    "fig_5_12_pi_stability_com": ("imgs/pi/bandwidth_stability_com.png", "图 5-12 树莓派 5 平台压缩文件带宽稳定性对比"),
    "fig_5_13_qemu_cpu_normal": ("imgs/qemu/cpu_usage_normal.png", "图 5-13 QEMU 平台普通文件 CPU 利用率对比"),
    "fig_5_14_qemu_cpu_hole": ("imgs/qemu/cpu_usage_hole.png", "图 5-14 QEMU 平台稀疏文件 CPU 利用率对比"),
    "fig_5_15_qemu_cpu_com": ("imgs/qemu/cpu_usage_com.png", "图 5-15 QEMU 平台压缩文件 CPU 利用率对比"),
    "fig_5_16_pi_cpu_normal": ("imgs/pi/cpu_usage_normal.png", "图 5-16 树莓派 5 平台普通文件 CPU 利用率对比"),
    "fig_5_17_pi_cpu_hole": ("imgs/pi/cpu_usage_hole.png", "图 5-17 树莓派 5 平台稀疏文件 CPU 利用率对比"),
    "fig_5_18_pi_cpu_com": ("imgs/pi/cpu_usage_com.png", "图 5-18 树莓派 5 平台压缩文件 CPU 利用率对比"),
}


class PackageBuilder:
    def __init__(self, src_docx: Path):
        self.src_docx = src_docx
        self.entries: dict[str, bytes] = {}
        self.image_parts: dict[Path, tuple[str, str]] = {}
        self.next_image = 100
        self.next_rid = 100
        self.docpr_id = 100
        with zipfile.ZipFile(src_docx) as z:
            for info in z.infolist():
                self.entries[info.filename] = z.read(info.filename)
        self.root = ET.fromstring(self.entries["word/document.xml"])
        self.rels_root = ET.fromstring(self.entries["word/_rels/document.xml.rels"])
        self.ct_root = ET.fromstring(self.entries["[Content_Types].xml"])

    def next_rel_id(self) -> str:
        used = {
            rel.get("Id")
            for rel in self.rels_root.findall(f"{{{REL_NS}}}Relationship")
            if rel.get("Id")
        }
        while f"rId{self.next_rid}" in used:
            self.next_rid += 1
        rid = f"rId{self.next_rid}"
        self.next_rid += 1
        return rid

    def ensure_content_type(self, ext: str, content_type: str):
        for node in self.ct_root.findall(f"{{{CT_NS}}}Default"):
            if node.get("Extension") == ext:
                return
        self.ct_root.append(ET.Element(f"{{{CT_NS}}}Default", {"Extension": ext, "ContentType": content_type}))

    def add_image_relationship(self, image_path: Path) -> tuple[str, str]:
        image_path = image_path.resolve()
        if image_path in self.image_parts:
            return self.image_parts[image_path]
        ext = image_path.suffix.lower().lstrip(".")
        if ext == "jpg":
            ext = "jpeg"
        media_name = f"image_generated_{self.next_image}.{ext}"
        self.next_image += 1
        target = f"media/{media_name}"
        rid = self.next_rel_id()
        rel = ET.Element(
            f"{{{REL_NS}}}Relationship",
            {
                "Id": rid,
                "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
                "Target": target,
            },
        )
        self.rels_root.append(rel)
        self.entries[f"word/{target}"] = image_path.read_bytes()
        if ext == "png":
            self.ensure_content_type("png", "image/png")
        elif ext in ("jpeg", "jpg"):
            self.ensure_content_type("jpeg", "image/jpeg")
        self.image_parts[image_path] = (rid, target)
        return rid, target

    def write(self, out_docx: Path):
        ignorable_key = qn("mc", "Ignorable")
        if ignorable_key in self.root.attrib:
            # ElementTree drops unused namespace declarations. Keep Ignorable
            # aligned with the prefixes that remain declared in the serialized
            # document so strict OOXML readers do not reject the file.
            self.root.set(ignorable_key, "w14 wp14")
        self.entries["word/document.xml"] = ET.tostring(self.root, encoding="utf-8", xml_declaration=True)
        self.entries["word/_rels/document.xml.rels"] = ET.tostring(
            self.rels_root, encoding="utf-8", xml_declaration=True
        )
        # Keep the source [Content_Types].xml byte-for-byte. The reference
        # document already declares png/jpeg, and LibreOffice is stricter than
        # Word about this part's default namespace serialization.
        with zipfile.ZipFile(out_docx, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for name, data in self.entries.items():
                z.writestr(name, data)


def make_image_paragraph(pkg: PackageBuilder, path: Path, max_width_cm: float = 14.2) -> ET.Element:
    rid, _ = pkg.add_image_relationship(path)
    with Image.open(path) as img:
        px_w, px_h = img.size
    max_width_emu = int(max_width_cm / 2.54 * 914400)
    height_emu = int(max_width_emu * px_h / px_w)
    width_emu = max_width_emu
    pkg.docpr_id += 1
    p = make_paragraph("", kind="caption", align="center")
    r = el("w:r")
    drawing = el("w:drawing")
    inline = el("wp:inline")
    append(
        inline,
        el("wp:extent", {"cx": str(width_emu), "cy": str(height_emu)}),
        el("wp:effectExtent", {"l": "0", "t": "0", "r": "0", "b": "0"}),
        el("wp:docPr", {"id": str(pkg.docpr_id), "name": f"Picture {pkg.docpr_id}"}),
        el("wp:cNvGraphicFramePr"),
    )
    graphic = el("a:graphic")
    graphic_data = el("a:graphicData", {"uri": PIC_NS})
    pic = el("pic:pic")
    nv = el("pic:nvPicPr")
    append(nv, el("pic:cNvPr", {"id": "0", "name": path.name}), el("pic:cNvPicPr"))
    blip_fill = el("pic:blipFill")
    blip = el("a:blip", {qn("r", "embed"): rid})
    append(blip_fill, blip, el("a:stretch"))
    blip_fill.find("a:stretch", NS).append(el("a:fillRect"))
    sp_pr = el("pic:spPr")
    xfrm = el("a:xfrm")
    append(xfrm, el("a:off", {"x": "0", "y": "0"}), el("a:ext", {"cx": str(width_emu), "cy": str(height_emu)}))
    append(sp_pr, xfrm, el("a:prstGeom", {"prst": "rect"}))
    sp_pr.find("a:prstGeom", NS).append(el("a:avLst"))
    append(pic, nv, blip_fill, sp_pr)
    graphic_data.append(pic)
    graphic.append(graphic_data)
    inline.append(graphic)
    drawing.append(inline)
    r.append(drawing)
    p.append(r)
    return p


def make_table(rows: list[list[str]]) -> ET.Element:
    tbl = el("w:tbl")
    tbl_pr = el("w:tblPr")
    append(
        tbl_pr,
        el("w:tblStyle", {qn("w", "val"): "TableGrid"}),
        el("w:jc", {qn("w", "val"): "center"}),
        el(
            "w:tblBorders",
            {},
        ),
    )
    borders = tbl_pr.find("w:tblBorders", NS)
    for side in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        borders.append(el(f"w:{side}", {qn("w", "val"): "single", qn("w", "sz"): "4", qn("w", "color"): "000000"}))
    tbl.append(tbl_pr)
    for row in rows:
        tr = el("w:tr")
        for cell_text in row:
            tc = el("w:tc")
            tc_pr = el("w:tcPr")
            tc_pr.append(el("w:tcW", {qn("w", "w"): "4500", qn("w", "type"): "dxa"}))
            tc.append(tc_pr)
            tc.append(make_paragraph(cell_text.strip(), kind="caption", align="center"))
            tr.append(tc)
        tbl.append(tr)
    return tbl


def make_cover_paragraph(lines: list[str] | str, *, align: str) -> ET.Element:
    if isinstance(lines, str):
        lines = [lines]
    p = el("w:p")
    ppr = el("w:pPr")
    add_spacing(ppr, line="360")
    ppr.append(el("w:jc", {qn("w", "val"): align}))
    p.append(ppr)
    rpr = dict(size_half_pt=32, east_asia="宋体", ascii_font="Times New Roman", bold=False)
    for idx, text in enumerate(lines):
        if idx:
            br = el("w:r")
            br.append(el("w:br"))
            p.append(br)
        p.append(make_run(text, **rpr))
    return p


def make_cover_cell(
    lines: list[str] | str,
    *,
    width_twips: int,
    align: str,
    bottom_border: bool = False,
) -> ET.Element:
    tc = el("w:tc")
    tc_pr = el("w:tcPr")
    tc_pr.append(el("w:tcW", {qn("w", "w"): str(width_twips), qn("w", "type"): "dxa"}))
    tc_pr.append(el("w:vAlign", {qn("w", "val"): "center"}))
    borders = el("w:tcBorders")
    if bottom_border:
        borders.append(
            el(
                "w:bottom",
                {
                    qn("w", "val"): "single",
                    qn("w", "sz"): "4",
                    qn("w", "space"): "0",
                    qn("w", "color"): "000000",
                },
            )
        )
    else:
        for side in ["top", "left", "bottom", "right"]:
            borders.append(el(f"w:{side}", {qn("w", "val"): "nil"}))
    tc_pr.append(borders)
    tc.append(tc_pr)
    tc.append(make_cover_paragraph(lines, align=align))
    return tc


def make_cover_field_table() -> ET.Element:
    rows = [
        ("题    目：", ["面向F2FS文件系统的", "Large Folios机制研究与实现"]),
        ("专    业：", "人工智能"),
        ("班    级：", "智能2202"),
        ("姓    名：", "赵南哲"),
        ("指导老师：", "万夕里"),
        ("起讫日期：", "2026年3月5日至2026年6月10日"),
    ]
    label_w, value_w = 2200, 5400
    tbl = el("w:tbl")
    tbl_pr = el("w:tblPr")
    append(
        tbl_pr,
        el("w:tblW", {qn("w", "w"): "0", qn("w", "type"): "auto"}),
        el("w:jc", {qn("w", "val"): "center"}),
        el("w:tblLayout", {qn("w", "type"): "fixed"}),
    )
    borders = el("w:tblBorders")
    for side in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        borders.append(el(f"w:{side}", {qn("w", "val"): "nil"}))
    tbl_pr.append(borders)
    cell_mar = el("w:tblCellMar")
    for side, width in [("top", "0"), ("left", "108"), ("bottom", "0"), ("right", "108")]:
        cell_mar.append(el(f"w:{side}", {qn("w", "w"): width, qn("w", "type"): "dxa"}))
    tbl_pr.append(cell_mar)
    tbl.append(tbl_pr)

    grid = el("w:tblGrid")
    grid.append(el("w:gridCol", {qn("w", "w"): str(label_w)}))
    grid.append(el("w:gridCol", {qn("w", "w"): str(value_w)}))
    tbl.append(grid)

    for label, value in rows:
        tr = el("w:tr")
        tr_pr = el("w:trPr")
        tr_pr.append(el("w:trHeight", {qn("w", "val"): "560"}))
        tr.append(tr_pr)
        tr.append(make_cover_cell(label, width_twips=label_w, align="right"))
        tr.append(make_cover_cell(value, width_twips=value_w, align="center", bottom_border=True))
        tbl.append(tr)
    return tbl


def parse_markdown_table(lines: list[str], i: int) -> tuple[list[list[str]], int]:
    rows = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        line = lines[i].strip()
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not all(re.fullmatch(r":?-{2,}:?", c.replace(" ", "")) for c in cells):
            rows.append(cells)
        i += 1
    return rows, i


def extract_abstracts() -> tuple[list[str], str, list[str], str]:
    lines = (BASE / "F2FS_中英文摘要.md").read_text(encoding="utf-8").splitlines()
    cn, en = [], []
    mode = None
    cn_kw = en_kw = ""
    for raw in lines:
        s = raw.strip()
        if s == "## 摘 要":
            mode = "cn"
            continue
        if s == "## ABSTRACT":
            mode = "en"
            continue
        if not s or s.startswith("#"):
            continue
        if mode == "cn":
            if "关键词" in s:
                cn_kw = s.replace("**", "").replace("关键词：", "").replace("关键词:", "").strip()
            else:
                cn.append(s)
        elif mode == "en":
            if "KEYWORDS" in s.upper():
                en_kw = s.replace("**", "").replace("KEYWORDS:", "").replace("KEYWORDS：", "").strip()
            else:
                en.append(s)
    return cn, cn_kw, en, en_kw


def collect_original_acknowledgement(pkg: PackageBuilder) -> list[str]:
    body = pkg.root.find("w:body", NS)
    paragraphs = [c for c in body if c.tag == qn("w", "p")]
    texts = [paragraph_text(p).strip() for p in paragraphs]
    try:
        start = texts.index("致谢") + 1
    except ValueError:
        return ["感谢我的导师在操作系统方面的悉心教学以及选题方面的指导。"]
    out = []
    for text in texts[start:]:
        if text:
            out.append(text)
    return out or ["感谢我的导师在操作系统方面的悉心教学以及选题方面的指导。"]


def collect_cover(pkg: PackageBuilder) -> list[ET.Element]:
    body = pkg.root.find("w:body", NS)
    children = list(body)
    cover: list[ET.Element] = []
    inserted_field_table = False
    skip_prefixes = (
        "题    目：",
        "专    业：",
        "班    级：",
        "姓    名：",
        "指导老师：",
        "起讫日期：",
    )
    skip_exact = {
        "Large Folios机制研究与实现",
        "至2026年6月10日",
    }
    for child in children:
        txt = paragraph_text(child).strip() if child.tag == qn("w", "p") else ""
        if txt == "面向F2FS文件系统的Large Folios机制研究与实现":
            break
        if child.tag == qn("w", "p") and (txt.startswith(skip_prefixes) or txt in skip_exact):
            if not inserted_field_table and txt.startswith("题    目："):
                cover.append(make_cover_field_table())
                inserted_field_table = True
            continue
        cover.append(copy.deepcopy(child))
    return cover


def collect_originality_declaration() -> list[ET.Element]:
    if not REFERENCE_DOCX.exists():
        raise FileNotFoundError(f"reference docx not found: {REFERENCE_DOCX}")
    ref_pkg = PackageBuilder(REFERENCE_DOCX)
    body = ref_pkg.root.find("w:body", NS)
    children = list(body)
    start = None
    end = None
    for idx, child in enumerate(children):
        txt = paragraph_text(child).strip() if child.tag == qn("w", "p") else ""
        if txt == "南京工业大学本科毕业设计（论文）原创性声明":
            start = idx
            break
    if start is None:
        raise RuntimeError("originality declaration start not found in reference docx")
    for idx in range(start + 1, len(children)):
        txt = paragraph_text(children[idx]).strip() if children[idx].tag == qn("w", "p") else ""
        if txt == "基于激光雷达数据的深度学习短期风速预测算法设计":
            end = idx
            break
    if end is None:
        raise RuntimeError("originality declaration end not found in reference docx")
    out: list[ET.Element] = []
    blank_run = 0
    for child in children[start:end]:
        clone = copy.deepcopy(child)
        for parent in clone.iter():
            for sect_pr in list(parent.findall("w:sectPr", NS)):
                parent.remove(sect_pr)
        is_blank_para = clone.tag == qn("w", "p") and not paragraph_text(clone).strip()
        if is_blank_para:
            blank_run += 1
            if blank_run > 2:
                continue
        else:
            blank_run = 0
        out.append(clone)
    while out and out[-1].tag == qn("w", "p") and not paragraph_text(out[-1]).strip():
        out.pop()
    return out


def is_img_only(line: str) -> bool:
    return bool(re.fullmatch(r"\{\{IMG:[^}]+}}", line.strip()))


def insert_line_with_images(pkg: PackageBuilder, output: list[ET.Element], line: str):
    pos = 0
    for m in re.finditer(r"\{\{IMG:([^}]+)}}", line):
        before = line[pos : m.start()].strip()
        if before:
            output.append(make_paragraph(before, kind="body"))
        img_id = m.group(1)
        if img_id not in IMAGE_MAP:
            output.append(make_paragraph(f"【图片缺失：{img_id}】", kind="body"))
        else:
            rel, caption = IMAGE_MAP[img_id]
            path = BASE / rel
            if not path.exists():
                output.append(make_paragraph(f"【图片缺失：{rel}】", kind="body"))
            else:
                output.append(make_image_paragraph(pkg, path))
                output.append(make_paragraph(caption, kind="caption"))
        pos = m.end()
    rest = line[pos:].strip()
    if rest:
        output.append(make_paragraph(rest, kind="body"))


def md_to_body(pkg: PackageBuilder, paths: list[Path]) -> list[ET.Element]:
    out: list[ET.Element] = []
    for path in paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        i = 0
        pending_table_caption: str | None = None
        in_code = False
        code_lines: list[str] = []
        while i < len(lines):
            line = lines[i].rstrip()
            stripped = line.strip()
            if stripped.startswith("```"):
                if in_code:
                    if code_lines:
                        # Render fenced snippets as a compact field table, never as VS Code style.
                        rows = [["字段/代码片段"], *[[x] for x in code_lines]]
                        out.append(make_table(rows))
                    code_lines = []
                    in_code = False
                else:
                    in_code = True
                i += 1
                continue
            if in_code:
                if stripped:
                    code_lines.append(stripped)
                i += 1
                continue
            if not stripped:
                i += 1
                continue
            if stripped.startswith(">"):
                i += 1
                continue
            if stripped.startswith("# "):
                out.append(make_heading(stripped[2:].strip(), 1))
                i += 1
                continue
            if stripped.startswith("## "):
                out.append(make_heading(stripped[3:].strip(), 2))
                i += 1
                continue
            if stripped.startswith("### "):
                out.append(make_heading(stripped[4:].strip(), 3))
                i += 1
                continue
            # Some rewritten Markdown sections use bare numbered headings
            # such as "2.1 页缓存与页描述符" instead of "## ...".
            if re.fullmatch(r"\d+\.\d+\s+\S.{0,60}", stripped):
                out.append(make_heading(stripped, 2))
                i += 1
                continue
            if re.fullmatch(r"\d+\.\d+\.\d+\s+\S.{0,60}", stripped):
                out.append(make_heading(stripped, 3))
                i += 1
                continue
            if re.match(r"^表\s*\d+-\d+\s+", stripped) and not re.search(r"(与表|对比了|汇总|分别)", stripped):
                pending_table_caption = stripped
                i += 1
                continue
            if stripped.startswith("|"):
                rows, new_i = parse_markdown_table(lines, i)
                following_caption = None
                if (
                    new_i < len(lines)
                    and re.match(r"^表\s*\d+-\d+\s+", lines[new_i].strip())
                    and not re.search(r"(与表|对比了|汇总|分别)", lines[new_i].strip())
                ):
                    following_caption = lines[new_i].strip()
                    new_i += 1
                caption = pending_table_caption or following_caption
                if caption:
                    out.append(make_paragraph(caption, kind="caption"))
                    pending_table_caption = None
                out.append(make_table(rows))
                i = new_i
                continue
            if stripped.startswith("- "):
                text = stripped[2:].strip()
                out.append(make_paragraph(text, kind="body", left_twips=480, first_line_twips=0))
                i += 1
                continue
            alg_match = re.fullmatch(r"\{\{ALG:[^}]+}}", stripped)
            if alg_match:
                out.append(make_paragraph(stripped, kind="body", align="center", first_line_twips=0))
                i += 1
                continue
            if "{{IMG:" in stripped:
                insert_line_with_images(pkg, out, stripped)
                i += 1
                continue
            out.append(make_paragraph(stripped, kind="body"))
            i += 1
    return out


def add_reference_section(out: list[ET.Element]):
    out.append(make_page_break())
    out.append(make_heading("参考文献", 1))
    refs = [line.strip() for line in (BASE / "参考文献-V2.md").read_text(encoding="utf-8").splitlines() if line.strip()]
    for ref in refs:
        out.append(make_paragraph(ref, kind="reference", first_line_twips=0))


def add_acknowledgement_section(out: list[ET.Element], ack: list[str]):
    out.append(make_page_break())
    out.append(make_heading("致谢", 1))
    for text in ack:
        out.append(make_paragraph(text, kind="body"))


def add_conclusion(out: list[ET.Element]):
    out.append(make_page_break())
    out.append(make_heading("结语", 1))
    paragraphs = [
        "本文围绕 F2FS 在动态大页条件下的缓冲 I/O 适配问题展开研究。论文首先从移动端大文件访问、页缓存粒度、块层连续 I/O 能力和 F2FS 闪存友好机制出发，说明传统 4KB 页缓存粒度在现代连续 I/O 场景下面临的路径开销问题；随后结合 F2FS 的块映射、压缩簇、垃圾回收和私有状态管理机制，分析动态大页进入现有路径后引发的粒度失配、字段冲突和生命周期判定问题。",
        "在设计与实现方面，本文将 F2FS 的块级映射结果转换为 iomap 字节区间描述，构建统一的 F2FS 扩展型动态大页状态对象，并针对普通读写、脏页写回、压缩文件读写和 GC 搬移路径分别完成适配。该方案在保持 F2FS 顺序追加写入、压缩簇语义和后台回收语义的前提下，使动态大页能够进入完整的缓冲 I/O 关键路径，并通过逐块状态位图和 pending 计数避免整动态大页写放大和提前完成判断。",
        "实验结果表明，本文原型在 QEMU 和树莓派平台的大块顺序 I/O 场景中均能够提升吞吐能力，并降低部分小粒度页缓存管理和逐块 I/O 组织带来的 CPU 开销。后续工作可以继续围绕更复杂的混合随机负载、长期老化后的 GC 行为、不同页面大小配置以及 Android 真实应用负载展开验证，以进一步完善 F2FS 动态大页路径的稳定性和适用范围。",
    ]
    for text in paragraphs:
        out.append(make_paragraph(text, kind="body"))


def build_intermediate():
    pkg = PackageBuilder(SOURCE_DOCX)
    cover = collect_cover(pkg)
    declaration = collect_originality_declaration()
    ack = collect_original_acknowledgement(pkg)

    body = pkg.root.find("w:body", NS)
    old_children = list(body)
    sect_pr = None
    if old_children and old_children[-1].tag == qn("w", "sectPr"):
        sect_pr = copy.deepcopy(old_children[-1])
    for child in old_children:
        body.remove(child)

    new_children: list[ET.Element] = []
    new_children.extend(cover)
    new_children.extend(declaration)
    new_children.append(make_page_break())

    cn_abs, cn_kw, en_abs, en_kw = extract_abstracts()
    new_children.append(make_paragraph("面向F2FS文件系统的Large Folios机制研究与实现", kind="abstract_title"))
    new_children.append(make_heading("摘  要", 1))
    for para in cn_abs:
        new_children.append(make_paragraph(para, kind="body"))
    new_children.append(make_paragraph("关键词：" + cn_kw, kind="body", first_line_twips=0))
    new_children.append(make_page_break())

    new_children.append(
        make_paragraph(
            "Research and Implementation of the Large Folios Mechanism for the F2FS File System",
            kind="abstract_title",
        )
    )
    new_children.append(make_heading("ABSTRACT", 1))
    for para in en_abs:
        new_children.append(make_paragraph(para, kind="body"))
    new_children.append(make_paragraph("Key Words: " + en_kw, kind="body", first_line_twips=0))
    new_children.append(make_page_break())

    new_children.append(make_paragraph("目  录", kind="toc_title"))
    new_children.append(make_toc_field())
    new_children.append(make_page_break())

    chapter_files = [
        BASE / "第一二章重写稿.md",
        BASE / "第三章开头重写稿.md",
        BASE / "第四章重写稿.md",
        BASE / "第五章重写稿.md",
    ]
    new_children.extend(md_to_body(pkg, chapter_files))
    add_conclusion(new_children)
    add_reference_section(new_children)
    add_acknowledgement_section(new_children, ack)

    if sect_pr is not None:
        new_children.append(sect_pr)
    for child in new_children:
        body.append(child)

    pkg.write(INTERMEDIATE)
    print(f"[OK] wrote intermediate: {INTERMEDIATE.name}")


def main():
    build_intermediate()


if __name__ == "__main__":
    main()
