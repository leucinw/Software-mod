# JobPool

Pool management has been automated for ForceBalance jobs if all the customization has been done as stated in this repo. 
There is no need to worry about it if you run ForceBalance jobs only. 

Technically, one pool is enough for all kinds of jobs on the Ren lab cluster, not limited to ForceBalance jobs. If you would like to make use of the pool for other kinds of jobs, 
read the code to find out how, or ask for help.

In the case that you prefer manual management, start a pool by
```
$ ./createPool
```
If the pool is created manually, it has to be closed manually as well by
```
$ ./closePool
```

