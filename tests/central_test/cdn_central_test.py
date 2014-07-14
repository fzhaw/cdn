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
__author__ = 'florian'

from central.central_db import User, PoP
from nose.tools import assert_equals, assert_true
from webtest import TestApp
import central.cdn_central
import sys, mock, nose, httpretty

# To run tests use nosetests --mongoengine --mongoengine-clear-after-class cdn_central_test.py

test_cdn = TestApp(central.cdn_central.app)


class test_cdn_central_pop(object):
    @classmethod
    def setUpClass(cls):
        global pop, user

        pop = PoP()
        pop.address = '192.168.10.3'
        pop.admin_password = 'admin_pass'
        pop.admin_username = 'admin'
        pop.location = 'France'
        pop.save()

    def setup(self):
        global test_cdn
        self.test_cdn = test_cdn

    def test_cdn_central_get_pops(self):
        global pop
        pop_dictionary = []
        test_pop = dict()
        test_pop['location'] = pop.location
        test_pop['address'] = pop.address
        pop_dictionary.append(test_pop)
        # test retrieval
        response = self.test_cdn.get('/pop')
        assert_equals(response.status_int, 200)
        assert_equals(response.content_type, 'application/json')
        assert_equals(response.json, pop_dictionary)

    def test_cdn_central_post_pop_unique_duplicate(self):
        existing = PoP.objects().first()
        if existing is not None:
            existing.delete()
        new_pop = dict()
        new_pop['url'] = '192.168.100.100'
        new_pop['admin_uname'] = 'admin'
        new_pop['admin_password'] = 'admin'
        new_pop['location'] = 'France'
        # test create
        response = self.test_cdn.post_json('/pop', new_pop)
        assert_equals(response.status_int, 201)
        pop_db = PoP.objects(address='192.168.100.100').first()
        assert_equals(pop_db.location, 'France')
        # test duplicate
        response2 = self.test_cdn.post_json('/pop', new_pop, expect_errors=True)
        assert_equals(response2.status_int, 409)

class test_cdn_central_account(object):
    @classmethod
    def setUpClass(cls):
        global pop, user

        pop = PoP()
        pop.address = '192.168.10.3'
        pop.admin_password = 'admin_pass'
        pop.admin_username = 'admin'
        pop.location = 'France'
        pop.save()

        user = User()
        user.global_id = '12345'
        user.global_pwd = '54321'
        user.origin_pop = pop
        user.dns_url = 'dns.url'
        user.dns_token = 'dns.token'
        user.dns_id_domain = '1'
        user.domain_name = '12345.cdn.mobile-cloud-networking.eu'
        user.save()

    def setup(self):
        global test_cdn
        self.test_cdn = test_cdn

    def test_cdn_central_post_account(self):
        global pop
        new_user = dict()
        new_user['global_password'] = 'test_pass'
        new_user['dns_url'] = 'dns.management.endpoint'
        new_user['dns_token'] = 'abcdef123456'
        # test create
        response = self.test_cdn.post_json('/account', new_user)
        assert_equals(response.status_int, 201)
        assert_equals(response.content_type, 'application/json')

    @mock.patch('central.cdn_central.update_local_accounts')
    def test_cdn_central_successful_update_account(self, mock_update):
        global user, pop
        req = dict()
        req['pops'] = [pop.address]
        req['global_password'] = user.global_pwd
        mock_update.return_value = True
        response = self.test_cdn.post_json('/account/' + user.global_id, req)
        assert_equals(response.status_int, 200)
        assert_equals(response.json, {'origin':pop.address})

    @mock.patch('central.cdn_central.update_local_accounts')
    def test_cdn_central_failed_update_account(self, mock_update):
        global user, pop
        req = dict()
        req['pops'] = [pop.address]
        req['global_password'] = user.global_pwd
        mock_update.return_value = False
        response = self.test_cdn.post_json('/account/' + user.global_id, req)
        assert_equals(response.status_int, 200)
        assert_equals(response.json, {'error':'could not update local accounts'})

    @mock.patch('central.cdn_central.DNSClient.updateUserRecords')
    def test_cdn_central_update_local_accounts(self, mock_update_user_records):
        global user, pop
        mock_update_user_records.return_value = True
        httpretty.enable()
        post = httpretty.register_uri(httpretty.POST, 'http://' + pop.address + '/account', status=201)
        delete = httpretty.register_uri(httpretty.DELETE, 'http://' + pop.address + '/account', status=204)
        user.pops = [pop.address]
        user.save()
        response = central.cdn_central.update_local_accounts(user)
        #This test does not test pop deletion, to be extended
        assert_equals(httpretty.last_request().method, 'POST')
        assert_true(response)



    # def test_cdn_central_de

