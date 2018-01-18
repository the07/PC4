import json

from record import Record
from user import User

class Peoplechain(object):

    users = []
    unconfirmed_records = []

    def __init__(self, remote_chain_data=None):

        if remote_chain_data is None:
            self.users = []
            self.unconfirmed_records = []
        else:
            for user in remote_chain_data['users']:
                new_user = User.from_json(json.loads(user))
                self.add_user(new_user)
            for unconfirmed_record in remote_chain_data['unconfirmed_records']:
                record = Record.from_json(json.loads(unconfirmed_record))
                self.add_unconfirmed_record(record)

    def add_user(self, user):
        if not user in self.users:
            self.users.append(user)
            return

    def add_unconfirmed_record(self, record):
        if not record in self.unconfirmed_records:
            self.unconfirmed_records.append(record)
            return

    def record_signed(self, record):
        for unconfirmed_record in self.unconfirmed_records:
            # Record now has signature, so we cannot simply use 'record in'
            if unconfirmed_record.endorsee == record.endorsee and unconfirmed_record.endorser == record.endorser and unconfirmed_record.detail == record.detail:
                self.unconfirmed_records.remove(unconfirmed_record)
                self.add_record_to_user(record)
                return

    def add_record_to_user(self, record):
        for user in self.users:
            if user.address == record.endorsee:
                user.add_record(record)
                return

    def get_user(self, address):
        for user in self.users:
            if user.address == address:
                return user
        return None

    def get_balance(self, address):
        balance = 100
        for user in self.users:
            for record in user.records:
                if record.endorsee == address:
                    if record.endorser == self.get_genesis_user().address:
                        balance += 1000
                    else:
                        balance += 50
                if record.endorser == address:
                    balance -= 50
        return balance

    def get_genesis_user(self):
        for user in self.users:
            if user.user_type == 3:
                return user

    def get_unconfirmed_records(self, address):
        ucrecords = []
        for record in self.unconfirmed_records:
            if record.endorser == address:
                ucrecords.append(record.to_json())
            if record.endorsee == address:
                ucrecords.append(record.to_json())
        return ucrecords

if __name__ == '__main__':
    pass
