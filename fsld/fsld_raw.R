fsld_raw <- function(fname,maskfname='') {
# fmri diagnosis for raw fmri timeseries data

.libPaths('/corral/utexas/poldracklab/software_lonestar/R_libs/')
MCTHRESH=2.0

if (!exists('maskfname')) {
	maskfname=''
	}
	
library(matlab)
library(lattice)
library(MASS)
library(fmri)
library(gplots)

si=Sys.info()
MYEMAIL=sprintf('%s@vone.psych.ucla.edu',si['user'])

# currently this code makes some pretty shaky assumptions that .img
# and .nii.gz are the only file types
is_gzipped=0

if (!file.exists(fname)) {
	stop(sprintf('%s does not exist - exiting!',fname))
	}
	
fileinfo=fileparts(fname)
if (fileinfo$pathstr=='' | fileinfo$pathstr=='/') {
	fileinfo$pathstr='.'
	}
if (fileinfo$ext == '.gz') {
    print(sprintf('unzipping %s...',fname))
	is_gzipped=1;
  	system(sprintf('gunzip %s',fname))
  	fname=sprintf('%s/%s',fileinfo$pathstr,fileinfo$name)
	fileinfo=fileparts(fname)
	if (fileinfo$pathstr==''| fileinfo$pathstr=='/') {
		fileinfo$pathstr='.'
	}

	}
#maskfname=sprintf('%s/%s_brain_mask%s',fileinfo$pathstr,fileinfo$name,fileinfo$ext)

if (maskfname == '') {
	maskfname=sprintf('%s/%s_brain_mask.nii.gz',fileinfo$pathstr,fileinfo$name)
	print(sprintf('checking for %s',maskfname))
	if (!file.exists(maskfname)) {
		print('hold on...')
		if (is_gzipped) {
  			system(sprintf('gzip %s',fname))
			}
		stop('no default or specified mask; you need to run betfunc first!')
		}
	}
if (!file.exists(maskfname)) {
	stop(sprintf('%s does not exist - exiting!',maskfname))
	}
maskfileinfo=fileparts(maskfname)
if (maskfileinfo$pathstr=='' | maskfileinfo$pathstr=='/') {
	maskfileinfo$pathstr='.'
	}
if (maskfileinfo$ext == '.gz') {
    print(sprintf('unzipping %s...',maskfname))
	is_gzipped=1;
  	system(sprintf('gunzip %s',maskfname))
  	maskfname=sprintf('%s/%s',maskfileinfo$pathstr,maskfileinfo$name)
	maskfileinfo=fileparts(maskfname)
	}
if (maskfileinfo$pathstr=='' | maskfileinfo$pathstr=='/') {
	maskfileinfo$pathstr='.'
	}


# load fmri data
if (file.exists(fname)) {
	print(sprintf('loading image data (%s)...',fname))
	func_data<-read.NIFTI(fname)
	img<-extract.data(func_data)

} else {
	print('image data already loaded - skipping load')
}


# load mask
if (file.exists(maskfname)) {
	print(sprintf('loading mask data (%s)...',maskfname))
	mask_data<-read.NIFTI(maskfname)
	maskimg<-extract.data(mask_data)

} else {
	print('mask_data already loaded - skipping load')
}

if (is_gzipped) {
	print('recompressing data files...')
  	system(sprintf('gzip %s',fname))
  	system(sprintf('gzip %s',maskfname))
	}

# load motion data
mcpar_file=sprintf('%s/%s.par',fileinfo$pathstr,fileinfo$name)
if (file.exists(mcpar_file)) {
	print(sprintf('loading motion parameters from %s',mcpar_file))
	mcpar=read.table(mcpar_file)	
	}  else {
	print(sprintf('no motion parameters present in %s',mcpar_file))
	mcpar=0
	}


#  compute displacement for motion data
if (length(mcpar) > 1) {
   ntp=length(mcpar[,1])
   mcdisp=mcpar[2:ntp,]-mcpar[1:ntp-1,]
   mean_mcdisp=mean(mcdisp)
   }

maxdisp=max(abs(mcdisp[,4:6]))
maxrot=max(abs(mcdisp[,1:3]))

img.size<-size(img)
img.std<-zeros(img.size[1:3])
img.mean<-zeros(img.size[1:3])

print('computing voxelwise statistics')

for (x in 1:img.size[1]) {
  for (y in 1:img.size[2]) {
  	for (z in 1:img.size[3]) {
  		img.std[x,y,z]=std(img[x,y,z,])
  		img.mean[x,y,z]=mean(img[x,y,z,])
  	}
  }
 }



img.mean_stdunits=img.mean/img.std
img.mask_mean=zeros(1,img.size[4])
img.mask_std=zeros(1,img.size[4])
img.n_outliers=zeros(1,img.size[4])
img.mean_resid=zeros(1,img.size[4])
out_cut=2
img.mad=zeros(1,img.size[4])
img.cv=zeros(1,img.size[4])
img.snr=zeros(1,img.size[4])

slice.mean=zeros(img.size[3],img.size[4])

print('computing timepoint statistics')

for (t in 1:img.size[4]) {
	tmp<-img[,,,t]
	tmp_nonbrain=tmp[maskimg==0]
	tmp<-tmp[maskimg>0]
	img.mask_mean[t]=mean(tmp)
#	img.mask_std[t]=std(tmp)	
	img.mad[t]=mad(tmp)/1.4826  # normalization factor to	approximate stdev estimate
	img.cv[t]=img.mad[t]/median(tmp)
	med=median(tmp)
	outliers=find(tmp<(med - img.mad[t]*out_cut ) | tmp>(med + img.mad[t]*out_cut ))
	img.n_outliers[t]=length(outliers)
	img.snr[t]=med/median(tmp_nonbrain)
	# compute slicewise statistics at each timepoint
	for (z in 1:img.size[3]) {
	    tmpslice=img[,,z,t]
	    maskslice=maskimg[,,z,1]
	    tmpslice=tmpslice[maskslice>0]
	    if (is.nan(mean(tmpslice))) {slice.mean[z,t]=0}
	    else {slice.mean[z,t]=mean(tmpslice)}
	    
	}
}

img.n_outliers=img.n_outliers/length(tmp)


# make figures

# first, make data diagnostics figure
pdf(file=sprintf('%s/%s_diag.pdf',fileinfo$pathstr,fileinfo$name),width=8,height=10)

layout(matrix(c(1,2,3,3,4,4,5,5),4,2,byrow=TRUE))
plotinfo=c(sprintf('%s',getwd()),sprintf('Mean SNR: %0.3f',mean(img.snr)),sprintf('Maximum translation: %0.3f',maxdisp),sprintf('Maximum rotation: %0.3f',maxrot))
textplot(plotinfo,halign="left",valign="top",cex=1)
img.hist.mean<-truehist(img.mean[img.mean > 0],xlab='Intensity')
title(main='Signal Histogram')
#img.hist.std<-truehist(img.std[img.mean > 0],xlab='Stdev')
#title(main='Stdev Histogram')
#plot(img.mean[img.mean > 0],img.std[img.mean > 0],xlab='Intensity',ylab='stdev')
#title(main='Stdev vs. mean')

plot(1:t,img.mask_mean,type='l',xlab='Timepoints',ylab='Mean intensity')
title(main='Global in-mask signal: Mean')

s=spectrum(t(img.mask_mean),spans=10,main='Log power spectrum of global signal timecourse',ylab='log power')

plot(1:t,img.snr,type='l',xlab='Timepoints',ylab='SNR')
title('Signal to noise ratio (based on BET mask)')

layout(matrix(c(1,2,3,4),4,1,byrow=TRUE))

imagesc(slice.mean,xlab='Timepoints',ylab='Slices')
title(main='Mean slice intensity by time')

plot(1:t,img.cv,type='l',xlab='Timepoints',ylab='Robust CV (MAD/median)')
title(main='Robust coefficient of variation on in-mask voxels')

if (length(mcpar)>1) {
	matplot(mcdisp[,4:6],type='l',xlab='timepoints',ylab='translational displacement (mm)',lty=c(1,1,1))
	title(sprintf('Motion parameters: Translation (max: X = %0.3f mm, Y = %0.3f mm, Z = %0.3f mm)',max(mcdisp[,4]),max(mcdisp[,5]), max(mcdisp[,6])))
	matplot(mcdisp[,1:3],type='l',xlab='timepoints',ylab='rotational displacement (degrees)',lty=c(1,1,1))
	title(sprintf('Motion parameters: Rotation (max: X = %0.3f mm, Y = %0.3f mm, Z = %0.3f mm)',max(mcdisp[,1]),max(mcdisp[,2]), max(mcdisp[,3])))

}

dev.off()

if (maxdisp > MCTHRESH) {
   print('motion threshold exceeded - sending email')
   mailmsg=sprintf('Filename: %s\nDirectory: %s\nMaximum translational displacement = %0.3f\nMaximum rotational displacement = %0.3f',fname,getwd(),maxdisp,maxrot)

   mailcmd=sprintf('echo "%s" | mailx -a %s -r %s -s "Motion threshold exceeded: %s", %s',mailmsg,sprintf('%s_diag.pdf',fileinfo$name),MYEMAIL,getwd(),MYEMAIL)

   system(mailcmd)
}

}
