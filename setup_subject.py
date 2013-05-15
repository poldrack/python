#!/usr/bin/env python
"""
process data from Skyra
Russ Poldrack, 8/31/2012

"""

import subprocess as sub
import argparse
import os,sys
from datetime import datetime
import dicom
import pickle
import socket
import xnat_tools

def run_logged_cmd(cmd,cmdfile):
        outfile=open(cmdfile,'a')
        subcode=cmdfile.split('/')[-2]
        outfile.write('\n%s: Running:'%subcode+cmd+'\n')
        p = sub.Popen(cmd.split(' '),stdout=sub.PIPE,stderr=sub.PIPE)
        output, errors = p.communicate()
        outfile.write('%s: Output: '%subcode+output+'\n')
        if errors:
            outfile.write('%s: ERROR: '%subcode+errors+'\n')
            print '%s: ERROR: '%subcode+errors
        outfile.close()

def log_message(message,cmdfile):
        outfile=open(cmdfile,'a')
        outfile.write(message+'\n')
        outfile.close()



def parse_command_line():
    parser = argparse.ArgumentParser(description='setup_subject')
    #parser.add_argument('integers', metavar='N', type=int, nargs='+',help='an integer for the accumulator')
    # set up boolean flags


    parser.add_argument('--getdata', dest='getdata', action='store_true',
        default=False,help='get data from XNAT')
    parser.add_argument('--keepdata', dest='keepdata', action='store_true',
        default=False,help='keep DICOMs after conversion')
    parser.add_argument('--dcm2nii', dest='dcm2nii', action='store_true',
        default=False,help='perform dicom conversion')
    parser.add_argument('-o', dest='overwrite', action='store_true',
        default=False,help='overwrite existing files')
    parser.add_argument('-t', dest='testmode', action='store_true',
        default=False,help='run in test mode (do not execute commands)')
    parser.add_argument('--motcorr', dest='motcorr', action='store_true',
        default=False,help='run motion correction')
    parser.add_argument('--betfunc', dest='betfunc', action='store_true',
        default=False,help='run BET on func data')
    parser.add_argument('--qa', dest='qa', action='store_true',
        default=False,help='run QA on func data')
    parser.add_argument('--fm', dest='fm', action='store_true',
        default=False,help='process fieldmap')
    parser.add_argument('--dtiqa', dest='dtiqa', action='store_true',
        default=False,help='run QA on DTI data')
    parser.add_argument('--topup', dest='topup', action='store_true',
        default=False,help='run topup on DTI data')
    parser.add_argument('--melodic', dest='melodic', action='store_true',
        default=False,help='run melodic on func data')
    parser.add_argument('--unzip', dest='unzip', action='store_true',
        default=False,help='unzip data file')
    parser.add_argument('--fsrecon', dest='fsrecon', action='store_true',
        default=False,help='run freesurfer autorecon1')
    parser.add_argument('-v', dest='verbose',action='store_true',
        help='give verbose output')
    parser.add_argument('--bet-inplane', dest='bet_inplane', action='store_true',
        default=False,help='run bet on inplane')
    parser.add_argument('--all', dest='doall', action='store_true',
        default=False,help='run all steps')

    # set up flags with arguments

    parser.add_argument('--xnat_server', dest='xnat_server',
        help='URL for xnat server',default="https://xnat.irc.utexas.edu/xnat-irc")
    parser.add_argument('--xnat_username', dest='xnat_username',
        help='user name for xnat server',default='')
    parser.add_argument('--xnat_password', dest='xnat_password',
        help='password for xnat server',default='')
    parser.add_argument('-f', dest='filename',
        help='path to zipped data file')
    parser.add_argument('--studyname', dest='studyname',
        help='name of study',required=True)
    parser.add_argument('-b', dest='basedir',
        help='base directory for data file', default='/corral-repl/utexas/poldracklab/data/')
    parser.add_argument('-s','--subcode', dest='subcode',
        help='subject code',required=True)
    parser.add_argument('--subdir', dest='subdir',
        help='subject dir (defaults to subject code)',default='')
    parser.add_argument('--mcflirt-args', dest='mcflirt_args',
        help='arguments for mcflirt',default='-plots -sinc_final')
    parser.add_argument('--xnat-project', dest='xnat_project',
        help='project in XNAT',default='poldrack')
    parser.add_argument('--mricrondir', dest='mricrondir',
        help='directory for mricron',default='')
    parser.add_argument('--fs-subdir', dest='fs_subdir',
        help='subject directory for freesurfer',default='/corral-repl/utexas/poldracklab/data/subdir')

    args = parser.parse_args()
    arglist={}
    for a in args._get_kwargs():
        arglist[a[0]]=a[1]

    return arglist

