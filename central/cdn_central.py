#!/usr/bin/python
"""
   Copyright 2014 ZHAW

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
from requests import post, delete
import json
from bottle import route, run, request, abort, response, HTTPResponse, Bottle, debug
from central_db import *
from uuid import uuid4
from simplejson.scanner import JSONDecodeError
import traceback
import sys
from central.DNSClient import DNSClient

app = Bottle()


@app.route('/account', method='POST')
def post_account():
    """
    Creates an account on each PoP, selects one PoP to be the origin
    Requires body in the request: {"global_password":"yyyy", "dns_url":"dns.management.endpoint", "dns_token":"tokendata"}
    global_id is generated, domain_name is created for this user
    Other informations may be needed to infer closest PoP
    TODO: Check with DNS

    :return: HTTP 201 if created, with json body {"global_id":"hduakdhwakdiwad",
    "domain_name":"uuid.cdn.mobile-cloud-networking.eu"}
    """
    try:
        jreq = request.json
        global_id = str(uuid4())
        password = jreq.get('global_password')
        dns_url = jreq.get('dns_url')
        dns_token = jreq.get('dns_token')

        if password is not None:
            # User exists?
            user = User.objects(global_id=global_id).first()
            if user is None:
                # for now, takes the first from the PoP list
                pop = PoP.objects().first()
                # generate domain name
                domain_name = global_id + '.cdn.mobile-cloud-networking.eu'
                # Save user to Mongo
                new_user = User(global_id=global_id, global_pwd=password, dns_url=dns_url,
                                dns_token=dns_token, domain_name=domain_name)
                new_user.save()

                body = {'global_id': global_id, 'origin': pop.address, 'domain': domain_name}
                response.set_header('Content-Type', 'application/json')
                response.status = 201
                return json.dumps(body)
                # return HTTPResponse(status=201)
            else:
                #TODO: Add update capabilities for User
                abort(409, 'User already exists')
        else:
            abort(400, 'JSON incomplete')
    except JSONDecodeError:
        abort(400, 'JSON received invalid')
        # except Exception, ex:
        #     abort(500, ex.message)


@app.route('/account/:global_id', method='GET')
def retrieve_configuration(global_id):
    """
    JSON format: {'global_password':'password'}
    """
    try:
        jreq = request.json
        password = jreq.get('global_password')

        if password is not None:
            user = User.objects(global_id=global_id, global_pwd=password).first()
            if user is not None:
                #For now sends list of pops back
                body = {'pops': user.pops}
                response.set_header('Content-Type', 'application/json')
                return json.dumps(body)
                #TODO: test case
            else:
                abort(409, 'Authentication invalid')
        else:
            abort(400, 'JSON incomplete')

    except JSONDecodeError:
        abort(400, 'JSON received invalid')


@app.route('/account/:global_id', method='POST')
def update_configuration(global_id):
    """
    JSON format: {'pops':['pop1.swift1.zhaw.ch', 'pop2.swift2.cloudsigma.ch'], 'global_password':'password'}
    Chooses random Origin PoP from this list
    returns: {"origin":"192.168.10.10"}
    """
    try:
        jreq = request.json
        password = jreq.get('global_password')
        pops_urls = jreq.get('pops')

        if password is not None:
            # User exists?
            user = User.objects(global_id=global_id, global_pwd=password).first()
            if user is not None:
                #Loop over pops checking existence on the DB
                for pop_url in pops_urls:
                    if PoP.objects(address=pop_url).first() is None:
                        abort('204', 'PoP ' + pop_url + ' does not exist.')
                # chooses first pop as origin
                user_origin_pop = PoP.objects(address=pops_urls[0]).first()
                print user_origin_pop.address
                user.origin_pop = user_origin_pop
                user.pops = pops_urls
                user.save()
                local_update = update_local_accounts(user)
                if local_update:
                    return HTTPResponse(status=200, body={'origin': user_origin_pop.address})
                else:
                    return HTTPResponse(status=200, body={'error': 'could not update local accounts'})
            else:
                abort(409, 'Authentication invalid for user: ' + global_id)
        else:
            abort(400, 'JSON incomplete')
    except JSONDecodeError:
        abort(400, 'JSON received invalid')


def update_local_accounts(user):
    """
    Internal method used to create accounts on all user-specified PoPs on behalf of a user
    :param global_id: new user's id
    :param global_password: new user's password
    """

    # Add authenticate X-Username and X-Password here when they will be supported local server-side

    payload = {'global_id': user.global_id, 'global_password': user.global_pwd}
    headers = {'Content-Type': 'application/json'}

    # sending account creation requests to all selected pops
    for pop_url in user.pops:
        pop = PoP.objects(address=pop_url).first()
        r = post('http://' + pop.address + '/account', data=json.dumps(payload), headers=headers)
        if r.status_code != 201 and r.status_code != 409:
            raise Exception("Error while creating account on " + pop.address + ". Error message is " + r.text)

    # deleting account from previous pops
    user_pops = user.pops
    for pop in PoP.objects(address__nin=user_pops):
        # delete account
        r = delete('http://' + pop.address + '/account', data=json.dumps(payload), headers=headers)
        if r.status_code != 204:
            raise Exception("Error while deleting account on " + pop.address + ". Error message is " + r.text)

    # update the DNS records
    dns_client = DNSClient(user)
    updated = dns_client.updateUserRecords()
    return updated


@app.route('/account', method='DELETE')
def delete_account():
    """
    Deletes an account and all its objects on all PoPs
    POST data must include a JSON body such as :
    {"global_id":"user1111","global_password":"password"}
    """
    try:
        jreq = request.json
        global_id = jreq.get('global_id')
        password = jreq.get('global_password')

        if global_id is not None and password is not None:
            user = User.objects(global_id=global_id, global_pwd=password).first()
            if user is not None:
                delete_local_accounts(user)
                user.delete()

                return HTTPResponse(status=204)
            else:
                abort(409, 'User does not exist')
        else:
            abort(400, 'JSON incomplete')
    except JSONDecodeError:
        abort(400, 'JSON received invalid')


def delete_local_accounts(user):
    """
    Internal method used to delete accounts on all local PoPs on behalf of a user
    :param global_id: user's id
    :param global_password: user's password
    """
    payload = {'global_id': user.global_id, 'global_password': user.global_pwd}
    for pop_url in user.pops:
        pop = PoP.objects(address=pop_url)
        r = delete('http://' + pop.address, json.dumps(payload))


@app.route('/pop', method='POST')
def post_pop():
    """
    Register a new PoP on the central server
    POST data must include a JSON body such as :
    {"url":"http://example.mcn.org:8181", "admin_uname":"admin","admin_password":"password","location":"FR"}
    """
    try:
        jreq = request.json
        pop_url = jreq.get('url')
        pop_admin_uname = jreq.get('admin_uname')
        pop_admin_password = jreq.get('admin_password')
        pop_location = jreq.get('location')
        #Pop exists?
        pop = PoP.objects(address=pop_url).first()
        if pop is None:
            #Create
            pop = PoP(address=pop_url,
                      admin_username=pop_admin_uname,
                      admin_password=pop_admin_password,
                      location=pop_location)
            pop.save()
            return HTTPResponse(status=201)
        else:
            #PoP exists, no update at the moment
            #TODO: Add update capabilities
            abort(409, 'PoP already registered')
    except JSONDecodeError:
        abort(400, 'JSON received invalid')
    except TypeError:
        traceback.print_exc(sys.stdout)
        abort(500)


@app.route('/pop', method='GET')
# @app.get('/pop')
def get_pops():
    """
    Retrieves list of currently registered PoPs
    """
    pops = [{'address': pop.address, 'location': pop.location} for pop in PoP.objects]
    response.content_type = 'application/json'
    return json.dumps(pops)


@app.route('/origin/:global_id', method='GET')
def get_origin(global_id):
    # TODO: Add some authentication from the PoP, this data shouldn't be public
    """
    Retrieves the origin PoP's url for specific user
    Used by local server when an object is missing locally

    :param global_id: the user's id
    :return: the url of the origin PoP as a String
    """
    user = User.objects(global_id=global_id).first()
    if user is not None:
        origin = {'origin_address': user.origin}  # JSON so it can be extended later if needed
        return json.dumps(origin)
    else:
        abort(404, "No user found using the provided id")


debug(True)
if __name__ == '__main__':
    run(app=app, host='0.0.0.0', port=8182, reloader=True, debug=True)
