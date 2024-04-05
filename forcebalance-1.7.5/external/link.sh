#!/bin/bash
# create soft links to the Tinker binaries

[ -z "$1" ] && exit 1
tinker_bin=`cd $1 && pwd`
find $tinker_bin -executable -type f | while read f; do
    nf=$(basename $f | sed "s/.x$//g")
    [ -L "$nf" ] && rm $nf
    ln -s $f $nf
done
