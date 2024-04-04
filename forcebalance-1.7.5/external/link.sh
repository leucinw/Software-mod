#!/bin/bash
# create soft links to the Tinker binaries

tinker_bin=`cd $1 && pwd`

[ -e "$tinker_bin/analyze" ] && ext='' || ext=".x"
ln -s $tinker_bin/analyze$ext analyze
ln -s $tinker_bin/minimize$ext minimize
ln -s $tinker_bin/dynamic$ext dynamic
ln -s $tinker_bin/optimize$ext optimize
