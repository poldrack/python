#!/usr/bin/env python
""" launch.py - a python function to launch SGE jobs on TACC Lonestar
this is a function version of the launch command line script 

"""

## Copyright 2011, Russell Poldrack. All rights reserved.

## Redistribution and use in source and binary forms, with or without modification, are
## permitted provided that the following conditions are met:

##    1. Redistributions of source code must retain the above copyright notice, this list of
##       conditions and the following disclaimer.

##    2. Redistributions in binary form must reproduce the above copyright notice, this list
##       of conditions and the following disclaimer in the documentation and/or other materials
##       provided with the distribution.

## THIS SOFTWARE IS PROVIDED BY RUSSELL POLDRACK ``AS IS'' AND ANY EXPRESS OR IMPLIED
## WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
## FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL RUSSELL POLDRACK OR
## CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
## CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
## SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
## ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
## NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
## ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.



import argparse
import sys,os
from tempfile import *
import subprocess
from launch_qsub import *


def main():
    if len(sys.argv)<2:
        usage()
        
    c,parser=SetupParser()
    argdata=parser.parse_known_args(sys.argv[1:],namespace=c)
    
     # first check for .launch file in home directory
    if os.path.exists(os.path.expanduser('~')+'/.launch_user') and not c.ignoreuser:
        f=open(os.path.expanduser('~')+'/.launch_user')
        for cmd in f.readlines():
                print cmd
                #sys.argv.append(cmd.strip())
                parser.parse_args([cmd.strip()],namespace=c)
        f.close()


    if not c.projname:
        print 'You must specify a project name using the -j flag - exiting'
        sys.exit(0)

    if len(argdata[1])>0:
        cmd=' '.join(argdata[1])
    else:
        cmd=''


    launch_qsub(cmd,script_name=c.script_name,runtime=c.runtime,ncores=c.ncores,parenv=c.parenv,jobname=c.jobname,projname=c.projname,queue=c.queue,email=c.email,qsubfile=c.qsubfile,keepqsubfile=c.keepqsubfile,ignoreuser=c.ignoreuser,test=c.test,compiler=c.compiler,verbose=1,parser=parser,c=c)
    


if __name__ == '__main__':
    main()