def setup_dir(args):

    # basedir for data
    studyname=args['studyname']
    subcode=args['subcode']
    if args['verbose']:
        print subcode

    studydir=os.path.join(args['basedir'],studyname)
    if not os.path.exists(studydir):
        print 'ERROR: study dir %s does not exist!'%studydir
        sys.exit()
        #subcode=sys.argv[1]

    subdir=os.path.join(studydir,args['subdir'])

    if not os.path.exists(subdir):
        os.mkdir(subdir)
    else:
        print 'subdir %s already exists'%subdir
        if args['overwrite']==False:
            sys.exit()
        else:
            print 'overwriting...'

    subdirs=['BOLD','DTI','anatomy','logs','raw','model','behav','fieldmap']
    subdir_names={}

    for s in subdirs:
        subdir_names[s]=os.path.join(subdir,s)
        if not os.path.exists(subdir_names[s]):
            os.mkdir(subdir_names[s])

    return subdir,subdir_names

def setup_outfiles():
    timestamp = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
    outfile={}
    outfile['main']=os.path.join(subdir,'logs/cmd_'+timestamp+'.log')
    outfile['dcm2nii']=os.path.join(subdir,'logs/dcm2nii_cmd_'+timestamp+'.log')
    outfile['unzip']=os.path.join(subdir,'logs/unzip_'+timestamp+'.log')

    log_message("#command file automatically generated by setup_subject.py\n#Started: %s\n\n"%timestamp,outfile['main'])
    return outfile

def load_dcmhdrs(subdir_names):
    TR={}
    hdrfile=os.path.join(subdir_names['logs'],'dicom_headers.pkl')
    f=open(hdrfile,'rb')
    dcmhdrs=pickle.load(f)
    f.close()
    for d in dcmhdrs.iterkeys():
        if dcmhdrs[d].SequenceName.find('epfid')>-1:
            TR[dcmhdrs[d].ProtocolName.replace(' ','_')]=float(dcmhdrs[d].RepetitionTime)/1000.0

    return dcmhdrs,TR

def save_dcmhdrs(dcmhdrs,subdir_names):
    hdrfile=os.path.join(subdir_names['logs'],'dicom_headers.pkl')
    f=open(hdrfile,'wb')
    pickle.dump(dcmhdrs,f)
    f.close()


def fs_setup(args,subdir_names):
    if args['verbose']:
        print 'running freesurfer setup'
        # set up subdir
    if not os.path.exists(args['fs_subdir']):
        print 'fs_subdir %s does not exist - skipping fs_setup'%args['fs_subdir']
    sub_fsdir=os.path.join(args['fs_subdir'],args['fs_subcode'])
    if os.path.exists(sub_fsdir):
        if not args['overwrite']:
            print 'subject dir %s already exists - skipping fs_setup'
            return
        else:
            print 'subject dir %s already exists - overwriting'
    else:
        cmd='recon-all -i %s -subjid %s -sd %s'%(os.path.join(subdir_names['anatomy'],'highres001.nii.gz'),args['fs_subcode'],args['fs_subdir'])
        print cmd
        if not args['testmode']:
            run_logged_cmd(cmd,outfile['main'])

def run_autorecon1(args,subdir_names):
    if args['verbose']:
        print 'running freesurfer autorecon1'
        # set up subdir
    sub_fsdir=os.path.join(args['fs_subdir'],args['fs_subcode'])
    brainmask=os.path.join(sub_fsdir,'mri/brainmask.mgz')

    if not os.path.exists(sub_fsdir):
        print 'subject dir %s does not exist - skipping autorecon1'%sub_fsdir
        return
    elif os.path.exists(brainmask):
        print 'brainmask %s already exists - skipping autorecon1'%brainmask
        return
    else:
        cmd='recon-all -autorecon1 -subjid %s -sd %s'%(args['fs_subcode'],args['fs_subdir'])
        print cmd
        if not args['testmode']:
            run_logged_cmd(cmd,outfile['main'])

