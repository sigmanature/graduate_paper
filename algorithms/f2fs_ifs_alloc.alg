@algorithm id=f2fs_ifs_alloc chapter=4 index=4 title="f2fs_ifs_alloc：统一状态结构的智能分配与迁移"

\Input folio, gfp（内存分配标志）, force_alloc（是否强制分配）
\Output f2fs_folio_state 指针，或 NULL
\State old ← folio->private

\If old ≠ NULL
    \State rbp ← READ_ONCE(old.read_bytes_pending)
    \If rbp == F2FS_IFS_MAGIC 或 rbp > F2FS_IFS_MAGIC
        \Comment 已是我们的类型，直接返回
        \Return old
    \Else
        \Comment 非空但不是我们的类型 → 推断为 iomap_folio_state
        \State 分配新的 f2fs_folio_state（含额外 2 个 unsigned long 的柔性数组空间）
        \State 将旧 iomap_folio_state 的头部和位图拷贝到新结构体
        \State 写入魔数 F2FS_IFS_MAGIC 到 read_bytes_pending
        \State 初始化 private_flags 和 dirty_bytes_pending 为 0
        \State folio_change_private(folio, new)  \Comment 原子替换指针
        \State kfree(old)
        \Return new
    \EndIf
\Else
    \Comment private 为空，直接分配
    \State 分配并零初始化新的 f2fs_folio_state
    \State 若 folio 当前 uptodate → 设置对应 uptodate 位图
    \State 若 folio 当前 dirty    → 设置对应 dirty 位图
    \State 写入魔数，初始化计数器
    \State folio_attach_private(folio, new)
    \Return new
\EndIf
