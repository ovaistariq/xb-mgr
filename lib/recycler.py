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
import stat
import shutil
from datetime import datetime, timedelta
from config_helper import Config_helper

class Recycler(object):
    def __init__(self, host, logger):
	self._host = host
	self._log_helper = logger

	config_helper = Config_helper(host=self._host)
	self._retention_days = int(config_helper.get_retention_days())
	self._retain_ready_backups = int(config_helper.get_retain_num_ready_backups())

	self._threshold_date = datetime.now() - timedelta(days=self._retention_days)

	self._backup_dir = os.path.join(config_helper.get_backup_dir(), self._host)
        self._backup_full_dir = os.path.join(self._backup_dir, "full")
        self._backup_inc_dir = os.path.join(self._backup_dir, "incremental")
	self._archive_dir = os.path.join(self._backup_dir, "ready")

    def recycle(self):
	dir_datetime_list = self.get_dirs_datetime_list()

	if len(dir_datetime_list) < 1:
	    return False

	self._log_helper.info_message("Starting to RECYCLE backups")
	self._log_helper.info_message("Leaving backups at least %d days old" %
					self._retention_days)

	threshold_dir_datetime = None
	for dir_datetime in reversed(dir_datetime_list):
	    if dir_datetime < self._threshold_date:
		dir_name = datetime.strftime(dir_datetime, "%Y_%m_%d_%H_%M_%S")
		if self.is_full_backup_dir(dir_name=dir_name):
		    threshold_dir_datetime = dir_datetime
		    break

	self._log_helper.info_message("Threshold date is set to %s" %
					threshold_dir_datetime)

	if threshold_dir_datetime is not None:
	    self._log_helper.info_message("Recycling full backups")
	    for root, dirs, files in os.walk(self._backup_full_dir):
		for dir_name in dirs:
		    try:
			dt = datetime.strptime(dir_name, "%Y_%m_%d_%H_%M_%S")
			if dt < threshold_dir_datetime:
			    backup_dir = os.path.join(root, dir_name)
			    self._log_helper.info_message("Removing backup %s" %
							backup_dir)
			    shutil.rmtree(backup_dir)
		    except Exception as e:
			continue

	    self._log_helper.info_message("Recycling incremental backups")
	    for root, dirs, files in os.walk(self._backup_inc_dir):
		for dir_name in dirs:
		    try:
			dt = datetime.strptime(dir_name, "%Y_%m_%d_%H_%M_%S")
			if dt < threshold_dir_datetime:
			    backup_dir = os.path.join(root, dir_name)
			    self._log_helper.info_message("Removing backup %s" %
                                                        backup_dir)
			    shutil.rmtree(backup_dir)
		    except Exception as e:
			continue

	self._log_helper.info_message("Recycling archived ready backups")
	self.recycle_archives()

	self._log_helper.info_message("Recycling completed")

	return True

    def recycle_archives(self):
	archive_list = []
	for root, dirs, files in os.walk(self._archive_dir):
	    for file in files:
		file_path = os.path.join(root, file)
		stats = os.stat(file_path)
		archive_list.append({'file_path': file_path, 
				'ctimestamp': stats[stat.ST_CTIME]})

	archive_list.sort(key=lambda archive: archive['ctimestamp'])
	for archive_to_del in archive_list[:-self._retain_ready_backups]:
	    self._log_helper.info_message("Removing archived ready backup %s" %
					archive_to_del['file_path'])
	    os.remove(archive_to_del['file_path'])
	
	return True

    def is_full_backup_dir(self, dir_name):
	return dir_name in os.listdir(self._backup_full_dir)

    def is_inc_backup_dir(self, dir_name):
	return dir_name in os.listdir(self._backup_inc_dir)

    def get_dirs_datetime_list(self):
	dir_datetime_list = []

	for root, dirs, files in os.walk(self._backup_full_dir):
	    for dir_name in dirs:
		try:
		    dt = datetime.strptime(dir_name, "%Y_%m_%d_%H_%M_%S")
		    dir_datetime_list.append(dt)
		except Exception as e:
		    continue

	for root, dirs, files in os.walk(self._backup_inc_dir):
	    for dir_name in dirs:
		try:
                    dt = datetime.strptime(dir_name, "%Y_%m_%d_%H_%M_%S")
                    dir_datetime_list.append(dt)
                except Exception as e:
                    continue

	dir_datetime_list.sort()

	return dir_datetime_list
