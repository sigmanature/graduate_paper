@algorithm id=f2fs_set_iomap chapter=4 index=1 title="f2fs_set_iomap：块映射到 iomap 区间转换"

\Input inode, map (f2fs_map_blocks 输出), offset, length, dio 标志
\Output 填充完成的 iomap 结构体
\State iomap.offset ← map.m_lblk 按块大小转换为字节偏移

\If map.m_flags 包含 F2FS_MAP_MAPPED
    \State iomap.length ← map.m_len 转换为字节长度
    \If map.m_pblk ≠ NEW_ADDR
        \State iomap.type ← IOMAP_MAPPED
        \State iomap.flags ← iomap.flags | IOMAP_F_MERGED
        \State iomap.addr ← map.m_pblk 转换为字节地址
    \Else
        \State iomap.type ← IOMAP_UNWRITTEN
        \State iomap.addr ← IOMAP_NULL_ADDR
    \EndIf
\Else
    \If dio 写路径
        \Return 错误（DIO 写不允许空洞）
    \EndIf
    \If map.m_pblk == NULL_ADDR
        \If map.m_flags 包含 F2FS_MAP_NODNODE
            \State iomap.length ← m_next_pgofs 字节偏移 - iomap.offset
        \Else
            \State iomap.length ← map.m_len 转换为字节长度
        \EndIf
        \State iomap.type ← IOMAP_HOLE
    \ElseIf map.m_pblk == NEW_ADDR
        \State iomap.length ← map.m_len 转换为字节长度
        \State iomap.type ← IOMAP_UNWRITTEN
    \EndIf
    \State iomap.addr ← IOMAP_NULL_ADDR
\EndIf

\If map.m_flags 包含 F2FS_MAP_NEW
    \State iomap.flags ← iomap.flags | IOMAP_F_NEW
\EndIf
\If inode 含 I_DIRTY_DATASYNC 或 (offset + length > i_size)
    \State iomap.flags ← iomap.flags | IOMAP_F_DIRTY
\EndIf
\Return 成功
