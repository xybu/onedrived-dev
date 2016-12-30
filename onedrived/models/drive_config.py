from collections import namedtuple


class LocalDriveConfig(namedtuple('LocalDriveConfig', ('drive_id', 'account_id', 'ignorefile_path', 'localroot_path'))):

    @property
    def data(self):
        return self._asdict()