def copy_stripped_T1(args,subdir_names):
    if args['verbose']:
        print 'copying stripped T1'
        # set up subdir
    sub_fsdir=os.path.join(args['fs_subdir'],args['fs_subcode'])
    brainmask=os.path.join(sub_fsdir,'mri/brainmask.mgz')

    if not os.path.exists(brainmask):
        print 'brainmask %s does not exist - skipping copy'%brainmask
        return
    else:
        cmd='mri_convert --out_orientation LAS %s --reslice_like %s/highres001.nii.gz  %s/highres001_brain.nii'%(brainmask,
                                                                                                                 subdir_names['anatomy'],subdir_names['anatomy'])
        print cmd
        if not args['testmode']:
            run_logged_cmd(cmd,outfile['main'])
        cmd='gzip  %s/highres001_brain.nii'%subdir_names['anatomy']
        print cmd
        if not args['testmode']:
            run_logged_cmd(cmd,outfile['main'])
        cmd='fslmaths %s/highres001_brain.nii.gz -thr 1 -bin %s/highres001_brain_mask.nii.gz'%(subdir_names['anatomy'],subdir_names['anatomy'])
        print cmd
        if not args['testmode']:
            run_logged_cmd(cmd,outfile['main'])

def bet_inplane(args,subdir_names):
    if args['verbose']:
        print 'running bet on inplane'
    inplane_file=os.path.join(subdir_names['anatomy'],'inplane001.nii.gz')
    if not os.path.exists(inplane_file):
        print 'inplane file %s does not exist - skippping bet_inplane'%inplane_file
        return
    cmd='bet %s %s -f 0.3 -R'%(os.path.join(subdir_names['anatomy'],'inplane001.nii.gz'),
                     os.path.join(subdir_names['anatomy'],'inplane001_brain.nii.gz'))
    print cmd
    if not args['testmode']:
        run_logged_cmd(cmd,outfile['main'])


def process_fieldmap(args,subdir_names):
	if args['verbose']:
		print 'processing field maps'
	magfile='%s/fieldmap_mag.nii.gz'%subdir_names['fieldmap']
	phasefile='%s/fieldmap_mag.nii.gz'%subdir_names['fieldmap']
	if not os.path.exists(magfile) or not os.path.exists(phasefile):
		print 'field map does not exist, skippping process_fieldmap'
		return
	

	cmd='bet %s/fieldmap_mag.nii.gz %s/fieldmap_mag_brain -f 0.3 -F'%(subdir_names['fieldmap'],subdir_names['fieldmap'])
	print cmd
	if not args['testmode']:
		run_logged_cmd(cmd,outfile['main'])
	
	
	cmd='fsl_prepare_fieldmap SIEMENS %s/fieldmap_phase.nii.gz %s/fieldmap_mag_brain.nii.gz %s/fm_prep 2.46'%(subdir_names['fieldmap'],subdir_names['fieldmap'],subdir_names['fieldmap'])
	print cmd
	if not args['testmode']:
		run_logged_cmd(cmd,outfile['main'])


def dtiqa(args,subdir_names):
    if args['verbose']:
        print 'running QC on DTI'
    dtifiles=[i.strip() for i in os.listdir(subdir_names['DTI']) if (i.find('DTI_')==0 and i.find('.nii.gz')>0)]
    for dtifile in dtifiles:
		    print 'found DTI file: %s'%dtifile

		    cmd='dtiqa.py %s'%os.path.join(subdir_names['DTI'],dtifile)
		    print cmd
		    if not args['testmode']:
			    run_logged_cmd(cmd,outfile['main'])
		    
def topup(args,subdir_names):
    if args['verbose']:
        print 'running topup on DTI'
    if (not os.path.exists(os.path.join(subdir_names['DTI'],'DTI_1.nii.gz'))) or (not os.path.exists(os.path.join(subdir_names['DTI'],'DTI_2.nii.gz'))):
	    print 'topup requires two DTI files - skipping'
	    return
    

    cmd='run_topup.py %s %s'%(os.path.join(subdir_names['DTI'],'DTI_1.nii.gz'),os.path.join(subdir_names['DTI'],'DTI_2.nii.gz'))
    print cmd
    if not args['testmode']:
	    run_logged_cmd(cmd,outfile['main'])
		    
	
