#!/usr/bin/env python3
from __future__ import annotations

import copy
import re
import sys
import zipfile
from pathlib import Path

from lxml import etree


NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
W = NS["w"]


def qn(tag: str) -> str:
    prefix, local = tag.split(":")
    return f"{{{NS[prefix]}}}{local}"


def text_of(el: etree._Element) -> str:
    return "".join(el.xpath(".//w:t/text()", namespaces=NS)).strip()


def style_of(el: etree._Element) -> str:
    if etree.QName(el).localname != "p":
        return ""
    pstyle = el.find("w:pPr/w:pStyle", NS)
    return pstyle.get(qn("w:val")) if pstyle is not None else ""


def clear_content_keep_ppr(p: etree._Element) -> None:
    for child in list(p):
        if etree.QName(child).localname != "pPr":
            p.remove(child)


def replace_para_text(p: etree._Element, text: str) -> etree._Element:
    p = copy.deepcopy(p)
    first_rpr = p.find(".//w:rPr", NS)
    clear_content_keep_ppr(p)
    r = etree.SubElement(p, qn("w:r"))
    if first_rpr is not None:
        r.append(copy.deepcopy(first_rpr))
    t = etree.SubElement(r, qn("w:t"))
    if text.startswith(" ") or text.endswith(" "):
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    return p


def clone(el: etree._Element) -> etree._Element:
    return copy.deepcopy(el)


def replace_text_in_paragraph(p: etree._Element, replacements: dict[str, str]) -> bool:
    old = text_of(p)
    new = old
    for src, dst in replacements.items():
        new = new.replace(src, dst)
    if new == old:
        return False
    new_p = replace_para_text(p, new)
    parent = p.getparent()
    parent.replace(p, new_p)
    return True


def replace_text_in_element_paragraphs(el: etree._Element, replacements: dict[str, str]) -> etree._Element:
    el = clone(el)
    if etree.QName(el).localname == "p":
        replace_text_in_paragraph(el, replacements)
    else:
        for p in el.xpath(".//w:p", namespaces=NS):
            replace_text_in_paragraph(p, replacements)
    return el


def find_body_index(body: etree._Element, predicate) -> int:
    for i, el in enumerate(body):
        if predicate(i, el):
            return i
    raise RuntimeError("body index not found")


def find_heading(body: etree._Element, startswith: str, style: str) -> int:
    return find_body_index(
        body,
        lambda _i, e: etree.QName(e).localname == "p"
        and style_of(e) == style
        and text_of(e).startswith(startswith),
    )


def find_para_text(body: etree._Element, startswith: str, start: int = 0) -> int:
    return find_body_index(
        body,
        lambda i, e: i >= start
        and etree.QName(e).localname == "p"
        and text_of(e).startswith(startswith),
    )


def find_caption(body: etree._Element, startswith: str, start: int = 0) -> int:
    return find_para_text(body, startswith, start)


def has_forbidden_sentence(text: str) -> bool:
    # User explicitly forbids the “不是...而是” sentence pattern.
    return re.search(r"不是[^。；\n]{0,80}而是", text) is not None


