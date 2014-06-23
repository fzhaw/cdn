import DNSaaSClient
from central_db import *

class DNSClient():

    def __init__(self, endpoint, token, user):
        self.endpoint = endpoint
        self.token = token
        self.user = user
        self.id_domain = None

        DNSaaSClient.DNSaaSClient.apiurlDNSaaS = endpoint
        DNSaaSClient.token = token

    def createUserDomain(self):
        self.id_domain = DNSaaSClient.createDomain(self.user.global_id, self.user.global_id + "@mcn", self.token)

    def deleteUserDomain(self):
        DNSaaSClient.deleteDomain(self.id_domain, self.token)

    def updateUserRecords(self):
        if self.id_domain is not None:
            self.deleteUserDomain()
        self.createUserDomain()
        for pop_url in self.user.pops:
            DNSaaSClient.createRecord(self.id_domain, {'name': 'www.'+self.user.global_id+'cdn.mobile-cloud-networking.eu.', 'type': 'A', 'data': pop_url})

