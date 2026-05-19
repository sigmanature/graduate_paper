您的建议非常切中肯綮。

1.  **关于 3.2 的合并**：完全同意。崩溃（Crash）是冲突（Conflict）的直接后果，合并后逻辑链条更完整。为了保持章节平衡（通常一个二级标题下至少有两个三级标题），我从 PDF 的 2.2.5 节提取了另一个关键数据结构问题——`f2fs_io_info` 的粒度问题（原结构无法描述 Large Folio 中的子区域），作为新的 3.2.2。
2.  **关于 4.3.2 的标题**：已根据您的建议，强调了“混合路径”和“记账”的概念。
3.  **关于页码字体**：已在代码中将所有页码字体强制修正为 **“宋体”**。

以下是调整后的 **Markdown 目录**、**Python 代码数据** 以及 **详细写作提纲**。

---

### 1. 调整后的目录结构 (Markdown)

```markdown
# 目录

## 摘要 (Abstract)

## 第一章 研究背景
1.1 内存管理机制的演进
    1.1.1 页表与 TLB 的工作原理
    1.1.2 struct page 与 LRU 链表管理
1.2 Linux 文件系统 I/O 栈概述
    1.2.1 Page Cache 与 VFS 层交互
    1.2.2 传统 Buffer Head 映射机制及其局限性
1.3 F2FS 文件系统架构
    1.3.1 日志结构文件系统 (LFS) 特性
    1.3.2 F2FS 的数据布局与索引机制

## 第二章 引入 Folio 和 iomap 的意义
2.1 Struct Folio：新一代内存管理单元
    2.1.1 复合页 (Compound Page) 的痛点
    2.1.2 Folio 在内核中的演进现状与趋势
2.2 iomap 框架：现代化的 I/O 路径
    2.2.1 iomap 数据结构与接口定义
    2.2.2 迭代器模式与区间映射优势

## 第三章 F2FS 支持 Large Folios 的核心难点
3.1 块映射与 I/O 提交的粒度失配
    3.1.1 逐页处理带来的 CPU 开销
    3.1.2 传统 bio 提交机制的并发缺陷
3.2 关键数据结构的冲突与兼容
    3.2.1 folio->private 字段的资源争夺与语义混淆
    3.2.2 I/O 描述符 (f2fs_io_info) 的粒度限制
3.3 压缩文件场景下的复杂性
    3.3.1 压缩簇与 Folio 边界的不对齐
    3.3.2 混合 I/O 模型（压缩与非压缩混排）
3.4 脏页回写中的写放大风险
    3.4.1 粗粒度脏页标记的弊端
    3.4.2 垃圾回收 (GC) 过程中的数据迁移挑战

## 第四章 方案设计与算法实现
4.1 基于 iomap 的 Buffered I/O 重构
    4.1.1 读路径：iomap_readahead 的适配
    4.1.2 写路径：iomap_file_buffered_write 的集成
4.2 核心数据结构创新：f2fs_iomap_folio_state
    4.2.1 结构体设计：魔数 (Magic Number) 与柔性数组
    4.2.2 智能分发的私有数据访问 API
4.3 压缩文件的大页读写算法
    4.3.1 “大 Folio 优先”的分配策略
    4.3.2 混合 I/O 路径下的字节级记账与同步
    4.3.3 延迟解锁与并发一致性保证
4.4 脏页回写与垃圾回收的精确化改造
    4.4.1 逐块脏页追踪 (Per-block Dirty Tracking)
    4.4.2 修复双重解锁与空悬 Folio 问题

## 第五章 性能测试与分析
5.1 测试环境与方法论
5.2 QEMU 虚拟机环境测试结果
5.3 树莓派 5 (16KB Page) 环境测试结果
5.4 性能收益总结

## 结语
## 参考文献
## 致谢
```

---

### 2. Python 代码变量 (`toc_data`)

请直接替换原脚本中的 `toc_data` 列表。所有页码字体已改为 `'宋体'`。

