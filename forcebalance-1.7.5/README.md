# ForceBalance 1.7.5 Mod

This folder contains files and scripts needed to set up ForceBalance 1.7.5 for the use on Ren lab cluster. Please refer to the official documentation of ForceBalance for general information.

## Installation

You will need conda in the server to continue. To install ForceBalance with the patch, open `installer.sh` and modify the variables at the beginning to fit your case, then run
```
$ bash installer.sh
```
Please refrain from deleting any files within this directory or the directory `../JobPool` after the installation, as certain files are utilized each time you execute a ForceBalance job.

When the installation completes, a message like the following will show you how to run a ForceBalance job. The filenames may vary.
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

### GPU nodes 

GPU node152  

GPU node154   

# CPU nodes 

CPU      node145  

CPU      node146  

CPU      node152  

CPU      node153  
```

## JobPool

`../JobPool` is required for the patched ForceBalance. See `../JobPool/README.md` for more information.

## Troubleshooting
1. If you see messages like below while executing `conda create`, it is because you have once installed ForceBalance of the same version and you have modified the content of the package without being careful enough. Conda uses hardlinks by default to save disk space when installing packages. If you make changes to package contents within any conda environment directory without first unlinking them, those modifications will affect all other conda environments containing the same package of the same version, including any new conda environments created in the future!

    ```
    Verifying transaction: /
    SafetyError: The package for forcebalance located at /work/yw24267/miniconda3/pkgs/forcebalance-1.7.5-py37h6dcda5c_3
    appears to be corrupted. The path 'lib/python3.7/site-packages/forcebalance/binding.py'
    has an incorrect size.
    reported size: 12317 bytes
    actual size: 14726 bytes

    SafetyError: The package for forcebalance located at /work/yw24267/miniconda3/pkgs/forcebalance-1.7.5-py37h6dcda5c_3
    appears to be corrupted. The path 'lib/python3.7/site-packages/forcebalance/data/npt.py'
    has an incorrect size.
    reported size: 32121 bytes
    actual size: 40338 bytes

    (...)
    ```
    That being said, if you only modified the files seen in `./mod/` in this repo, rest assured that the newly created conda enviroment is all good since the modifications has been overwritten by `installer.sh` only within the new environment. All other environments remain unaltered. Otherwise, see the solution below.
    1. Backup the modifications you have made on ForceBalance previously.
    1. Remove the new environment created by `installer.sh`.
    1. Remove ForceBalance 1.7.5 from all conda enviroments.
    2. Remove all cache using `conda clean -a -y`.
    3. Reinstall ForceBalance 1.7.5 into the enviroments in Step 3.
    4. This time, back up the original package files if needed, then use 
        `cp --remove-destination` to copy your modified files to the enviroment directory.
    5. Run `installer.sh` again. The SafetyError you saw should be gone now.

## Update / Reinstallation

```
conda remove -n <env_name> --all
git pull
bash installer.sh
```
