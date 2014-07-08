import DNSaaSClient
from central_db import *

class DNSClient():

    def __init__(self, user):
        self.user = user
        DNSaaSClient.DNSaaSClient.apiurlDNSaaS = self.user.dns_url
        DNSaaSClient.token = self.user.dns_token

    def createUserDomain(self):
        self.user.dns_id_domain = DNSaaSClient.createDomain(self.user.global_id, self.user.global_id + "@mcn", self.token)
        self.user.save()

    def deleteUserDomain(self):
        DNSaaSClient.deleteDomain(self.user.dns_id_domain, self.token)

    def updateUserRecords(self):
        if self.user.dns_id_domain is not None:
            self.deleteUserDomain()
        self.createUserDomain()
        for pop_url in self.user.pops:
            DNSaaSClient.createRecord(self.id_domain, {'name': 'www.'+self.user.global_id+'.cdn.mobile-cloud-networking.eu', 'type': 'A', 'data': pop_url})
        return True
