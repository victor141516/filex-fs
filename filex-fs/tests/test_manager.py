import json
from mockito import mock, when, patch
import pytest
import redis
import uuid as uuid_pack


class MockRedis(object):
    def __init__(self, *args, **kwargs):
        super(MockRedis, self).__init__()
        self.elements = {}
        self.current_uuid_i = 0
        self.uuids = ['uuid0000', 'uuid0001', 'uuid0002', 'uuid0003', 'uuid0004', 'uuid0005', 'uuid0006', 'uuid0007', 'uuid0008', 'uuid0009']

    def get(self, key):
        return self.elements.get(key)

    def set(self, key, value):
        self.elements[key] = value
        return True

    def delete(self, key):
        if key in self.elements:
            del self.elements[key]
            return 1
        else:
            return 0

    def _clear(self):
        self.elements = {}
        self.current_uuid_i = 0

    def _keys(self):
        return list(self.elements.keys())

    def _next_uuid(self):
        r_uuid = self.uuids[self.current_uuid_i]
        self.current_uuid_i += 1
        return r_uuid


redis_mock = MockRedis()
when(redis).StrictRedis(...).thenReturn(redis_mock)
patch(uuid_pack.uuid1, redis_mock._next_uuid)
from explorer.manager import (Explorer, cache)


@pytest.fixture
def explorer():
    redis_mock._clear()
    return Explorer('000')


def test__init(explorer):
    assert redis_mock._keys() == ['000#/', '000#d_list-/']
    assert json.loads(redis_mock.elements['000#/']) == {
        'id': '/', 'name': '', 'directory_id': None, 'size': None, 'i_type': 'd'}
    assert json.loads(redis_mock.elements['000#d_list-/']) == []


def test__add_directory(explorer):
    explorer.add_directory('dir1')
    explorer.add_directory('dir1')
    explorer.add_directory('dir2')
    explorer.add_directory('dir2', '/')
    explorer.add_directory('dir3', 'uuid0000')
    assert redis_mock._keys() == ['000#/', '000#d_list-/', '000#uuid0000',
                            '000#d_list-uuid0000', '000#uuid0002', '000#d_list-uuid0002', '000#uuid0004', '000#d_list-uuid0004']
    assert json.loads(redis_mock.elements['000#/']) == {
        'id': '/', 'name': '', 'directory_id': None, 'size': None, 'i_type': 'd'}
    assert json.loads(
        redis_mock.elements['000#d_list-/']) == ['uuid0000', 'uuid0002']
    assert json.loads(redis_mock.elements['000#uuid0000']) == {'id': 'uuid0000', 'name': 'dir1', 'directory_id': '/', 'size': None, 'i_type': 'd'}
    assert json.loads(redis_mock.elements['000#d_list-uuid0000']) == ['uuid0004']
    assert json.loads(redis_mock.elements['000#uuid0002']) == {
        'id': 'uuid0002', 'name': 'dir2', 'directory_id': '/', 'size': None, 'i_type': 'd'}
    assert json.loads(redis_mock.elements['000#d_list-uuid0002']) == []
    assert json.loads(redis_mock.elements['000#uuid0004']) == {
        'id': 'uuid0004', 'name': 'dir3', 'directory_id': 'uuid0000', 'size': None, 'i_type': 'd'}
    assert json.loads(redis_mock.elements['000#d_list-uuid0004']) == []