def download_from_xnat(args,subdir):
		args['keepdata'] = True
		#use default download username
		if (len(args['xnat_username'])<1) or (len(args['xnat_password'])<1):
		    xnat_tools.down_subject_dicoms(args['xnat_server'],
			  os.path.join(subdir,'raw'),
			  args['xnat_project'], args['subcode'])
		else:
		    xnat_tools.down_subject_dicoms(args['xnat_server'],
			  os.path.join(subdir,'raw'),
			  args['xnat_project'], args['subcode'],
			  xnat_username=args['xnat_username'],
			  xnat_password=args['xnat_password'])

def do_unzipping(args,subdir):
	    if not args['filename'] or not os.path.exists(args['filename']):
	        print 'filename %s not found for unzipping - exiting'%args['filename']
	        sys.exit()
	    cmd='unzip %s -d %s'%(args['filename'],subdir)
	    print cmd
	    if not args['testmode']:
	        run_logged_cmd(cmd,outfile['unzip'])

def convert_dicom_to_nifti(args, subdir):
	
	TR={}
	scan_keys = {
			'anatomy': ['MPRAGE','FSE','T1w','T2w','PDT','PD-T2','tse2d','mprage','t1w','t2w','t2spc','t2_spc'],
			'BOLD':['epfid'],
			'DTI':['ep_b'],
			'fieldmap':['fieldmap','field_mapping','FieldMap'],
			'localizer':['localizer','Localizer','Scout','scout'],
			'reference':['SBRef']
			}
	
	if args['unzip']:
	 	dcmbase=os.path.join(subdir,args['subcode'],'SCANS')
	else:
	 	dcmbase=os.path.join(subdir,'raw',args['subcode'])
	dcmdirs=os.listdir(dcmbase)
	dcmhdrs={}
	for d in dcmdirs:
		if args['unzip']:
			dcmdir=os.path.join(dcmbase,d,'DICOM')
		else:
			dcmdir=os.path.join(dcmbase,d)
			dcmfiles=[i for i in os.listdir(dcmdir) if i.find('.dcm')>0]
		try:
			dcmhdrs[d]=dicom.read_file(os.path.join(dcmdir,dcmfiles[0]))
		except:
			continue
		file_type='raw'
		#print d, dcmhdrs[d].ImageType
		if not dcmhdrs[d].ImageType[0]=='ORIGINAL':
			print 'skipping derived series ',d
			file_type='derived'
		# first look for anatomy
		if file_type=='raw':
			for key in scan_keys['reference']:
				if (dcmhdrs[d].ProtocolName.find(key)>-1)  or (dcmhdrs[d].SeriesDescription.find(key)>-1) :
					file_type='reference'
		if file_type=='raw':
			for key in scan_keys['BOLD']:
					if dcmhdrs[d].SequenceName.find(key)>-1:
						file_type='BOLD'
						TR[dcmhdrs[d].ProtocolName.replace(' ','_')+'_'+d]=float(dcmhdrs[d].RepetitionTime)/1000.0
		if file_type=='raw':
			for key in scan_keys['anatomy']:
				if (dcmhdrs[d].ProtocolName.find(key)>-1)  or (dcmhdrs[d].SequenceName.find(key)>-1) :
					file_type='anatomy'
		if file_type=='raw':
			for key in scan_keys['localizer']:
					if dcmhdrs[d].ProtocolName.find(key)>0:
						file_type='localizer'
		if file_type=='raw':
			for key in scan_keys['DTI']:
				if dcmhdrs[d].SequenceName.find(key)>-1:
					file_type='DTI'
		if file_type=='raw':
			for key in scan_keys['fieldmap']:
				if (dcmhdrs[d].ProtocolName.find(key)>-1) or (dcmhdrs[d].SequenceName.find(key)>-1):
					file_type='fieldmap'


		print 'detected %s: (%s) %s %s'%(file_type,d,dcmhdrs[d].ProtocolName,dcmhdrs[d].SeriesDescription)
		if (not file_type=='localizer') and (not file_type=='derived') and (not file_type=='reference'):
			cmd='%sdcm2nii -d n -i n -o %s %s'%(args['mricrondir'],subdir_names[file_type],dcmdir)
			print cmd
			if not args['testmode']:
				run_logged_cmd(cmd,outfile['main'])
	# save dicom headers to pickle file
	save_dcmhdrs(dcmhdrs,subdir_names)

	if not args['keepdata']:
		cmd='rm -rf %s'%dcmbase
		print cmd
		if not args['testmode']:
			run_logged_cmd(cmd,outfile['main'])
		
	# save the
	# rename data appropriately
	boldfiles=[i for i in os.listdir(subdir_names['BOLD']) if i.find('.nii.gz')>0]
	for f in boldfiles:
		runnum=f.rsplit('a')[-2].rsplit('s')[-1].lstrip('0')
		runname=dcmhdrs[runnum].ProtocolName.replace(' ','_')
		rundir=os.path.join(subdir_names['BOLD'],'%s_%s'%(runname,runnum))
		if not os.path.exists(rundir):
			os.mkdir(rundir)
		cmd='mv %s %s/bold.nii.gz'%(os.path.join(subdir_names['BOLD'],f),rundir)
		print cmd
		if not args['testmode']:
			run_logged_cmd(cmd,outfile['dcm2nii'])
	
	anatfiles=[i for i in os.listdir(subdir_names['anatomy']) if i.find('.nii.gz')>0]
	other_anat_dir=os.path.join(subdir_names['anatomy'],'other')
	if not os.path.exists(other_anat_dir):
		os.mkdir(other_anat_dir)
	
	highresctr=1
	inplanectr=1
	for a in anatfiles:
		print a
		runnum=a.rsplit('a')[-2].rsplit('s')[-1].lstrip('0')
		mprage=0
		for key in ['MPRAGE','mprage','t1w','T1w']:
			if a.find(key)>0:
				mprage=1
			if a.find('o')==0 and mprage==1 :
				cmd='mv %s %s/highres%03d.nii.gz'%(os.path.join(subdir_names['anatomy'],a),subdir_names['anatomy'],highresctr)
				print cmd
				if not args['testmode']:
					run_logged_cmd(cmd,outfile['main'])
					highresctr+=1
					print 'highresctr is at ',highresctr
		if (mprage != 1) and a.find('PDT2')>0:
				cmd='fslroi %s %s/inplane%03d.nii.gz 1 1'%(os.path.join(subdir_names['anatomy'],a),subdir_names['anatomy'],inplanectr)
				print cmd
				if not args['testmode']:
					run_logged_cmd(cmd,outfile['main'])
					inplanectr+=1
				cmd='mv %s %s'%(os.path.join(subdir_names['anatomy'],a),other_anat_dir)
				print cmd
				if not args['testmode']:
					run_logged_cmd(cmd,outfile['main'])
		elif not mprage == 1:
				cmd='mv %s %s'%(os.path.join(subdir_names['anatomy'],a),other_anat_dir)
				print cmd
				if not args['testmode']:
					run_logged_cmd(cmd,outfile['main'])
	
	# process fieldmap files
	# TBD: need to distinguish between SE and gradient field maps
	# we are making a brittle assumption here taht the first series is the
	# magnitude image
	fmfiles=[i for i in os.listdir(subdir_names['fieldmap']) if i.find('fieldmap')>0]
	fmctr=0
	fmtypes=['mag','phase']
	for f in fmfiles:
		cmd='mv %s/%s %s/fieldmap_%s.nii.gz'%(subdir_names['fieldmap'],f,subdir_names['fieldmap'],fmtypes[fmctr])
		print cmd
		if not args['testmode']:
			run_logged_cmd(cmd,outfile['main'])
		fmctr+=1
	
	
	
	# process DTI files 
	dtifiles=[i for i in os.listdir(subdir_names['DTI']) if i.find('.nii.gz')>0]
	dtictr=1
	for f in dtifiles:
		cmd='mv %s/%s %s/DTI_%d.nii.gz'%(subdir_names['DTI'],f,subdir_names['DTI'],dtictr)
		print cmd
		if not args['testmode']:
			run_logged_cmd(cmd,outfile['main'])
	
		cmd='mv %s/%s %s/DTI_%d.bvec'%(subdir_names['DTI'],f.replace('.nii.gz','.bvec'),subdir_names['DTI'],dtictr)
		print cmd
		if not args['testmode']:
			run_logged_cmd(cmd,outfile['main'])
		
		cmd='mv %s/%s %s/DTI_%d.bval'%(subdir_names['DTI'],f.replace('.nii.gz','.bval'),subdir_names['DTI'],dtictr)
		print cmd
		if not args['testmode']:
			run_logged_cmd(cmd,outfile['main'])
		dtictr+=1
		    

	return subdir_names, TR

