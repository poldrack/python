#!/usr/bin/env python
""" check_all_featdirs.py - check all first-level feat dirs

USAGE: check_featdir <basedir>
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

import os,sys
from check_featdir import *


def usage():
    """ print the docstring and exit"""
    sys.stdout.write(__doc__)
    sys.exit(2)


def main():
    if len(sys.argv)<2:
        usage()

    check_all_featdirs(sys.argv[1])
    
def check_all_featdirs(basedir):
    import numpy as N
   
    if not os.path.exists(basedir):
        print basedir+' does not exist!'
        usage()
    if basedir[-1]=='/':
        basedir=basedir[:-1]
        
    featdirs=[]
    for d in os.listdir(basedir):
        if d[0:3]=='sub':
            for m in os.listdir('%s/%s/model/'%(basedir,d)):
                if m[-5:]=='.feat':
                    #print 'found %s/%s/model/%s'%(basedir,d,m)
                    featdirs.append('%s/%s/model/%s'%(basedir,d,m))

    badness={}
    status={}
    print 'checking %d featdirs...'%len(featdirs)
    for f in featdirs:
        badness[f],status[f]=check_featdir(f)
    if N.sum(badness.values())==0:
        print 'no problems found'
    else:
      for f in featdirs:
        if badness[f]>0:
            print 'problem with %s'%f
            print status[f]
    
    return badness,status


if __name__ == '__main__':
    main()
