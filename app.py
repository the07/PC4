import json
from klein import Klein

import requests
from twisted.web.static import File
from bs4 import BeautifulSoup
import urllib.request

from record import Record
from user import User
from key import Key
from node import NodeMixin

import razorpay

class Instance:

    def __init__(self, session_id, key):

        self.__session_id__ = session_id
        self.__key__ = key

    @property
    def session_id(self):
        return self.__session_id__

    def get_key_by_session(self, session_id):

        if self.__session_id__ == session_id:
            return self.__key__

class App(NodeMixin):

    app = Klein()
    CLIENT_PORT = 30906
    instances = []

    def __init__(self):
        self.request_nodes_from_all()
        self.app.run('0.0.0.0', self.CLIENT_PORT)

    def get_all_user_address(self):
        self.request_nodes_from_all()
        for node in self.full_nodes:
            url = self.USER_URL.format(node, self.FULL_NODE_PORT)
            try:
                response = requests.get(url)
                addresses = []
                for address in json.loads(response.content.decode('utf-8'))['users']:
                    addresses.append(address)
                return addresses
            except requests.exceptions.RequestException as re:
                pass

    def get_genesis_user_address(self):
        self.request_nodes_from_all()
        for node in self.full_nodes:
            url = self.GENESIS_URL.format(node, self.FULL_NODE_PORT)
            try:
                response = requests.get(url)
                return response.content.decode('utf-8')
            except requests.exceptions.RequestException as re:
                pass

    def get_user(self, address):
        self.request_nodes_from_all()
        for node in self.full_nodes:
            url = self.USER_GET_URL.format(node, self.FULL_NODE_PORT, address)
            try:
                response = requests.get(url)
                response_content = response.json()
                if response_content is not '':
                    user_json = json.loads(response_content['user'])
                    return User.from_json(user_json)
            except requests.exceptions.RequestException as re:
                pass

    def get_unconfirmed_records(self, address):
        #ur.endorser -> sign it, ur.endorsee -> show in pending
        self.request_nodes_from_all()
        for node in self.full_nodes:
            url = self.URECORD_URL.format(node, self.FULL_NODE_PORT, address)
            try:
                response = requests.get(url)
                urecords = []
                for record in json.loads(response.content.decode('utf-8'))['records']:
                    urecords.append(Record.from_json(json.loads(record)))
                return urecords
            except requests.exceptions.RequestException as re:
                pass

    def get_balance(self, address):
        self.request_nodes_from_all()
        for node in self.full_nodes:
            url = self.BALANCE_URL.format(node, self.FULL_NODE_PORT, address)
        try:
            response = requests.get(url)
            return response.content.decode('utf-8')
        except requests.exceptions.RequestException as re:
            pass
        return None

    @app.route('/', methods=['GET'], branch=True)
    def get_root(self, request):
        return File('./web/')

    @app.route('/signup', methods=['POST'])
    def signup(self, request):
        # Read request content
        content = request.content.read().decode('utf-8')
        user_data = content.split('&')
        name = user_data[0].split('=')[1].replace('%2B', ' ')
        email = user_data[1].split('=')[1].replace('%40', '@')
        user_type = user_data[2].split('=')[1]
        # Initialize a key pair
        self.key = Key()
        user = User(self.key.get_public_key(), name, email, user_type)
        self.broadcast_user(user)
        message = "Your account has been created, please note your address: {} and password: {}.".format(self.key.get_public_key(), self.key.get_private_key()) + "<a href='index.html'>Login</a>"
        return json.dumps(message)

    @app.route('/login', methods=['POST'])
    def login(self, request):
        # Read request content
        content = request.content.read().decode('utf-8')
        password = content.split('=')[1]
        # Initialize a key pair from existing key
        key = Key(password)
        session_id = request.getSession().uid.decode('utf-8')
        instance = Instance(session_id, key)
        self.instances.append(instance)
        request.redirect('/user')
        return

    @app.route('/logout', methods=['GET'])
    def logout(self, request):
        request.getSession().expire()
        request.redirect('/')
        return

    @app.route('/user', methods=['GET'])
    def user_profile(self, request):

        session_id = request.getSession().uid.decode('utf-8')
        for instance in self.instances:
            if instance.session_id == session_id:
                key = instance.get_key_by_session(session_id)

        user = self.get_user(key.get_public_key())
        unconfirmed_records = self.get_unconfirmed_records(key.get_public_key())
        addresses = self.get_all_user_address()

        html_file = open('web/user.html').read()
        soup = BeautifulSoup(html_file, 'html.parser')

        soup.find(id='name').string = user.name
        soup.find(id='address').string = user.address
        soup.find(id='email').string = user.email
        soup.find(id='balance').string = self.get_balance(user.address)
        soup.find(id='user_type').string = user.user_type

        select_div = soup.find(id="address_list")
        for address in addresses:
            new_option_tag = soup.new_tag('option')
            new_option_tag['value'] = address
            select_div.append(new_option_tag)

        records_div = soup.find(id="records")
        for rec in user.records:
            record = Record.from_json(rec)
            new_p_tag = soup.new_tag('p')
            new_p_tag.string = "Record Detail: " + record.detail + "        Signed By: " + record.endorser
            records_div.append(new_p_tag)

        for record in unconfirmed_records:
            if record.endorsee == user.address:
                new_p_tag = soup.new_tag('p')
                new_p_tag.string = "Record Detail: " + record.detail + "        Signed By: Pending"
                records_div.append(new_p_tag)

        record_requests_div = soup.find(id="record_requests")
        for record in unconfirmed_records:
            if record.endorser == user.address:
                new_form_tag = soup.new_tag('form', method='post', action='/sign', enctype="application/x-www-form-urlencoded")
                new_form_tag['accept-charset']='utf-8'
                new_input_tag = soup.new_tag("input", type="textarea")
                new_input_tag['readonly'] = None
                new_input_tag["name"] = "endorsee"
                new_input_tag["value"] = record.endorsee
                new_input_tag["size"] = "160"
                new_form_tag.append(new_input_tag)
                new_input_tag_detail = soup.new_tag("input", type="text")
                new_input_tag_detail['readonly'] = None
                new_input_tag_detail['name'] = "detail"
                new_input_tag_detail['value'] = record.detail
                new_form_tag.append(new_input_tag_detail)
                submit_tag = soup.new_tag("input", type="submit", value="Sign")
                new_form_tag.append(submit_tag)
                record_requests_div.append(new_form_tag)

        return str(soup)

    @app.route('/record', methods=['POST'])
    def create_record(self, request):
        session_id = request.getSession().uid.decode('utf-8')
        for instance in self.instances:
            if instance.session_id == session_id:
                key = instance.get_key_by_session(session_id)
        content = request.content.read().decode('utf-8')
        record_data = content.split('&')
        endorser = record_data[0].split('=')[1]
        detail = record_data[1].split('=')[1]
        record = Record(key.get_public_key(), endorser.replace('%3A', ':'), detail)
        self.broadcast_record(record)
        message = "Record created. <a href='/user'>Go Back</a>"
        return json.dumps(message)

    @app.route('/sign', methods=['POST'])
    def sign_record(self, request):
        session_id = request.getSession().uid.decode('utf-8')
        for instance in self.instances:
            if instance.session_id == session_id:
                key = instance.get_key_by_session(session_id)
        content = request.content.read().decode('utf-8')
        endorsee = content.split('&')[0].split('=')[1].replace('%3A', ':')
        detail = content.split('&')[1].split('=')[1].replace('%2B', '+')
        print (endorsee, detail, key.get_public_key())
        record = Record(endorsee, key.get_public_key(), detail)
        record.sign(key.get_private_key())
        self.broadcast_record(record)
        message = "Checked records signed. <a href='/user'>Go Back</a>"
        return json.dumps(message)

    @app.route('/purchase', methods=['POST'])
    def handle_payment(self, request):
        session_id = request.getSession().uid.decode('utf-8')
        for instance in self.instances:
            if instance.session_id == session_id:
                key = instance.get_key_by_session(session_id)
        razorpay_payment_id = request.content.read().decode('utf-8').split('&')[1].split('=')[1]
        #TODO: capture payment
        endorser = self.get_genesis_user_address()
        endorsee = key.get_public_key()
        detail = "CoinPurchase"
        record = Record(endorsee, endorser, detail)
        self.broadcast_record(record)
        message = "Once transaction is mined, amount will be credited to you account. <a href='/user'>Go Back</a>"
        return json.dumps(message)


if __name__ == '__main__':
    app = App()
