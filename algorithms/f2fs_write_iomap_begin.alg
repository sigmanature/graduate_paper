@algorithm id=f2fs_write_iomap_begin chapter=4 index=3 title="f2fs_buffered_write_iomap_begin: range allocation for buffered write"

\Input inode, offset, length, flags
\Output iomap
\State map.m_lblk <- F2FS_BYTES_TO_BLK(offset)
\State map.m_len <- F2FS_BYTES_TO_BLK(offset + length - 1) - map.m_lblk + 1
\State map.m_may_create <- true
\State iomap.bdev <- inode.sb.bdev; iomap.folio_ops <- f2fs_iomap_folio_ops
\State err <- call f2fs_map_blocks(inode, &map, F2FS_GET_BLOCK_IOMAP)
\If err != 0 and err != -ENOSPC
    \Return err
\EndIf
\If map.m_pblk == NULL_ADDR
    \State err <- call f2fs_map_blocks_preallocate(inode, &map)
\EndIf
\If err != 0 and err != -ENOSPC
    \Return err
\EndIf
\Return call f2fs_set_iomap(inode, &map, iomap, flags, offset, length, false)
