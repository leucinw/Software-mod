#!/bin/bash
#################################################################################################
# This script is used to install forcebalance 1.7.5 with the patch for the use of Tinker 8 and 
# Tinker 9 on Ren lab cluster. The script will 
# create a conda environment for forcebalance with the name assigned below, 
# install forcebalance 1.7.5 and dependencies, 
# patch the mod files for the use of Tinker,
# and generate a bashrc file with name assigned below for your future forcebalance jobs. 
# Please modify the variables below to fit your case before running the script.

# path to Tinker binaries
tinker_bin=/home/liuchw/Softwares/tinkers/Tinker8/2402/source
tinker9_bin=/home/liuchw/Softwares/tinkers/Tinker9/2403/build
# the name of the conda environment for forcebalance
conda_env=FB17
# where to put the generated bashrc file
fb_bashrc=~/.bashrc.FB17
#################################################################################################

###
### create conda environment, install forcebalance 1.7.5, and patch the mod
###
conda create -n $conda_env python=3.7 forcebalance==1.7.5 pymbar==3.0.5 pathos -c conda-forge -y
condaHOME=$(conda env list | grep -E "^$conda_env " | tr -d '*' | awk '{print $2}')
fbHOME=$condaHOME/lib/python3.7/site-packages/forcebalance
modfileHOME=$(cd ./mod && pwd)
# back up the original files
cp $fbHOME/binding.py $fbHOME/binding.py_back
cp $fbHOME/liquid.py $fbHOME/liquid.py_back
cp $fbHOME/tinkerio.py $fbHOME/tinkerio.py_back
cp $fbHOME/parser.py $fbHOME/parser.py_back
cp $fbHOME/data/npt.py $fbHOME/data/npt.py_back
cp $condaHOME/bin/ForceBalance $condaHOME/bin/ForceBalance_back
# patch the mod
cp $modfileHOME/binding.py $fbHOME/binding.py
cp $modfileHOME/liquid.py  $fbHOME/liquid.py
cp $modfileHOME/tinkerio.py $fbHOME/tinkerio.py
cp $modfileHOME/parser.py $fbHOME/parser.py
cp $modfileHOME/data/npt.py $fbHOME/data/npt.py
cp $modfileHOME/minimum_match.py $fbHOME/minimum_match.py
cp $modfileHOME/solvation.py $fbHOME/solvation.py
cp $modfileHOME/ForceBalance $condaHOME/bin/ForceBalance

###
### link Tinker executables
###
cd ./external/
bash link.sh $tinker_bin
tinker_link_path=$(pwd)
cd ..

###
### prepare the bashrc for forcebalance
###
echo -e "#!/usr/bin/bash

. $(conda env list | grep -E "^base " | tr -d '*' | awk '{print $2}')/etc/profile.d/conda.sh
conda activate $conda_env

export TINKERPATH=$tinker_link_path
export tk9home=$tinker9_bin
export JOBPOOL=$(cd ../JobPool && pwd)
" > $fb_bashrc

echo -e '
export PATH=$TINKERPATH:$PATH
export FBBASHRC=`readlink -f "${BASH_SOURCE[0]}"`

VAL=`nvidia-smi &> /dev/null; echo $?`
# check existence
if [ $VAL != 0 ]; then
    echo -e "   \e[101mCUDA utility not installed on `hostname`\e[0m"
else
    export  DYNAMIC="$tk9home/dynamic9"
    export  ANALYZE="$tk9home/analyze9"
    export      BAR="$tk9home/bar9"
    export MINIMIZE="$tk9home/minimize9"
    export TESTGRAD="$tk9home/testgrad9"
fi
' >> $fb_bashrc

echo -e "

Installation completed. To run a ForceBalance job:

     $ source $fb_bashrc
     $ ForceBalance example.in
"