```python
    # >>> 数据配置区：在这里修改或添加章节 <<<
    # 常用字号常量
    S_4   = Pt(14) # 四号
    S_X4  = Pt(12) # 小四

    # 数据列表：每一行代表目录的一条
    # 格式：(标题, 页码, 层级, 标题字体, 标题字号, 页码字体)
    # 注意：所有页码字体(pg_fn)均已设置为 '宋体'

    toc_data = [
        # 摘要：黑体 四号，页码 I (宋体)
        {"txt": "摘要", "pg": "I", "lvl": 0, "fn": "黑体", "fs": S_4, "pg_fn": "宋体"},

        # ABSTRACT：Times New Roman 四号，页码 II (宋体)
        {"txt": "ABSTRACT", "pg": "II", "lvl": 0, "fn": "Times New Roman", "fs": S_4, "pg_fn": "宋体"},

        # 第一章
        {"txt": "第一章 研究背景", "pg": "1", "lvl": 0, "fn": "黑体", "fs": S_4, "pg_fn": "宋体"},

        {"txt": "1.1 内存管理机制的演进", "pg": "1", "lvl": 1, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "1.1.1 页表与 TLB 的工作原理", "pg": "1", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "1.1.2 struct page 与 LRU 链表管理", "pg": "2", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},

        {"txt": "1.2 Linux 文件系统 I/O 栈概述", "pg": "3", "lvl": 1, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "1.2.1 Page Cache 与 VFS 层交互", "pg": "3", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "1.2.2 传统 Buffer Head 映射机制及其局限性", "pg": "4", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},

        {"txt": "1.3 F2FS 文件系统架构", "pg": "5", "lvl": 1, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "1.3.1 日志结构文件系统 (LFS) 特性", "pg": "5", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "1.3.2 F2FS 的数据布局与索引机制", "pg": "6", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},

        # 第二章
        {"txt": "第二章 引入 Folio 和 iomap 的意义", "pg": "8", "lvl": 0, "fn": "黑体", "fs": S_4, "pg_fn": "宋体"},

        {"txt": "2.1 Struct Folio：新一代内存管理单元", "pg": "8", "lvl": 1, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "2.1.1 复合页 (Compound Page) 的痛点", "pg": "8", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "2.1.2 Folio 在内核中的演进现状与趋势", "pg": "9", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},

        {"txt": "2.2 iomap 框架：现代化的 I/O 路径", "pg": "10", "lvl": 1, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "2.2.1 iomap 数据结构与接口定义", "pg": "10", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "2.2.2 迭代器模式与区间映射优势", "pg": "11", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},

        # 第三章
        {"txt": "第三章 F2FS 支持 Large Folios 的核心难点", "pg": "15", "lvl": 0, "fn": "黑体", "fs": S_4, "pg_fn": "宋体"},

        {"txt": "3.1 块映射与 I/O 提交的粒度失配", "pg": "15", "lvl": 1, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "3.1.1 逐页处理带来的 CPU 开销", "pg": "15", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "3.1.2 传统 bio 提交机制的并发缺陷", "pg": "16", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},

        {"txt": "3.2 关键数据结构的冲突与兼容", "pg": "17", "lvl": 1, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "3.2.1 folio->private 字段的资源争夺与语义混淆", "pg": "17", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "3.2.2 I/O 描述符 (f2fs_io_info) 的粒度限制", "pg": "18", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},

        {"txt": "3.3 压缩文件场景下的复杂性", "pg": "19", "lvl": 1, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "3.3.1 压缩簇与 Folio 边界的不对齐", "pg": "19", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "3.3.2 混合 I/O 模型（压缩与非压缩混排）", "pg": "20", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},

        {"txt": "3.4 脏页回写中的写放大风险", "pg": "21", "lvl": 1, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "3.4.1 粗粒度脏页标记的弊端", "pg": "21", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "3.4.2 垃圾回收 (GC) 过程中的数据迁移挑战", "pg": "22", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},

        # 第四章
        {"txt": "第四章 方案设计与算法实现", "pg": "24", "lvl": 0, "fn": "黑体", "fs": S_4, "pg_fn": "宋体"},

        {"txt": "4.1 基于 iomap 的 Buffered I/O 重构", "pg": "24", "lvl": 1, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "4.1.1 读路径：iomap_readahead 的适配", "pg": "25", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "4.1.2 写路径：iomap_file_buffered_write 的集成", "pg": "27", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},

        {"txt": "4.2 核心数据结构创新：f2fs_iomap_folio_state", "pg": "30", "lvl": 1, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "4.2.1 结构体设计：魔数 (Magic Number) 与柔性数组", "pg": "30", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "4.2.2 智能分发的私有数据访问 API", "pg": "32", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},

        {"txt": "4.3 压缩文件的大页读写算法", "pg": "35", "lvl": 1, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "4.3.1 “大 Folio 优先”的分配策略", "pg": "35", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "4.3.2 混合 I/O 路径下的字节级记账与同步", "pg": "37", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "4.3.3 延迟解锁与并发一致性保证", "pg": "39", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},

        {"txt": "4.4 脏页回写与垃圾回收的精确化改造", "pg": "42", "lvl": 1, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "4.4.1 逐块脏页追踪 (Per-block Dirty Tracking)", "pg": "42", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
            {"txt": "4.4.2 修复双重解锁与空悬 Folio 问题", "pg": "44", "lvl": 2, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},

        # 第五章
        {"txt": "第五章 性能测试与分析", "pg": "45", "lvl": 0, "fn": "黑体", "fs": S_4, "pg_fn": "宋体"},
        {"txt": "5.1 测试环境与方法论", "pg": "45", "lvl": 1, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
        {"txt": "5.2 QEMU 虚拟机环境测试结果", "pg": "47", "lvl": 1, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
        {"txt": "5.3 树莓派 5 (16KB Page) 环境测试结果", "pg": "49", "lvl": 1, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},
        {"txt": "5.4 性能收益总结", "pg": "52", "lvl": 1, "fn": "宋体", "fs": S_X4, "pg_fn": "宋体"},

        # 结尾
        {"txt": "结语", "pg": "55", "lvl": 0, "fn": "黑体", "fs": S_4, "pg_fn": "宋体"},
        {"txt": "参考文献", "pg": "56", "lvl": 0, "fn": "黑体", "fs": S_4, "pg_fn": "宋体"},
        {"txt": "致谢", "pg": "57", "lvl": 0, "fn": "黑体", "fs": S_4, "pg_fn": "宋体"},
    ]
```

