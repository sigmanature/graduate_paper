@algorithm id=f2fs_ifs_alloc chapter=4 index=4 title="f2fs_ifs_alloc: attach or migrate state"

\Input folio, gfp, force_alloc
\Output f2fs_folio_state or NULL
\State old <- folio_get_private(folio)
\If folio_order(folio) == 0 and not force_alloc
    \Return NULL
\EndIf
\If old != NULL
    \State rbp <- READ_ONCE(old.read_bytes_pending)
    \If rbp >= F2FS_IFS_MAGIC
        \Return old
    \EndIf
    \State new <- call kmalloc(sizeof(f2fs_folio_state) + f2fs_ifs_total_longs(folio))
    \If new == NULL
        \Return NULL
    \EndIf
    \State call ifs_to_f2fs_ifs(old, new, folio)
    \State init counters and state_lock
    \State call folio_change_private(folio, new)
    \State call kfree(old)
    \Return new
\EndIf
\State new <- call kzalloc(sizeof(f2fs_folio_state) + f2fs_ifs_total_longs(folio))
\If new == NULL
    \Return NULL
\EndIf
\State init counters and state_lock
\If folio_test_uptodate(folio)
    \State set all uptodate bits
\EndIf
\If folio_test_dirty(folio)
    \State set all dirty bits
\EndIf
\State call folio_attach_private(folio, new)
\Return new
