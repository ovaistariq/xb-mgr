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

import ConfigParser
import os
import os.path

class Config_helper(object):
    CONFIG_PATH = '/usr/local/xb-mgr/conf/backup.conf'

    @staticmethod
    def get_hosts_to_backup():
        config = ConfigParser.RawConfigParser()
        config.read(Config_helper.CONFIG_PATH)

        hosts = []
        for section in config.sections():
            if section == 'default':
                continue
            if config.has_option(section, 'hostname'):
                hosts.append(config.get(section, 'hostname'))
        return hosts

    def __init__(self, host):
        self._config = ConfigParser.RawConfigParser()
        self._config.read(Config_helper.CONFIG_PATH)
        self._host = host

    def get_root_dir(self):
	return self.get_param_value(param_name='root_dir')

    def get_backup_dir(self):
        return self.get_param_value(param_name='backup_dir')

    def get_backup_manager_host(self):
        return self.get_param_value(param_name='backup_manager_host')

    def get_remote_backup_cmd(self):
        return self.get_param_value(param_name='remote_backup_cmd')

    def get_full_backup_day(self):
        return self.get_param_value(param_name='full_backup_day')

    def get_mysql_user(self):
        return self.get_param_value(param_name='mysql_user')

    def get_mysql_password(self):
        return self.get_param_value(param_name='mysql_password')

    def get_log_file(self):
        return self.get_param_value(param_name='log')

    def get_pid_file(self):
	return self.get_param_value(param_name='pid')

    def get_retention_days(self):
        return self.get_param_value(param_name='retain_days')

    def get_retain_num_ready_backups(self):
	return self.get_param_value(param_name='retain_num_ready_backups')

    def get_private_key_file(self):
        return self.get_param_value(param_name='ssh_private_key_file')

    def get_error_email_recipient(self):
	return self.get_param_value(param_name='error_email_recipient')

    def get_param_value(self, param_name):
        if self._config.has_section('default') == False:
            return False

        param_value = self._config.get('default', param_name)
        for section in self._config.sections():
            if (self._host is not None and 
		    section == self._host and
		    self._config.has_option(section, param_name)):
                param_value = self._config.get(section, param_name)

        return param_value
