import json
import logging
import redis
import uuid as uuid_pack

cache = redis.StrictRedis(host='redis', port=6379, db=0, decode_responses=True)
BASE_DIRECTORY_LIST = 'd_list-{}'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger('Explorer')


def get(key):
    value = cache.get(key)
    if value is None:
        LOGGER.warning(f'key: {key} doesn\'t exists')
        return None
    raw = json.loads(value)
    if type(raw) is dict:
        return FsItem(raw)
    else:
        return raw


def add(key, value):
    if type(value) is FsItem:
        return cache.set(key, value.to_json())
    else:
        return cache.set(key, json.dumps(value))


def delete(key):
    return cache.delete(key)


def uuid():
    return str(uuid_pack.uuid1())[:8]


class ItemNotFoundException(Exception):
    def __init__(self, **kwargs):
        super(ItemNotFoundException, self).__init__()
        self.data = kwargs


class FsItem(object):
    def __init__(self, data):
        super(FsItem, self).__init__()
        self.id = data.get('id')
        self.name = data.get('name')
        self.directory_id = data.get('directory_id')
        self.size = data.get('size')
        self.i_type = data.get('i_type')  # d (directory), f (file), l (link)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'directory_id': self.directory_id,
            'size': self.size,
            'i_type': self.i_type
        }

    def to_json(self):
        return json.dumps(self.to_dict())

    def __repr__(self):
        return f"<FsItem {{'id'={self.id}, 'name'={self.name}, 'directory_id'={self.directory_id}, 'size'={self.size}, 'i_type'={self.i_type}}}>"


class Explorer(object):
    def __init__(self, telegram_user_id):
        super(Explorer, self).__init__()
        self.DIRECTORY_LIST = f'{telegram_user_id}#{BASE_DIRECTORY_LIST}'
        self.ITEM_ID = f'{telegram_user_id}#' + '{}'
        self.telegram_user_id = telegram_user_id
        if get(self.ITEM_ID.format('/')) is None:
            add(self.ITEM_ID.format('/'), FsItem({
                'id': '/',
                'name': '',
                'directory_id': None,
                'size': None,
                'i_type': 'd'
            }))
        if get(self.DIRECTORY_LIST.format('/')) is None:
            add(self.DIRECTORY_LIST.format('/'), [])
        self.current_path = ['/']

    def summary(self):
        return f"""
        Explorer for #{self.telegram_user_id}
        Current directory: {self.get_current_directory_id()} - {get(self.ITEM_ID.format(self.get_current_directory_id())).name}
        Current path: {self.get_directory_parents_string()}
        Current directory contents: {self.get_directory_contents()}
        """

    def get_current_directory_id(self):
        return self.current_path[-1]

    def get_directory_contents(self, directory_id=None):
        if directory_id is None:
            directory_id = self.get_current_directory_id()
        element_ids = get(self.DIRECTORY_LIST.format(directory_id))
        elements = []
        for id in element_ids:
            element = get(self.ITEM_ID.format(id))
            elements.append(get(self.ITEM_ID.format(id)))
        add(self.DIRECTORY_LIST.format(directory_id), [e.id for e in elements])
        return elements

    def get_item_by_name(self, name, directory_id=None):
        if directory_id is None:
            directory_id = self.get_current_directory_id()
        contents = self.get_directory_contents(directory_id)
        for item in contents:
            if item.name == name:
                return item
        raise ItemNotFoundException(name=name)

    def get_directory_parents(self, directory_id=None):
        if directory_id is None:
            directory_id = self.get_current_directory_id()
        family = [directory_id]
        while True:
            directory = get(self.ITEM_ID.format(directory_id))
            if directory.directory_id is None:
                break
            family = [directory.directory_id] + family
            directory_id = directory.directory_id
        return family

    def get_directory_parents_string(self):
        path = ''
        for directory_id in self.current_path:
            path = f"{path}/{get(self.ITEM_ID.format(directory_id)).name}"
        return path

    def go_to_directory(self, directory_id):
        self.current_path = self.get_directory_parents(directory_id)

    def add_directory(self, name, parent_directory_id=None):
        if parent_directory_id is None:
            parent_directory_id = self.get_current_directory_id()
        directory_id = uuid()

        contents = self.get_directory_contents(parent_directory_id)
        for element in contents:
            if element.name == name:
                LOGGER.warning(f'{name} already exists in this directory')
                return

        dir_fs_item = FsItem({
            'id': directory_id,
            'name': name,
            'directory_id': parent_directory_id,
            'size': None,
            'i_type': 'd'
        })
        add(self.ITEM_ID.format(directory_id), dir_fs_item)
        add(self.DIRECTORY_LIST.format(directory_id), [])
        parent_list = get(self.DIRECTORY_LIST.format(parent_directory_id))
        add(self.DIRECTORY_LIST.format(parent_directory_id), parent_list + [directory_id])
        if parent_directory_id == self.get_current_directory_id():  # So that the directory appears
            self.go_to_directory(parent_directory_id)
        return dir_fs_item

    def add_file(self, file_id, name, size, directory_id=None):
        if directory_id is None:
            directory_id = self.get_current_directory_id()

        contents = self.get_directory_contents(directory_id)
        for element in contents:
            if element.name == name:
                LOGGER.warning(f'{name} already exists in this directory')
                return

        file_fs_item = FsItem({
            'id': file_id,
            'name': name,
            'directory_id': directory_id,
            'size': size,
            'i_type': 'f'
        })
        add(self.ITEM_ID.format(file_id), file_fs_item)
        directory_list = get(self.DIRECTORY_LIST.format(directory_id))
        add(self.DIRECTORY_LIST.format(directory_id), directory_list + [file_id])
        if directory_id == self.get_current_directory_id():  # So that the file appears
            self.go_to_directory(directory_id)
        return file_fs_item

    def delete_item(self, item_id, is_recursed=False):
        item = get(self.ITEM_ID.format(item_id))
        LOGGER.debug(f' Delete {item_id} = {item}')

        if item.i_type == 'd':
            LOGGER.debug(f' {item.name} is directory')
            item_ids = get(self.DIRECTORY_LIST.format(item_id))
            LOGGER.debug(f' {item.name} contents {item_ids}')
            for each in item_ids:
                element = get(self.ITEM_ID.format(each))
                LOGGER.debug(f'     {each} = {element}')
                if element.i_type == 'd':
                    LOGGER.debug(f'     {each} is directory, recursion...')
                    self.delete_item(each, True)
                    LOGGER.debug(f'     {each} recursion end !!!')
                    delete(self.DIRECTORY_LIST.format(each))
                    LOGGER.debug(f'     {each} dir delete list')
                delete(self.ITEM_ID.format(each))
                LOGGER.debug(f'     {each} delete item')
            delete(self.DIRECTORY_LIST.format(item.id))

        if not is_recursed:
            LOGGER.debug(f'     No more recurion !!!')
            parent_directory_id = item.directory_id
            LOGGER.debug(f'     Parent directory_id = {parent_directory_id}')
            delete(self.ITEM_ID.format(item_id))
            LOGGER.debug(f'     Item deleted')
            parent_elements_ids = get(self.DIRECTORY_LIST.format(parent_directory_id))
            LOGGER.debug(f'     Parent content before = {parent_elements_ids}')
            parent_elements_ids.remove(item_id)
            LOGGER.debug(f'     Parent content after = {parent_elements_ids}')
            add(self.DIRECTORY_LIST.format(parent_directory_id), parent_elements_ids)
            LOGGER.debug(f'     Parent content stored')
