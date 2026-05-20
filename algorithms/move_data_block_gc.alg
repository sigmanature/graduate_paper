@algorithm id=move_data_block_gc chapter=4 index=9 title="move_data_block：GC 后台搬移子范围脏标记"

\Input inode, bidx（目标逻辑块号）, gc_type
\Output 错误码
\State folio ← f2fs_get_lock_data_folio(inode, bidx, true)
\If gc_type == BG_GC
    \If folio 正在 writeback
        \Return -EAGAIN
    \EndIf
    \State f2fs_set_folio_private_gcing(folio)
    \Comment 通过 f2fs_folio_state 统一 API 设置 ONGOING_MIGRATION 标志
    \If folio_order(folio) == 0
        \State folio_mark_dirty(folio)
        \Comment 0 阶 folio：沿用全 folio 脏标记
    \Else
        \State iomap_set_range_dirty(folio, bidx << PAGE_SHIFT, PAGE_SIZE)
        \Comment 高阶 folio：仅标记目标子块 4KB 范围为脏
        \Comment 后续 4.5 写回路径仅提交该 4KB 而非整 64KB
    \EndIf
\Else
    \Comment FG_GC（前台 GC）：沿用原有 f2fs_do_write_data_page 逻辑
    \State folio_mark_dirty(folio)
    \State f2fs_set_folio_private_gcing(folio)
    \State err ← f2fs_do_write_data_page(&fio)
    \If err == -EAGAIN
        \State 重试（与原有逻辑相同）
    \EndIf
\EndIf
\State f2fs_folio_put(folio, true)
\Return err
