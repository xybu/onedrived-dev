"""
od_account.py
Core component for user account management.
:copyright: (c) Xiangyu Bu <xybu92@live.com>
:license: MIT
"""


class OneDriveAccountProfile:

    def __init__(self, user_id, user_name):
        self.user_id = user_id
        self.user_name = user_name

    def __repr__(self):
        return '%s (%s)' % (self.user_name, self.user_id)
