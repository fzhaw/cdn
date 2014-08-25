'''
Created on 03/04/2014
@author: Onesource
'''
import httplib2 as http
import json
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


class DNSaaSClientCore:
    '''
    Works as a client to the API DNSaaS. This class can be employed by other MCN services, or applications that require services from DNSaaS.
    '''
    version = 1
    apiurlDNSaaS = 'http://localhost:8080'
    token = ''
    idDomain = ''
    idRecord = ''

    def doRequest(self, method, path, body):
        '''
        Method to perform requests to the DNSaaS API. Requests can include creation, delete and other operations.
        This method needs to handle requests through a REST API.
        '''
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json; charset=UTF-8',
            'x-auth-token': self.token
        }
        target = urlparse(self.apiurlDNSaaS+path)

        h = http.Http()

        try:
            '''
            TODO: check error output on delete operations.
            '''
            response, content = h.request(target.geturl(), method, body, headers)

        except :
            return -1, "Server API not reachable"
        response_status = response.get("status")
        content_dict = json.loads(content)

        return response_status, content_dict

    def processReply(self, response):
        '''
        Method to process the reply from the DNSaaS API. The processing can be a simple print or other kind of treatment.
        '''
        print "processReply"


#Global Variables
DNSaaSClient = DNSaaSClientCore()




########    METHODS   ##########
def verifyAuthentication(user, password, tenant):
    '''
    Method to authenticate user.
    :param user: Name of the user
    :param password: Password of the user
    '''
    msgJson = {'user': user, 'password': password, 'tenant':tenant}
    status, content = DNSaaSClient.doRequest('GET', '/credencials', json.dumps(msgJson))
    #Verify response from DNSaaS API
    if status == '200':
        #Verify response from Designate
        if content['status'] == '200':
            return content['data']['access']['token']['id']
        else:
            print 'Status: '+str(content['status'])+'\nMessage: '+str(content['data'])
            return ''
    else:
        print 'Status: '+str(status)+'\nMessage: '+str(content)
        return ''



def createDomain(name, email, tokenId):
    '''
    Method to create a domain.
    :param name: Name of the domain
    '''
    msgJson = {'name': name , 'ttl': 3600, 'email': email}
    status, content = DNSaaSClient.doRequest('POST', '/domains', json.dumps(msgJson))
    if status == '200':
        print content
    else:
        print "No connection"

def getDomain(name, tokenId):
    '''
    Method to create a domain.
    :param name: Name of the domain
    '''
    msgJson = {'name': name}
    status, content = DNSaaSClient.doRequest('GET', '/domains', json.dumps(msgJson))
    if status == '200':
        if content['status'] == '200':
            DNSaaSClient.idDomain = content['data']['id']
            print content
    else:
        print content

def updateDomain(idDomain, email, tokenId):
    '''
    Method to update a domain.
    :param name: Name of the domain
    '''
    msgJson = {'idDomain':idDomain,'dataDomainUpdate': {'ttl': 7200, 'email': email} }
    status, content = DNSaaSClient.doRequest('PUT', '/domains', json.dumps(msgJson))
    if status == '200':
        print content
    else:
        print content

def deleteDomain(idDomain, tokenId):
    '''
    Method to delete a domain.
    :param name: Name of the domain
    '''
    msgJson = {'idDomain': idDomain}
    status, content = DNSaaSClient.doRequest('DELETE', '/domains', json.dumps(msgJson))
    if status == '200':
        print content
    else:
        print content

def createRecord(idDomain, jsonRecord,tokenId):
    '''
    Method to create a record.
    :param idDomain: Id of the domain
    '''
    msgJson = {'idDomain': idDomain , 'dataRecord': jsonRecord}
    status, content = DNSaaSClient.doRequest('POST', '/records', json.dumps(msgJson))
    if status == '200':
        print content
    else:
        print content

def getRecord(idDomain, jsonRecord,tokenId):
    '''
    Method to create a record.
    :param idDomain: Id of the domain
    '''
    msgJson = {'idDomain': idDomain , 'dataRecord': jsonRecord}
    status, content = DNSaaSClient.doRequest('GET', '/records', json.dumps(msgJson))
    if status == '200':
        DNSaaSClient.idRecord = content['data']['id']
        print content
    else:
        print content
def updateRecord(idDomain,idRecord, jsonRecord,tokenId):
    '''
    Method to create a record.
    :param idDomain: Id of the domain
    '''
    msgJson = {'idDomain': idDomain ,'idRecord': idRecord , 'dataRecord': jsonRecord}
    status, content = DNSaaSClient.doRequest('PUT', '/records', json.dumps(msgJson))
    if status == '200':
        print content
    else:
        print content

def deleteRecord(idDomain, idRecord, jsonRecord,tokenId):
    '''
    Method to create a record.
    :param idDomain: Id of the domain
    '''
    msgJson = {'idDomain': idDomain , 'idRecord': idRecord, 'dataRecord': jsonRecord}
    status, content = DNSaaSClient.doRequest('DELETE', '/records', json.dumps(msgJson))
    if status == '200':
        print content
    else:
        print content

if __name__ == '__main__':
    #Verify authentication of client DEFAULT = user1, pass1, tenant1 (user, pass, tenant)
    tokenid = verifyAuthentication('user1', 'password','tenant_user1')
    #####     Store token in the class DNSaaSClient
    DNSaaSClient.token =  tokenid
    #####     Function to create Domain
    #print(DNSaaSClient.token)

    createDomain('testuser1.com.','testadmin@example.org', DNSaaSClient.token)
    #####     Function to get info from domain
    getDomain('testuser1.com.', DNSaaSClient.token)
    #####     Function to Update the domain
    updateDomain(DNSaaSClient.idDomain, 'testadmin@example.org', DNSaaSClient.token)
    #####     Function to create record to the domain
    createRecord(DNSaaSClient.idDomain, {'name': 'www.testuser1.com.', 'type': 'A', 'data': '192.0.2.3'},  DNSaaSClient.token)
    #####     Function to create record to the domain
    getRecord(DNSaaSClient.idDomain, {'name': 'www.testuser1.com.', 'type': 'A'},  DNSaaSClient.token)
    #####     Function to update record from the domain
    updateRecord(DNSaaSClient.idDomain, DNSaaSClient.idRecord,{'data': '192.0.2.5'},  DNSaaSClient.token)
    ####     Function to delete record from the domain
    deleteRecord(DNSaaSClient.idDomain, DNSaaSClient.idRecord,{},  DNSaaSClient.token)
    #####   Function to Delete the domain
    deleteDomain(DNSaaSClient.idDomain, DNSaaSClient.token)
