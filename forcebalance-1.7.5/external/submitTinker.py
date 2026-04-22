#!/usr/bin/env python

# This is an external program used with ForceBalance for Tinker jobs submission
# The following jobs are supported:
# 1. dynamic_gpu: run with GPU on the `gpu` node
# 2. analyze: run with CPU on the `cpu` node
# 3. dynamic: run with CPU on the `cpu` node

# Chengwen Liu
# Feb 2022

import os
import sys
import time
import datetime as dt
import argparse
import subprocess
import numpy as np

# color
RED = '\033[91m'
ENDC = '\033[0m'
GREEN = '\033[92m'
YELLOW = '\033[93m'

def check_cpu_avail(node, nproc_required):
  
  # assume fully occupied
  tot_occ = 64.0 
  
  try:
    # occupied nproc
    cmd = f'ssh -o stricthostkeychecking=no {node} "top -n1 -b" | grep " R \| S " '
    sp_ret = subprocess.check_output(cmd, timeout=10.0, shell=True).decode("utf-8").split('\n')[:-1]
    tot_occ = 0 
    for r in sp_ret:
      if 'R'  in r:
        occ = r.split('R')[-1].split()[0]
        if occ.replace('.', '', 1).isdigit():
          tot_occ += float(occ)/100.0
      if 'S'  in r:
        occ = r.split('S')[-1].split()[0]
        if occ.replace('.', '', 1).isdigit():
          tot_occ += float(occ)/100.0
    tot_occ = round(tot_occ)
  
  except:
    pass
  
  # assume no CPUs 
  nproc = 0
  try:
    # total nproc
    cmd = f'ssh -o stricthostkeychecking=no {node} "nproc" '
    sp_ret = subprocess.check_output(cmd, timeout=10.0, shell=True).decode("utf-8").split('\n')[0]
    if sp_ret != '':
      nproc = int(sp_ret) 
  except:
    pass

  # limit the usage to 60%
  nproc = int(nproc*0.6)
  
  # available nproc
  avail = False
  avail_nproc = nproc - tot_occ
  if avail_nproc > nproc_required:
    avail = True
  return avail

def check_gpu_avail(node):
  lim_card = None  # None means all
  if "-" in node:
    node, lim_card = node.split("-")
  sp_ret0 = '  '
  sp_ret1 = '  '
  try:
    # occupied nproc
    cmd = f'ssh -o stricthostkeychecking=no {node} "nvidia-smi -a" 2>/dev/null'
    sp_ret0 = subprocess.check_output(cmd, timeout=10.0, shell=True).decode("utf-8").split('\n')[:-1]
    cmd = f'ssh -o stricthostkeychecking=no {node} "nvidia-smi" 2>/dev/null'
    sp_ret1 = subprocess.check_output(cmd, timeout=10.0, shell=True).decode("utf-8").split('\n')[:-1]
  except:
    pass

  tot_cards = []
  occ_cards = []

  twojobs = False
  for r in sp_ret0:
    if ("Product Name" in r):
      if ('RTX 4090' in r):
        twojobs = True
  
  # manual switch on/off for twojobs
  twojobs = False  # False == disable two jobs, True == enable auto switch above
  ncard = 0 
  for r in sp_ret0:
    if 'Attached GPU' in r:
      ncard = int(r.split()[-1])
    
  for i in range(ncard):  
    tot_cards.append(str(i))
    if twojobs:
      tot_cards.append(str(i))
  
  # tinker9/dynamic9/bar9 is for Tinker9
  # dynamic is for openmm
  # gmx is for gromacs
  for r in sp_ret1:        
    if ('tinker9' in r) or ('dynamic' in r) or ('dynamic9' in r) or ('gmx' in r) or ('bar9' in r) or ('python' in r) or ("terachem" in r):
      occ_cards.append(r.split()[1])
  
  ava_cards = tot_cards
  if lim_card:
      ava_cards = [c for c in ava_cards if c == lim_card]
  
  if occ_cards != []:
    for c in occ_cards:
      if c in ava_cards:
        ava_cards.remove(c)
  return ava_cards 

