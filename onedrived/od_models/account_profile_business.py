
class OneDriveAccountBusinessProfile:

    def __init__(self, data):
        self.data = data

    @property
    def account_id(self):
        return self.data['id']

    @property
    def account_root_folder(self):
        return self.data['webUrl']

    @property
    def account_type(self):
        return self.data['account_type']
