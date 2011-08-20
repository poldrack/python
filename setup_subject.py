#!/usr/bin/env python
""" setup_subject.py - script to process a complete MRI dataset
- based on the setup_subject shell script from UCLA

requires:
- pydicom (http://code.google.com/p/pydicom/)
- launch_qsub.py (https://github.com/poldrack/python)
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


import os,sys,time

import argparse
from launch_qsub import *
from tempfile import *
import subprocess
import dicom
from pprint import pprint

def usage():
    """ print the docstring and exit"""
    sys.stdout.write(__doc__)
    sys.exit(2)

def save_dicom_info(outfile,dcminfo):
    f=open(outfile,'w')
    pprint(dcminfo,stream=f)
    f.close()
    
class C(object):
    pass

def SetupParser():
    c=C()
    parser = argparse.ArgumentParser(description='process fmri dataset')

    parser.add_argument('-e','--origdicomdir',help='location of dicom files (if unset, will scp from workerbee)',dest='origdicomdir')
    
    parser.add_argument('-b','--basedir',help='base dir for subject dirs',dest='basedir',default='/corral/utexas/poldracklab/data')
    parser.add_argument('-p','--projdir',help='project directory',dest='projdir',required=True)
    
    parser.add_argument('-s','--subcode',help='subject code',dest='subcode',required=True)

    parser.add_argument('-v','--verbose',help='print extra info',dest='verbose',default=False, action="store_true")

    parser.add_argument('-o','--overwrite',help='overwrite existing files',dest='overwrite',default=False, action="store_true")

    parser.add_argument('-t','--testmode',help='do not run commands',dest='test',default=False, action="store_true")
    parser.add_argument('-f','--process_func',help='process functional data',dest='process_func_data',default=1,type=int)
    parser.add_argument('-a','--process_struct',help='process structural data',dest='process_struct_data',default=1,type=int)
    parser.add_argument('-d','--process_dti',help='process dti data',dest='process_dti',default=1,type=int)
    parser.add_argument('-c','--convert_dicom',help='do DICOM conversion',dest='convert_dicom',default=1,type=int)
    
    return c,parser


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
    
def main():
    """ setup_subject: process full MR dataset on TACC

    """
    
    #sys.argv=[sys.argv[0],'-b','/corral/utexas/poldracklab/data/test','-s','M1_034_TS1','-t']
    #if 1==1:
#    if len(sys.argv)<3:
#        usage()

    fsld_script='/corral/utexas/poldracklab/software_lonestar/fsld/fsld_raw.R'
    launchinfo={}
    
    c,parser=SetupParser()
    argdata=parser.parse_args(sys.argv[1:],namespace=c)
    c.basedir=c.basedir+'/'+c.projdir
    # setup variables
    verbose=c.verbose
    overwrite=c.overwrite

#    process_func_data=1
#    process_struct_data=1
#    convert_dicom=1
#    process_dti=1


    # test basedir
    if not os.path.exists(c.basedir):
        print 'basedir %s does not exist!'
        sys.exit(2)
    elif verbose:
        print 'using base dir: %s'%c.basedir

    # ensure trailing slash
    if not c.basedir[-1]=='/':
        c.basedir=c.basedir+'/'
        
    subdir=c.basedir+c.subcode+'/'
    if os.path.exists(subdir):
        if not overwrite:
            print 'subdir %s already exists! please delete first'%subdir
            sys.exit(2)
    else:
        os.mkdir(subdir)

    subdirs=['behav','BOLD','model','anatomy','log','raw','dicom']
    for s in subdirs:
        if not os.path.exists(subdir+s):
            os.mkdir(subdir+s)

    # set up logging
    localtime = time.asctime( time.localtime(time.time()) )
    localtime='_'.join(localtime.split(' ')[1:])
    logfile='%slog/setup_log_%s'%(subdir,localtime)
    logfile_fid=open(logfile,'w')
    if verbose:
        print 'using logfile %s'%logfile

    
    if not c.origdicomdir:
        # download data from workerbee
        wbdir='/data1/poldracklab/DICOM/'+c.subcode
        print 'copying data from workerbee:%s/ ...'%wbdir
        src='workerbee.clm.utexas.edu:%s/"*"'%wbdir
        dest='%s/dicom'%subdir
        process=subprocess.Popen('scp -r %s %s'%(src,dest), shell=True, stdout=subprocess.PIPE)
        for line in process.stdout:
                 print line.strip()
        process.wait()
        if os.listdir(dest):
            c.origdicomdir=dest
            logfile_fid.write('Data copied from %s to %s\n'%(src,dest))
        else:
            print 'problem downloading files'
            sys.exit(2)
    
    # get info about data
    if not os.path.exists(c.origdicomdir):
        print 'DICOM dir %s does not exist!'%c.origdicomdir
        sys.exit(2)

    series_info={}
    seriescode_dict={}
    dicomdir_dict={}
    dicom_cvrt='%s/log/dicom_convert.sh'%(subdir)
    dicom_cvrt_fid=open(dicom_cvrt,'w')
    niifile={}
    for dcdir in os.listdir(c.origdicomdir):
            flist=os.listdir(c.origdicomdir+'/'+dcdir)
            dcminfo=dicom.read_file(c.origdicomdir+'/'+dcdir+'/'+flist[0])
            dicomdir_dict[dcminfo.SeriesNumber]=c.origdicomdir+'/'+dcdir+'/'
            series_info[dcminfo.SeriesNumber]=dcminfo
            seriescode=dcminfo.SeriesDescription.replace(' ','_').replace('/','_')
            # create dicom conversion for this series
            #dicom_cvrt_fid.write('dcm2nii -o %s/raw/%03d_%s %s\n'%(subdir,dcminfo.SeriesNumber,seriescode,c.origdicomdir+'/'+dcdir))
            dicom_cvrt_fid.write('mri_convert --out_orientation RAS  %s %s/raw/%03d_%s/%03d_%s.nii.gz\n'%(c.origdicomdir+'/'+dcdir+'/'+flist[0],subdir,dcminfo.SeriesNumber,seriescode,dcminfo.SeriesNumber,seriescode))
            seriescode_dict[dcminfo.SeriesNumber]='%03d_%s'%(dcminfo.SeriesNumber,seriescode)
            niifile['%03d_%s'%(dcminfo.SeriesNumber,seriescode)]='%s/raw/%03d_%s/%03d_%s.nii.gz'%(subdir,dcminfo.SeriesNumber,seriescode,dcminfo.SeriesNumber,seriescode)
            if not os.path.exists('%s/raw/%03d_%s'%(subdir,dcminfo.SeriesNumber,seriescode)):
                os.mkdir('%s/raw/%03d_%s'%(subdir,dcminfo.SeriesNumber,seriescode))
            
    dicom_cvrt_fid.close()
    
    if verbose:
        print 'found the following series:'
    logfile_fid.write('Series Info:\n')
    for skeys in series_info.iterkeys():
        if verbose:
            print '%d: %s'%(skeys,series_info[skeys].SeriesDescription)
        logfile_fid.write('%d: %s\n'%(skeys,series_info[skeys].SeriesDescription))
        save_dicom_info('%slog/series%03d.dcmhdr'%(subdir,skeys),series_info[skeys])

    # convert to dicom
    if c.convert_dicom:
        if verbose:
            print 'launching DICOM conversion script: %s'%dicom_cvrt
        if not c.test:
            launchinfo['dicom_cvrt'],launch_output=launch_qsub(script_name=dicom_cvrt,runtime='00:20:00',jobname=c.subcode+'-dcm2nii',email=False,outfile='%slog/dicom_convert'%subdir,cwd='%slog'%subdir)

    # get series info
    dti_series=[]
    functional_series=[]
    fse_series=[]
    highres_series=[]
    for series in series_info.iterkeys():
        if series_info[series].SeriesDescription.find('unctional')>-1:
            functional_series.append(series)
        if series_info[series].SeriesDescription.find('FSE')>-1:
            fse_series.append(series)
        if series_info[series].SeriesDescription.find('hi_res')>-1:
            highres_series.append(series)
        if series_info[series].SeriesDescription.find('HARD')>-1:
            dti_series.append(series)

    if c.process_func_data:

        # run mfclirt
        mcflirt_cmd='%slog/run_mcflirt.sh'%subdir
        mcflirt_cmd_fid=open(mcflirt_cmd,'w')
        mcffile={}
        for series in functional_series:
            mcflirt_cmd_fid.write('mcflirt -in %s -sinc_final -plots\n'%niifile[seriescode_dict[series]])
            mcffile[series]=niifile[seriescode_dict[series]].replace('.nii','_mcf.nii')

        mcflirt_cmd_fid.close()
        if not launchinfo.has_key('dicom_cvrt'):
            launchinfo['dicom_cvrt']=0
        if verbose:
            print 'launching mcflirt script: %s'%mcflirt_cmd
        if not c.test:
            launchinfo['mcflirt'],launch_output=launch_qsub(script_name=mcflirt_cmd,runtime='00:30:00',jobname=c.subcode+'-mcflirt',email=False,cwd='%slog'%subdir,hold=launchinfo['dicom_cvrt'])

        # run bet on functional and FSE

        betfunc_cmd='%slog/run_betfunc.sh'%subdir
        betfunc_cmd_fid=open(betfunc_cmd,'w')
        betfuncfile={}
        for series in functional_series:
            betfuncfile[series]=mcffile[series].replace('.nii','_brain.nii')
            betfunc_cmd_fid.write('bet %s %s -F\n'%(mcffile[series],betfuncfile[series]))
        for series in fse_series:
            betfuncfile[series]=niifile[seriescode_dict[series]].replace('.nii','_brain.nii')
            betfunc_cmd_fid.write('bet %s %s -f 0.2\n'%(niifile[seriescode_dict[series]],betfuncfile[series]))

        betfunc_cmd_fid.close()
        if not launchinfo.has_key('mcflirt'):
            launchinfo['mcflirt']=0
        if verbose:
            print 'launching betfunc script: %s'%betfunc_cmd
        if not c.test:
            launchinfo['betfunc'],launch_output=launch_qsub(script_name=betfunc_cmd,runtime='00:10:00',jobname=c.subcode+'-betfunc',email=False,cwd='%slog'%subdir,hold=launchinfo['mcflirt'])

        # run fsld diagnostic report
        fsld_cmd='%slog/run_fsld.sh'%subdir
        fsld_cmd_fid=open(fsld_cmd,'w')
        fsld_cmd_fid.write('module load R\n')
        for series in functional_series:
             fsld_cmd_fid.write('echo "source(\'%s\'); fsld_raw(\'%s\')"|R --no-save\n'%(fsld_script,mcffile[series]))

        fsld_cmd_fid.close()
        if not launchinfo.has_key('betfunc'):
            launchinfo['betfunc']=0
        if verbose:
            print 'launching fsld script: %s'%fsld_cmd
        if not c.test:
            launchinfo['fsld'],launch_output=launch_qsub(script_name=fsld_cmd,runtime='01:00:00',jobname=c.subcode+'-fsld',email=False,cwd='%slog'%subdir,hold=launchinfo['betfunc'],compiler='gcc')


        
        # run melodic on BOLD data

        melodic_cmd='%slog/run_melodic.sh'%subdir
        melodic_cmd_fid=open(melodic_cmd,'w')
        mcffile={}
        for series in functional_series:
            melodic_cmd_fid.write('melodic -i %s --Oall\n'%betfuncfile[series])
            mcffile[series]=niifile[seriescode_dict[series]].replace('.nii','_mcf.nii')

        melodic_cmd_fid.close()
        if not launchinfo.has_key('betfunc'):
            launchinfo['betfunc']=0
        if verbose:
            print 'launching melodic script: %s'%melodic_cmd
        if not c.test:
            launchinfo['melodic'],launch_output=launch_qsub(script_name=melodic_cmd,runtime='02:00:00',jobname=c.subcode+'-melodic',email=False,cwd='%slog'%subdir,hold=launchinfo['betfunc'])



    if c.process_struct_data:
        # run freesurfer on highres
        fs_subdir='/corral/utexas/poldracklab/data/subjects/'

        autorecon_cmd='%slog/run_autorecon-setup.sh'%subdir
        autorecon_cmd_fid=open(autorecon_cmd,'w')
        if len(highres_series)>1:
            highres_imgs=' '.join(niifile[seriescode_dict[highres_series]])

        else:
             cmd='recon-all -i %s -subjid %s -sd %s'%(niifile[seriescode_dict[highres_series[0]]].replace('//','/'),c.subcode,fs_subdir)
             autorecon_cmd_fid.write('%s\n'%cmd)

        autorecon_cmd_fid.close()

        print 'launching autorecon-setup script: %s'%autorecon_cmd
        if not c.test:
            launchinfo['autorecon-setup'],launch_output=launch_qsub(serialcmd='sh '+autorecon_cmd,runtime='02:00:00',jobname=c.subcode+'-autorecon-setup',email=False,cwd='%slog'%subdir,hold=launchinfo['dicom_cvrt'])
 #           run_shell_cmd(cmd,cwd='%slog'%subdir)


        autorecon_cmd='%slog/run_autorecon1.sh'%subdir
        autorecon_cmd_fid=open(autorecon_cmd,'w')
        autorecon_cmd_fid.write('recon-all -autorecon1  -subjid %s -sd %s\n'%(c.subcode,fs_subdir))
        autorecon_cmd_fid.close()
        if not launchinfo.has_key('autorecon-setup'):
            launchinfo['autorecon-setup']=0

        print 'launching autorecon1 script: %s'%autorecon_cmd
        if not c.test:
            launchinfo['autorecon1'],launch_output=launch_qsub(serialcmd='sh '+autorecon_cmd,runtime='02:00:00',jobname=c.subcode+'-autorecon1',email=False,cwd='%slog'%subdir,hold=launchinfo['autorecon-setup'],compiler='gcc')



        autorecon_cmd='%slog/run_autorecon2.sh'%subdir
        autorecon_cmd_fid=open(autorecon_cmd,'w')
        autorecon_cmd_fid.write('recon-all -autorecon2  -subjid %s -sd %s\n'%(c.subcode,fs_subdir))
        autorecon_cmd_fid.close()
        if not launchinfo.has_key('autorecon1'):
            launchinfo['autorecon1']=0

        print 'launching autorecon2 script: %s'%autorecon_cmd
        if not c.test:
            launchinfo['autorecon2'],launch_output=launch_qsub(serialcmd='sh '+autorecon_cmd,runtime='12:00:00',jobname=c.subcode+'-autorecon2',email=False,cwd='%slog'%subdir,hold=launchinfo['autorecon1'],compiler='gcc')

        autorecon_cmd='%slog/run_autorecon3.sh'%subdir
        autorecon_cmd_fid=open(autorecon_cmd,'w')
        autorecon_cmd_fid.write('recon-all -autorecon3  -subjid %s -sd %s\n'%(c.subcode,fs_subdir))
        autorecon_cmd_fid.close()
        if not launchinfo.has_key('autorecon2'):
            launchinfo['autorecon2']=0

        print 'launching autorecon3 script: %s'%autorecon_cmd
        if not c.test:
            launchinfo['autorecon3'],launch_output=launch_qsub(script_name=autorecon_cmd,runtime='24:00:00',jobname=c.subcode+'-autorecon3',email=False,cwd='%slog'%subdir,hold=launchinfo['autorecon2'],compiler='gcc')

        autorecon_cmd='%slog/run_fscopy.sh'%subdir
        autorecon_cmd_fid=open(autorecon_cmd,'w')
        autorecon_cmd_fid.write('mri_convert --out_orientation RAS %s/%s/mri/brainmask.mgz %s/anatomy/highres_brain.nii.gz\n'%(fs_subdir,c.subcode,subdir))
        autorecon_cmd_fid.write('fslmaths %s/anatomy/highres_brain.nii.gz -thr 1 -bin %s/anatomy/highres_brain_mask.nii.gz \n'%(subdir,subdir))
        autorecon_cmd_fid.close()
        if not launchinfo.has_key('autorecon3'):
            launchinfo['autorecon3']=0

        print 'launching fscopy script: %s'%autorecon_cmd
        if not c.test:
            launchinfo['fscopy'],launch_output=launch_qsub(serialcmd='sh '+autorecon_cmd,runtime='00:10:00',jobname=c.subcode+'-fscopy',email=False,cwd='%slog'%subdir,hold=launchinfo['autorecon3'])



    # process DTI
    if c.process_dti:
        dti_cmd='%slog/run_dtifit.sh'%subdir
        dti_cmd_fid=open(dti_cmd,'w')
        for series in dti_series:
            # first, use dcm2nii to get the bvals/vecs
            dtidir='%s/raw/%s'%(subdir,seriescode_dict[series])
            print 'getting bval/bvec files...'
            run_shell_cmd('dcm2nii -d N -i N -p N -o %s/raw/%s %s\n'%(subdir,seriescode_dict[series],dicomdir_dict[series]))
    
            for files in os.listdir(dtidir):
                if files.find('.bval')>-1:
                    bval_file=dtidir+'/'+files
                if files.find('.bvec')>-1:
                    bvec_file=dtidir+'/'+files
            if not (bvec_file and bval_file):
                print 'no bvec/bval files, skipping DTI analysis for series %s'%series
            else:
                dti_cmd_fid.write('fslroi %s %s 0 1\n'%(niifile[seriescode_dict[series]],niifile[seriescode_dict[series]].replace('.nii','_b0.nii')))
                dti_cmd_fid.write('bet %s %s -m\n'%(niifile[seriescode_dict[series]].replace('.nii','_b0.nii'),niifile[seriescode_dict[series]].replace('.nii','_b0_brain.nii')))
                if not os.path.exists('%s/dtifit'%dtidir):
                    os.mkdir('%s/dtifit'%dtidir)
                dti_cmd_fid.write('dtifit -k %s -m %s -o %s/dtifit/dtifit -r %s -b %s \n'%(niifile[seriescode_dict[series]],niifile[seriescode_dict[series]].replace('.nii','_b0_brain.nii'),dtidir,bvec_file,bval_file))

        dti_cmd_fid.close()
        print 'launching dtifit script: %s'%dti_cmd
        if not c.test:
            launchinfo['dtifit'],launch_output=launch_qsub(serialcmd='sh '+dti_cmd,runtime='02:00:00',jobname=c.subcode+'-dtifit',email=False,cwd='%slog'%subdir,hold=launchinfo['dicom_cvrt'])
        
    logfile_fid.close()


if __name__ == '__main__':
    main()
