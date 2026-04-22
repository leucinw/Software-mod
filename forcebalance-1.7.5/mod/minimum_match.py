""" @package forcebalance.minimum_match interaction energy minimum match fitting module.

@author Chengwen Liu 
@date 03/2023
@date 07/2024
"""
from __future__ import division

from builtins import str
from builtins import range
import os
import shutil
import numpy as np
from forcebalance.nifty import col, eqcgmx, flat, floatornan, fqcgmx, invert_svd, kb, printcool, bohr2ang, commadash, uncommadash, printcool_dictionary
from forcebalance.target import Target
from re import match, sub
from forcebalance.finite_difference import fdwrap, f1d2p, f12d3p, in_fd
from collections import OrderedDict
import sys
from forcebalance.output import getLogger
logger = getLogger(__name__)

class MinimumMatch(Target):

  def __init__(self,options,tgt_opts,forcefield):
    
    super(MinimumMatch,self).__init__(options,tgt_opts,forcefield)
    
    # set scaling factors for E,bond and angle
    self.set_option(None, None, 'energyscale', val=tgt_opts['energyscale'])
    self.set_option(None, None, 'bondscale', val=tgt_opts['bondscale'])
    self.set_option(None, None, 'anglescale', val=tgt_opts['anglescale'])

    self.energyfile = os.path.join(self.tgtdir,"energy.txt")
    self.geometryfile = os.path.join(self.tgtdir,"geometry.txt")
    self.minthrfile = os.path.join(self.tgtdir,"min_threshold.txt")
    self.bondIndices = []
    self.angleIndices = []
    self.eqms = []
    self.dimers = []
    self.monomers = []
    self.bndqms = []
    self.angqms = []
    self.bndmms = []
    self.angmms = []
    self.structures = []
    self.e_weights = []
    self.b_weights = []
    self.a_weights = []
    for line in open(self.energyfile).readlines():
      if "#" not in line:
        sline = line.split()
        self.dimers.append(sline[0])
        self.eqms.append(float(sline[1]))
        self.e_weights.append(float(sline[2]))

    for line in open(self.geometryfile).readlines():
      if "#" not in line:
        sline = line.split()
        self.structures.append(sline[0])
        self.bondIndices.append(sline[1].split(',')[0:2])
        self.angleIndices.append(sline[2].split(',')[0:3])
        self.bndqms.append(float(sline[1].split(',')[2]))
        self.angqms.append(float(sline[2].split(',')[3]))
        self.b_weights.append(float(sline[-2]))
        self.a_weights.append(float(sline[-1]))

    self.minthr = {}
    if os.path.isfile(self.minthrfile):
      logger.info(f"Detected min_threshold file for MinimumMatch target. Using custom RMS gradient thresholds for:\n")
      for line in open(self.minthrfile).readlines():
        if "#" not in line:
          logger.info(line,)
          sline = line.split()
          self.minthr[sline[0]] = sline[1]

    for i in range(len(self.dimers)):
      dimer = self.dimers[i]
      mono1 = dimer.replace('.xyz', '_m01.xyz')
      mono2 = dimer.replace('.xyz', '_m02.xyz')
      self.monomers.append(mono1)
      self.monomers.append(mono2)
      
    self.ndimer = len(self.dimers)
    self.ngeom = len(self.structures)

    self.QMs = [x*self.energyscale for x in self.eqms] + [x*self.bondscale for x in self.bndqms] + [x*self.anglescale for x in self.angqms]

    # QMs array has E + bond + angle
    self.QMs = np.array(self.QMs)
    
    self.eqms = np.array(self.eqms)
    self.bndqms = np.array(self.bndqms)
    self.angqms = np.array(self.angqms)
    
    self.prefactor = 1.0
    self.divisor = 1.0
    for dimer in self.dimers:
      if not os.path.isfile(os.path.join(self.tgtdir, dimer)):
        logger.info(f"dimer structure {dimer} does not exist! exiting ...\n")
        sys.exit()
  
    e_weights = np.array(self.e_weights)
    self.e_weights_norm = e_weights/np.linalg.norm(e_weights)
    
    b_weights = np.array(self.b_weights)
    self.b_weights_norm = b_weights/np.linalg.norm(b_weights)
    
    a_weights = np.array(self.a_weights)
    self.a_weights_norm = a_weights/np.linalg.norm(a_weights)
    
    if not os.path.isfile(os.path.join(self.tgtdir, 'interactions.key')):
      logger.info(f"tinker key file: interactions.key, does not exist! exiting ...\n")
      sys.exit()

  def indicate(self):
    bar = printcool("Minimum Match for Energy (in Kcal/mol)" + '\n%-30s%12s%12s%12s%12s'%('Dimer', 'QM',  'MM', 'Diff', 'Diff(W)'), color=4)
    for i in range(len(self.dimers)):
      diff = self.emms[i]-self.eqms[i]
      logger.info(f"{self.dimers[i]:30s}{self.eqms[i]:12.6f}{self.emms[i]:12.6f}{diff:12.6f}{diff*self.energyscale*self.e_weights_norm[i]:12.6f}\n")
    logger.info(bar)
    
    bar = printcool("Minimum Match for Geometry: Bond (in Angstrom)" + '\n%-30s%12s%12s%12s%12s'%('Dimer', 'QM',  'MM', 'Diff', 'Diff(W)'), color=4)
    for i in range(len(self.structures)):
      qm = self.bndqms[i]
      mm = self.bndmms[i]
      diff = mm - qm
      logger.info(f"{self.structures[i]:30s}{qm:12.6f}{mm:12.6f}{diff:12.6f}{diff*self.bondscale*self.b_weights_norm[i]:12.6f}\n")
    logger.info(bar)
    
    bar = printcool("Minimum Match for Geometry: Angle (in Degree)" + '\n%-30s%12s%12s%12s%12s'%('Dimer', 'QM',  'MM', 'Diff', 'Diff(W)'), color=4)
    for i in range(len(self.structures)):
      qm = self.angqms[i]
      mm = self.angmms[i]
      diff = mm - qm
      logger.info(f"{self.structures[i]:30s}{qm:12.6f}{mm:12.6f}{diff:12.6f}{diff*self.anglescale*self.a_weights_norm[i]:12.6f}\n")
    logger.info(bar)
    return 
  
  def get(self, mvals, AGrad=False, AHess=False):
    """ Evaluate objective function. """
    Answer = {'X':0.0, 'G':np.zeros(self.FF.np), 'H':np.zeros((self.FF.np, self.FF.np))}
    
    # If the weight is zero, turn all derivatives off.
    if (self.weight == 0.0):
      AGrad = False
      AHess = False
   
    os.system(f'cp {os.path.join(self.root, self.tgtdir, "interactions.key")} .')
    for dimer in self.dimers:
      cpstr = f'cp {os.path.join(self.root, self.tgtdir, dimer)} .'
      os.system(cpstr)
      
    with open('run_opt.sh', 'w') as f:
      for dimer in self.dimers:
        thr = self.minthr.get(dimer, 0.01)
        f.write(f'minimize {dimer} -k interactions.key {thr} > {dimer.replace("xyz", "out")}\n')
      f.write('wait\n')
   
    with open('run_split.sh', 'w') as f:
      for dimer in self.dimers:
        f.write(f'lChemFileEditor.py -i {dimer} -m split\n')

    with open('run_ana.sh', 'w') as f:
      for mono in self.monomers:
        f.write(f'analyze {mono} -k interactions.key E > {mono.replace("xyz", "log")}\n')
      for dimer in self.dimers:
        f.write(f'analyze {dimer} -k interactions.key E > {dimer.replace("xyz", "log")}\n')
      f.write('wait\n')
   
    def CalculateBondAngle(txyz, bnd_idx, ang_idx):
      atom2coords = {}
      for line in open(txyz).readlines()[1:]:
        s = line.split()
        atom = s[0]
        x = float(s[2])
        y = float(s[3])
        z = float(s[4])
        atom2coords[atom] = [x,y,z]
      
      coord1 = np.array(atom2coords[bnd_idx[0]])
      coord2 = np.array(atom2coords[bnd_idx[1]])
      bond_length = np.sqrt(np.square(coord1-coord2).sum())
      
      coord1 = np.array(atom2coords[ang_idx[0]])
      coord2 = np.array(atom2coords[ang_idx[1]])
      coord3 = np.array(atom2coords[ang_idx[2]])
      vec21 = coord1 - coord2 
      vec23 = coord3 - coord2
      dot = np.dot(vec21, vec23)
      vec21norm = np.linalg.norm(vec21) 
      vec23norm = np.linalg.norm(vec23) 
      angle_degree = 180.0/np.pi * (np.arccos(dot/(vec21norm*vec23norm)))
      
      return bond_length, angle_degree
    
    def callM(mvals_):
      logger.info("\r")
      MMs = []
      emms = []
      bnds = []
      angs = []
      pvals = self.FF.make(mvals_)
      os.system('sh run_opt.sh')
      os.system('rename xyz_2 xyz *')
      os.system('sh run_split.sh >/dev/null')
      os.system('sh run_ana.sh')
      
      for i in range(len(self.dimers)):
        dimer = self.dimers[i]
        dimerlog = dimer.replace('xyz', 'log')
        mono1log = dimerlog.replace('.log', '_m01.log')
        mono2log = dimerlog.replace('.log', '_m02.log')
        emm = 0.0
        e_mono1 = 0.0
        e_mono2 = 0.0
        for line in open(dimerlog).readlines():
          if 'Total Potential' in line:
            e_dimer = float(line.split()[-2])
        for line in open(mono1log).readlines():
          if 'Total Potential' in line:
            e_mono1 = float(line.split()[-2])
        for line in open(mono2log).readlines():
          if 'Total Potential' in line:
            e_mono2 = float(line.split()[-2])
        emm = e_dimer - e_mono1 - e_mono2
        emms.append(emm)
      
      
      for i in range(len(self.structures)):
        dimer = self.structures[i]
        bnd_idx = self.bondIndices[i]
        ang_idx = self.angleIndices[i]

        # calculate HB bond/angle for each dimer
        bnd, ang = CalculateBondAngle(dimer, bnd_idx, ang_idx)
        bnds.append(bnd)
        angs.append(ang)
      
      MMs = np.array([x*self.energyscale for x in emms] + [x*self.bondscale for x in bnds] + [x*self.anglescale for x in angs])
      return MMs 
    
    logger.info("Executing\r")
    MMs = callM(mvals)
    
    D = MMs - self.QMs
    weights = np.concatenate((self.e_weights_norm, self.b_weights_norm, self.a_weights_norm))
    D = D*weights

    dV = np.zeros((self.FF.np,len(MMs)))
    
    # Do the finite difference derivative.
    if AGrad or AHess:
      for p in self.pgrad:
        dV[p,:], _ = f12d3p(fdwrap(callM, mvals, p), h = self.h, f0 = MMs)
      # Create the force field one last time.
      pvals  = self.FF.make(mvals)
    
    Answer['X'] = np.dot(self.prefactor*D/self.divisor,D/self.divisor)
    for p in self.pgrad:
      Answer['G'][p] = 2*np.dot(self.prefactor*D/self.divisor, dV[p,:]/self.divisor)
      for q in self.pgrad:
        Answer['H'][p,q] = 2*np.dot(self.prefactor*dV[p,:]/self.divisor, dV[q,:]/self.divisor)
    if not in_fd():
      self.MMs = MMs
      self.emms = self.MMs[0:self.ndimer]/self.energyscale
      self.bndmms = self.MMs[self.ndimer:(self.ndimer+self.ngeom)]/self.bondscale
      self.angmms = self.MMs[(self.ndimer+self.ngeom):]/self.anglescale
      self.objective = Answer['X']
    return Answer
