# 中英文摘要

## 摘 要

随着移动端本地数据规模和端侧人工智能模型文件体量持续增长，应用启动、资源装载、模型加载和后台更新等过程对文件系统的连续 I/O 能力提出了更高要求。F2FS 作为 Android 设备中常用的闪存友好文件系统，具有顺序追加写入、垃圾回收和压缩文件等面向闪存的优化机制，但其原有缓冲 I/O 路径长期以 4KB 页和文件系统块为基本处理单位，难以充分利用底层块设备对大粒度连续 I/O 的支持。

可变阶数动态大页（Large Folio）能够扩大页缓存对象粒度，减少缓存对象数量和映射查询开销，而 F2FS 原有缓冲 I/O 路径仍围绕 4KB 页和文件系统块组织，难以直接承接一个页缓存对象覆盖多个文件系统块的情况。针对这一适配问题，本文将动态大页引入 F2FS 缓冲 I/O 路径，为 F2FS 支持大粒度连续文件 I/O 提供页缓存基础，并设计实现了一套基于 iomap 的动态大页缓冲 I/O 适配框架。该框架将 F2FS 的块级映射结果转换为面向文件字节区间的 iomap 描述，并扩展动态大页内部逐页状态对象，使动态大页能够在 F2FS 中完成区间化读写、子范围状态维护和 I/O 完成判断，并在此基础上对于 F2FS 专属的垃圾回收和压缩文件路径进行了针对性扩展，使后台块搬移和簇级压缩处理能够在兼容原有语义的同时支持动态大页，最终使 F2FS 能够在兼容顺序追加写入、垃圾回收和压缩文件等闪存友好机制的前提下，将动态大页应用到完整的缓冲 I/O 关键路径中。

本文在 QEMU 虚拟机和树莓派平台上对所实现的原型系统进行了实验评估。实验结果表明，相比未接入 iomap 动态大页路径的基线系统，本文框架在大块顺序 I/O 场景下能够显著提升 F2FS 的吞吐能力，其中 QEMU 平台上的普通文件写入带宽获得约 2–3 倍提升，树莓派平台上的普通文件、稀疏文件和压缩文件写入场景最高获得约 3–4 倍以上提升；同时，CPU 开销和带宽稳定性结果表明，该框架能够降低小粒度页缓存管理和逐块 I/O 组织带来的额外开销。实验结果验证了 F2FS 支持动态大页缓冲 I/O 的可行性和有效性。

**关键词：** F2FS；动态大页；页缓存；iomap；缓冲 I/O；压缩文件

## ABSTRACT

As local data volume on mobile devices and the file size of on-device artificial intelligence models continue to grow, processes such as application startup, resource loading, model loading, and background updates impose higher requirements on the sequential I/O capability of file systems. F2FS, as a flash-friendly file system commonly used on Android devices, provides flash-oriented optimizations such as sequential append writing, garbage collection, and compressed files. However, its original buffered I/O path has long used 4 KB pages and file system blocks as the basic processing units, making it difficult to fully utilize the support of underlying block devices for large-granularity sequential I/O.

Variable-order large folios, namely Large Folios, can enlarge the granularity of page-cache objects and reduce the number of cache objects as well as mapping lookup overhead. However, the original F2FS buffered I/O path is still organized around 4 KB pages and file system blocks, making it difficult to directly handle the case where a single page-cache object covers multiple file system blocks. To address this adaptation problem, this thesis introduces large folios into the F2FS buffered I/O path, providing a page-cache foundation for F2FS to support large-granularity sequential file I/O. Based on this, this thesis designs and implements an iomap-based large-folio buffered I/O adaptation framework. The framework converts F2FS block-level mapping results into iomap descriptions based on file byte ranges, and extends the per-page state object inside large folios, enabling large folios in F2FS to support range-based read and write operations, subrange state maintenance, and I/O completion determination. On this basis, targeted extensions are further made for F2FS-specific garbage collection and compressed file paths, so that background block migration and cluster-level compression processing can support large folios while remaining compatible with their original semantics. As a result, F2FS can apply large folios to the complete key paths of buffered I/O while remaining compatible with its flash-friendly mechanisms, including sequential append writing, garbage collection, and compressed files.

This thesis evaluates the implemented prototype system on both QEMU virtual machines and a Raspberry Pi platform. Experimental results show that, compared with the baseline system without the iomap-based large-folio path, the proposed framework can significantly improve F2FS throughput under large-block sequential I/O workloads. Specifically, ordinary file write bandwidth on the QEMU platform is improved by approximately 2–3 times, while ordinary file, sparse file, and compressed file write scenarios on the Raspberry Pi platform achieve up to more than 3–4 times improvement. Meanwhile, CPU overhead and bandwidth stability results show that the framework can reduce the extra overhead caused by fine-grained page-cache management and block-by-block I/O organization. These results demonstrate the feasibility and effectiveness of supporting large-folio buffered I/O in F2FS.

**KEYWORDS:** F2FS; Large Folio; Page Cache; iomap; Buffered I/O; Compressed File
