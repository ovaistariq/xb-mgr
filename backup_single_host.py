#!/usr/bin/python

# (c) 2012, Ovais Tariq <ovais.tariq@percona.com>
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
import lib.config_helper
import sys
from optparse import OptionParser

# parse comand line arguments
parser = OptionParser()
parser.add_option('--host', type='string')
(options, args) = parser.parse_args()

exit_code = 1

# Get a list of hosts defined to be backed up
hosts_to_backup = lib.config_helper.Config_helper.get_hosts_to_backup()
num_hosts = len(hosts_to_backup)

# If there are no hosts defined then exit with error
if num_hosts < 1:
    sys.exit(exit_code)

# If there was no host provided on the command-line or the host 
# provided is not defined in the config file
if options.host is None or options.host not in hosts_to_backup:
    sys.exit(exit_code)

# Do the backup
host_backup = Host_backup(options.host)
host_backup.run()
exit_code = 0

sys.exit(exit_code)
