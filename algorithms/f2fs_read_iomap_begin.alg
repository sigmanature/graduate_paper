@algorithm id=f2fs_read_iomap_begin chapter=4 index=2 title="f2fs_buffered_read_iomap_begin: range map for buffered read"

\Input inode, offset, length, flags
\Output iomap
\State map.m_lblk <- F2FS_BYTES_TO_BLK(offset)
\State map.m_len <- F2FS_BYTES_TO_BLK(offset + length - 1) - map.m_lblk + 1
\State map.m_next_pgofs <- &next_pgofs; map.m_may_create <- false
\If flags has IOMAP_WRITE
    \Return -EINVAL
\EndIf
\State err <- call f2fs_map_blocks(inode, &map, F2FS_GET_BLOCK_IOMAP)
\If err != 0
    \Return err
\EndIf
\If map.m_pblk == COMPRESS_ADDR
    \Return -EINVAL
\EndIf
\Return call f2fs_set_iomap(inode, &map, iomap, flags, offset, length, false)
