@algorithm id=f2fs_compress_write_iomap_begin chapter=4 index=7 title="f2fs_buffered_write_iomap_begin: compressed range prepare"

\Input inode, offset, length, flags
\Output iomap with prepared folio
\State folio <- call iomap_get_folio(iter, offset, length)
\State fifs <- call f2fs_ifs_alloc(folio, iter.flags, false)
\If folio_order(folio) > 0 and fifs != NULL
    \State fifs.read_bytes_pending <- fifs.read_bytes_pending + 1
\EndIf
\State head <- first cluster touched by offset
\State tail <- last cluster covered by folio
\If head is partial
    \State prepare head range; add pending bytes
    \If any page is stale
        \State call f2fs_read_multi_folios(cc, pblks, dn, bio)
    \EndIf
    \State call f2fs_reset_compress_ctx(cc)
\EndIf
\For c <- first_full_cluster to last_full_cluster
    \State err <- call f2fs_ensure_dn_for_cluster(inode, c, dn)
    \If err != 0
        \Return err
    \EndIf
    \If data_blkaddr(dn) != COMPRESS_ADDR
        \State goto normal_path_or_done
    \EndIf
    \State call mark_full_cluster_uptodate(folio, c)
    \State iomap.length <- iomap.length + cluster_size
\EndFor
\If tail is partial and tail != head
    \State prepare tail range; add pending bytes
    \If any page is stale
        \State call f2fs_read_multi_folios(cc, pblks, dn, bio)
    \EndIf
\EndIf
\If bio != NULL
    \State call f2fs_submit_read_bio(sbi, bio, DATA)
\EndIf
\While fifs.read_bytes_pending != F2FS_IFS_MAGIC + 1
    \State call f2fs_io_schedule_timeout(DEFAULT_IO_TIMEOUT)
\EndWhile
\State fifs.read_bytes_pending <- fifs.read_bytes_pending - 1
\State call folio_mark_uptodate(folio)
\State iomap.private <- folio; iomap.type <- IOMAP_MAPPED
\Return 0
