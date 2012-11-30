import re, os, tempfile

from fabric.api import *
from fabric.colors import green, blue, red
from fabric.contrib.console import confirm

from conf import workloads
from fabfile.helpers import get_db, get_workload, _at, get_outfilename, base_time, almost_nothing

def _ycsbloadcmd(database, clientno, timestamp):
    totalclients = len(env.roledefs['client'])
    cmd = workloads.root + '/bin/ycsb load %s -s' % database['command']
    for (key, value) in database['properties'].items():
        cmd += ' -p %s=%s' % (key, value)
    for (key, value) in workloads.data.items():
        if key == 'operationcount':
            cmd += ' -p %s=%s' % (key, value / totalclients)
        else:
            cmd += ' -p %s=%s' % (key, value)
    insertcount = workloads.data['recordcount'] / totalclients
    insertstart = insertcount * clientno
    cmd += ' -p insertstart=%s' % insertstart
    cmd += ' -p insertcount=%s' % insertcount
    outfile = get_outfilename(database['name'], 'load', 'out', timestamp)
    errfile = get_outfilename(database['name'], 'load', 'err', timestamp)
    cmd += ' > %s/%s' % (database['home'], outfile)
    cmd += ' 2> %s/%s' % (database['home'], errfile)
    return cmd

def _ycsbruncmd(database, workload, timestamp, target=None):
    totalclients = len(env.roledefs['client'])
    cmd = workloads.root + '/bin/ycsb run %s -s' % database['command']
    for file in workload['propertyfiles']:
        cmd += ' -P %s' % file
    for (key, value) in database['properties'].items():
        cmd += ' -p %s=%s' % (key, value)
    for (key, value) in workloads.data.items():
        if key == 'operationcount':
            cmd += ' -p %s=%s' % (key, int(value) / totalclients)
        else:
            cmd += ' -p %s=%s' % (key, value)
    if target is not None:
        cmd += ' -target %s' % str(target)
    outfile = get_outfilename(database['name'], workload['name'], 'out', timestamp, target)
    errfile = get_outfilename(database['name'], workload['name'], 'err', timestamp, target)
    cmd += ' > %s/%s' % (database['home'], outfile)
    cmd += ' 2> %s/%s' % (database['home'], errfile)
    return cmd

def _client_no():
    # env.all_hosts is empty for @parallel in fabric 1.3.2
    # return env.all_hosts.index(env.host)
    return env.roledefs['client'].index(env.host)

def _totalclients():
    return len(env.roledefs['client'])

@roles('client')
def load(db):
    """Starts loading of data to the database"""
    timestamp = base_time()
    print green(timestamp, bold = True)
    clientno = _client_no()
    database = get_db(db)
    with cd(database['home']):
        run(_at(_ycsbloadcmd(database, clientno, timestamp), timestamp))

@roles('client')
def run_workload(db, workload, target=None):
    """Starts running of the workload"""
    timestamp = base_time()
    print green(timestamp, bold = True)
    database = get_db(db)
    load = get_workload(workload)
    with cd(database['home']):
        if target is not None:
            part = int(target) / len(env.roledefs['client'])
            run(_at(_ycsbruncmd(database, load, timestamp, part), timestamp))
        else:
            run(_at(_ycsbruncmd(database, load, timestamp), timestamp))

@roles('client')
def status(db):
    """ Shows status of the currently running YCSBs """
    with almost_nothing():
        database = get_db(db)
        with(cd(database['home'])):
            ls_out = run('ls --format=single-column --sort=t *.lock')
            msg = green('free') if 'cannot access' in ls_out else red('locked')
            print blue('Lock:', bold = True), msg
            print blue('Scheduled:', bold = True)
            # print run('tail -n 2 /var/spool/cron/atjobs/*')
            print sudo('atq')
            print blue('Running:', bold = True)
            # print run('ps -f -C java')
            print run('ps aux | grep python')
            # sort the output of ls by date, the first entry should be the *.err needed
            ls_out = run('ls --format=single-column --sort=t *.err')
            if 'cannot access' in ls_out:
                logfile = '<no any *.err files>'
                tail = ''
            else:
                ls = ls_out.split("\r\n")
                logfile = ls[0]
                tail = run('tail %s' % logfile)
            print blue('Log:', bold = True), green(logfile, bold = True)
            print tail
            # print blue('List:', bold = True)
            # ls_out = run('ls --format=single-column --sort=t')
            # print ls_out
            print

