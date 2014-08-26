# Copyright 2014 Zuercher Hochschule fuer Angewandte Wissenschaften
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import DNSaaSClient
from central_db import *

class DNSClient():

    def __init__(self, user):
        self.user = user
        DNSaaSClient.DNSaaSClient.apiurlDNSaaS = self.user.dns_url
        DNSaaSClient.token = self.user.dns_token

    def createUserDomain(self):
        self.user.dns_id_domain = DNSaaSClient.createDomain(self.user.global_id, self.user.global_id + "@mcn", self.user.dns_token)
        self.user.save()

    def deleteUserDomain(self):
        DNSaaSClient.deleteDomain(self.user.dns_id_domain, self.user.dns_token)

    def updateUserRecords(self):
        if self.user.dns_id_domain is not None:
            self.deleteUserDomain()
        self.createUserDomain()
        for pop_url in self.user.pops:
            DNSaaSClient.createRecord(self.id_domain, {'name': 'www.'+self.user.global_id+'.cdn.mobile-cloud-networking.eu', 'type': 'A', 'data': pop_url})
        return True