---

### 3. 详细内容提纲 (Content Outline)

这是基于您的 PDF 和目录结构拆解的详细写作点，您可以直接用作正文生成的输入。

#### 第一章 研究背景
*   **1.1 内存管理机制的演进**
    *   **1.1.1 页表与 TLB 的工作原理**：简述 CPU 如何通过页表将虚拟地址转换为物理地址，TLB (Translation Lookaside Buffer) 在其中的加速作用，以及 4KB 小页面在现代大内存场景下导致的 TLB Miss 开销。
    *   **1.1.2 struct page 与 LRU 链表管理**：介绍 Linux 内核使用 `struct page` 管理物理内存，以及 LRU (Least Recently Used) 链表在内存回收中的作用。指出海量 4KB 页面带来的元数据开销（`mem_map` 占用）和链表扫描压力。
*   **1.2 Linux 文件系统 I/O 栈概述**
    *   **1.2.1 Page Cache 与 VFS 层交互**：描述 VFS（虚拟文件系统）如何通过 Page Cache 缓存文件数据，以及 `address_space` 和 `radix tree` (或 xarray) 的作用。还必须说出vfs中vfs_read,vfs_write一直到具体文件系统file_operation中调用read,write_iter函数这个调用过程。以及filemap中的readahead预读算法。
    *   **1.2.2 传统 Buffer Head 映射机制及其局限性**：分析旧的 `buffer_head` 机制在处理大文件时，需要为每个 4KB 块创建元数据，导致内存占用高、链表操作繁琐，以及到bio层的提交十分频繁和繁琐,无法高效支持大块连续 I/O。
*   **1.3 F2FS 文件系统架构**
    *   **1.3.1 日志结构文件系统 (LFS) 特性**：介绍 F2FS 的异地更新（Out-of-place Update）策略，如何将随机写转换为顺序写，以及 Segment/Section/Zone 的磁盘布局。
    *   **1.3.2 F2FS 的数据布局与索引机制**：简述 Node Address Table (NAT)、Site Address Table (SIT) 以及多级索引结构，为后文的块映射优化做铺垫。

#### 第二章 引入 Folio 和 iomap 的意义
*   **2.1 Struct Folio：新一代内存管理单元**
    *   **2.1.1 复合页 (Compound Page) 的痛点**：分析旧内核中 Compound Page 的歧义性（Head page vs Tail page），导致 API 使用混乱，容易引发 Bug。
    *   **2.1.2 Folio 在内核中的演进现状与趋势**：介绍 Matthew Wilcox 引入 Folio 的目标（类型安全、API 统一）。引用内核 5.15+ 的变化，说明 Folio 如何通过批量操作减少 LRU 锁竞争和 TLB Miss。
