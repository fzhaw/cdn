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
import mongoengine


connect('cdn_central')

class PoP(Document):
    address = StringField(required=True)
    admin_username = StringField(default="admin")
    admin_password = StringField(default="admin")
    location = StringField(default="unknown")


class User(Document):
    #global cdn user id
    global_id = StringField(required=True)
    global_pwd = StringField(required=True)
    #Origin Point of Presence
    origin_pop = ReferenceField('PoP', reverse_delete_rule=DENY)

    # Property fields to retrieve PoP entry faster
    @property
    def origin(self):
        return self.origin_pop.address

    @property
    def origin_admin(self):
        return self.origin_pop.admin_username

    @property
    def origin_password(self):
        return self.origin_pop.admin_password