def main() -> int:
    src = Path(sys.argv[1])
    out = Path(sys.argv[2])
    ledger = Path(sys.argv[3])
    tmp = out.with_suffix(".tmp.docx")

    with zipfile.ZipFile(src) as zin:
        xml = zin.read("word/document.xml")
        all_files = {name: zin.read(name) for name in zin.namelist() if name != "word/document.xml"}

    root = etree.fromstring(xml)
    body = root.find("w:body", NS)
    if body is None:
        raise RuntimeError("word/document.xml has no w:body")

    h1 = find_heading(body, "第三章", "3")
    h5 = find_heading(body, "第五章", "3")

    # Templates are taken from the current document so section typography and spacing survive.
    tpl_h1 = body[h1]
    tpl_h2 = body[find_heading(body, "3.1", "4")]
    tpl_h3 = body[find_heading(body, "4.2.1", "5")]
    tpl_body = body[find_para_text(body, "前两章已经建立", h1)]
    tpl_caption = body[find_caption(body, "图 4-1", h1)]

    # Existing rich objects / tables / figures that should be reused.
    p_img_arch = body[find_para_text(body, "", h1) + 0]  # overwritten below
    p_img_arch = body[find_para_text(body, "", find_caption(body, "图 4-1", h1) - 1)]
    # The empty paragraph immediately before a caption is the image paragraph in this document.
    img_arch = body[find_caption(body, "图 4-1", h1) - 1]
    img_state = body[find_caption(body, "图 4-2", h1) - 1]
    img_private = body[find_caption(body, "图 4-3", h1) - 1]
    img_cross = body[find_caption(body, "图 4-4", h1) - 1]
    img_write = body[find_caption(body, "图 4-5", h1) - 1]
    img_pending = body[find_caption(body, "图 4-6", h1) - 1]
    img_wb = body[find_caption(body, "图 4-7", h1) - 1]

    tbl_state_struct = body[find_caption(body, "图 4-2", h1) - 4]
    if etree.QName(tbl_state_struct).localname != "tbl":
        raise RuntimeError("state struct table not found at expected position")

    tbl_problem_map = body[find_caption(body, "表 4-4", h1) + 1]
    if etree.QName(tbl_problem_map).localname != "tbl":
        raise RuntimeError("problem map table not found")

    # Algorithm/table blocks remain in Chapter 4.  We clone them from the original sequence.
    def block(start_text: str, end_before_text: str | None) -> list[etree._Element]:
        start = find_para_text(body, start_text, h1)
        if end_before_text is None:
            end = h5
        else:
            end = find_para_text(body, end_before_text, start + 1)
        return [clone(e) for e in body[start:end]]

    alg_41 = block("算法 4-1", "该函数在三种映射状态间")
    after_41 = block("该函数在三种映射状态间", "4.2.2")
    sec_422 = block("4.2.2", "4.2.3")
    sec_423 = block("4.2.3", "4.3 F2FS")
    alg_44_plus_private = block("结构体的核心分配函数", "4.4 压缩文件")
    sec_441_alg = block("iomap 开始回调", "4.4.2")
    sec_442_alg = block("算法 4-7", "4.5动态大页")
    sec_451_alg = block("本系统用 F2FS 单动态大页写回函数", "4.5.2")
    sec_452_impl = block("压缩文件的写回复用", "4.6 垃圾回收")
    sec_46_impl = block("子范围脏区标记", "4.7 本章小结")

    new: list[etree._Element] = []
    added: list[str] = []

    def H1(text: str) -> None:
        new.append(replace_para_text(tpl_h1, text))

    def H2(text: str) -> None:
        new.append(replace_para_text(tpl_h2, text))

    def H3(text: str) -> None:
        new.append(replace_para_text(tpl_h3, text))

    def P(text: str, add: bool = True) -> None:
        if has_forbidden_sentence(text):
            raise RuntimeError(f"forbidden sentence pattern in: {text}")
        new.append(replace_para_text(tpl_body, text))
        if add:
            added.append(text)

    def CAP(text: str, add: bool = False) -> None:
        new.append(replace_para_text(tpl_caption, text))
        if add:
            added.append(text)

    def E(el: etree._Element) -> None:
        new.append(clone(el))

    H1("第三章 F2FS 动态大页缓冲 I/O 方案设计")
    H2("3.1 设计目标与总体思路")
    P("前文已经说明，F2FS 原有缓冲 I/O 路径长期以 4KB 页缓存对象和 4KB 文件系统块为基本单位组织映射、提交与状态管理。动态大页扩大页缓存对象覆盖范围后，一个页缓存对象可能同时覆盖多个文件系统块，使原有页索引、逻辑块号、脏页状态和异步完成语义之间的对应关系发生变化。基于此，本文在不改变 F2FS 基本磁盘布局和通用页缓存框架的前提下，设计面向动态大页的缓冲 I/O 适配方案。")
    P("本章从方案设计角度展开，围绕区间化块映射、统一状态对象、子范围写回控制以及压缩文件与 GC 专属路径适配四个方面说明本文方案的总体思路。具体函数、算法和路径流程将在第四章展开。")
    P("本文方案需要满足以下目标：")
    P("（1）解除页缓存对象粒度与文件系统块粒度的直接绑定，使 F2FS 能够为动态大页返回连续字节区间映射；")
    P("（2）统一 F2FS 私有标志与 iomap 动态大页内部状态，避免 folio->private 字段在不同路径中被解释为不同语义；")
    P("（3）以子范围为单位记录 dirty、uptodate 与异步完成状态，避免局部修改扩大为整动态大页写回；")
    P("（4）保持 F2FS 压缩文件、GC 搬移等专属路径的原有语义，使普通前台 I/O 路径与后台维护路径共享一致的动态大页状态。")
    P("为便于说明，后文主要以 64KB 动态大页为例展开分析；该示例对应一个动态大页覆盖 16 个 4KB 文件系统块的情况。")

    H2("3.2 系统总体架构")
    P("本文设计的 F2FS 动态大页缓冲 I/O 方案以通用 iomap 框架为基础，在 F2FS 层提供区间映射、写入预分配和子范围写回等定制回调，并进一步适配 F2FS 的 GC 与压缩文件路径。方案整体由普通文件区间化读写、扩展型动态大页状态对象、子范围写回控制、压缩文件适配和 GC 路径适配五部分组成，如图 3-1 所示。")
    E(img_arch)
    CAP("图 3-1 F2FS 动态大页缓冲 I/O 总体架构")
    P("在普通文件路径中，缓冲读复用 iomap 预读框架，通过 F2FS 区间映射回调将块级映射结果转换为字节区间；缓冲写复用 iomap 缓冲写框架，通过区间预分配回调为连续写入范围预留空间；写回路径则在写回迭代框架内引入 F2FS 单动态大页写回函数，以子范围为单位提交实际脏区。上述路径共同依赖 F2FS 区间设置函数完成块映射到 iomap 区间的转换，并依赖 F2FS 扩展型动态大页状态对象保存逐块位图、F2FS 私有标志和异步完成计数。")
    P("在 F2FS 专属路径中，GC 搬移仍保留以单个逻辑块为目标的语义，但通过子范围 dirty 标记和块设备I/O请求偏移修正确保目标块定位到动态大页内部的正确子范围。压缩读路径复用 iomap 区间迭代器的外层推进逻辑，并以 F2FS 定制的压缩读页迭代器替换通用读迭代器中的 I/O 提交策略；压缩写路径复用缓冲写区间准备流程，在完整覆盖的中间簇上跳过旧数据读取。这样，普通文件路径、压缩文件路径和 GC 路径能够共享同一套区间映射与状态管理基础设施。")

    H2("3.3 普通文件区间化映射机制设计")
    P("F2FS 原有普通文件 I/O 路径默认页缓存对象与文件系统块大小一致，因此页缓存索引可以直接作为逻辑块号使用。动态大页引入后，一个页缓存对象覆盖多个连续逻辑块，原有逐块映射方式无法直接表达动态大页所需的连续区间。")
    P("因此，普通读写路径的核心设计目标是将原有以逻辑块为单位的映射查询，转换为面向文件字节范围的区间映射，使一次动态大页 I/O 能够覆盖多个连续逻辑块。")
    P("F2FS 的块映射接口以逻辑块号 m_lblk、物理块号 m_pblk 和连续块数 m_len 为单位返回映射结果，而 iomap 框架以文件字节偏移 offset、设备字节地址 addr 和字节长度 length 描述映射区间。动态大页覆盖多个块后，块映射结果必须统一转换为空洞、已映射、预分配、脏状态等 iomap 语义。")
    P("为此，本文将块映射到字节区间的转换逻辑收敛到统一的 F2FS 区间设置函数。该函数为缓冲读、缓冲写和直接 I/O 提供统一的区间描述，使不同路径不再分别解释 F2FS 块映射结果。")
    P("在连续块可合并的情况下，上层 iomap 回调可一次性请求动态大页覆盖的完整区间，由 F2FS 块映射函数合并物理和逻辑连续的相邻块，再统一转换为 iomap 字节区间。以 64KB 动态大页为例，原先需要围绕 16 个 4KB 块分别执行的映射查询，可以被合并为一次连续区间映射。")

    H2("3.4 扩展型动态大页状态对象设计")
    P("除映射粒度变化外，动态大页还要求页缓存对象能够同时表达整对象状态和内部子块状态。F2FS 原有 private 字段用法与 iomap 动态大页状态对象之间存在语义冲突，因此需要设计统一的状态对象。")
    P("每个页缓存对象预留 private 字段供文件系统使用。在传统 4KB 路径中，F2FS 直接利用该字段的低位保存 ONGOING_MIGRATION、ATOMIC_WRITE 等私有标志；iomap 缓冲 I/O 路径则通过同一字段挂接 iomap 动态大页状态对象，用逐块位图和 pending 计数记录动态大页内部状态。")
    P("若缺少统一对象，同一字段可能在不同路径中被分别解释为整数标志或状态对象指针，从而破坏跨路径状态语义，甚至导致错误解引用。因此，所有可能进入 iomap 路径的动态大页，不论阶数，都必须统一管理 F2FS 私有标志、iomap 位图状态和运行时计数。")
    P("在动态大页条件下，页缓存对象的状态需要拆成两个层次理解。动态大页级标志（PG_locked、PG_uptodate、PG_dirty、PG_writeback）仍然描述整个对象是否被锁定、是否就绪、是否脏或是否正在写回；动态大页内部的不同子块则可能分别处于 uptodate、dirty 或 I/O 未完成状态。")
    P("iomap 动态大页状态对象通过逐块位图记录内部子块是否 uptodate 或 dirty，并用 pending 字节计数汇总多个异步 I/O 完成事件。本文在此基础上设计 F2FS 扩展型动态大页状态对象：保留 iomap 状态对象头部布局，使通用 iomap 函数能够继续访问 state_lock、read_bytes_pending 和 write_bytes_pending，同时在柔性数组中扩展 F2FS 私有标志和压缩路径所需的脏 pending 计数。")
    E(tbl_state_struct)
    P("F2FS 扩展型动态大页状态对象与 iomap 动态大页状态对象的关系可以从内存布局和功能扩展两个维度理解。在内存布局上，前三个成员与 iomap 状态对象保持一致；在功能上，柔性数组在 iomap 逐块位图之后额外保存 F2FS 私有标志和未完成脏字节计数，从而为 GC、原子写和压缩写回提供统一状态承载位置。")
    P("由于动态大页的 private 字段可能指向原生 iomap 状态对象或 F2FS 扩展型状态对象，运行时需要识别对象类型。本文通过魔数识别扩展对象，并在必要时将已有 iomap 状态对象迁移为 F2FS 扩展型状态对象，如图 3-2 所示。")
    E(img_state)
    CAP("图 3-2 F2FS 扩展型动态大页状态对象布局")

    H2("3.5 子范围脏区与异步完成管理设计")
    P("传统 F2FS 写回路径中，页级 PG_dirty 标志、页缓存索引和文件系统逻辑块在 4KB 配置下保持一致。动态大页扩大页缓存对象后，该一致性不再成立：一个动态大页内部可能只有部分 4KB 子块被修改，也可能对应多个异步块设备I/O请求。因此，写回路径需要从整动态大页粒度转向子范围粒度。")
    P("若写回入口在清除整动态大页 PG_dirty 后缺少子块级 dirty 位图，系统将无法区分实际修改范围，局部 4KB 修改可能扩大为整个 64KB 动态大页写回。")
    P("若仍沿用逐页拆解后调用单页写回函数的方式，写回函数会反复使用动态大页起始索引作为块坐标，导致动态大页内部后续子块无法写入对应逻辑位置。")
    P("为解决上述问题，本文采用三项设计：第一，以逐块 dirty 位图记录动态大页内实际脏区，写回时只提交被修改的子范围；第二，以 writeback pending 计数器汇总多个异步块设备I/O请求完成事件，只有全部子范围完成后才结束动态大页 writeback 生命周期；第三，将重试逻辑下沉到子块级别，避免局部失败导致已提交子范围重复写回。")

    H2("3.6 压缩文件与 GC 路径适配策略")
    P("F2FS 压缩文件以簇为基本单位组织，每若干连续文件系统块组成一个压缩簇。动态大页可能覆盖多个压缩簇，也可能同时覆盖压缩区间与非压缩区间，因此压缩路径需要在簇语义和动态大页生命周期之间建立统一边界。")
    P("当一个动态大页覆盖多个压缩簇时，压缩路径不能继续按传统逐页方式独立加锁、提交和解锁，否则不同簇会共享同一个动态大页对象并破坏其完整生命周期。多个簇、多个块设备I/O请求和多个完成回调必须统一汇总后，才能结束动态大页的读写生命周期。")
    E(img_cross)
    CAP("图 3-3 压缩路径中动态大页跨簇子区间示意")
    P("压缩读路径由三部分组成：簇感知的 iomap 开始回调、多簇压缩读页迭代器，以及统一的完成计数机制。簇感知回调负责在动态大页对齐并跨越多个簇时一次性获取多个簇的物理块信息；压缩读页迭代器在 F2FS 层替换通用读迭代器内部的提交策略；完成计数机制将解压填充与直接磁盘读的完成事件汇总到同一动态大页状态对象中。")
    P("压缩写路径不以压缩簇为最高组织单位，而是以动态大页覆盖范围为入口，将覆盖范围划分为 head、middle、tail 三类簇区间：首尾部分簇需要读取旧数据以保留未覆盖内容，中间完整簇可直接标记为就绪并跳过旧数据读取。")
    P("压缩写回仍尊重簇级提交边界。本文在 dirty 范围扫描时将写回区间截断到当前压缩簇末尾，并通过未完成脏字节计数延迟解锁动态大页，避免单个簇完成后提前释放整个动态大页。")
    P("GC 路径以单个逻辑块为搬移对象，而动态大页可能覆盖多个逻辑块。因此，GC 适配需要保留单块搬移语义，并在动态大页内部定位目标子范围。")
    P("本文在 GC 路径中采用三项适配策略：首先，后台搬移只将目标逻辑块对应的 4KB 子范围标记为 dirty；其次，GC 私有标志通过扩展型状态对象保存，避免重新占用 folio->private 字段；最后，在读写块设备I/O请求构建时显式计算子页在动态大页内的相对偏移，保证 I/O 请求只覆盖目标子块。")

    H2("3.7 本章小结")
    P("本章给出了 F2FS 动态大页缓冲 I/O 的总体方案。围绕动态大页进入 F2FS 后引发的映射粒度、状态承载、写回范围、压缩簇边界和 GC 子块定位问题，本文分别设计了区间化映射、扩展型动态大页状态对象、子范围写回、压缩文件适配和 GC 路径适配机制。")
    P("各问题约束与设计机制之间的对应关系如表 3-1 所示。")
    CAP("表 3-1 问题约束与设计机制对应")
    tbl_problem_map_new = replace_text_in_element_paragraphs(
        tbl_problem_map,
        {
            "4.2.1": "4.1.1",
            "4.2.2": "4.1.2",
            "4.2.3": "4.1.3",
            "4.3": "4.2",
            "4.4.1": "4.3.1",
            "4.4.2": "4.3.2",
            "4.5.1": "4.4.1",
            "4.5.2": "4.4.2",
            "4.6": "4.5",
        },
    )
    E(tbl_problem_map_new)
    P("这些机制共享两项基础设施：F2FS 区间设置函数提供块到区间的统一转换，F2FS 扩展型动态大页状态对象提供跨路径的统一状态管理。第四章将在此基础上说明各机制在 F2FS 具体函数、算法和路径中的落地方式。")

    H1("第四章 F2FS 动态大页缓冲 I/O 关键路径实现")
    P("第三章已经给出 F2FS 动态大页缓冲 I/O 的总体方案。本章进一步围绕普通文件读写、状态对象、压缩文件读写、子范围写回和 GC 搬移五条关键路径，说明各机制在 F2FS 中的具体实现方式。")

    H2("4.1 普通文件区间化读写实现")
    H3("4.1.1 块映射到 iomap 区间的转换实现")
    P("第三章 3.3 节已经说明区间化映射机制的设计目标。本节进一步给出 F2FS 区间设置函数的具体转换规则和边界处理。")
    for e in alg_41 + after_41:
        new.append(e)

    # Renumber section headings and cross references in cloned implementation material.
    for e in sec_422:
        if etree.QName(e).localname == "p" and text_of(e).startswith("4.2.2"):
            new.append(replace_para_text(tpl_h3, "4.1.2 普通文件缓冲读回调实现"))
        else:
            new.append(e)
    for e in sec_423:
        if etree.QName(e).localname == "p" and text_of(e).startswith("4.2.3"):
            new.append(replace_para_text(tpl_h3, "4.1.3 普通文件缓冲写回调实现"))
        else:
            new.append(e)

    H2("4.2 扩展型动态大页状态对象实现")
    P("第三章 3.4 节已经给出扩展型动态大页状态对象的设计。本节保留实现层内容，重点说明对象分配、迁移、私有标志宏族和 private 字段兼容策略。")
    for e in alg_44_plus_private:
        txt = text_of(e)
        if txt.startswith("图 4-3"):
            new.append(replace_para_text(tpl_caption, "图 4-1 F2FS private 字段兼容策略"))
        elif txt == "":
            # keep image paragraph before private-field compatibility caption only
            new.append(e)
        else:
            new.append(e)

    H2("4.3 压缩文件动态大页读写实现")
    H3("4.3.1 压缩文件缓冲读实现")
    P("第三章 3.6 节已经给出压缩文件路径的适配策略。本节首先说明压缩读的多簇映射、定制迭代器和完成计数实现。")
    for e in sec_441_alg:
        txt = text_of(e)
        if txt.startswith("iomap 开始回调"):
            new.append(e)
        else:
            new.append(e)

    H3("4.3.2 压缩文件缓冲写实现")
    P("压缩文件缓冲写实现围绕动态大页视角展开，核心在于 head、middle、tail 三类簇区间的旧数据准备和就绪标记。")
    E(img_write)
    CAP("图 4-2 压缩文件缓冲写的 head/middle/tail 簇处理")
    for e in sec_442_alg:
        txt = text_of(e)
        if txt.startswith("图 4-5"):
            continue
        if txt == "" and e.xpath(".//a:blip", namespaces=NS):
            # skip cloned old figure 4-5 image; already inserted and renumbered.
            continue
        if txt.startswith("图 4-6"):
            new.append(replace_para_text(tpl_caption, "图 4-3 未完成读字节计数的偏置等待机制"))
        else:
            new.append(e)

    H2("4.4 动态大页子范围写回实现")
    H3("4.4.1 普通文件子范围写回实现")
    P("第三章 3.5 节已经给出子范围脏区和异步完成管理设计。本节说明普通文件写回路径如何按字节范围定位脏子块、提交块设备I/O请求并处理完成计数。")
    E(img_wb)
    CAP("图 4-4 动态大页脏区间写回路径")
    for e in sec_451_alg:
        txt = text_of(e)
        if txt.startswith("图 4-7"):
            continue
        if txt == "" and e.xpath(".//a:blip", namespaces=NS):
            continue
        else:
            new.append(e)

    H3("4.4.2 压缩文件写回与延迟解锁实现")
    for e in sec_452_impl:
        new.append(e)

    H2("4.5 GC 路径动态大页适配实现")
    P("第三章 3.6 节已经给出 GC 保留单块搬移语义的适配策略。本节说明 GC 路径中的子范围脏标记、私有标志写入和块设备I/O请求偏移修正。")
    for e in sec_46_impl:
        new.append(e)

    H2("4.6 本章小结")
    P("本章围绕第三章提出的设计机制，说明了 F2FS 动态大页缓冲 I/O 在关键路径中的实现方式。普通文件路径通过 F2FS 区间设置函数和缓冲读写回调完成块映射到 iomap 区间的转换；状态对象实现通过分配、迁移和宏族兼容解决 private 字段冲突；压缩文件路径通过多簇读迭代、动态大页视角写准备和延迟解锁保持簇语义；写回和 GC 路径则通过子范围 dirty 位图、pending 计数和块设备I/O请求偏移修正保证动态大页内部子块被精确处理。")
    P("这些实现共同保证普通前台 I/O、压缩文件 I/O、写回和 GC 搬移路径共享同一套区间映射与状态管理基础设施，避免不同路径各自维护独立的动态大页语义。")

    # Replace old chapter 3 and 4 range.
    for el in list(body)[h1:h5]:
        body.remove(el)
    insert_at = h1
    for el in new:
        body.insert(insert_at, el)
        insert_at += 1

    # Update first chapter organization paragraphs.
    for el in list(body):
        if etree.QName(el).localname != "p":
            continue
        txt = text_of(el)
        if txt.startswith("第三章分析 F2FS 支持动态大页"):
            repl = "第三章介绍 F2FS 动态大页缓冲 I/O 方案设计，从设计目标、总体架构、区间化映射、统一状态对象、子范围写回以及压缩文件与 GC 路径适配等方面，说明本文方案的机制组成。"
            el.getparent().replace(el, replace_para_text(tpl_body, repl))
            added.append(repl)

    # Remove the forbidden “不是...而是” construction that already existed in earlier chapters.
    global_replacements = {
        "因此，本文面临的核心挑战并不是单独使用动态大页或单独接入 iomap，而是如何在 F2FS 的普通读写、脏页写回、垃圾回收和压缩文件路径中，同时解决缓存粒度扩大、区间映射转换和私有状态兼容三个问题。":
            "因此，本文的核心挑战集中在 F2FS 的普通读写、脏页写回、垃圾回收和压缩文件路径中，需要同时解决缓存粒度扩大、区间映射转换和私有状态兼容三个问题。",
        "阶数不是预设的，而是在运行时决定的。":
            "阶数由运行时状态决定。",
        "上述三种机制——异地更新、GC 和压缩文件——共同决定了 F2FS 不是一条简单的\"读块→写块\"直线，而是普通读写、后台搬移和压缩数据处理三个路径相互交叉的网络。这为后文讨论动态大页适配的复杂性提供了必要的背景。":
            "上述三种机制——异地更新、GC 和压缩文件——共同决定了 F2FS 呈现出超出简单\"读块→写块\"流程的路径结构，普通读写、后台搬移和压缩数据处理三个路径相互交叉。这为后文讨论动态大页适配的复杂性提供了必要的背景。",
        "第四章介绍 F2FS动态大页缓冲 I/O 的设计与实现，重点说明普通文件区间映射、统一状态管理、脏页写回控制、GC 路径适配以及压缩文件场景扩展的具体方案。":
            "第四章介绍 F2FS 动态大页缓冲 I/O 的关键路径实现，重点说明普通文件读写回调、扩展型状态对象分配与迁移、压缩文件读写、动态大页子范围写回和 GC 搬移适配的具体实现。",
        "通过 4.2.1 节的 F2FS 区间设置函数":
            "通过 4.1.1 节的 F2FS 区间设置函数",
        "后续 4.5 节的子范围写回控制":
            "后续 4.4 节的子范围写回控制",
        "由 4.2.3 节的 iomap 设置范围脏函数":
            "由 4.1.3 节的 iomap 设置范围脏函数",
        "这意味着 4.5 节的 F2FS 单动态大页写回函数":
            "这意味着 4.4 节的 F2FS 单动态大页写回函数",
        "通过 4.3 节 F2FS 扩展型动态大页状态对象":
            "通过 4.2 节 F2FS 扩展型动态大页状态对象",
    }
    for p in root.xpath(".//w:p", namespaces=NS):
        old = text_of(p)
        if any(k in old for k in global_replacements):
            replace_text_in_paragraph(p, global_replacements)
            added.append(text_of(p))
        elif txt.startswith("第四章介绍 F2FS动态大页缓冲 I/O 的设计与实现"):
            repl = "第四章介绍 F2FS 动态大页缓冲 I/O 的关键路径实现，重点说明普通文件读写回调、扩展型状态对象分配与迁移、压缩文件读写、动态大页子范围写回和 GC 搬移适配的具体实现。"
            el.getparent().replace(el, replace_para_text(tpl_body, repl))
            added.append(repl)

    full_text = text_of(root)
    if has_forbidden_sentence(full_text):
        raise RuntimeError("output still contains forbidden “不是...而是” sentence pattern")

    out_xml = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone="yes")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for name, data in all_files.items():
            zout.writestr(name, data)
        zout.writestr("word/document.xml", out_xml)
    tmp.replace(out)

    ledger.write_text(
        "# 第三、第四章重构新增/改写片段记录\n\n"
        f"- 源文件：`{src.name}`\n"
        f"- 输出文件：`{out.name}`\n"
        "- 原则：优先搬移和压缩旧文案；伪代码/算法表保留在第四章；第三章不搬入算法块。\n"
        "- 说明：下列条目为本脚本新写或明显改写的句段，供人工审查。\n\n"
        + "\n".join(f"{i+1}. {s}" for i, s in enumerate(added))
        + "\n",
        encoding="utf-8",
    )
    print(out)
    print(ledger)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
