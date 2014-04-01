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

#Version 0.1

import logging
import traceback

from keystoneclient import v2_0 as keystone
from simplejson.scanner import JSONDecodeError
import swiftclient
from swiftclient.exceptions import ClientException

from local.local_db import StorageObject, User as StorageUser
import sys
from requests import get
from threading import Thread
from socket import gethostname
from bottle import route, run, redirect, request, abort, HTTPResponse
import ConfigParser

config = ConfigParser.SafeConfigParser()
config.read('local/cdn_local.conf')

#log config
filename = config.get('log', 'filename')
logging.basicConfig(filename=filename, level=logging.DEBUG)
# logging.basicConfig(filename='cdn.log', level=logging.DEBUG)

# Local server details
local_port = config.get('server', 'port')
# local_port = 8181
local_address = 'http://' + gethostname() + ":" + str(local_port)

# Keystone access details
auth_url = config.get('keystone', 'auth_url')
auth_version = config.get('keystone', 'auth_version')
# auth_url = 'http://192.168.56.10:5000/v2.0'
# auth_version = '2'

#Admin connection details
auth_admin = config.get('keystone', 'auth_admin')
auth_adminpass = config.get('keystone', 'auth_adminpassword')
auth_admintenant = config.get('keystone', 'auth_admintenant')
# auth_admin = 'admin'
# auth_adminpass = 'admin'
# auth_admintenant = 'admin'

# Swift root
swift_root = config.get('swift', 'root')
# swift_root = 'http://192.168.56.10:8080/v1/AUTH_'

# Predefined global CDN directory address, should come from config file later
cdn_central_address = config.get('centralCDN', 'url')
# cdn_central_address = 'http://localhost:8182'

# Path where objects are locally stored before being stored to the object service when caching
store_path = config.get('temporaryStorage', 'path')
# store_path = '/tmp'

# Admin Connection object to Swift using swiftclient
admin_swift_conn = swiftclient.Connection(auth_url, auth_admin, auth_adminpass, auth_version=auth_version,
                                          tenant_name=auth_admintenant, insecure=True)

# Admin Connection object to Keystone using keystoneclient
admin_ks_conn = keystone.client.Client(username=auth_admin, password=auth_adminpass,
                                       tenant_name=auth_admintenant, auth_url=auth_url)


#keystoneclient connection may hang if keystone cannot be joined
#TODO:workaround to exit in this case after specific timeout?

@route('/account', method='POST')
def post_account():
    """
    Creates an account on underlying keystone
    Requires body in the request: {"global_id":"xxxx", "global_password":"yyyy"}
    :return: HTTP 201 if created

    """
    try:
        # TODO: Add X-Username and X-Password for admin authentication
        jreq = request.json
        global_id = jreq.get('global_id')
        password = jreq.get('global_password')
        if global_id is not None and password is not None:
            # User exists?
            user = StorageUser.objects(global_id=global_id).first()
            if user is None:
                # Create tenant
                tenant_id = admin_ks_conn.tenants.create(tenant_name=global_id).id
                # Create user
                user_id = admin_ks_conn.users.create(name=global_id, password=password, tenant_id=tenant_id)
                # Set admin role in tenant
                admin_role_id = admin_ks_conn.roles.find(name='admin').id
                admin_ks_conn.roles.add_user_role(user_id, admin_role_id, tenant_id)

                # Save to Mongo
                new_user = StorageUser(global_id=global_id, global_pwd=password, tenant_id=tenant_id)
                new_user.save()

                return HTTPResponse(status=201)
            else:
                abort(409, 'User already exists')
        else:
            abort(400, 'JSON incomplete')
    except JSONDecodeError:
        abort(500, 'JSON received invalid')
    except ClientException, ex:
        abort(500, ex.message)



