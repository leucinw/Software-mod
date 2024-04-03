""" @package forcebalance.minimum_match interaction energy minimum match fitting module.

@author Chengwen Liu 
@date 03/2023
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

from forcebalance.output import getLogger
logger = getLogger(__name__)

class MinimumMatch(Target):

  def __init__(self,options,tgt_opts,forcefield):
    
    super(MinimumMatch,self).__init__(options,tgt_opts,forcefield)
    
    self.IE = os.path.join(self.tgtdir,"IE.dat")
    self.eqms = []
    self.dimers = []
    self.monomers = []
    for line in open(self.IE).readlines():
      sline = line.split()
      if "#" not in sline:
        self.dimers.append(sline[0])
        self.eqms.append(float(sline[1]))
    for dimer in self.dimers:
      mono1 = dimer.replace('.xyz', '_m01.xyz')
      mono2 = dimer.replace('.xyz', '_m02.xyz')
      self.monomers.append(mono1)
      self.monomers.append(mono2)
    self.eqms = np.array(self.eqms)
    self.prefactor = 1.0
    self.divisor = 1.0
    for dimer in self.dimers:
      if not os.path.isfile(os.path.join(self.tgtdir, dimer)):
        logger.info(f"dimer structure {dimer} does not exist! exiting ...\n")
        sys.exit()
  
  def indicate(self):
    logger.info('%-30s%10s%10s%10s\n'%('Dimer', 'QM',  'MM', 'Diff'))
    for i in range(len(self.dimers)):
      logger.info(f"{self.dimers[i]:30s}{self.eqms[i]:10.4f}{self.emms[i]:10.4f}{(self.eqms[i]-self.emms[i]):10.4f}\n")
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
        f.write(f'minimize {dimer} -k interactions.key 0.1 > {dimer.replace("xyz", "out")}\n')
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
    
    def callM(mvals_):
      logger.info("\r")
      emms = []
      pvals = self.FF.make(mvals_)
      os.system('sh run_opt.sh')
      os.system('rename xyz_2 xyz *')
      os.system('sh run_split.sh >/dev/null 2>split.err')
      os.system('sh run_ana.sh')
      
      for dimer in self.dimers:
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
      emms = np.array(emms)
      return emms 
    
    logger.info("Executing\r")
    emms = callM(mvals)
    
    D = emms - self.eqms
    dV = np.zeros((self.FF.np,len(emms)))
    
    # Do the finite difference derivative.
    if AGrad or AHess:
      for p in self.pgrad:
        dV[p,:], _ = f12d3p(fdwrap(callM, mvals, p), h = self.h, f0 = emms)
      # Create the force field one last time.
      pvals  = self.FF.make(mvals)
    
    Answer['X'] = np.dot(self.prefactor*D/self.divisor,D/self.divisor)
    for p in self.pgrad:
      Answer['G'][p] = 2*np.dot(self.prefactor*D/self.divisor, dV[p,:]/self.divisor)
      for q in self.pgrad:
        Answer['H'][p,q] = 2*np.dot(self.prefactor*dV[p,:]/self.divisor, dV[q,:]/self.divisor)
    if not in_fd():
      self.emms = emms
      self.objective = Answer['X']
    return Answer
