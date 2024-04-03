export libdir=/home/liuchw/anaconda3/envs/FB17/lib/python3.7/site-packages/forcebalance
export curdir=/home/liuchw/Documents/Github.leucinw/Software-mod/forcebalance-1.7.5
action=$1

$action $libdir/binding.py      $curdir/binding.py
$action $libdir/liquid.py       $curdir/liquid.py
$action $libdir/parser.py       $curdir/parser.py
$action $libdir/tinkerio.py     $curdir/tinkerio.py
$action $libdir/data/npt.py     $curdir/data/npt.py
$action $libdir/minimum_match.py      $curdir/minimum_match.py
$action $libdir/solvation.py      $curdir/solvation.py