@route('/account', method='DELETE')
def delete_account():
    """
    Deletes an account on underlying keystone
    :return: HTTP 204 if deleted

    """
    try:
        # TODO: Add X-Username and X-Password for admin authentication
        jreq = request.json
        global_id = jreq.get('global_id')
        password = jreq.get('global_password')
        if global_id is not None and password is not None:
            # User exists?
            user = StorageUser.objects(global_id=global_id).first()
            if user is not None:
                # Delete swift content manually (otherwise unrecoverable)
                conn = swiftclient.Connection(auth_url, global_id, password, auth_version=auth_version,
                                              tenant_name=global_id, insecure=True)
                for container in conn.get_account()[1]:
                    container_name = container['name']
                    for obj in conn.get_container(container_name)[1]:
                        object_name = obj['name']
                        conn.delete_object(container_name, object_name)
                    conn.delete_container(container_name)

                conn.close()

                # Delete KS user
                admin_ks_conn.users.delete(global_id)

                # Delete tenant
                admin_ks_conn.tenants.delete(global_id)

                # Delete from Mongo
                user.delete()

                return HTTPResponse(status=200)
            else:
                abort(409, 'User does not exist')
        else:
            abort(400, 'JSON incomplete')
    except JSONDecodeError:
        abort(400, 'JSON received invalid')


@route('/cdn/:global_id/:container_name', method='DELETE')
def delete_container(global_id, container_name):
    """
    Deletes a container for specific tenant
    :param global_id: user id
    :param container_name: container name
    :return: HTTP 204 if deleted
    """
    password = request.headers.get('X-Password')
    if StorageUser.objects(global_id=global_id, global_pwd=password).first() is not None:
        try:
            conn = swiftclient.Connection(auth_url, global_id, password, auth_version=auth_version,
                                          tenant_name=global_id,
                                          insecure=True)
            for obj in conn.get_container(container_name)[1]:
                # delete objects one by one before deleting the container
                conn.delete_object(container_name, obj['name'])
            # now deletes container
            conn.delete_container(container_name)
            conn.close()
            return HTTPResponse(status=204)
        except:
            traceback.print_exc(sys.stdout)
            abort(500, 'Server Error, Please check logs')
    else:
        abort(401, 'Unknown user')


@route('/cdn/:global_id/:container_name', method='POST')
def create_container(global_id, container_name):
    """
    Creates a container for specific tenant
    :param global_id: user id
    :param container_name: container name
    :return: HTTP 201 if created
    """
    password = request.headers.get('X-Password')
    if StorageUser.objects(global_id=global_id, global_pwd=password).first() is not None:
        try:
            conn = swiftclient.Connection(auth_url, global_id, password, auth_version=auth_version,
                                          tenant_name=global_id,
                                          insecure=True)
            conn.put_container(container_name, {"X-Container-Read": ".r:*"})
            conn.close()
            return HTTPResponse(status=201)
        except:
            traceback.print_exc(sys.stdout)
            abort(500, 'Server Error, Please check logs')
    else:
        abort(401, 'Unknown user')


@route('/cdn/:global_id/:container_name/:object_name', method='GET')
def get_object(global_id, container_name, object_name):
    """
    Redirects to an object already stored in Swift
    If object missing, raise 404
    :param global_id: global user id
    :param container_name: container name
    :param object_name: file name
    :return: redirection (HTTP 303) to the actual object
    """

    #if file exists
    obj = StorageObject.objects(tenant_name=global_id, container_name=container_name,
                                object_name=object_name).first()
    if obj is not None:
        return redirect(swift_root + "%s/%s/%s" % (obj.tenant_id, container_name, object_name), 303)
    else:
        # let's try to retrieve it... if it exists
        # Before checking anything, verify that user global_id exists!
        usr = StorageUser.objects(global_id=global_id).first()
        if usr is not None:
            # find origin for user from central
            # TODO: this value should definitely be cached or even set at account creation time
            r = get(cdn_central_address + '/origin/' + global_id)
            jresp = r.json()
            origin_address = jresp['origin_address']

            # If current instance of cdnlocal IS the origin, then file does not exist, returns a 404
            if origin_address == local_address:
                return abort(404, 'File does not exist or is unavailable')

