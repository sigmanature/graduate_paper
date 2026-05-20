@algorithm id=f2fs_write_iomap_begin chapter=4 index=3 title="f2fs_buffered_write_iomap_begin：普通文件缓冲写区间映射与预分配"

\Input inode, pos, length（写入字节区间）
\Output iomap（含映射或预分配区间）
\State start_blk ← 将 pos 转换为起始逻辑块号
\State len_blks  ← 将 (pos + length) 转换为块数

\State 调用 f2fs_map_blocks_iomap(inode, start_blk, len_blks, &map)
\Comment 查询写入区间内已有映射
\If 出错（且非 ENOSPC）
    \Return 错误
\EndIf

\If map.m_pblk == NULL_ADDR
    \Comment 区间为空洞，触发区间预分配
    \State 调用 f2fs_map_blocks_preallocate(inode, map.m_lblk, map.m_len, &map)
    \Comment 内部以 F2FS_GET_BLOCK_PRE_AIO 模式调用 f2fs_map_blocks
    \Comment map_is_mergeable 合并连续 NEW_ADDR：m_pblk==NEW_ADDR && blkaddr==NEW_ADDR
    \Comment 遍历到节点页末尾时批量调用 f2fs_reserve_new_blocks
    \If 出错（且非 ENOSPC）
        \Return 错误
    \EndIf
\EndIf

\State 将 map 结果转换为 iomap（复用 f2fs_set_iomap 逻辑）
\Return 成功
