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

from datetime import datetime
import logging
import os
from config_helper import Config_helper
from buffered_email_handler import Buffered_email_handler

class Log_helper(object):
    def __init__(self, host, log_name):
	self._host = host

        config = Config_helper(host)
        self._log_file = config.get_log_file()

        self._log_format = "[%(asctime)s] [" + host + "] [%(levelname)s] %(message)s"
        self._date_format = '%Y-%m-%d %H:%M:%S'
        self._log_level = logging.INFO
        
        self._logger = logging.getLogger("%s.%s" % (log_name, host))
        self._logger.setLevel(self._log_level)

    def setup(self):
        self.setup_log_file()
        self.setup_logging_handlers()

    def info_message(self, msg):
        self._logger.info(msg)

    def error_message(self, msg):
        self._logger.error(msg)

    def setup_log_file(self):
        log_dir = os.path.dirname(self._log_file)
        if os.path.isdir(log_dir) == False:
            os.makedirs(log_dir)

        with file(self._log_file, 'a'):
            os.utime(self._log_file, None)

    def setup_logging_handlers(self):
        formatter = logging.Formatter(fmt=self._log_format,
                                    datefmt=self._date_format)

        # Add a handler for logging messages to STDOUT/STDERR
        #console_handler = logging.StreamHandler()
        #console_handler.setLevel(self._log_level)
        #console_handler.setFormatter(formatter)
        #self._logger.addHandler(console_handler)

        # Add a handler for logging messages to log file
        log_file_handler = logging.FileHandler(self._log_file)
        log_file_handler.setLevel(self._log_level)
        log_file_handler.setFormatter(formatter)
        self._logger.addHandler(log_file_handler)

	# Add a handler for emailing messages
	email_handler = Buffered_email_handler(host=self._host)
        email_handler.setLevel(self._log_level)
        email_handler.setFormatter(formatter)
        self._logger.addHandler(email_handler)