#TODO: Now test cache
            # Cache object, but should redirect to origin this time so user does not wait for file retrieval
            t = Thread(target=cache_object, args=(origin_address, usr, container_name, object_name))
            t.start()

            return redirect("%s/cdn/%s/%s/%s" % (origin_address, global_id, container_name, object_name), 303)
        else:
            return abort(404, 'User does not exist')


def cache_object(origin_address, user, container_name, object_name):
    """
    Threaded internal method to retrieve object from origin and add it locally.

    :param origin_address: Address of the origin PoP of this user
    :param user: User object from mongoengine corresponding to global_id user
    :param container_name: container name
    :param object_name: object name
    """

    # Download the object
    r = get("%s/cdn/%s/%s/%s" % (origin_address, user.global_id, container_name, object_name), stream=True)
    if r.status_code == 303:
        fname = store_path + "/" + user.global_id + "-" + object_name
        with open(fname, 'wb') as f:
            for chunk in r.iter_contents(1024):
                f.write(chunk)

        # Check if container exists if not create it
        conn = swiftclient.Connection(auth_url, user.global_id, user.global_pwd, auth_version=auth_version,
                                      tenant_name=user.global_id, insecure=True)

        containers = conn.get_account()[1]
        for container in containers:
            if container['name'] == container_name:
                break
        else:
            # Container does not exist
            conn.put_container(container_name, {"X-Container-Read": ".r:*"})

        # Add object
        conn.put_object(container_name, object_name, open(fname))


@route('/cdn/:global_id/:container/:object_name', method='DELETE')
def delete_object(global_id, container, object_name):
    """
    Deletes an Object

    :param global_id: user id
    :param container: container name
    :return: HTTP 201 if created
    """
    password = request.headers.get('X-Password')
    user = StorageUser.objects(global_id=global_id, global_pwd=password).first()
    if user is not None:
        try:
            conn = swiftclient.Connection(auth_url, global_id, password, auth_version=auth_version,
                                          tenant_name=global_id, insecure=True)
            conn.delete_object(container, object_name)
            conn.close()

            # Delete entry from Mongo
            obj = StorageObject.objects(tenant_name=global_id, container_name=container,
                                        object_name=object_name).first()
            if obj is not None:
                obj.delete()

            return HTTPResponse(status=204)
        except ClientException:
            traceback.print_exc(sys.stderr)
            abort(500, "Could not delete file")
        except AttributeError:
            traceback.print_exc(sys.stderr)
            abort(400, "Request malformed")
    else:
        abort(401, 'Unknown user')


@route('/cdn/:global_id/:container/object', method='POST')
def post_object(global_id, container):
    """
    Uploads an Object, must include a file with id=file_content and a header X-Password=global_id user's password
    :param global_id: user id
    :param container: container name
    :return: HTTP 201 if created
    """
    password = request.headers.get('X-Password')
    user = StorageUser.objects(global_id=global_id, global_pwd=password).first()
    if user is not None:
        tenant_id = user.tenant_id
        fil = request.files.get('file_content')
        try:
            conn = swiftclient.Connection(auth_url, global_id, password, auth_version=auth_version,
                                          tenant_name=global_id, insecure=True)
            conn.put_object(container, fil.filename, fil.file)
            conn.close()

            # Save to Mongo
            obj = StorageObject(tenant_id=tenant_id, tenant_name=global_id, container_name=container,
                                object_name=fil.filename)
            obj.save()

            return HTTPResponse(status=201)
        except ClientException:
            traceback.print_exc(sys.stderr)
            abort(500, "Could not upload file")
        except AttributeError:
            abort(400, "Request malformed, probably object is not sent with the file_content identifier")
    else:
        abort(401, 'Unknown user')

run(host='0.0.0.0', port=local_port, debug=True)
