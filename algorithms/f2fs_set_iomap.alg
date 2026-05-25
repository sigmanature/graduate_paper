@algorithm id=f2fs_set_iomap chapter=4 index=1 title="f2fs_set_iomap: block map to iomap"

\Input inode, map, offset, length, dio
\Output iomap
\State iomap.offset <- F2FS_BLK_TO_BYTES(map.m_lblk)
\If map has F2FS_MAP_MAPPED
    \State iomap.length <- F2FS_BLK_TO_BYTES(map.m_len)
    \If dio and map.m_pblk == NEW_ADDR
        \Return -EINVAL
    \EndIf
    \If map.m_pblk != NEW_ADDR
        \State iomap.type <- IOMAP_MAPPED; set IOMAP_F_MERGED
        \State iomap.addr <- F2FS_BLK_TO_BYTES(map.m_pblk)
    \Else
        \State iomap.type <- IOMAP_UNWRITTEN; iomap.addr <- IOMAP_NULL_ADDR
    \EndIf
\Else
    \If dio and write flag set
        \Return -ENOTBLK
    \EndIf
    \If map.m_pblk == NULL_ADDR
        \State iomap.length <- hole_end(map) - iomap.offset
        \State iomap.type <- IOMAP_HOLE; iomap.addr <- IOMAP_NULL_ADDR
    \ElseIf map.m_pblk == NEW_ADDR
        \State iomap.length <- F2FS_BLK_TO_BYTES(map.m_len)
        \State iomap.type <- IOMAP_UNWRITTEN; iomap.addr <- IOMAP_NULL_ADDR
    \Else
        \Return -EFAULT
    \EndIf
\EndIf
\If map has F2FS_MAP_NEW
    \State set IOMAP_F_NEW
\EndIf
\If inode is datasync-dirty or offset + length > i_size(inode)
    \State set IOMAP_F_DIRTY
\EndIf
\Return 0
