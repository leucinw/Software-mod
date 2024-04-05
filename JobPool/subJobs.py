#!/usr/bin/env python
# submit jobs if there are any in the pool
# 

import os
import sys
import time
import subprocess 
from datetime import datetime

if __name__ == "__main__":
  sleeptime = 10.0
  if sys.argv[1] == "GPU":
    sleeptime += 10.0
  submitters_file = ".submitters"
  if len(sys.argv) > 2:
    submitters_file += sys.argv[2]

  def _worker():
    os.system("./lock get "+sys.argv[1])
    # print("Got Lock j", flush=True)
    try:
      cmd = "grep ' " + sys.argv[1] + " ' *.sh -l 2>/dev/null" 
      sp_ret = subprocess.check_output(cmd, shell=True).decode("utf-8").split('\n')[:-1]
      for sp in sp_ret:
        subcmd = f"sh {sp}; rm {sp}"
        os.system(subcmd)
        print(subcmd, flush=True)
    except:
      pass
    finally:
      os.system("./lock release "+sys.argv[1])
  
  while os.path.exists(submitters_file):
    _worker()
    time.sleep(sleeptime)
  _worker()