*   **2.2 iomap 框架：现代化的 I/O 路径**
    *   **2.2.1 iomap 数据结构与接口定义**：解析 `struct iomap` 结构体（addr, length, type），说明它如何用一个结构体描述一段连续的物理磁盘空间。
    *   **2.2.2 迭代器模式与区间映射优势**：重点比较 `iomap_iter` 与传统 `get_block` 的区别。iomap 支持一次映射极大范围（Extent），天然契合 Large Folio 的需求，避免了逐页映射的 CPU 开销。

#### 第三章 F2FS 支持 Large Folios 的核心难点
*   **3.1 块映射与 I/O 提交的粒度失配**
    *   **3.1.1 逐页处理带来的 CPU 开销**：分析 F2FS 原生代码（如 `f2fs_read_single_page`,`f2fs_write_begin`）硬编码了 4KB 处理逻辑，导致处理大 Folio 时需要循环调用多次，(但是注意一点是f2fs_get_dnode_of_data是只调用了一次)浪费 CPU。
    *   **3.1.2 传统 bio 提交机制的并发缺陷**：指出如果将一个大 Folio 拆分成多个 BIO 提交，缺乏统一的完成通知机制，可能导致部分数据未就绪时 Folio 就被解锁。
*   **3.2 关键数据结构的冲突与兼容**
    *   **3.2.1 folio->private 字段的资源争夺与语义混淆**：
        *   **冲突**：F2FS 需要用 `private` 存私有标志（如原子写、GC 迁移），iomap 需要用它存 `iomap_folio_state` 指针。
        *   **崩溃**：详细描述 0 阶 Folio 在 GC 时设置了标志位（小整数），却被 iomap 误判为指针导致内核 Panic 的场景（PDF 3.3.2）。
    *   **3.2.2 I/O 描述符 (f2fs_io_info) 的粒度限制**：指出原有的 `f2fs_io_info` 结构体只有一个 `page` 指针，无法表达“这是大 Folio 中的第 N 个子页”这一语义，导致底层驱动无法正确计算偏移量（PDF 2.2.5）。
*   **3.3 压缩文件场景下的复杂性**
    *   **3.3.1 压缩簇与 Folio 边界的不对齐**：说明 F2FS 压缩簇通常是 16KB（4页），而 Folio 大小是动态的。可能出现 Folio 覆盖多个簇，或者只覆盖簇的一部分，导致映射逻辑极其复杂。
    *   **3.3.2 混合 I/O 模型（压缩与非压缩混排）**：分析一个大 Folio 可能一部分是压缩数据（需要解压），一部分是未压缩数据（直接读取）。这两条路径是都需要
*   **3.4 脏页回写中的写放大风险**
    *   **3.4.1 粗粒度脏页标记的弊端**：解释如果仅修改了大 Folio 中的一小部分，传统机制会将整个 Folio 标脏回写，导致严重的写放大（Write Amplification）。
    *   **3.4.2 垃圾回收 (GC) 过程中的数据迁移挑战**：GC 需要搬运有效数据块。如果不能识别大 Folio 中的具体脏块，GC 可能会错误地回写整个大页，或者在搬运过程中发生双重解锁（Double Unlock）问题。

#### 第四章 方案设计与算法实现
*   **4.1 基于 iomap 的 Buffered I/O 重构**
    *   **4.1.1 读路径：iomap_readahead 的适配**：
        *   实现 `f2fs_buffered_read_iomap_begin`。
        *   利用 F2FS 的 `extent_cache` 快速返回大段映射，避免读取 dnode。
        *   代码实现细节：`f2fs_map_blocks` 对 `F2FS_GET_BLOCK_IOMAP` 标志的支持。
    *   **4.1.2 写路径：iomap_file_buffered_write 的集成**：
        *   实现 `f2fs_buffered_write_iomap_begin`。
        *   支持 `NEW_ADDR` 的区间合并，实现一次性预分配多个块，减少元数据操作。
