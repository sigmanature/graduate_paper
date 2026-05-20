@algorithm id=f2fs_read_iomap_begin chapter=4 index=2 title="f2fs_buffered_read_iomap_begin：普通文件缓冲读区间映射"

\Input inode, offset, length（字节区间）
\Output 填充完成的 iomap（区间映射描述符）
\State map.m_lblk ← 将 offset 转换为逻辑块号
\State map.m_len  ← 将 (offset + length) 转换为块数
\State map.m_next_pgofs ← next_pgofs 指针
\State map.m_may_create ← false

\If 文件系统已关闭
    \Return 错误
\EndIf
\If flags 包含 IOMAP_WRITE
    \Return 错误（读路径不应出现写标志）
\EndIf

\State 调用 f2fs_map_blocks(inode, &map, F2FS_GET_BLOCK_IOMAP)
\Comment 内部双路径：extent cache 命中 → 直接返回连续区间
\Comment           extent cache 未命中 → dnode 遍历 + map_is_mergeable 合并连续块
\If 出错
    \Return 错误
\EndIf
\If map.m_pblk == COMPRESS_ADDR
    \Return 错误（压缩文件不应进入普通读路径）
\EndIf

\State 调用 f2fs_set_iomap(inode, &map, iomap, flags, offset, length, false)
\Return 成功
