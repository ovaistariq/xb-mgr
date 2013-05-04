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

import ansible.runner
import time
import os
from config_helper import Config_helper

class Async_remote_command(object):
    def __init__(self, host, command):
        self._host = host
        self._command = command
        self._job_id = 0
        self._COMMAND_SUCCESS_OUTPUT = "SUCCESS"

	config_helper = Config_helper(host=host)
        self._ssh_user = config_helper.get_ssh_user()
        self._private_key_file = config_helper.get_private_key_file()

    def setup_remote_command(self):
        # Setup remote command directory first
        command_dirname = os.path.dirname(self._command)
        ansible_cmd_args = "state=directory path=%s" % command_dirname
        runner_obj = ansible.runner.Runner(pattern=self._host,
                                            module_name="file", 
                                            module_args=ansible_cmd_args,
                                            remote_user=self._ssh_user,
                                            private_key_file=self._private_key_file)
        results = runner_obj.run()
        if self.validate_host_connection(remote_cmd_result=results) == False:
            print "Error connecting to", self._host
            return False

        host_result = results['contacted'][self._host]
        if 'state' not in host_result or host_result['state'] != 'directory':
            return False

        # Now copy the remote command to the host
        ansible_cmd_args = "src=%s dest=%s mode=0755" % (self._command, self._command)
        runner_obj = ansible.runner.Runner(pattern=self._host,
                                            module_name="copy",
                                            module_args=ansible_cmd_args,
                                            remote_user=self._ssh_user,
                                            private_key_file=self._private_key_file)
        results = runner_obj.run()
        if self.validate_host_connection(remote_cmd_result=results) == False:
            print "Error connecting to", self._host
            return False

        host_result = results['contacted'][self._host]
        if 'state' not in host_result or host_result['state'] != 'file':
            return False

        return True

    def execute_command(self, command_args, max_run_seconds=86400):
        ansible_cmd_args = "%s %s" % (self._command, command_args)
        runner_obj = ansible.runner.Runner(pattern=self._host, 
                                            module_name="command", 
                                            module_args=ansible_cmd_args, 
                                            background=max_run_seconds,
                                            remote_user=self._ssh_user,
                                            private_key_file=self._private_key_file)
        results = runner_obj.run()
        if self.validate_host_connection(remote_cmd_result=results) == False:
            print "Error connecting to", self._host
            return False

        host_result = results['contacted'][self._host]
        if host_result['started'] == 1:
            self._job_id = host_result['ansible_job_id']
            return True

        return False

    def poll_command_result(self, poll_seconds=10):
        poller_obj = ansible.runner.Runner(pattern=self._host, 
					    module_name="async_status", 
					    module_args="jid="+self._job_id,
                                            remote_user=self._ssh_user,
                                            private_key_file=self._private_key_file)

        while True:
            results = poller_obj.run()

            if self.validate_host_connection(remote_cmd_result=results) == False:
                print "Error connecting to", self._host
                return {'error': True, 
                        'error_msg': "Error connecting to %s" % self._host}

            host_result = results['contacted'][self._host]
            
            if 'finished' in host_result and host_result['finished'] == 1:
                if 'failed' in host_result and host_result['failed'] == 1:
                    return {'error': True, 'error_msg': host_result['msg']}
                
                if 'stderr' in host_result and host_result['stderr'] != '':
                    return {'error': True, 'error_msg': host_result['stderr']}
                
                if host_result['stdout'] == self._COMMAND_SUCCESS_OUTPUT:
                    return {'error': False, 'start_time': host_result['start'],
                            'end_time': host_result['end'], 
                            'duration': host_result['delta']}
            
                return {'error': True, 'error_msg': host_result['stdout']}

            time.sleep(poll_seconds)
       
    def validate_host_connection(self, remote_cmd_result):
        if (remote_cmd_result is None or self._host in remote_cmd_result['dark'] or
                self._host not in remote_cmd_result['contacted']):
            return False

        return True
