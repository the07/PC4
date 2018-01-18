import requests
from klein import Klein
import json
import random

from peoplechain import Peoplechain
from record import Record
from user import User
from key import Key

import socket

class NodeMixin(object):

    full_nodes = set(['103.88.129.43']) #TODO move to a configuration file
    FULL_NODE_PORT = 30609
    NODES_URL = "http://{}:{}/nodes"
    CHAIN_URL = "http://{}:{}/chain"
    RECORD_URL = "http://{}:{}/record"
    URECORD_URL = "http://{}:{}/record/{}"
    USER_URL = "http://{}:{}/user"
    BALANCE_URL = "http://{}:{}/balance/{}"
    USER_GET_URL = "http://{}:{}/user/{}"
    GENESIS_URL = "http://{}:{}/genesis"

    def request_nodes(self, node):
        url = self.NODES_URL.format(node, self.FULL_NODE_PORT)
        try:
            response = requests.get(url)
            if response.status_code == 200:
                all_nodes = response.json()
                return all_nodes
        except requests.exceptions.RequestException as re:
            pass
        return None

    def request_nodes_from_all(self):
        full_nodes = self.full_nodes.copy()
        bad_nodes = set()

        for node in full_nodes:
            all_nodes = self.request_nodes(node)
            if all_nodes is not None:
                full_nodes = full_nodes.union(all_nodes["full_nodes"])
            else:
                bad_nodes.add(node)

        self.full_nodes = full_nodes

        for node in bad_nodes:
            self.remove_node(node)
        return

    def remove_node(self, node):
        pass

    def random_node(self):
        all_nodes = self.full_nodes.copy()
        node = random.sample(all_nodes, 1)[0]
        return node

    def broadcast_record(self, record):
        self.request_nodes_from_all()
        bad_nodes = set()
        data = {
            "record": record.to_json()
        }

        for node in self.full_nodes:
            url = self.RECORD_URL.format(node, self.FULL_NODE_PORT)
            try:
                response = requests.post(url, json=data)
            except requests.exceptions.RequestException as re:
                bad_nodes.add(node)

        for node in bad_nodes:
            self.remove_node(node)
        bad_nodes.clear()
        return
        #TODO: convert to grequests and return list of responses

    def broadcast_user(self, user):
        self.request_nodes_from_all()
        bad_nodes = set()
        data = {
            "user": user.to_json()
        }

        for node in self.full_nodes:
            url = self.USER_URL.format(node, self.FULL_NODE_PORT)
            try:
                response = requests.post(url, json=data)
            except requests.exceptions.RequestException as re:
                bad_nodes.add(node)

        for node in bad_nodes:
            self.remove_node(node)
        bad_nodes.clear()
        return

