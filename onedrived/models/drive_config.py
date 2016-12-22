class LocalDriveConfig:

    def __init__(self, drive_id, account_id, ignorefile_path, localroot_path):
        self.data = {
            'drive_id': drive_id,
            'account_id': account_id,
            'ignorefile_path': ignorefile_path,
            'localroot_path': localroot_path
        }

    @property
    def drive_id(self):
        return self.data['drive_id']

    @property
    def account_id(self):
        return self.data['account_id']

    @property
    def ignorefile_path(self):
        return self.data['ignorefile_path']

    @property
    def localroot_path(self):
        return self.data['localroot_path']
