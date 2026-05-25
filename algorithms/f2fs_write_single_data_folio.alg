@algorithm id=f2fs_write_single_data_folio chapter=4 index=8 title="f2fs_write_single_data_folio: subrange writeback"

\Input folio, wbc, compr_blocks, from_compress, start, end
\Output err, submitted_pages_count
\If folio_order(folio) == 0
    \State err <- call f2fs_write_single_data_page(folio, wbc)
    \If err == -EAGAIN and sync writeback
        \State call f2fs_io_schedule_timeout(DEFAULT_IO_TIMEOUT)
        \State goto retry_single
    \EndIf
    \Return err
\EndIf
\State fifs <- folio.private
\State first <- (start - folio_pos(folio)) >> PAGE_SHIFT
\State last <- (end - 1 - folio_pos(folio)) >> PAGE_SHIFT
\For i <- first to last
    \State page <- folio_page(folio, i)
    \State fio <- build_io_info(page, wbc, compr_blocks)
    \State fio.need_lock <- compr_blocks ? LOCK_DONE : LOCK_RETRY
retry:
    \State atomic_add(PAGE_SIZE, fifs.write_bytes_pending)
    \State err <- call f2fs_do_write_data_page(fio)
    \If err == -EAGAIN and (sync writeback or from_compress)
        \State call f2fs_io_schedule_timeout(DEFAULT_IO_TIMEOUT)
        \State fio.need_lock <- LOCK_REQ
        \State goto retry
    \EndIf
    \If err != 0
        \State atomic_sub(PAGE_SIZE, fifs.write_bytes_pending)
        \State break
    \EndIf
    \State submitted++
\EndFor
\State submitted_pages_count <- submitted
\Return err
