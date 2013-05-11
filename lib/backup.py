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

import os
import time
import ConfigParser
from datetime import datetime
from async_remote_command import Async_remote_command
from config_helper import Config_helper

class Backup(object):
    CHECKPOINTS_FILE = "xtrabackup_checkpoints"
    BACKUP_TYPE_FULL = "full"
    BACKUP_TYPE_INC = "inc"

    def __init__(self, host, logger):
        self._host = host
	self._log_helper = logger

        config_helper = Config_helper(host=self._host)

        self._backup_manager_host = config_helper.get_backup_manager_host()
        self._full_backup_day = config_helper.get_full_backup_day()

        self._remote_backup_cmd = config_helper.get_remote_backup_cmd()
        self._remote_cmd = Async_remote_command(host=self._host,
                                                command=self._remote_backup_cmd)

        self._backup_directory = os.path.join(config_helper.get_backup_dir(), self._host)
        self._backup_full_directory = os.path.join(self._backup_directory, "full")
        self._backup_incremental_directory = os.path.join(self._backup_directory, "incremental")

    def setup(self):
        self._log_helper.info_message("Initializing backup directories and remote command...")

        if not os.path.isdir(self._backup_full_directory):
            os.makedirs(self._backup_full_directory)

        if not os.path.isdir(self._backup_incremental_directory):
            os.makedirs(self._backup_incremental_directory)

        self._remote_cmd.setup_remote_command()
            
    def is_full_backup_day(self):
        day_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        current_time = time.localtime()
        today = day_of_week[current_time.tm_wday]

        if today == self._full_backup_day:
            return True

        return False

    def can_do_incremental_backup(self):
	# If today is a full backup day, and no prior full backups have been
	# done today, then full backup must be done
        if self.is_full_backup_day():
	    full_backup_dt_list = self.get_directories_list(path=self._backup_full_directory)
	    today = datetime.now()

	    full_backup_done_today = False
	    for dir_dt in full_backup_dt_list:
		if dir_dt.date() == today.date():
		    full_backup_done_today = True

	    if not full_backup_done_today:
		return False

	# If no backups are found, then full backup must be done
        latest_backup_dir_name = self.get_latest_backup_dir_name()
        if latest_backup_dir_name is None:
            return False

	# If last backup was taken more than 1 day ago, then full backup must
	# be done
        latest_backup_dir_name = latest_backup_dir_name.rstrip('/')
        latest_backup_date = datetime.strptime(os.path.basename(latest_backup_dir_name), "%Y_%m_%d_%H_%M_%S")
        timedelta = datetime.today() - latest_backup_date
        if timedelta.days > 1:
            return False

        return True

    def do_backup(self):
        if self.can_do_incremental_backup():
            return_val = self.do_incremental_backup()
        else:
            return_val = self.do_full_backup()

        return return_val

    def do_full_backup(self):
        self._log_helper.info_message("Starting FULL backup")

        backup_dir_name = os.path.join(self._backup_full_directory, time.strftime("%Y_%m_%d_%H_%M_%S"))
        if os.path.isdir(backup_dir_name):
            self._log_helper.error_message("Backup directory %s already exists. Please move it away." % backup_dir_name)
            return False

        self._log_helper.info_message("Created backup directory %s" % backup_dir_name)

        os.makedirs(backup_dir_name)

        self._log_helper.info_message("Backup STARTED ...")

        backup_cmd_args = "-H %s -f -d %s" % (self._backup_manager_host, backup_dir_name)

        self._log_helper.info_message("Executing remote command %s %s" % (self._remote_backup_cmd, backup_cmd_args))

        if self.execute_remote_backup_cmd(backup_cmd_args=backup_cmd_args) == False:
            return False

        self._log_helper.info_message("Standardizing checkpoints file so it can be used for next run")
        if self.standardize_checkpoints_file(backup_dir_name) == False:
            self._log_helper.error_message("Failed to standardize the checkpoints file, probably it does not exist")
            return False

        self._log_helper.info_message("Backup COMPLETED")
        return {'backup_type': Backup.BACKUP_TYPE_FULL, 'backup_dir': backup_dir_name}

    def do_incremental_backup(self):
        self._log_helper.info_message("Starting INCREMENTAL backup")

        latest_backup_dir_name = self.get_latest_backup_dir_name()

        self._log_helper.info_message("Last latest backup found at %s" % latest_backup_dir_name)

        last_lsn = self.get_last_lsn(latest_backup_dir_name)
        if last_lsn == False:
            self._log_helper.error_message("Couldn't find LSN info from the latest backup dir %s" % latest_backup_dir_name)
            return False

        backup_dir_name = os.path.join(self._backup_incremental_directory, time.strftime("%Y_%m_%d_%H_%M_%S"))
        if os.path.isdir(backup_dir_name):
            self._log_helper.error_message("Backup directory %s already exists. Please move it away." % backup_dir_name)
            return False

        self._log_helper.info_message("Created backup directory %s" % backup_dir_name)

        os.makedirs(backup_dir_name)

        self._log_helper.info_message("Backup STARTED from LSN %d ..." % last_lsn)

        backup_cmd_args = "-H %s -i -l %d -d %s" % (self._backup_manager_host, last_lsn, backup_dir_name)

        self._log_helper.info_message("Executing remote command %s %s" % (self._remote_backup_cmd, backup_cmd_args))

        if self.execute_remote_backup_cmd(backup_cmd_args=backup_cmd_args) == False:
            return False

        self._log_helper.info_message("Standardizing checkpoints file so it can be used for next run")
        if self.standardize_checkpoints_file(backup_dir_name) == False:
            self._log_helper.error_message("Failed to standardize the checkpoints file, probably it does not exist")
            return False

        self._log_helper.info_message("Backup COMPLETED")
        return {'backup_type': Backup.BACKUP_TYPE_INC, 'backup_dir': backup_dir_name}

    def execute_remote_backup_cmd(self, backup_cmd_args):
        if self._remote_cmd.execute_command(command_args=backup_cmd_args) == False:
            self._log_helper.error_message("Error executing remote backup "
					    "script on %s" % self._host)
            return False

        cmd_result = self._remote_cmd.poll_command_result()

        if cmd_result['error'] == False:
            self._log_helper.info_message("Backup FINISHED successfully [Duration: %s]" % cmd_result['duration'])
            return True

        self._log_helper.error_message("Backup FAILED")
        self._log_helper.error_message(cmd_result['error_msg'])
        return False

    def get_last_lsn(self, backup_dir):
        config = ConfigParser.RawConfigParser()
        try:
            config.read(os.path.join(backup_dir, Backup.CHECKPOINTS_FILE))
            return config.getint('xtrabackup_lsn_info', 'to_lsn')
        except Exception as e:
            return False

    def get_latest_backup_dir_name(self):
        full_backup_dir_list = self.get_directories_list(self._backup_full_directory)
        inc_backup_dir_list = self.get_directories_list(self._backup_incremental_directory)

        if len(full_backup_dir_list) == 0 and len(inc_backup_dir_list) == 0:
            return None

        if len(full_backup_dir_list) > 0:
            max_full_backup_day = max(full_backup_dir_list)
        if len(inc_backup_dir_list) > 0:
            max_inc_backup_day = max(inc_backup_dir_list)

        if (len(inc_backup_dir_list) == 0 or max_full_backup_day > max_inc_backup_day):
            latest_backup_dir = os.path.join(self._backup_full_directory,
                                            max_full_backup_day.strftime("%Y_%m_%d_%H_%M_%S"))
        else:
            latest_backup_dir = os.path.join(self._backup_incremental_directory,
                                            max_inc_backup_day.strftime("%Y_%m_%d_%H_%M_%S"))
        return latest_backup_dir

    def get_directories_list(self, path):
        dir_list = []
        for root, dirs, files in os.walk(path):
            for dir in dirs:
                try:
                    dt = datetime.strptime(dir, "%Y_%m_%d_%H_%M_%S")
                    dir_list.append(dt)
                except Exception as e:
                    continue
        return dir_list

    def standardize_checkpoints_file(self, backup_dir):
        checkpoint_file = os.path.join(backup_dir, Backup.CHECKPOINTS_FILE)
        if os.path.isfile(checkpoint_file) == False:
            return False

        with open(checkpoint_file) as f:
            data = f.read()
        with open(checkpoint_file, 'w') as f:
            f.write("[xtrabackup_lsn_info]\n" + data)

        return True
