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

from lib.threaded_host_backup import Threaded_host_backup
from lib.lock_helper import Lock_helper
import lib.config_helper
import sys
import time
import Queue
import threading

# Take a global lock via PID file so that only one instance of this app runs at
# a single time
backup_lock_manager = Lock_helper()
if backup_lock_manager.lock_exists():
    sys.exit(1)
if not backup_lock_manager.acquire_lock():
    sys.exit(1)


hosts_to_backup = lib.config_helper.Config_helper.get_hosts_to_backup()
num_hosts = len(hosts_to_backup)

if num_hosts < 1:
    sys.exit(1)

queue = Queue.Queue()

backup_threads = []
# Spawn threads to do the backup
for i in range(num_hosts):
    thd = Threaded_host_backup(queue)
    thd.setDaemon(True)
    thd.start()
    backup_threads.append(thd)

# Add hosts that are to be backed up to the job queue
for host in hosts_to_backup:
    queue.put(host)

# Join every thread 
for thd in backup_threads:
    thd.join(0.5)

# Wait for all the items in the queue to be processed
#queue.join()
try:
    while threading.active_count() > 1:
        time.sleep(10)
except KeyboardInterrupt as e:
    print "Caught SIGINT, will now exit"
finally:
    # Release the lock
    backup_lock_manager.release_lock()

# Release the lock
#backup_lock_manager.release_lock()

sys.exit(0)
