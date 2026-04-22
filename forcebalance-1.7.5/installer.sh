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
tinker_bin=/home/yw24267/programs/tinker/Tinker8/latest/bin
tinker9_bin=/home/yw24267/programs/tinker/Tinker9/latest/build
# the name of the conda environment for forcebalance
conda_env=FB17
# where to put the generated bashrc file
fb_bashrc=~/.bashrc.FB17
#################################################################################################

###
### create conda environment, install forcebalance 1.7.5, and patch the mod
###
conda create -n $conda_env python=3.7 forcebalance==1.7.5 pymbar==3.0.5 ruamel=0.17 pathos -c conda-forge -y
condaHOME=$(conda env list | grep -E "^$conda_env " | tr -d '*' | awk '{print $2}')
fbHOME=$condaHOME/lib/python3.7/site-packages/forcebalance
modfileHOME=$(cd ./mod && pwd)
# back up the original files
cp $fbHOME/binding.py $fbHOME/binding.py_back
cp $fbHOME/liquid.py $fbHOME/liquid.py_back
cp $fbHOME/tinkerio.py $fbHOME/tinkerio.py_back
cp $fbHOME/parser.py $fbHOME/parser.py_back
cp $fbHOME/objective.py $fbHOME/objective.py_back
cp $fbHOME/molecule.py $fbHOME/molecule.py_back
cp $fbHOME/data/npt.py $fbHOME/data/npt.py_back
cp $fbHOME/data/md_ism_hfe.py $fbHOME/data/md_ism_hfe.py_back
cp $condaHOME/bin/ForceBalance $condaHOME/bin/ForceBalance_back
# patch the mod
cp --remove-destination $modfileHOME/binding.py $fbHOME/binding.py
cp --remove-destination $modfileHOME/liquid.py  $fbHOME/liquid.py
cp --remove-destination $modfileHOME/tinkerio.py $fbHOME/tinkerio.py
cp --remove-destination $modfileHOME/parser.py $fbHOME/parser.py
cp --remove-destination $modfileHOME/objective.py $fbHOME/objective.py
cp --remove-destination $modfileHOME/molecule.py $fbHOME/molecule.py
cp --remove-destination $modfileHOME/data/npt.py $fbHOME/data/npt.py
cp --remove-destination $modfileHOME/data/md_ism_hfe.py $fbHOME/data/md_ism_hfe.py
cp --remove-destination $modfileHOME/minimum_match.py $fbHOME/minimum_match.py
cp --remove-destination $modfileHOME/solvation.py $fbHOME/solvation.py
cp --remove-destination $modfileHOME/ForceBalance $condaHOME/bin/ForceBalance

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
export AUTOBARPATH=$(readlink -f ../autoBAR/autoBAR.py)
" > $fb_bashrc

echo -e 'export PATH=$TINKERPATH:$PATH
# minimum_match invokes some of CWs scripts.
export PATH=$PATH:/home/liuchw/bin/
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

ForceBalance 1.7.5 has been installed into the conda environment $conda_env.
The bashrc file for ForceBalance has been generated at $fb_bashrc.
The Tinker executables have been linked into $tinker_link_path,
which is also recorded in $fb_bashrc as \`TINKERPATH\`.
Please make sure \`TINKERPATH\` and \`tk9home\` in $fb_bashrc are up to date before running jobs.
Please set the \`tinkerpath\` in your ForceBalance input file (e.g., example.in)
as the same to \`TINKERPATH\`, so that a consistent Tinker installation is invoked throughout the job.
Installation completed. To run a ForceBalance job:

     $ source $fb_bashrc
     $ ForceBalance example.in
"
