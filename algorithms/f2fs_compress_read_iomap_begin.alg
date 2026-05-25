@algorithm id=f2fs_compress_read_iomap_begin chapter=4 index=5 title="f2fs_buffered_read_compress_iomap_begin: compressed-cluster mapping"

\Input inode, pos, length, flags
\Output iomap
\State ctx <- iter.private
\State index <- pos >> PAGE_SHIFT
\State folio <- ctx.cur_folio or call readahead_folio(ctx.rac)
\State cluster <- cluster_idx(ctx.cc, index)
\State all <- (folio_nr_pages(folio) - (index - folio.index)) >> ctx.cc.log_cluster_size
\State iomap.offset <- F2FS_BLK_TO_BYTES(F2FS_BYTES_TO_BLK(pos))
\State iomap.bdev <- inode.sb.bdev
\If index != cluster << log_cluster_size or all <= 1
    \State err <- call f2fs_get_dnode_of_data(ctx.dn, cluster << log_cluster_size)
    \If err != 0
        \Return err
    \EndIf
    \If data_blkaddr(ctx.dn) == COMPRESS_ADDR
        \State ctx.compressed_clusters <- 1
        \State iomap.length <- min(length, cluster_end(index) - index)
        \State iomap.type <- IOMAP_MAPPED
        \Return 0
    \EndIf
\Else
    \State all <- min(all, MAX_PBLLKS_INFO_SIZE)
    \For i <- 0 to all - 1
        \State cidx <- cluster + i
        \If call f2fs_lookup_read_extent_cache(inode, cidx, ei)
            \State ctx.pblks_arr[i] <- extent pblk info
        \Else
            \State err <- call f2fs_get_dnode_of_data(ctx.dn, cidx << log_cluster_size)
            \If err != 0
                \Return err
            \EndIf
            \If data_blkaddr(ctx.dn) != COMPRESS_ADDR
                \State break
            \EndIf
            \State ctx.pblks_arr[i] <- dnode pblk list
        \EndIf
        \State process++
    \EndFor
    \State ctx.compressed_clusters <- process
    \State iomap.length <- bytes(process clusters); iomap.type <- IOMAP_MAPPED
    \Return 0
\EndIf
\Return call f2fs_buffered_read_iomap_begin(inode, pos, length, flags, iomap)
