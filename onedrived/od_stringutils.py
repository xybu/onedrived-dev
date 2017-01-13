import os


def get_filename_with_incremented_count(filename):
    """
    Get a new filename with a count value appended. The scheme follows the policy for name.conflictBehavior=rename.
    See https://dev.onedrive.com/items/create.htm.
    :param str filename:
    :return str:
    """
    name, ext = os.path.splitext(filename)
    if ' ' in name:
        orig_name, count = name.rsplit(' ', maxsplit=1)
        if count.isdigit() and count[0] != '0':
            count = int(count) + 1
            return orig_name + ' ' + str(count) + ext
    return name + ' 1' + ext
