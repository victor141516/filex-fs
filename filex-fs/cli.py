from explorer.manager import Explorer

ex = Explorer('cli')


def ls():
    contents = ex.get_directory_contents()
    for item in contents:
        print(f'{item["i_type"]} {item["name"]}')


def pwd():
    print(ex.get_directory_parents_string())


def cd(directory_name):
    item = ex.get_item_by_name(directory_name)
    if item['i_type'] != 'd':
        print(f'{directory_name} is not a directory')
    else:
        ex.go_to_directory(item['id'])


def mkdir(name):
    ex.add_directory(name)


def touch(name):
    ex.add_file(uuid(), name, 1)