@roles('client')
@parallel
def get_log(db, regex='.*', do=False):
    """ Show *.err and *.out logs satisfying the regex to be transferred """
    with settings(hide('running', 'warnings', 'stdout', 'stderr'), warn_only=True):
        p = re.compile(regex)
        database = get_db(db)
        cn = _client_no() + 1
        with cd(database['home']):
            ls = run('ls --format=single-column --sort=t *.err *.out').split("\r\n")
            file_name = [f for f in ls if p.search(f)][0] # the most recent file satisfying pattern
            f0 = os.path.splitext(file_name)[0]           # strip off extension
        # now we have the map {'host' -> 'xxx'}
        # perform self-check and maybe continue
        print blue('Filename at c%s: ' % cn, bold = True), green(f0, bold = True)
        # now do the processing, if enabled
        if do:
            with cd(database['home']):
                tempdir_local = '%s/c%s' % (tempfile.gettempdir(), cn)
                bz2err_remote = '%s-c%s-err.bz2' % (f0, cn)
                bz2out_remote = '%s-c%s-out.bz2' % (f0, cn)
                bz2err_full_local = '%s/%s-err.bz2' % (tempdir_local, f0)
                bz2out_full_local = '%s/%s-out.bz2' % (tempdir_local, f0)
                # packing
                print blue('c%s packing ...' % cn)
                run('tar -jcvf %s %s.err' % (bz2err_remote, f0))
                run('tar -jcvf %s %s.out' % (bz2out_remote, f0))
                # download them
                print blue('c%s transferring to %s...' % (cn, tempdir_local))
                get(bz2err_remote, bz2err_full_local)
                get(bz2out_remote, bz2out_full_local)
                # the files are here, remove remote bz2
                run('rm -f %s' % bz2err_remote)
                run('rm -f %s' % bz2out_remote)
                # unpacking to temp dir
                print blue('c%s unpacking ...' % cn)
                local('tar -xvf %s -C %s' % (bz2err_full_local, tempdir_local))
                local('tar -xvf %s -C %s' % (bz2out_full_local, tempdir_local))
                # unpacked ok, remove local bz2
                #local('rm -f %s' % bz2err_full_local)
                #local('rm -f %s' % bz2out_full_local)
                print blue('c%s moving to current dir ...' % cn)
                local('mv %s/%s.err ./%s-c%s.err' % (tempdir_local, f0, f0, cn))
                local('mv %s/%s.out ./%s-c%s.out' % (tempdir_local, f0, f0, cn))
                local('rm -rf %s' % tempdir_local)

@roles('client')
def kill():
    """Kills YCSB processes"""
    with settings(warn_only=True):
        run('ps -f -C java')
        if confirm(red("Do you want to kill Java on the client?")):
            run('killall java')

@roles('client')
def clean_logs():
    """Removed all logs from /dev/shm"""
    if confirm(red("Do you want to clear all logs from RAM?")):
        run('rm -r /run/shm/*')

@runs_once
def _build_and_upload():
    local('mvn clean package')
    put('distribution/target/ycsb-0.1.4.tar.gz', '~/ycsb.tar.gz')

@roles('client')
def deploy():
    """Builds and deploys YCSB to the clients"""
    _build_and_upload()
    client1 = env.roledefs['client'][0]
    run('scp %s:ycsb.tar.gz .' % client1)
    with cd('/opt'):
        run('rm -r ycsb-0.1.4')
        run('tar xzvf ~/ycsb.tar.gz')
        
