@algorithm id=f2fs_compress_readpage_iter chapter=4 index=6 title="f2fs_compress_readpage_iter：压缩读内层迭代器"

\Input iter（iomap 迭代器）, ctx（F2FS 预读上下文）
\Output 迭代推进的字节数
\State folio ← ctx.cur_folio
\State 调用 f2fs_ifs_alloc(folio, flags, false) 确保状态结构存在
\State 调用 iomap_adjust_read_range(inode, folio, &pos, length, &poff, &plen)
\Comment 复用 iomap 框架通用函数：计算 folio 内实际需要读取的子区间
\If plen == 0
    \State goto done（无需读取）
\EndIf

\If iomap_block_needs_zeroing(iter, pos)
    \Comment 复用 iomap 框架：判断该区间是否需零填充（空洞/文件尾）
    \State folio_zero_range(folio, poff, plen)
    \State iomap_set_range_uptodate(folio, poff, plen)
    \State goto done
\EndIf

\If ctx.compressed_clusters > 0
    \Comment 压缩路径：延迟聚合提交
    \State 调用 f2fs_do_read_multi_folios(ctx, pos, plen)
    \Comment 内部：将 folio 子页加入 compress_ctx，递增 read_bytes_pending
    \Comment       当簇满或预读结束时统一提交 bio 读取并解压
\Else
    \Comment 非压缩路径（压缩文件内的非压缩区域）：直接提交
    \State 调用 f2fs_do_read_single_folio_iomap(iter, ctx, pos, plen, poff)
    \Comment 内部：构建 bio，递增 read_bytes_pending，提交读取
\EndIf

done:
\State length ← pos - iter.pos + plen
\State 调用 iomap_iter_advance(iter, &length)
\Comment 复用 iomap 框架：推进迭代器位置