class FullNode(NodeMixin):

    NODE_TYPE = 'full'
    peoplechain = None
    app = Klein()

    def __init__(self, private_key=None): #TODO Raise mining request, approved by existing miners then can mine.

        if private_key is None:
            print ("Starting a new chain\n")
            print ("Generating Genesis User Key Pair")
            self.key = Key()
            print ("Generating Genesis User")
            print ("Network Key: {}".format(self.key.get_private_key()))
            #TODO: store the information in config file
            user = User(self.key.get_public_key(), "Network", "peoplechain@peoplechain.in", 3)
            self.peoplechain = Peoplechain()
            self.peoplechain.add_user(user)
            print ("Peoplechain Created.")
            print (self.peoplechain.users)
        else:
            print ("Generating key pair from private key")
            self.key = Key(private_key)
            self.request_nodes_from_all()
            if not self.discover_user(self.key.get_public_key()):
                raise Exception()
            remote_chain = self.download()
            self.peoplechain = Peoplechain(remote_chain)
            self.node = self.get_my_node()
            self.full_nodes.union([self.node])
            self.broadcast_node()

        print ("\n -------------- Starting Full Node Server -------------- \n")
        self.app.run('0.0.0.0', self.FULL_NODE_PORT)

    def discover_user(self, address):

        bad_nodes = set()
        for node in self.full_nodes:
            url = self.USER_URL.format(node, self.FULL_NODE_PORT) + '/{}'.format(address)
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException as re:
                bad_nodes.add(node)

        for node in bad_nodes:
            self.remove_node(node)
        bad_nodes.clear()
        return False

    def download(self):

        for node in self.full_nodes:
            url = self.CHAIN_URL.format(node, self.FULL_NODE_PORT)
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    return response.json()
            except requests.exceptions.RequestException as re:
                pass

    def get_my_node(self):
        my_node = requests.get('https://api.ipify.org').text
        return my_node

    def broadcast_node(self):
        bad_nodes = set()
        data = {
            "host": self.node
        }
        for node in self.full_nodes:
            url = self.NODES_URL.format(node, self.FULL_NODE_PORT)
            try:
                requests.post(url, json=data)
            except requests.exceptions.RequestException as re:
                bad_nodes.add(node)

        for node in bad_nodes:
            self.remove_node(node)
        bad_nodes.clear()
        return

    @app.route('/record', methods=['POST'])
    def add_record(self, request):
        record_data = json.loads(request.content.read().decode('utf-8'))
        record_json = json.loads(record_data['record'])
        record = Record.from_json(record_json)
        if record.signature is None:
            self.peoplechain.add_unconfirmed_record(record)
            return
        else:
            self.peoplechain.record_signed(record)
            #payment_record = Record(record.endorser, record.endorsee, "Payment for Signing", 2, record.hash)
            #self.peoplechain.add_record_to_user(payment_record) #TODO: verify this record.signature == this.record.endorser.somerecord.hash
            return

    @app.route('/record/<address>', methods=['GET'])
    def get_all_unconfirmed_transactions(self, request, address):
        urecords = self.peoplechain.get_unconfirmed_records(address)
        data = {
            "records": urecords
        }
        return json.dumps(data).encode('utf-8')


    @app.route('/user', methods=['POST'])
    def create_user(self, request):
        user_data = json.loads(request.content.read().decode('utf-8'))
        user_json = json.loads(user_data['user'])
        print (type(user_json))
        user = User.from_json(user_json)
        self.peoplechain.add_user(user)
        response = {
            "message": "User Profile created"
        }
        return json.dumps(response).encode('utf-8')

    @app.route('/user/<address>', methods=['GET'])
    def get_user_by_address(self, request, address):
        user = self.peoplechain.get_user(address)
        if user is not None:
            data = {
                "user": user.to_json()
            }
            return json.dumps(data).encode('utf-8')
        else:
            return

    @app.route('/nodes', methods=['GET'])
    def get_nodes(self, request):
        response = {
            "full_nodes": list(self.full_nodes)
        }
        return json.dumps(response).encode('utf-8')

    @app.route('/nodes', methods=['POST'])
    def post_node(self, request):
        body = json.loads(request.content.read().decode('utf-8'))
        host = body['host']
        self.full_nodes.add(host)
        response = {
            "message": "Node Registered"
        }
        return json.dumps(response).encode('utf-8')

    @app.route('/chain', methods=['GET'])
    def get_chain(self, request):
        data = {
            "users": [user.to_json() for user in self.peoplechain.users],
            "unconfirmed_records": [ur.to_json() for ur in self.peoplechain.unconfirmed_records]
        }
        return json.dumps(data).encode('utf-8')

    @app.route('/balance/<address>', methods=['GET'])
    def get_balance(self, request, address):
        return str(self.peoplechain.get_balance(address))

    @app.route('/genesis', methods=['GET'])
    def get_genesis_user_address(self, request):
        return self.peoplechain.get_genesis_user_address()

if __name__ == '__main__':
    private_key = str(input('Enter private key, leave blank for new chain'))
    if private_key == '':
        node = FullNode()
    else:
        node = FullNode(private_key)
