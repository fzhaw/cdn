__author__ = 'florian'
from central.central_db import User, PoP
from nose.tools import assert_equals


class testCentralDB(object):
    @classmethod
    def setUpClass(cls):

        global o1_id

        # Create two objects for test
        o1 = User()
        o1.global_id = 'user1'
        o1.global_pwd = 'pass1'
        o1.pops=['1.ex.ch','2.ex.ch']
        o1.save()

        o1_id = o1.id
       # This method run on every test

    def setUp(self):
        global o1_id
        self.o1_id = o1_id

    def test_schema(self):
        find = User.objects(global_id='user1').first()
        assert_equals(find.id, self.o1_id)