def execute_commands(args, subdir_names, TR):

	bolddirs=[d for d in os.listdir(subdir_names['BOLD']) if os.path.isdir(os.path.join(subdir_names['BOLD'],d))]
	
	print 'bolddirs:'
	print bolddirs
	
	command_dict={'motcorr':"'mcflirt -in %s/bold.nii.gz %s'%(__import__('os').path.join(subdir_names['BOLD'],b),args['mcflirt_args'])",
	    'qa':"'fmriqa.py %s/bold_mcf.nii.gz %f'%(__import__('os').path.join(subdir_names['BOLD'],b),TR[b])",
	    'betfunc':"'bet %s/bold_mcf.nii.gz %s/bold_mcf_brain.nii.gz -F'%(__import__('os').path.join(subdir_names['BOLD'],b),__import__('os').path.join(subdir_names['BOLD'],b))",
	    'melodic':"'melodic -i %s/bold_mcf.nii.gz --Oall --report'%__import__('os').path.join(subdir_names['BOLD'],b)"}
	
	bold_commands=['motcorr','betfunc','qa','melodic']
	if bolddirs:
	 for k in bold_commands:
	  if args[k]:
	    if args['verbose']:
	        print 'running %s'%k
	        # run betfunc
	    else:
	        for b in bolddirs:
		    print k
		    print command_dict
		    print command_dict[k]
				#  NO O_O
	            cmd=eval(command_dict[k])
	            print cmd
	            if not args['testmode']:
	                run_logged_cmd(cmd,outfile['main'])


