@algorithm id=move_data_block_gc chapter=4 index=9 title="move_data_block: GC subrange migration"

\Input inode, bidx, gc_type
\Output err
\State folio <- call f2fs_get_lock_data_folio(inode, bidx, true)
\If folio is writeback and gc_type == BG_GC
    \Return -EAGAIN
\EndIf
\State call f2fs_set_folio_private_gcing(folio)
\If gc_type == BG_GC
    \If folio_order(folio) == 0
        \State call folio_mark_dirty(folio)
    \Else
        \State off <- (bidx - folio.index) << PAGE_SHIFT
        \State call iomap_set_range_dirty(folio, off, PAGE_SIZE)
    \EndIf
    \State call f2fs_folio_put(folio, true)
    \Return 0
\EndIf
\State call folio_mark_dirty(folio)
\State err <- call f2fs_do_write_data_page(fio)
\If err == -EAGAIN
    \State goto retry_fg
\EndIf
\State call f2fs_folio_put(folio, true)
\Return err
