from fabric.api import env
import pytz

#user name to ssh to hosts
env.user = 'satoshi_yokohata'
#user password (the better is to use pubkey authentication)
env.password = 'thumbtack'

env.show = ['debug']

env.roledefs = {
    #list of client hosts
    'client': ['load13',],
    #'client': ['c1.citrusleaf.local', 'c2.citrusleaf.local', 'c3.citrusleaf.local', 'c4.citrusleaf.local'],
    #'client': ['c1.citrusleaf.local', 'c2.citrusleaf.local', 'c3.citrusleaf.local', 'c4.citrusleaf.local', 'c5.citrusleaf.local', 'c6.citrusleaf.local'],
    #'client': ['c1.citrusleaf.local', 'c2.citrusleaf.local', 'c3.citrusleaf.local', 'c6.citrusleaf.local', 'r1.citrusleaf.local', 'r2.citrusleaf.local', 'r3.citrusleaf.local', 'r5.citrusleaf.local'],
    #'client': ['c1.citrusleaf.local', 'c2.citrusleaf.local', 'c3.citrusleaf.local', 'c6.citrusleaf.local', 'c4.citrusleaf.local', 'c5.citrusleaf.local', 'r3.citrusleaf.local', 'r5.citrusleaf.local'],
    #'client': ['c1.citrusleaf.local', 'c2.citrusleaf.local', 'c3.citrusleaf.local', 'c4.citrusleaf.local', 'c5.citrusleaf.local', 'c6.citrusleaf.local', 'r1.citrusleaf.local', 'r2.citrusleaf.local', 'r3.citrusleaf.local', 'r5.citrusleaf.local'],

    #list of server hosts
    'server': ['load05', 'load06', 'load12', ],

    #list of all available client hosts
    'all_client': ['load13',],
    #'all_client': ['c1.citrusleaf.local', 'c2.citrusleaf.local', 'c3.citrusleaf.local', 'c6.citrusleaf.local', 'r1.citrusleaf.local', 'r2.citrusleaf.local', 'r3.citrusleaf.local', 'r5.citrusleaf.local'],
}

#hosts timezone (required to correctly schedule ycsb tasks)
timezone = pytz.timezone('Asia/Tokyo')