if __name__ == "__main__":
			
	args=parse_command_line()
	
	# parse doall
	doall_cmds=['dcm2nii','motcorr','betfunc','qa','melodic','bet_inplane','fsrecon']
	if args['doall']:
		for c in doall_cmds:
			args[c]=True
	
	# this is for debugging - detect whether I am
	# on my macbook or on lonestar
	if socket.gethostname().find('tacc')>0:
	    USE_MAC=0
	else:
	    USE_MAC=1
	
	if USE_MAC:
	    args['basedir']='/Users/poldrack/data2/setup_subject_ut/data'
	    args['mricrondir']='/Applications/fmri_progs/mricronmac/'
	    args['filename']='/Users/poldrack/data2/setup_subject_ut/Skyra_testing/rpo-BOOST-pilot1_8_30_2012_17_32_1.zip'
	
	if args['subdir']=='':
		args['subdir']=args['subcode']
	args['fs_subcode']='%s_%s'%(args['studyname'],args['subdir'])
	
	subdir,subdir_names=setup_dir(args)
	
	outfile=setup_outfiles()

	if args['getdata']:
		download_from_xnat(args,subdir)

	if args['unzip']:
		do_unzipping(args,subdir)
	
	
	
	if args['dcm2nii']:
		subdir_names, TR = convert_dicom_to_nifti(args, subdir)

	else:  # try to load dicom headers
	    try:
		    dcmhdrs,TR=load_dcmhdrs(subdir_names)
	    except:
		    print "can't load dicom headers from pickle, exiting (ignore this if just running --getdata)"
		    sys.exit()
	##from here
	execute_commands(args,subdir_names, TR)
	## to here
	if args['bet_inplane']:
	    bet_inplane(args,subdir_names)
	
	# run freesurfer autorecon1
	if args['fsrecon']:
	    fs_setup(args,subdir_names)
	    run_autorecon1(args,subdir_names)
	    copy_stripped_T1(args,subdir_names)
	
	if args['dtiqa']:
		dtiqa(args,subdir_names)
	
	if args['fm']:
		process_fieldmap(args,subdir_names)
		
	log_message("completed: %s"%datetime.now().strftime('%Y_%m_%d_%H_%M_%S'),outfile['main'])
	
