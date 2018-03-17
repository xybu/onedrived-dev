
class AccountTypes:
    PERSONAL = 0
    BUSINESS = 1


class OneDriveAccount:

    def __init__(self, data):
        self.data = data

    @property
    def account_type(self):
        return self.data['account_type']

    def getAccount(self):
        if self.account_type == AccountTypes.BUSINESS:
            return OneDriveAccountBusiness(self.data)
        else:
            return OneDriveAccountPersonal(self.data)


class OneDriveAccountPersonal:

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

    @property
    def account_type(self):
        return self.data['account_type']


class OneDriveAccountBusiness:

    def __init__(self, data):
        self.data = data

    @property
    def account_id(self):
        # TODO: check if can be 36 digits instead of 17(personal)
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
        return self.data['emails']

    @property
    def account_root_folder(self):
        return self.data['webUrl']

    @property
    def account_type(self):
        return self.data['account_type']

    @property
    def tenant(self):
        site = self.account_root_folder
        return site[8:site.find('-my.sharepoint.com/')]

    @property
    def endpoint(self):
        return 'https://' + self.tenant + '-my.sharepoint.com/'
