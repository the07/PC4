import coincurve
import random
import requests

class Key(object):

    __private_key__ = None
    __public_key__ = None

    def __init__(self, private_key=None):
        if private_key is not None:
            self.__private_key__ = coincurve.PrivateKey.from_hex(private_key)
        else:
            print ("Creating new key pair")
            self.__private_key__ = coincurve.PrivateKey()
        self.__public_key__ = self.__private_key__.public_key

    def get_public_key(self):
        address = ":".join(map(str, self.__public_key__.point()))
        return address

    def get_private_key(self):
        return self.__private_key__.to_hex()
