class OneDriveAccountProfile:

    def __init__(self, data):
        self.data = data

    @property
    def account_id(self):
        return self.data['id']

    @property
    def account_name(self):
        return self.data['name']

    @property
    def account_firstname(self):
        return self.data['first_name']

    @property
    def account_lastname(self):
        return self.data['last_name']

    @property
    def account_email(self):
        return self.data['emails']['account']