*   **4.2 核心数据结构创新：f2fs_iomap_folio_state**
    *   **4.2.1 结构体设计：魔数 (Magic Number) 与柔性数组**
        *   设计 `struct f2fs_iomap_folio_state`，头部兼容 `iomap_folio_state`。
        *   利用 C 语言柔性数组（Flexible Array）在尾部扩展 F2FS 私有域。
        *   **类型识别**：在 `read_bytes_pending` 字段中写入 `F2FS_IFS_MAGIC`，用于运行时动态区分标准 iomap 结构与 F2FS 扩展结构。
    *   **4.2.2 智能分发的私有数据访问 API (F2FS_FOLIO_PRIVATE_SET_FUNC)**
        *   **安全判决核心**：引入 `f2fs_should_use_buffered_iomap` 函数。检测 Inode 类型（是否为常规文件、非加密、非 Verity 等），决定是否强制启用 iomap 兼容模式 (`force_alloc`)。
        *   **强制分配策略 (Force Alloc)**：若 `force_alloc` 为真，**即使是 0 阶 Folio**，也强制分配 `f2fs_iomap_folio_state`。这是为了防止 GC 等后台线程设置的标志位被前台 `iomap_file_buffered_write` 误判为指针而导致崩溃。
        *   **传统优化路径**：仅当 `force_alloc` 为假（如 Meta/Node 映射）且 `private` 为空时，才回退到旧的“指针位图”优化模式，直接在指针值上操作位。
        *   **原子性保证**：在分配结构体后，使用原子位操作（`set_bit`）设置标志，确保并发安全。
*   **4.3 压缩文件的大页读写算法**
    *   **4.3.1 “大 Folio 优先”的分配策略**：
        *   摒弃初赛的“逐簇填充”思路。
        *   新算法：在 `iomap_begin` 阶段根据 I/O 长度计算所需页面数，一次性分配一个巨大的 Folio，然后用多个压缩簇的数据去填充它。
    *   **4.3.2 混合 I/O 路径下的字节级记账与同步**：
        *   引入 `read_bytes_pending` 计数器。
        *   **压缩路径**：解压完成后减计数。
        *   **非压缩路径**：BIO 完成后减计数。
        *   **同步**：只有计数器归零时，才执行 `folio_end_read`，确保混合路径下的数据一致性。
    *   **4.3.3 延迟解锁与并发一致性保证**：
        *   在 `buffered_write` 路径中，利用 `read_bytes_pending` 加偏置（Bias）的方法，实现对异步解压 I/O 的同步等待，防止数据未就绪就写入。
*   **4.4 脏页回写与垃圾回收的精确化改造**
    *   **4.4.1 逐块脏页追踪 (Per-block Dirty Tracking)**：
        *   利用 `iomap_folio_state` 中的位图记录脏状态。
        *   修改 `move_data_page`，在 GC 时只回写位图中标记为脏的子块，彻底解决写放大。
    *   **4.4.2 修复双重解锁与空悬 Folio 问题**：
        *   **双重解锁**：修正 `f2fs_submit_page_bio`，传递 `fio->idx` 和 `fio->cnt`，确保 BIO 回调只处理对应的子页范围。
        *   **空悬 Folio**：在回写循环末尾增加检查，手动解锁那些未被提交 BIO 的“干净”Folio，防止死锁。

#### 第五章 性能测试与分析
*   **5.1 测试环境与方法论**
    *   **硬件**：QEMU (x86-64, 8vCPU, 8G RAM) 和 树莓派 5 (ARM64, 4G RAM, NVMe SSD)。
    *   **关键配置**：树莓派启用 **16KB Page Size**（亮点）。
    *   **工具**：FIO。测试指标：带宽 (BW)、IOPS。
*   **5.2 QEMU 虚拟机环境测试结果**
    *   **普通文件**：1MB 块大小下，顺序写性能提升约 3 倍（减少了 dnode 查找和锁竞争）。
    *   **空洞文件**：写入性能提升 1.5 倍（iomap 跳过空洞更高效）。
*   **5.3 树莓派 5 (16KB Page) 环境测试结果**
    *   **压缩文件**：写入性能最高提升 **4 倍**。
    *   **分析**：16KB 页大小与 F2FS 压缩簇（通常也是 16KB）完美对齐，结合 Large Folio 的批量处理，消除了大量碎片化开销。
*   **5.4 性能收益总结**
    *   总结：Large Folios 显著减少了 TLB Miss；iomap 框架大幅降低了 CPU 在块映射上的开销；新算法解决了并发瓶颈。

---