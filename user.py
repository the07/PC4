import json

class User(object):

    def __init__(self, address, name, email, user_type, records=None):

        self._address = address
        self._name = name
        self._email = email
        self._user_type = user_type
        if records is None:
            self._records = []
        else:
            self._records = records

    @property
    def address(self):
        return self._address

    @property
    def name(self):
        return self._name

    @property
    def email(self):
        return self._email

    @property
    def user_type(self):
        return self._user_type

    @property
    def records(self):
        return self._records

    @classmethod
    def from_json(cls, user_json):
        user = cls(user_json['address'], user_json['name'], user_json['email'], user_json['user_type'], user_json.get('records', None))
        return user

    def add_record(self, record):
        self._records.append(record)
        return

    def to_json(self):
        return json.dumps(self, default=lambda o: {key.lstrip('_'):value for key, value in o.__dict__.items()}, sort_keys=True)

    def __repr__(self):
        return "<User: Address - {}>".format(self._address)

    def __str__(self):
        return str(self.__dict__)

    def __eq__(self, other):
        return self._address == other._address

    def __ne__(self, other):
        return not self == other

if __name__ == '__main__':
    pass
