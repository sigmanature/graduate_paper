@algorithm id=f2fs_compress_read_iomap_begin chapter=4 index=5 title="f2fs_buffered_read_compress_iomap_begin：压缩文件缓冲读多簇映射"

\Input inode, pos, length（请求的字节区间）
\Output iomap（长度截断至簇边界或覆盖多个簇）
\State index ← pos 按页大小右移得到页索引
\State cluster_start_idx ← 将 index 对齐到当前簇起始页号
\State folio ← 当前预读 folio（ctx.cur_folio）
\State all_clusters ← 计算 folio 内从 index 起覆盖的完整簇数

\If index 未对齐到簇起始 或 all_clusters ≤ 1
    \Comment 单簇路径（非对齐或 folio 只覆盖一个簇）
    \State 获取 dnode，检查簇头物理地址是否为 COMPRESS_ADDR
    \If 是压缩簇
        \State ctx.compressed_clusters ← 1
        \State iomap.length ← min(length, 当前簇末尾 - index 的字节数)
        \State iomap.type ← IOMAP_MAPPED
        \Return 成功
    \EndIf
\Else
    \Comment 多簇路径（folio 对齐且跨越多个压缩簇）
    \State all_clusters ← min(all_clusters, MAX_PBLLKS_INFO_SIZE)
    \For i ← 0 to all_clusters-1
        \If extent cache 命中 cluster_idx
            \State 从 extent_info 获取物理块头地址 blk 和连续长度 c_len
        \Else
            \State 通过 dnode 查找簇头物理地址
            \If 簇头 ≠ COMPRESS_ADDR
                \State break（遇到非压缩区域，停止）
            \EndIf
            \State 遍历 dnode 获取该簇内所有有效物理块地址
        \EndIf
        \State 将本簇物理块信息存入 ctx.pblks_arr[i]
        \State process_clusters++
    \EndFor
    \State ctx.compressed_clusters ← process_clusters
    \State iomap.length ← process_clusters 转换为字节总长度
    \State iomap.type ← IOMAP_MAPPED
    \Return 成功
\EndIf
\State 非压缩位置 → 回退到 f2fs_buffered_read_iomap_begin（普通读路径）
