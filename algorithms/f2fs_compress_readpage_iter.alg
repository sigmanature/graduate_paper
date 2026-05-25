@algorithm id=f2fs_compress_readpage_iter chapter=4 index=6 title="f2fs_compress_readpage_iter: compressed read iterator"

\Input iter, ctx
\Output advanced length or error
\State pos <- iter.pos
\State length <- iomap_length(iter)
\State folio <- ctx.cur_folio
\State fifs <- call f2fs_ifs_alloc(folio, iter.flags, false)
\State call iomap_adjust_read_range(iter.inode, folio, &pos, length, &poff, &plen)
\If plen == 0
    \State goto done
\EndIf
\If call iomap_block_needs_zeroing(iter, pos)
    \State call zero_and_mark_uptodate(folio, poff, plen)
    \State goto done
\EndIf
\If ctx.compressed_clusters > 0
    \State ret <- call f2fs_do_read_multi_folios(ctx, pos, plen)
\Else
    \State ret <- call f2fs_do_read_single_folio_iomap(iter, ctx, pos, plen, poff)
\EndIf
\If ret != 0
    \Return ret
\EndIf
done:
\State length <- pos - iter.pos + plen
\Return call iomap_iter_advance(iter, &length)
