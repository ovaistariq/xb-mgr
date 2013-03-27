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
import shutil
import subprocess
import fnmatch
import ConfigParser
from datetime import datetime
from backup import Backup
from config_helper import Config_helper

class Preparer(object):
    XBSTREAM_CMD = "/usr/bin/xbstream"
    QPRESS_CMD = "/usr/bin/qpress"
    INNOBACKUPEX_CMD = "/usr/bin/innobackupex"
    CHECKPOINT_FILENAME = "prepare_checkpoint"

    def __init__(self, host, backup_type, backup_dir, prepare_dir, logger):
        self._host = host
        self._backup_type = backup_type
        self._backup_dir = backup_dir
        self._prepare_directory = prepare_dir
        self._log_helper = logger

        config_helper = Config_helper(host=self._host)

        self._backup_directory = os.path.join(
                                    config_helper.get_backup_dir(), 
                                    self._host)
        self._backup_full_directory = os.path.join(
                                    self._backup_directory, 
                                    "full")
        self._backup_incremental_directory = os.path.join(
                                        self._backup_directory, 
                                        "incremental")

    def setup(self):
        self._log_helper.info_message("Initializing directories "
                                    "for backup preparation...")

        # Setup prepare directory
        if self._backup_type == Backup.BACKUP_TYPE_FULL:
            if os.path.isdir(self._prepare_directory):
                shutil.rmtree(self._prepare_directory)

        if not os.path.isdir(self._prepare_directory):
            os.makedirs(self._prepare_directory)

    def prepare(self):
        start_time = datetime.now()

        if self._backup_type == Backup.BACKUP_TYPE_FULL:
            self._log_helper.info_message("Preparing FULL backup %s" % 
                                        self._backup_dir)
            if self.prepare_full_backup() == False:
                return False
        elif self._backup_type == Backup.BACKUP_TYPE_INC:
            self._log_helper.info_message("Preparing INCREMENTAL "
                                        "backup %s" % self._backup_dir)
            if self.prepare_incremental_backup() == False:
                return False
        else:
            self._log_helper.error_message("Unknown backup type %s, "
                                            "backup cannot continue" % 
                                            self._backup_type)
            return False
        
        end_time = datetime.now()
        timedelta = end_time - start_time

        self._log_helper.info_message("Backup PREPARED successfully "
                                    "[Duration: %s]" % str(timedelta))
        return self._prepare_directory

    def prepare_full_backup(self):
        self._log_helper.info_message("Prepared backup will be "
                                    "available in %s" % 
                                    self._prepare_directory)

        return self.prepare_backup_low_level(
                                    backup_dir=self._backup_dir, 
                                    prepare_dir=self._prepare_directory,
                                    backup_type=Backup.BACKUP_TYPE_FULL)

    def prepare_incremental_backup(self):
        self._log_helper.info_message("Prepared backup will be "
                                    "available in %s" % 
                                    self._prepare_directory)

        backup_to_prep_lsn_info = self.get_lsn_info(
                                    backup_dir=self._backup_dir,
                                    checkpoint_filename=Backup.CHECKPOINTS_FILE)

        start_lsn = self.get_prepare_dir_to_lsn()
        end_lsn = backup_to_prep_lsn_info['to_lsn']

        self._log_helper.info_message("Backup will be prepared from LSN %s upto LSN %s" % 
                                        (start_lsn, end_lsn))

        # If the prepare directory is empty then must prepare the last full
        # backup first
        self._log_helper.info_message("Checking to see if backups prior "
                                    "to this incremental backup have "
                                    "already been prepared")
        if start_lsn == 0:
            latest_full_backup_dir = self.get_latest_full_backup()

            self._log_helper.info_message("Preparing the last full backup "
                                        "%s first" % latest_full_backup_dir)

            if latest_full_backup_dir == False:
                self._log_helper.error_message("Could not prepare "
                                            "the last full backup")
                return False

            return_val = self.prepare_backup_low_level(
                                        backup_dir=latest_full_backup_dir,
                                        prepare_dir=self._prepare_directory,
                                        backup_type=Backup.BACKUP_TYPE_FULL)
            if return_val == False:
                self._log_helper.error_message("Could not prepare "
                                            "the last full backup")
                return False

            prep_dir_lsn_info = self.get_lsn_info(
                                    backup_dir=self._prepare_directory, 
                                    checkpoint_filename=Preparer.CHECKPOINT_FILENAME)
            start_lsn = prep_dir_lsn_info['to_lsn']
            if start_lsn == 0:
                self._log_helper.error_message("Last full backup was prepared "
                                            "but LSN information was "
                                            "not updated")
                return False

            self._log_helper.info_message("Backup rolled forward to LSN %s" %
                                            start_lsn)

        self._log_helper.info_message("We will now roll forward the "
                                    "incremental backups one by one "
                                    "upto the backup %s" % self._backup_dir)

        # Prepare all incremental backups upto the current backup
        inc_dir_datetime_list = self.get_directories_datetime_list(
                                        path=self._backup_incremental_directory)
        if len(inc_dir_datetime_list) < 1:
            self._log_helper.error_message("Could not find any "
                                        "incremental backup to roll forward")
            return False

	# list of incremental backup dirs that have been prepared
	inc_dir_rolled_fwd = []

        while start_lsn != end_lsn:
            for inc_dir_datetime in inc_dir_datetime_list:
                inc_dir = os.path.join(self._backup_incremental_directory,
                                    inc_dir_datetime.strftime("%Y_%m_%d_%H_%M_%S"))

                inc_dir_lsn_info = self.get_lsn_info(
                                        backup_dir=inc_dir,
                                        checkpoint_filename=Backup.CHECKPOINTS_FILE)
                
                if (inc_dir_lsn_info['from_lsn'] == start_lsn) and (inc_dir not in inc_dir_rolled_fwd):
                    self._log_helper.info_message("Rolling forward to the "
                                                "next incremental backup %s" %
                                                inc_dir)

                    return_val = self.prepare_backup_low_level(
                                                backup_dir=inc_dir,
                                                prepare_dir=self._prepare_directory,
                                                backup_type=Backup.BACKUP_TYPE_INC)
                    if return_val == False:
                        self._log_helper.error_message("Could not roll forward"
                                                    " to %s" % inc_dir)
                        return False

                    prep_dir_lsn_info = self.get_lsn_info(
                                            backup_dir=self._prepare_directory, 
                                            checkpoint_filename=Preparer.CHECKPOINT_FILENAME)
                    start_lsn = prep_dir_lsn_info['to_lsn']
                    if start_lsn == 0:
                        self._log_helper.error_message("Backup was rolled "
                                                    "forward but LSN "
                                                    "informaiton was not "
                                                    "updated")
                        return False

		    inc_dir_rolled_fwd.append(inc_dir)

                    self._log_helper.info_message("Backup rolled forward to "
                                                    "LSN %s" % start_lsn)

                    break

        return True

    def prepare_backup_low_level(self, backup_dir, prepare_dir, backup_type):
        if backup_type == Backup.BACKUP_TYPE_FULL:
            unpack_to_dir = prepare_dir
            incremental_dir = None
        else:
            incremental_dir = os.path.join(prepare_dir, "tmp_incremental")
            unpack_to_dir = incremental_dir
            if os.path.isdir(unpack_to_dir):
                shutil.rmtree(unpack_to_dir)
            os.makedirs(unpack_to_dir)
        
        # Change working directory to prepare directory
        os.chdir(unpack_to_dir)

        # Unpack the backup archive
        backup_file = os.path.join(backup_dir, "backup.xbstream")
        self._log_helper.info_message("Unpacking backup archive %s to %s" % 
                                        (backup_file, unpack_to_dir))
        if self.unpack_archive(backup_file) == False:
            self._log_helper.error_message("Failed to unpack the backup "
                                        "archive, probably it does not exist")
            return False

        # Uncompress the individual compressed files
        self._log_helper.info_message("Uncompressing compressed files")
        if self.uncompress_files(unpack_to_dir) == False:
            self._log_helper.error_message("Failed to uncompress the files "
                                        "from backup archive")
            return False

        # Apply log
        self._log_helper.info_message("Preparing backup by replaying "
                                    "committed transactions")
        prepare_log_name = "prepare_%s.log" % os.path.basename(backup_dir)
        prepare_log = os.path.join(prepare_dir, prepare_log_name)
        return_val = self.prepare_backup_innobackupex(prepare_dir=prepare_dir,
                                        incremental_dir=incremental_dir,
                                        log_file=prepare_log)

        # Copy the checkpoint file so that it can be used for the next backup
        self.standardize_checkpoints_file(dir=prepare_dir)

        if return_val == False:
            self._log_helper.error_message("Backup preparation failed, check "
                                        "%s for details" % prepare_log)
            return False

        # Clean the tmp incremental directory
        if backup_type == Backup.BACKUP_TYPE_INC:
            if os.path.isdir(incremental_dir):
                shutil.rmtree(incremental_dir)

        return True

    def unpack_archive(self, backup_file):
        cmd = [Preparer.XBSTREAM_CMD, "-x"]
        with open(backup_file) as f:
            cmd_return_code = subprocess.call(cmd, stdin=f)

        if cmd_return_code > 0:
            return False

        return True
        
    def uncompress_files(self, unpacked_archive_dir):
        for root, dirs, files in os.walk(unpacked_archive_dir):
            for filename in files:
                if fnmatch.fnmatch(filename, "*.qp") == False:
                    continue

                file_path = os.path.join(root, filename)
                file_dir = root
                cmd = [Preparer.QPRESS_CMD, "-d", file_path, file_dir]
                cmd_return_code = subprocess.call(cmd)

                if cmd_return_code > 0:
                    return False

                os.remove(file_path)

        return True
        
    def prepare_backup_innobackupex(self, prepare_dir, incremental_dir, log_file):
        cmd = [Preparer.INNOBACKUPEX_CMD, "--apply-log", "--redo-only"]
        if incremental_dir is not None:
            cmd.append("--incremental-dir")
            cmd.append(incremental_dir)
        cmd.append(prepare_dir)

        self._log_helper.info_message("Executing command %s" % ' '.join(cmd))

        with open(log_file, "w") as f:
            cmd_return_code = subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT)

        if cmd_return_code > 0:
            return False

        return True

    def get_prepare_dir_to_lsn(self):
        prep_dir_is_empty = (os.listdir(self._prepare_directory) == False)
        if prep_dir_is_empty:
            start_lsn = 0
        else:
            prep_dir_lsn_info = self.get_lsn_info(
                                    backup_dir=self._prepare_directory,
                                    checkpoint_filename=Preparer.CHECKPOINT_FILENAME)
            if prep_dir_lsn_info == False:
                start_lsn = 0
            else:
                start_lsn = prep_dir_lsn_info['to_lsn']

        return start_lsn

    def get_lsn_info(self, backup_dir, checkpoint_filename):
        config = ConfigParser.RawConfigParser()
        try:
            config.read(os.path.join(backup_dir, checkpoint_filename))
            from_lsn = config.getint('xtrabackup_lsn_info', 'from_lsn')
            to_lsn = config.getint('xtrabackup_lsn_info', 'to_lsn')
            return {'from_lsn': from_lsn, 'to_lsn': to_lsn}
        except Exception as e:
            return False

    def standardize_checkpoints_file(self, dir):
        checkpoint_file_orig = os.path.join(dir, Backup.CHECKPOINTS_FILE)
        checkpoint_file_copy = os.path.join(dir, Preparer.CHECKPOINT_FILENAME)
        shutil.copyfile(checkpoint_file_orig, checkpoint_file_copy)

        if os.path.isfile(checkpoint_file_copy) == False:
            return False

        with open(checkpoint_file_copy) as f:
            data = f.read()
        with open(checkpoint_file_copy, 'w') as f:
            f.write("[xtrabackup_lsn_info]\n" + data)

        return True
   
    def get_latest_full_backup(self):
        full_backup_dir_list = self.get_directories_datetime_list(
                                            path=self._backup_full_directory)
        if len(full_backup_dir_list) == 0:
            return False

        full_backup_datetime = max(full_backup_dir_list)
        dir_name = os.path.basename(self._backup_dir)
        backup_to_prep_datetime = datetime.strptime(dir_name, 
                                                        "%Y_%m_%d_%H_%M_%S")
        if full_backup_datetime > backup_to_prep_datetime:
            return False

        return os.path.join(self._backup_full_directory,
                            full_backup_datetime.strftime("%Y_%m_%d_%H_%M_%S"))

    def get_directories_datetime_list(self, path):
        dir_list = []
        for root, dirs, files in os.walk(path):
            for dir in dirs:
                try:
                    dt = datetime.strptime(dir, "%Y_%m_%d_%H_%M_%S")
                    dir_list.append(dt)
                except Exception as e:
                    continue

        dir_list.sort()
        return dir_list
