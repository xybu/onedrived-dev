import hashlib


def hash_match(local_abspath, remote_item):
    """
    :param str local_abspath:
    :param onedrivesdk.model.item.Item remote_item:
    :return True | False:
    """
    file_facet = remote_item.file
    if file_facet:
        hash_facet = file_facet.hashes
        if hash_facet:
            return hash_facet.sha1_hash and hash_facet.sha1_hash == sha1_value(local_abspath)
    return False


def sha1_value(file_path, block_size=2<<22):
    """
    Calculate the MD5 or SHA hash value of the data of the specified file.
    :param str file_path:
    :param int block_size:
    :return str:
    """
    alg = hashlib.sha1()
    with open(file_path, 'rb') as f:
        data = f.read(block_size)
        while len(data):
            alg.update(data)
            data = f.read(block_size)
    return alg.hexdigest().upper()
