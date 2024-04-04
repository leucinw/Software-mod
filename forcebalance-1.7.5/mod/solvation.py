""" @package forcebalance.solvation Solvation free energy fitting module for Tinker

@author Chengwen Liu 
@date 04/2021
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
        ## Read in the reference data
        self.read_reference_data()
        # Number of time steps in the liquid "equilibration" run
        self.set_option(tgt_opts,'liquid_eq_steps',forceprint=True)
        # Number of time steps in the liquid "production" run
        self.set_option(tgt_opts,'liquid_md_steps',forceprint=True)
        ## logger info 
        logger.info("Solvation free energies from BAR simulation\n")
        ## External script to run BAR simulations 
        self.barsim = "/home/liuchw/Documents/Github.leucinw/autoBAR/autoBAR.py"
        ## Extra files to be linked into the temp-directory.
        self.solvfiles = [self.liquid_xyz, self.gas_xyz, self.settings_yaml]
        ## Check the existence of files
        for f in self.solvfiles:
            if not os.path.exists(os.path.join(self.root, self.tgtdir, f)):
                logger.error("%s doesn't exist; please provide this option\n" % f)
                raise RuntimeError

    def post_init(self, options):
        # Prepare the temporary directory.
        self.prepare_temp_directory()
    
    def read_reference_data(self):
        """ Read the reference solvation data from a file. """
        # Read the SFE data file for experimental value and weight 
        for line in open(self.datafile).readlines():
            s = line.split()
            self.expsfe = float(s[-1])

    def prepare_temp_directory(self):
        """ Prepare the temporary directory by copying in important files. """
        abstempdir = os.path.join(self.root,self.tempdir)
        for f in self.solvfiles:
            LinkFile(os.path.join(self.root, self.tgtdir, f), os.path.join(abstempdir, f))

    def indicate(self):
        """ Print qualitative indicator. """
        banner = "Solvation free energies (kcal/mol)"
        data = self.expsfe
        print(data)

    def solvation_driver_sp(self):
        """ Get SFE from BAR simulation result""" 
        cmdstr = "python %s auto" %self.barsim
        os.system(cmdstr)
        sfe = 0.0
        while True:
          if os.path.isfile(os.path.join(self.root,self.rundir,"result.txt")):
            break
          else:
            time.sleep(30.0)
        sfe = float(open("result.txt").readlines()[-1].split()[-2])
        if abs(sfe) < 0.01:
          print(f"Warnning: free energy {sfe} is too small!")
        return sfe

    def get_sp(self, mvals, AGrad=False, AHess=False):
        """ Get the SFE and its first derivative using numerical method""" 
        def get_sfe(mvals_):
            self.FF.make(mvals_)
            self.calsfe = self.solvation_driver_sp()
            return self.calsfe 
        D = get_sfe(mvals) - self.expsfe
        G = np.zeros(self.FF.np)

        mvals_ = mvals
        if AGrad or AHess:
            h = self.h
            f0 = calc_sfe
            for i in self.pgrad:
                mvals_[i] += -abs(h)
                minus = get_sfe(mvals)
                mvals_[i] += abs(h)*2.0
                plus = get_sfe(mvals)
                mvals_[i] += -abs(h)
                G[i] = (plus - minus)/(h*2.0)
        return D,G 


    def get(self, mvals, AGrad=True, AHess=False):
         
        """ Evaluate objective function. """
        Answer = {'X':0.0, 'G':np.zeros(self.FF.np), 'H':np.zeros((self.FF.np, self.FF.np))}
        D, G = self.get_sp(mvals, AGrad, AHess)
        Answer['X'] = D
        if AGrad:
          Answer['G'] = G
          for p in self.pgrad:
            Answer['G'][p] = 2*np.dot(D, dD[p,:]) / self.denom**2 
            for q in self.pgrad:
              Answer['H'][p,q] = 2*np.dot(dD[p,:], dD[q,:]) / self.denom**2 
        return Answer
