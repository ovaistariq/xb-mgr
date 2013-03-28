#!/usr/bin/python

# (c) 2012, Ovais Tariq <ovaistariq@gmail.com>
#
# This file is part of Xtrabackup Backup Manager
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.host_backup import Host_backup
from lib.lock_helper import Lock_helper
import lib.config_helper
import sys
from optparse import OptionParser

# parse comand line arguments
parser = OptionParser()
parser.add_option('-H', '--host', type='string', 
        help='The host alias to backup as defined in the configuration file')
(options, args) = parser.parse_args()

# Setup exit codes
E_NO_HOSTS = 61
E_UNDEFINDED_HOST = 62
E_LOCK_EXISTS = 63
E_FAILED_LOCK_ACQUIRE = 64

# Get a list of hosts defined to be backed up
hosts_to_backup = lib.config_helper.Config_helper.get_hosts_to_backup()
num_hosts = len(hosts_to_backup)

# If there are no hosts defined then exit with error
if num_hosts < 1:
    print "No hosts defined for backup"
    sys.exit(E_NO_HOSTS)

# If there was no host provided on the command-line or the host 
# provided is not defined in the config file
if options.host is None or options.host not in hosts_to_backup:
    print ("Either no host name provided or the host name provided "
            "is not defined in the configuration")
    sys.exit(E_UNDEFINDED_HOST)

# Take a lock via PID file so that only one backup per host is running
# at a single time
backup_lock_manager = Lock_helper(host=options.host)
if backup_lock_manager.lock_exists():
    print ("Lock file already exists, probably another backup of "
            "%s is already running" % options.host)
    sys.exit(E_LOCK_EXISTS)
if not backup_lock_manager.acquire_lock():
    print ("Failed to acquire lock on the lock file, probably "
            "another backup of %s is already running" % options.host)
    sys.exit(E_FAILED_LOCK_ACQUIRE)

# Do the backup
host_backup = Host_backup(options.host)
host_backup.run()
exit_code = 0

# Release the lock
backup_lock_manager.release_lock()

# Exit the script
sys.exit(0)
