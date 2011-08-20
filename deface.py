#!/usr/bin/env python
""" deface an image using FSL
USAGE:  deface <filename to deface>
"""

import nibabel 
import os,sys
import numpy as N

import subprocess

def run_shell_cmd(cmd,cwd=[]):
    """ run a command in the shell using Popen
    """
    if cwd:
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,cwd=cwd)
    else:
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    for line in process.stdout:
             print line.strip()
    process.wait()
    
def usage():
    """ print the docstring and exit"""
    sys.stdout.write(__doc__)
    sys.exit(2)


template='/corral/utexas/poldracklab/data/facemask/mean_reg2mean.nii.gz'
facemask='/corral/utexas/poldracklab/data/facemask/facemask.nii.gz'

if len(sys.argv)<2:
#    usage()
    infile='mprage.nii.gz'
else:
    infile=sys.argv[1]

if os.environ.has_key('FSLDIR'):
    FSLDIR=os.environ['FSLDIR']
else:
    print 'FSLDIR environment variable must be defined'
    sys.exit(2)
    

#temp=nibabel.load(template)

#tempdata=temp.get_data()

#facemask=N.ones((91,109,91))

#facemask[:,71:,:18]=0

#facemaskimg=nibabel.Nifti1Image(facemask,temp.get_affine())
#facemaskimg.to_filename('facemask.nii.gz')

cmd='flirt -in %s -ref %s -omat tmp_mask.mat'%(template,infile)
print 'Running: '+cmd
run_shell_cmd(cmd)

cmd='flirt -in %s -out facemask_tmp -ref %s -applyxfm -init tmp_mask.mat'%(facemask,infile)
print 'Running: '+cmd
run_shell_cmd(cmd)


cmd='fslmaths %s -mul facemask_tmp %s'%(infile,infile.replace('.nii.gz','_defaced.nii.gz'))
print 'Running: '+cmd
run_shell_cmd(cmd)

os.remove('facemask_tmp.nii.gz')
os.remove('tmp_mask.mat')
