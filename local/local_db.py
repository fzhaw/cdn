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
from mongoengine import *
#
connect('cdn_local')


class User(Document):
    #global cdn user id, also tenant_name in a swift/keystone
    global_id = StringField(required=True)
    global_pwd = StringField(required=True)
    #real tenant id corresponding to the id of the tenant which name is global_id
    tenant_id = StringField()
    #origin = ReferenceField(Origin, reverse_delete_rule=NULLIFY)


class StorageObject(Document):
    tenant_id = StringField()
    tenant_name = StringField()
    container_name = StringField()
    object_name = StringField()
    user = ReferenceField(User, reverse_delete_rule=CASCADE)

class Origin(Document):
    url = StringField()
    user = ReferenceField(User, reverse_delete_rule=CASCADE)
    created = DateTimeField(default=datetime.now)
    meta = {
        'indexes': [
            {'fields': ['created'], 'expireAfterSeconds': 3600}
        ]
    }