def submit_jobs(jobcmds, jobtype):
  njob_pointer = 0
  if jobtype == "CPU":
    for i in range(len(cpu_node_list)):
      if njob_pointer >= len(jobcmds): break
      if check_cpu_avail(cpu_node_list[i], nproc):
        cmdstr = f"ssh -o stricthostkeychecking=no {cpu_node_list[i]} '" + jobcmds[njob_pointer] +  "' &"
        subprocess.run(cmdstr, shell=True)
        jobcmds[njob_pointer] = 'x'
        print(f"[{time.asctime()}]   --> {cmdstr}")
        njob_pointer += 1
    # wait for 15 sec. to let job appear on a node
    # i.e., shown by top command to avoid CPU overloading 
    time.sleep(15.0)
  else:
    for i in range(len(gpu_node_list)): 
      if njob_pointer >= len(jobcmds): break
      ava_cards = check_gpu_avail(gpu_node_list[i]) 
      if ava_cards != []:
        for card in ava_cards:
          cuda_device = f'export CUDA_VISIBLE_DEVICES="{card}"'
          pci_bus_id = 'export CUDA_DEVICE_ORDER=PCI_BUS_ID'
          if njob_pointer < len(jobcmds):
            cmdstr = f"ssh -o stricthostkeychecking=no {gpu_node_list[i].split('-')[0]} '{pci_bus_id}; {cuda_device}; {jobcmds[njob_pointer]} ' &"
            subprocess.run(cmdstr, shell=True)
            jobcmds[njob_pointer] = 'x'
            print(f"[{time.asctime()}]   --> {cmdstr}")
            njob_pointer += 1
    # wait for 30 sec. to let job appear on a node
    # i.e., shown by nvidia-smi command
    # to avoid submitting multiple jobs on one GPU card
    time.sleep(30.0)
     
  # return the remainig jobcmds
  tmp = [] 
  for jobcmd in jobcmds:
    if jobcmd != 'x':
      tmp.append(jobcmd)
  jobcmds = tmp
  return jobcmds

def is_nighttime(start=23, end=6):
    now = dt.datetime.now().time()
    start = dt.time(start, 0)
    end = dt.time(end, 0)
    if start <= end:
        return now >= start and now < end
    else:
        return now >= start or now < end

def read_node_list():
  g_list = []
  c_list = []
  node_list = f"{os.path.dirname(os.path.abspath(__file__))}/nodes.dat"
  lines = open(node_list).readlines()
  for line in lines:
    line = line.strip()
    if not line or line.startswith("#"):
      continue
    s = line.split()
    node_type = s[0]
    node_name = s[1]
    if is_nighttime() and "-" in node_type:
        node_type_split = node_type.rsplit("-", 1)
        if node_type_split[1] == "N":
            node_type = node_type_split[0]
    if node_type == "GPU":
      g_list.append(s[1])
    elif node_type == "CPU":
      c_list.append(s[1])
  return g_list, c_list

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-x', dest = 'jobshs',  nargs='+', help = "Scripts to run", default = []) 
  parser.add_argument('-c', dest = 'jobcmds',  nargs='+', help = "Commands to run", default = []) 
  parser.add_argument('-p', dest = 'paths',  nargs='+', help = "Working directories in the same order as jobshs or jobcmds", default=[]) 
  parser.add_argument('-t', dest = 'type',  help = "Job type", choices =['CPU', 'GPU'], required=True, type = str.upper) 
  parser.add_argument('-n', dest = 'nproc',  help = "Nproc requested", default=2, type=int) 
  parser.add_argument('-nodes', dest = 'nodes',  nargs='+', help = "node list", default = []) 
  args = vars(parser.parse_args())
  jobshs = args["jobshs"]
  jobcmds = args["jobcmds"]
  jtyp = args["type"]
  global nproc,paths
  paths = args["paths"]
  nproc = args["nproc"]
  nodes = args["nodes"]  

  global gpu_node_list
  global cpu_node_list
  
  workingdir = os.getcwd()

  if len(paths) == 0: 
    workingdir = os.getcwd()
    if jobcmds != []:
      for i in range(len(jobcmds)):
        paths.append(workingdir) 
    if jobshs != []:
      for i in range(len(jobshs)):
        paths.append(workingdir) 
  elif len(paths) == 1:
    workingdir = paths[0] 
    if jobcmds != []:
      for i in range(len(jobcmds)):
        paths.append(workingdir) 
    if jobshs != []:
      for i in range(len(jobshs)):
        paths.append(workingdir) 
  else:
    if jobcmds != []:
      if len(jobcmds) != len(paths):
        sys.exit("Error: number of paths and jobcmds are not the same!")
    if jobshs != []:
      if len(jobshs) != len(paths):
        sys.exit("Error: number of paths and jobshs are not the same!")
  
  # submit cmds
  if jobcmds != []:
    for i in range(len(jobcmds)):
      workingdir = paths[i]
      jobcmds[i] = f"cd {workingdir}; {jobcmds[i]}"
  
  # submit scripts 
  if jobshs != []:
    for i in range(len(jobshs)):
      workingdir = paths[i]
      jobsh = jobshs[i]
      jobcmds.append(f'cd {workingdir}; sh {jobsh}')
  
  print(f"[{time.asctime()}]", GREEN + f"   === Submitting {jtyp} Jobs to Ren Lab Clusters === " + ENDC)
  if nodes != []:
    gpu_node_list = nodes
    cpu_node_list = nodes
  else:
    gpu_node_list, cpu_node_list = read_node_list()
  jobcmds = submit_jobs(jobcmds, jtyp)
  while jobcmds != []:
    time.sleep(5.0)
    jobcmds = submit_jobs(jobcmds, jtyp)
