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
from requests import post
import json
from bottle import route, run, request, abort, response, HTTPResponse
from central_db import *
from uuid import uuid4
from simplejson.scanner import JSONDecodeError
import traceback
import sys


@route('/account', method='POST')
def post_account():
    """
    Creates an account on each PoP, selects one PoP to be the origin
    Requires body in the request: {"global_password":"yyyy"}
    global_id is generated
    Other informations may be needed to infer closest PoP
    TODO: Check with DNS

    :return: HTTP 201 if created, with json body {"global_id":"hduakdhwakdiwad", "origin":"http://example.mcn.org:8181/cdn"}
    """
    try:
        jreq = request.json
        global_id = str(uuid4())
        password = jreq.get('global_password')

        if password is not None:
            # User exists?
            user = User.objects(global_id=global_id).first()
            if user is None:
                # TODO: Retrieve closest PoP
                # for now, takes the first from the PoP list
                pop = PoP.objects().first()

                # Save user to Mongo
                new_user = User(global_id=global_id, global_pwd=password, origin_pop=pop)
                new_user.save()

                # Create local accounts
                create_accounts(global_id, password)

                body = {'global_id': global_id, 'origin': pop.address}
                response.set_header('Content-Type', 'application/json')
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


def create_accounts(global_id, global_password):
    """
    Internal method used to create accounts on all local PoPs on behalf of a user
    :param global_id: new user's id
    :param global_password: new user's password
    """

    # Add authenticate X-Username and X-Password here when they will be supported local server-side

    payload = {'global_id': global_id, 'global_password': global_password}
    headers = {'Content-Type': 'application/json'}

    # Only few PoPs at the moment, so sending the post requests from the main thread here
    # TODO: Thread the account creation requests is probably better

    for pop in PoP.objects:
        r = post(pop.address + '/account', data=json.dumps(payload), headers=headers)
        if r.status_code != 201:
            raise Exception("Error while creating account on " + pop.address + ". Error message is " + r.text)

    #TODO: Answer something and add account creation to general log


@route('/account', method='DELETE')
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
                delete_local_accounts(global_id, password)
                user.delete()

                return HTTPResponse(status=204)
            else:
                abort(409, 'User does not exist')
        else:
            abort(400, 'JSON incomplete')
    except JSONDecodeError:
        abort(400, 'JSON received invalid')


def delete_local_accounts(global_id, global_password):
    """
    Internal method used to delete accounts on all local PoPs on behalf of a user
    :param global_id: user's id
    :param global_password: user's password
    """
    payload = {'global_id': global_id, 'global_password': global_password}
    for pop in PoP.objects:
        r = post(pop.address, json.dumps(payload))


@route('/pop', method='POST')
def post_pop():
    """
    Register a new PoP on the central server
    POST data must include a JSON body such as :
    {"url":"http://example.mcn.org:8181", "admin_uname":"admin","admin_password":"password"}
    """
    try:
        jreq = request.json
        pop_url = jreq.get('url')
        pop_admin_uname = jreq.get('admin_uname')
        pop_admin_password = jreq.get('admin_password')
        #Pop exists?
        pop = PoP.objects(address=pop_url).first()
        if pop is None:
            #Create
            pop = PoP(address=pop_url, admin_username=pop_admin_uname, admin_password=pop_admin_password)
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


@route('/origin/:global_id', method='GET')
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


run(host='0.0.0.0', port=8182, debug=True)