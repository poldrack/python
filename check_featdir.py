#!/usr/bin/env python
""" check_featdir.py - check a first-level feat dir

USAGE: check_featdir <featdir>
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
from mvpa.misc.fsl.base import read_fsl_design


def usage():
    """ print the docstring and exit"""
    sys.stdout.write(__doc__)
    sys.exit(2)

def main():
    if len(sys.argv)<2:
        usage()

    badness,status=check_featdir(sys.argv[1])
    if badness==0:
        print 'no problems found'
    else:
        print 'problem found'
        print status

def check_featdir(featdir):

    if not os.path.exists(featdir+'/design.fsf'):
        print featdir+'/design.fsf does not exist!'
        usage()
    
    design=read_fsl_design(featdir+'/design.fsf')

    status={}
    badness=0
    
    status['subdirs']={}
    subdirs_to_check=['reg','stats']
    for s in subdirs_to_check:
        if not os.path.exists(featdir+'/'+s):
            status['subdirs'][s]=0
            print 'missing: '+featdir+'/'+s
            badness+=1
        else:
            status['subdirs'][s]=1

    status['files']={}
    files_to_check=['filtered_func_data.nii.gz','stats/res4d.nii.gz','reg/example_func2standard.mat','reg/highres2standard_warp.nii.gz']
    for s in files_to_check:
        if not os.path.exists(featdir+'/'+s):
            status['files'][s]=0
            print 'missing: '+featdir+'/'+s
            badness+=1
        else:
            status['files'][s]=1


    status['zstats']={}
    ncontrasts=design['fmri(ncon_orig)']
    for c in range(ncontrasts):
        if not os.path.exists(featdir+'/stats/zstat%d.nii.gz'%int(c+1)):
            status['zstats'][c+1]=0
            badness+=1
        else:
            status['zstats'][c+1]=1
            
    if badness>0:
        print 'found %d problems'%badness

    return badness,status

if __name__ == '__main__':
    main()
