import hashlib
import zlib


def hash_match(local_abspath, remote_item):
    """
    :param str local_abspath:
    :param onedrivesdk.model.item.Item remote_item:
    :return True | False:
    """
    file_facet = remote_item.file
    if file_facet is not None:
        hash_facet = file_facet.hashes
        if hash_facet is not None:
            return (hash_facet.crc32_hash and hash_facet.crc32_hash == crc32_value(local_abspath) or
                    hash_facet.sha1_hash and hash_facet.sha1_hash == hash_value(local_abspath))
    return False


def hash_value(file_path, block_size=1048576, algorithm=hashlib.sha1()):
    """
    Calculate the MD5 or SHA hash value of the data of the specified file.
    :param str file_path:
    :param int block_size:
    :param algorithm: A hash function defined in hashlib.
    :return str:
    """
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(block_size)
            if not data:
                break
            algorithm.update(data)
    return algorithm.hexdigest().upper()


def crc32_value(file_path, block_size=1048576):
    """
    Calculate the CRC32 value of the data of the specified file.
    :param str file_path:
    :param int block_size:
    :return str:
    """
    crc = 0
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(block_size)
            if not data:
                break
            crc = zlib.crc32(data, crc)
    return str(crc).upper()
