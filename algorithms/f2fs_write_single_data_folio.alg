@algorithm id=f2fs_write_single_data_folio chapter=4 index=8 title="f2fs_write_single_data_folio：脏页写回子范围控制"

\Input folio, wbc（回写控制）, start, end（字节范围，非默认整 folio）
      compr_blocks（压缩块数）, from_compress（是否来自压缩路径）
\Output 错误码，submitted_pages_count
\If folio_order(folio) == 0
    \State 回退到 f2fs_write_single_data_page（原有 0 阶逻辑，含重试）
    \Return
\EndIf

\State fifs ← folio.private
\State folio_start_idx ← (start - folio 起始位置) 转换为页内索引
\State folio_end_idx   ← (end   - folio 起始位置) 转换为页内索引

\For i ← folio_start_idx to folio_end_idx
    \State page ← folio_page(folio, i)
    \State 构建 f2fs_io_info（含 page、wbc、compr_blocks 等）
    \State fio.need_lock ← compr_blocks ? LOCK_DONE : LOCK_RETRY
    \Comment 压缩路径：由上层统一解锁（DEFERRED_UNLOCK）
retry_multi:
    \State atomic_add(PAGE_SIZE, &fifs.write_bytes_pending)
    \Comment 递增未完成写入字节计数
    \State err ← f2fs_do_write_data_page(&fio)
    \If err == -EAGAIN
        \If wbc.sync_mode == WB_SYNC_ALL 或 from_compress
            \State 等待超时后重试
            \State fio.need_lock ← LOCK_REQ
            \State goto retry_multi
        \Else
            \State goto handle_multi_err
        \EndIf
    \EndIf
    \State local_submitted_count++
handle_multi_err:
    \If err ≠ 0
        \State 原子递减 write_bytes_pending，若归零则 folio_end_writeback
        \State break（终止后续子块提交）
    \EndIf
\EndFor
\State submitted_pages_count ← local_submitted_count
\Return err
