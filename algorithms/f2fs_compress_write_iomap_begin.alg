@algorithm id=f2fs_compress_write_iomap_begin chapter=4 index=7 title="f2fs_buffered_write_iomap_begin（压缩路径）：大 Folio 视角写入"

\Input inode, offset, length（写入字节区间）
\Output iomap（iomap.private 指向已填充就绪的大 folio）
\State folio ← iomap_get_folio(iter, offset, length)
\Comment 一次性分配覆盖全部簇范围的大 folio
\State fifs ← f2fs_ifs_alloc(folio, flags, false)
\If folio_order(folio) > 0 且 fifs 存在
    \State fifs.read_bytes_pending ← fifs.read_bytes_pending + 1
    \Comment 偏置：阻止 bio 完成回调提前触发 folio_end_read
\EndIf

\State 识别 head 部分簇（写入起始不齐簇边界）、中间完整簇、tail 部分簇

\If head 部分簇存在
    \State 将该簇内页面填入 compress_ctx
    \State 递增 read_bytes_pending
    \For 簇内每个 folio 的子页
        \State 检查 per-block uptodate 位（f2fs_ifs_block_is_uptodate）
        \If 所有子页均已 uptodate
            \State 跳过读（数据已就绪）
        \Else
            \State 调用 f2fs_read_multi_folios 发起磁盘读取
        \EndIf
    \EndFor
    \State 重置 compress_ctx
\EndIf

\For 每个中间完整簇
    \Comment 该簇将被整个写入覆盖，旧数据无保留价值
    \State 确认簇头为 COMPRESS_ADDR（否则回退到普通路径）
    \State 调用 iomap_set_range_uptodate(folio, 簇内偏移, 簇字节大小)
    \Comment 直接标记 uptodate，不读磁盘
    \State iomap.length ← iomap.length + 簇字节大小
\EndFor

\If tail 部分簇存在（且不同于 head 簇）
    \State 与 head 簇同样处理：检查 uptodate 位，按需读取
\EndIf

\State 提交所有待处理的 bio
\While fifs.read_bytes_pending ≠ F2FS_IFS_MAGIC + 1
    \State 轮询等待（f2fs_io_schedule_timeout）
\EndWhile
\State fifs.read_bytes_pending ← fifs.read_bytes_pending - 1
\Comment 移除偏置，folio 完全就绪

\State iomap.private ← folio
\State iomap.type ← IOMAP_MAPPED
\Return 成功
