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
    Explorer('000')
    Explorer('000')
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


def test__summary(explorer):
    explorer.add_directory('dir1')
    explorer.add_file('file1', 'filename', 42)
    assert explorer.summary() == "\n        Explorer for #000\n        Current directory: / - \n        Current path: /\n        Current directory contents: [{'id': 'uuid0000', 'name': 'dir1', 'directory_id': '/', 'size': None, 'i_type': 'd'}, {'id': 'file1', 'name': 'filename', 'directory_id': '/', 'size': 42, 'i_type': 'f'}]\n        "


def test__get_directory_parents(explorer):
    nested_dir =explorer.add_directory('dir5',
        explorer.add_directory('dir4',
            explorer.add_directory('dir3',
                explorer.add_directory('dir2',
                    explorer.add_directory('dir1'
                    )['id']
                )['id']
            )['id']
        )['id']
    )
    explorer.go_to_directory(nested_dir['id'])
    assert explorer.get_directory_parents(nested_dir['id']) == ['/', 'uuid0000', 'uuid0001', 'uuid0002', 'uuid0003', 'uuid0004']
    assert explorer.get_directory_parents() == ['/', 'uuid0000', 'uuid0001', 'uuid0002', 'uuid0003', 'uuid0004']


def test__add_file(explorer):
    explorer.add_file(redis_mock._next_uuid(), redis_mock._next_uuid(), 1)
    explorer.go_to_directory(explorer.add_directory('dir1')['id'])
    explorer.add_file(redis_mock._next_uuid(), redis_mock._next_uuid(), 2)
    explorer.add_file(redis_mock._next_uuid(), redis_mock._next_uuid(), 3, '/')
    explorer.add_file(redis_mock._next_uuid(), 'uuid0001', 1, '/')

    assert redis_mock._keys() == ['000#/', '000#d_list-/', '000#uuid0000', '000#uuid0002', '000#d_list-uuid0002', '000#uuid0003', '000#uuid0005']
    assert json.loads(redis_mock.elements['000#/']) == {'id': '/', 'name': '', 'directory_id': None, 'size': None, 'i_type': 'd'}
    assert json.loads(redis_mock.elements['000#d_list-/']) == ['uuid0000', 'uuid0002', 'uuid0005']
    assert json.loads(redis_mock.elements['000#uuid0000']) == {'id': 'uuid0000', 'name': 'uuid0001', 'directory_id': '/', 'size': 1, 'i_type': 'f'}
    assert json.loads(redis_mock.elements['000#uuid0002']) == {'id': 'uuid0002', 'name': 'dir1', 'directory_id': '/', 'size': None, 'i_type': 'd'}
    assert json.loads(redis_mock.elements['000#d_list-uuid0002']) == ['uuid0003']
    assert json.loads(redis_mock.elements['000#uuid0003']) == {'id': 'uuid0003', 'name': 'uuid0004', 'directory_id': 'uuid0002', 'size': 2, 'i_type': 'f'}
    assert json.loads(redis_mock.elements['000#uuid0005']) == {'id': 'uuid0005', 'name': 'uuid0006', 'directory_id': '/', 'size': 3, 'i_type': 'f'}


def test__delete(explorer):
    f1 = explorer.add_file(redis_mock._next_uuid(), redis_mock._next_uuid(), 1)['id']
    d1 = explorer.add_directory('dir1')['id']
    f2 = explorer.add_file(redis_mock._next_uuid(), redis_mock._next_uuid(), 2, d1)['id']
    d2 = explorer.add_directory('dir2', d1)['id']
    f3 = explorer.add_file(redis_mock._next_uuid(), redis_mock._next_uuid(), 3, d2)['id']
    f4 = explorer.add_file(redis_mock._next_uuid(), redis_mock._next_uuid(), 4)['id']
    explorer.delete_item(f1)
    explorer.delete_item(d1)

    assert redis_mock._keys() == ['000#/', '000#d_list-/', '000#uuid0008']
    assert json.loads(redis_mock.elements['000#/']) == {'id': '/', 'name': '', 'directory_id': None, 'size': None, 'i_type': 'd'}
    assert json.loads(redis_mock.elements['000#d_list-/']) == ['uuid0008']
    assert json.loads(redis_mock.elements['000#uuid0008']) == {'id': 'uuid0008', 'name': 'uuid0009', 'directory_id': '/', 'size': 4, 'i_type': 'f'}
