#   Copyright (c) 2013-2015, Intel Performance Learning Solutions Ltd, Intel Corporation.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""
CDN SO.
"""

import os
import threading
import requests
import json
from sdk.mcn import util
from sdk import services

HERE = os.environ['OPENSHIFT_REPO_DIR']


class ServiceOrchstratorExecution(object):
    """
    Sample SO execution part.
    """

    def __init__(self, token):
        self.token = token

        # Find out service endpoint
        self.endpoint = services.get_service_endpoint("cdnaas", token, tenant_name='zhaw_test')
        if self.endpoint is None:
            raise Exception("No CDN endpoint")
        # Find out user submitted parameters (through SM)
        self.password = 'pass1234'

        self.userid = None
        self.origin = None

    def design(self):
        """
        Do initial design steps here.
        """
        pass

    def deploy(self):
        """
        deploy SICs.
        """
        if self.password is not None:
            payload = {"global_password": self.password}
            headers = {'Content-Type': 'application/json'}

            r = requests.post(self.endpoint + '/account', data=json.dumps(payload), headers=headers)
            if r.status_code != 201:
                raise Exception("No CDN endpoint")

            jreq = r.json()
            self.userid = jreq['global_id']
            self.origin = jreq['origin']

    def provision(self):
        """
        (Optional) if not done during deployment - provision.
        """
        pass

    def dispose(self):
        """
        Dispose SICs.
        """
        if self.userid is not None:
            payload = {"global_id": self.userid, "global_password": self.password}
            headers = {'Content-Type': 'application/json'}

            r = requests.delete(self.endpoint + '/account', data=json.dumps(payload), headers=headers)

    def state(self):
        """
        Report on state.
        """

        #TODO: Send back credentials based on syntax used in e2e so

        if self.userid is not None:
            creds = {'mcn.cdnaas.endpoint': self.endpoint, 'mcn.cdnaas.userid': self.userid, 'mcn.cdnaas.password': self.password}
            return json.dumps(creds)
            # return 'Service is ready. Access credentials: '
        # Should contact CDN central for status, not implemented yet
        pass
        # if self.stack_id is not None:
        #     tmp = self.deployer.details(self.stack_id, self.token)
        #     if tmp['state'] != 'CREATE_COMPLETE':
        #         return 'Stack is currently being deployed...'
        #     else:
        #         return 'All good - Stack id is: ' + str(self.stack_id) + \
        #                ' - Output is: ' + str(tmp['output'][0]['output_value'])
        # else:
        #     return 'Stack is not deployed atm.'


class ServiceOrchstratorDecision(object):
    """
    Sample Decision part of SO.
    """

    def __init__(self, so_e, token):
        self.so_e = so_e
        self.token = token

    def run(self):
        """
        Decision part implementation goes here.
        """
        pass


class ServiceOrchstrator(object):
    """
    Sample SO.
    """

    def __init__(self, token):
        self.so_e = ServiceOrchstratorExecution(token)
        self.so_d = ServiceOrchstratorDecision(self.so_e, token)
        # so_d.start()
