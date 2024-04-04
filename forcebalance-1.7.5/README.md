# ForceBalance 1.7.5 Mod

This folder contains files and scripts needed to set up ForceBalance 1.7.5 for the use on Ren lab cluster. Please refer to the official documentation of ForceBalance for general information.

## Installation

To install ForceBalance with the patch, open `installer.sh` and modify the variables at the beginning to fit your case, then run
```
$ bash installer.sh
```
Please refrain from deleting any files within this directory or the directory `../JobPool` after the installation, as certain files are utilized each time you execute a ForceBalance job.

When the installation completes, a message like the following will show you how to run a ForceBalance job.
```
Installation completed. To run a ForceBalance job:

     $ source ~/.bashrc.FB17
     $ ForceBalance example.in
```

Please make sure `TINKERPATH` and `tk9home` in the generated bashrc file are up to date before running jobs.
Please set the `tinkerpath` in your ForceBalance input file (e.g., `example.in`)
as the same to `TINKERPATH`, so that a consistent Tinker installation is invoked throughout the job.

## Node list to submit Tinker jobs

This script `./external/submitTinker.py` is responsible for submitting Tinker CPU and GPU jobs on to Ren lab clusters. This script is reading node list from `./external/nodes.dat` file, which looks like the following. Change the file as needed.
```
#===========================================
#   Any line starts with "#" will be ignored.
#   Only the first two columns matter !!
#   Add / remove nodes as needed.

#   This file is used by submitTinker.py,
#   and must be placed in the same folder.
#   Do not change the filename. 
#===========================================

### GPU nodes mainly use

GPU node152   4090    2

GPU node154   4090    2

#CPU nodes nthreads

CPU      node145  32

CPU      node146  32

CPU      node152  64

CPU      node153  64
```

## JobPool

`../JobPool` is required for the patched ForceBalance. See `../JobPool/README.md` for more information.
