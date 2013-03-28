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
import subprocess
import shutil
import time
import ConfigParser
import contextlib
import mmap
from datetime import datetime
from config_helper import Config_helper

class Verifier(object):
    INNOBACKUPEX_CMD = "/usr/bin/innobackupex"
    MYSQLD_CMD = "/usr/sbin/mysqld"
    MYSQLCHECK_CMD = "/usr/bin/mysqlcheck"
    MYSQL_CNF_FILENAME = "backup-my.cnf"

    def __init__(self, host, dir_to_verify, logger):
        self._host = host
        self._verify_directory = dir_to_verify

        self._log_helper = logger
        config_helper = Config_helper(host=self._host)

        self._backup_directory = os.path.join(config_helper.get_backup_dir(),
                                            self._host)

    def setup(self):
        self._log_helper.info_message("Initializing verification directory...")

        self._error_log = os.path.join(self._verify_directory, "mysqld_verify.log")
        self._pid_file = os.path.join(self._verify_directory, "mysqld_verify.pid")
        self._socket_file = os.path.join(self._verify_directory,
                            "mysqld_verify.sock")
        self._mysqlcheck_log = os.path.join(self._verify_directory, "mysqlcheck.log")

    def verify(self):
        start_time = datetime.now()

        # Apply log
        self._log_helper.info_message("Preparing the verification directory")
        prepare_log = os.path.join(self._verify_directory, "apply_log.log")
        if not self.apply_log(log_file=prepare_log):
            self._log_helper.error_message("Failed to prepare the verification"
                                        " directory, check %s for details" %
                                        prepare_log)
            return False

        # Set correct dir permissions
        self._log_helper.info_message("Setting correct permissions on the "
                                    "verification directory")
        if not self.set_correct_dir_permissions():
            self._log_helper.error_message("Failed to set permissions")
            return False

        # Start mysqld and check tables
        if not self.verify_low_level():
            self._log_helper.error_message("VERIFICATION failed")
            return False
        
        end_time = datetime.now()
        timedelta = end_time - start_time

        self._log_helper.info_message("VERIFICATION completed successfully [Duration: %s]" %
                                    str(timedelta))
        return self._verify_directory

    def apply_log(self, log_file):
        cmd = [Verifier.INNOBACKUPEX_CMD, "--apply-log", self._verify_directory]

        self._log_helper.info_message("Executing command %s" % ' '.join(cmd))

        with open(log_file, "w") as f:
            cmd_return_code = subprocess.call(cmd, stdout=f,
                                            stderr=subprocess.STDOUT)

        if cmd_return_code > 0:
            return False

        return True

    def set_correct_dir_permissions(self):
        cmd = ["chown", "-R", "mysql:mysql", self._verify_directory]

        self._log_helper.info_message("Executing command %s" % ' '.join(cmd))
        
        cmd_return_code = subprocess.call(cmd)
        if cmd_return_code > 0:
            return False

        return True

    def verify_low_level(self):
        mysqld_ready_test_string = "ready for connections"
        mysqld_exited = False

        cmd = [Verifier.MYSQLD_CMD, 
                "--user=mysql", 
                "--skip-grant-tables",
                "--skip-networking", 
                "--log-error=%s" % self._error_log,
                "--pid=%s" % self._pid_file, 
                "--socket=%s" % self._socket_file,
                "--datadir=%s" % self._verify_directory,
                "--log-slow-queries=0",
                "--skip-slave-start",
                "--log=0",
                "--skip-log-warnings"]

        mysqld_extra_params = self.get_mysql_params()
        if not mysqld_extra_params:
            self._log_helper.error_message("Failed to parse %s file, "
                                        "verification cannot continue" % 
                                        Verifier.MYSQL_CNF_FILENAME)
            return False

        cmd.append("--innodb_data_file_path=%s" % mysqld_extra_params['innodb_data_file_path'])
        cmd.append("--innodb_log_files_in_group=%d" % mysqld_extra_params['innodb_log_files_in_group'])
        cmd.append("--innodb_log_file_size=%d" % mysqld_extra_params['innodb_log_file_size'])

        self._log_helper.info_message("Starting mysqld instance with command %s" % 
                                        ' '.join(cmd))
        
        with open(self._error_log, "a+") as f:
            mysqld_process = subprocess.Popen(cmd, stdout=f,
                                            stderr=subprocess.STDOUT)

            while True:
                time.sleep(1)

                if mysqld_process.poll() is not None:
                    mysqld_exited = True
                    break

                with open(self._error_log, "r") as f_ro:
                    if mysqld_ready_test_string in f_ro.read():
                        break

            if mysqld_exited:
                self._log_helper.error_message("MySQL daemon failed to start or "
                                    "exited, check %s for details" % self._error_log)
                return False

            self._log_helper.info_message("Checking all MySQL tables for errors"
                                            " or corruption")
            if not self.run_mysql_check():
                self._log_helper.error_message("One or more MySQL tables has "
                                            "errors or is corrupt, check "
                                            "%s for details" % self._mysqlcheck_log)
		return_val = False
            else:
		self._log_helper.info_message("Checking of MySQL tables complete. No errors found")
		self._log_helper.info_message("Shutting down mysqld instance")
		return_val = True

	    if mysqld_process.poll() is not None:
		self._log_helper.error_message("MySQL daemon was not running, "
					    "check %s for details" % self._error_log)
		return_val = False
            
            mysqld_process.terminate()
	    mysqld_process.wait()
        
        return return_val

    def run_mysql_check(self):
        check_cmd = [Verifier.MYSQLCHECK_CMD, "--socket=%s" % self._socket_file,
                    "--all-databases"]

        with open(self._mysqlcheck_log, "w") as f:
            check_cmd_status = subprocess.call(check_cmd, stdout=f,
                                            stderr=subprocess.STDOUT)

        if check_cmd_status > 0:
            return False

	with open(self._mysqlcheck_log) as f:
	    with contextlib.closing(mmap.mmap(f.fileno(), 0, prot=mmap.PROT_READ)) as m:
		if m.find("Error") != -1:
		    return False

        return True

    def get_mysql_params(self):
        mysql_cnf_file = os.path.join(self._verify_directory, "backup-my.cnf")
        config = ConfigParser.RawConfigParser()
        try:
            config.read(mysql_cnf_file)
            return {
                    'innodb_data_file_path': config.get("mysqld", 
                                                    "innodb_data_file_path"),
                    'innodb_log_files_in_group': config.getint("mysqld",
                                                    "innodb_log_files_in_group"),
                    'innodb_log_file_size': config.getint("mysqld",
                                                    "innodb_log_file_size")
                    }
        except Exception as e:
            return False
