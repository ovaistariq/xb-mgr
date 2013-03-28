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

import logging
import logging.handlers
from config_helper import Config_helper
from email_helper import Email_helper

class Buffered_email_handler(logging.handlers.MemoryHandler):
    BUFFER_CAPACITY = 16*1024

    def __init__(self, host):
        logging.handlers.MemoryHandler.__init__(self, target=None,
                            flushLevel=logging.ERROR,
                            capacity=Buffered_email_handler.BUFFER_CAPACITY)
        self._emailer = Email_helper()

	self._host = host

	config_helper = Config_helper(host=host)
	to_emails = config_helper.get_error_email_recipient()
	self._to_email_list = to_emails.split(',')

	self._error_logged = False

    def flush(self):
	if not self._error_logged:
	    subject = "BACKUP run on %s successfully completed" % self._host
	else:
	    subject = "ERROR: BACKUP on %s failed" % self._host

        if len(self.buffer) > 0:
            try:
                msg = ""
                for record in self.buffer:
                    record = self.format(record)
                    msg = msg + record + "\r\n"

                self._emailer.send_email(subject=subject, msg=msg,
                                    to_email_list=self._to_email_list)
            except:
                self.handleError(None)

            self.buffer = []

    def shouldFlush(self, record):
	if record.levelno >= logging.ERROR:
	    self._error_logged = True

	return (len(self.buffer) >= self.capacity or 
		record.levelno >= self.flushLevel)
