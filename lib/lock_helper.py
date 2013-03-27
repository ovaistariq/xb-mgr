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

import os
import fcntl
from config_helper import Config_helper

class Lock_helper(object):
    def __init__(self):
	config_helper = Config_helper(host=None)
	self._root_dir = config_helper.get_root_dir()
	self._pid_file = config_helper.get_pid_file()
	self._pid = os.getpid()
	self._pid_file_handle = None

    def acquire_lock(self):
	self._pid_file_handle = open(self._pid_file, "w")

	try:
	    fcntl.flock(self._pid_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
	except IOError as e:
	    self._pid_file_handle.close()
	    return False

	self._pid_file_handle.write(str(self._pid))
	self._pid_file_handle.flush()

	return True

    def release_lock(self):
	if self._pid_file_handle.closed:
	    return False
	
	try:
	    fcntl.flock(self._pid_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
	except IOError as e:
	    self._pid_file_handle.close()
	    return False

	os.remove(self._pid_file)
	fcntl.flock(self._pid_file_handle.fileno(), fcntl.LOCK_UN)
	self._pid_file_handle.close()

	return True

    def lock_exists(self):
	if not os.path.isfile(self._pid_file):
	    return False

	with open(self._pid_file, "w+") as f:
	    try:
		fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
	    except IOError as e:
		return True

	    pid = f.read()
	
	if not pid:
	    return False

	proc_dir = "/proc/%s" % pid
	if not os.path.isdir(proc_dir):
	    return False

	cmd = "%s/backup_manager" % self._root_dir
	cmdline_file = "%s/cmdline" % proc_dir
	if not os.path.isfile(cmdline_file) or not cmd in cmdline_file:
	    return False

	return True
