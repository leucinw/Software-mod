""" @package forcebalance.solvation Solvation free energy fitting module for Tinker

@author Chengwen Liu 
@date 04/2021
@date 10/2025
"""
from __future__ import division

from builtins import range
import os
import shutil
import time
import numpy as np
from copy import deepcopy
from forcebalance.target import Target
from forcebalance.molecule import Molecule
from re import match, sub
from forcebalance.finite_difference import fdwrap, f1d2p, f12d3p, in_fd
from collections import defaultdict, OrderedDict
from forcebalance.nifty import getWorkQueue, queue_up, LinkFile, printcool, link_dir_contents, lp_dump, lp_load, _exec, kb, col, flat, uncommadash, statisticalInefficiency, isfloat

from forcebalance.output import getLogger
logger = getLogger(__name__)

class Solvation(Target):

    """ Subclass of Target for fitting force fields to solvation free energies."""
    
    def __init__(self,options,tgt_opts,forcefield):
        """Initialization."""
        
        # Initialize the SuperClass!
        super(Solvation,self).__init__(options,tgt_opts,forcefield)
        
        #======================================#
        # Options that are given by the parser #
        #======================================#
        self.set_option(tgt_opts,'sfedata_txt','datafile')
        ## The vdata.txt file that contains the solvations.
        self.datafile = os.path.join(self.tgtdir,self.datafile)
        # set the autobarpath variable
        self.set_option(tgt_opts,'autobar_path','autobarpath')
        # set the run_dynamic_every_iter variable
        self.set_option(tgt_opts,'run_dynamic_every_iter','dynamicflag')
        self.dynamicflag = int(self.dynamicflag)
        ## Read in the reference data
        self.read_reference_data()
        ## logger info 
        logger.info("Solvation free energies from BAR simulation\n")


    def post_init(self, options):
        # Prepare the temporary directory.
        self.prepare_temp_directory()
    
    def read_reference_data(self):
        """ Read the reference solvation data from a file. """
        # Read the SFE data file for experimental value and weight 
        for line in open(self.datafile).readlines():
          if '#' not in line and line.strip():
            s = line.split()
            self.expsfe = float(s[-1])

    def prepare_temp_directory(self):
        """ Prepare the temporary directory by copying in important files. """
        abstempdir = os.path.join(self.root,self.tempdir)
        
        # copy the necessary input files for autoBAR
        for f in self.solvfiles:
          os.system(f"cp {os.path.join(self.root, self.tgtdir, f)} {os.path.join(abstempdir, f)}")

    def indicate(self):
        bar = printcool("Solvation Free Energy (in Kcal/mol)" + '%12s%12s%12s\n'%('Expt.',  'Calc.', 'Diff'), color=4)
        diff = self.calsfe - self.expsfe
        logger.info('%12.4f%12.4f%12.4f\n'%(self.expsfe, self.calsfe, diff))
        logger.info(bar)
  
    def solvation_driver_sp(self):
        """ Get SFE from BAR simulation result""" 
        
        if os.path.isfile(os.path.join(self.root,self.rundir,"result.txt")):
          os.system(f'rm -f {os.path.join(self.root,self.rundir,"result.txt")}')
       
        # if dynamicflag == 0 and iter != 0 
        # link files from the iter_0000 directory
        if (self.dynamicflag == 0) and ('iter_0000' not in self.rundir):
          refdir = self.rundir[:-4] + '0000'

          # check if gas/ directory exists
          ref_gas_dir = os.path.join(self.root,refdir, 'gas')
          if os.path.isdir(ref_gas_dir):
            current_gas_dir = os.path.join(self.root,self.rundir, 'gas')
            os.system(f'mkdir -p {current_gas_dir}')
            files = os.listdir(ref_gas_dir)
            for f in files:
              if (('.log' in f) or ('.arc' in f) or ('.bar' in f) or ('.ene' in f) or ('.key' in f)) and (('e000-' in f) or ('-v100') in f):
                os.system(f"ln -sf {os.path.join(ref_gas_dir, f)} {os.path.join(current_gas_dir, f)}")
          
          # check if liquid/ directory exists
          ref_liquid_dir = os.path.join(self.root,refdir, 'liquid')
          if os.path.isdir(ref_liquid_dir):
            current_liquid_dir = os.path.join(self.root,self.rundir, 'liquid')
            os.system(f'mkdir -p {current_liquid_dir}')
            files = os.listdir(ref_liquid_dir)
            for f in files:
              if (('.log' in f) or ('.arc' in f) or ('.bar' in f) or ('.ene' in f) or ('.key' in f)) and (('e000-' in f) or ('-v100') in f):
                os.system(f"ln -sf {os.path.join(ref_liquid_dir, f)} {os.path.join(current_liquid_dir, f)}")

          # copy parameter file from iter_0000
          iter0prm = self.FF.fnms[0] + '_iter0'
          os.system(f'cp {os.path.join(self.root, refdir, self.FF.fnms[0])} {os.path.join(self.root, self.rundir, iter0prm)}')
          os.system(f"cp {iter0prm} {self.FF.fnms[0]}")

        # when run autoBAR, first step is to run minimize, which requires a prm file

        cmdstr = "python %s auto" %self.autobarpath
        rtn = os.system(cmdstr)
        if rtn != 0:
          raise RuntimeError("autoBAR execution failed with return code %d." % rtn)

        sfe0 = 0.0
        sfe1 = np.zeros(self.FF.np)
        feps = []
        while True:
          if os.path.isfile(os.path.join(self.root,self.rundir,"result.txt")):
            break
          else:
            time.sleep(30.0)
        
        lines = open('result.txt').readlines()

        for line in lines:
          if 'SUM OF THE TOTAL FREE ENERGY' in line:
            sfe0 = float(line.split()[-2])
          if 'FEP_' in line:
            feps.append(float(line.split()[-1]))

        # for iter_0001, use FEP_01 as sfe0
        if (self.dynamicflag == 0) and ('iter_0000' not in self.rundir):
          sfe0 = feps[0]
          sfe1 = np.array(feps[1:])
        else:
          sfe1 = np.array(feps)

        return sfe0, sfe1

    def get_sp(self, mvals, AGrad=False, AHess=False):
        """ Get the SFE and its first derivative using finite difference method"""
        
        if (self.dynamicflag == 0) and ('iter_0000' not in self.rundir):
          self.FF.make(mvals)
          os.rename(self.FF.fnms[0],  f"{self.FF.fnms[0]}_01")
        else:
          self.FF.make(mvals)
          
        f0, _ = self.solvation_driver_sp()  
        
        self.calsfe = f0

        # D is the different between calculated and reference values
        D = f0 - self.expsfe
        # initialize the G (gradient array)
        G = np.zeros(self.FF.np)
        
        # do FEP to get the gradient
        if AGrad or AHess:
          prmprefix = self.FF.fnms[0].split('.prm')[0]
          # backup the current parameter file
          os.rename(prmprefix +".prm", prmprefix + ".prm.org")
          
          h = self.h
          idx = 1
          if (self.dynamicflag == 0) and ('iter_0000' not in self.rundir):
            idx = 2
          
          # first make all purterbed prm files
          for i in self.pgrad:
            mvals_= mvals
            
            # add the numerical difference
            mvals_[i] += abs(h) 
            self.FF.make(mvals_)
            os.rename(prmprefix + ".prm", prmprefix + f".prm_{idx:02d}")
            idx += 1
            
            # add the numerical difference
            mvals_[i] -= 2.0*abs(h) 
            self.FF.make(mvals_)
            os.rename(prmprefix + ".prm", prmprefix + f".prm_{idx:02d}")
            idx += 1

            # change to the original value
            mvals_[i] += abs(h)
         
          # change the name back
          os.rename(prmprefix + ".prm.org", prmprefix +".prm")
          # fp has the size of FF parameters
          _,fp = self.solvation_driver_sp()
          
          print('LENGTH CHECK:', len(fp), 2*self.FF.np)
          assert len(fp) == 2*(self.FF.np)
          
          # here we use central difference
          for i in range(self.FF.np):
            plus = fp[2*i]
            minus = fp[2*i+1]
            G[i] = (plus - minus) / (2*h)
        return D,G 


    def get(self, mvals, AGrad=True, AHess=False):
         
        """ Evaluate objective function. """
        printcool("Target: %s - running autoBAR program" % (self.name), color=0)

        Answer = {'X':0.0, 'G':np.zeros(self.FF.np), 'H':np.zeros((self.FF.np, self.FF.np))}
        D, dD = self.get_sp(mvals, AGrad, AHess)
        
        Answer['X'] = D*D
        if AGrad:
          Answer['G'] = D*dD
        return Answer
