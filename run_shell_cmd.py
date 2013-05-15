"""
utility functions to run shell commands
"""

import subprocess

def run_shell_cmd(cmd,echo=False,cwd=[]):
    """ run a command in the shell using Popen
    """
    stdout_holder=[]
    if cwd:
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,cwd=cwd)
    else:
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    for line in process.stdout:
        if echo:
            print line.strip()
        stdout_holder.append(line.strip())
    process.wait()
    return stdout_holder

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

