#from ldap3 import Server, Connection, ALL, NTLM

from ldap3 import Server, \
    Connection, \
    AUTO_BIND_NO_TLS, \
    SUBTREE, \
    ALL_ATTRIBUTES

from flask_wtf import Form
from wtforms import TextField, PasswordField
from wtforms.validators import InputRequired
from app import db, app
 
 
def get_ldap_connection():
    conn = ldap3.initialize(app.config['LDAP_PROVIDER_URL'])
    return conn
 
 
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    is_authenticated = True
    is_anonymous = False
    is_active = True

    username = db.Column(db.String(100))
 
    def __init__(self, username, password):
        self.username = username
 
    @staticmethod
    def try_login(username, passwd):
        #print("trying to login: " + username)
        #server = Server(app.config['LDAP_PROVIDER_URL'], get_info=ALL)
        #conn = Connection(server, user="RIMNET\\"+username, password=passwd, authentication=NTLM)
        #print(conn.extend.standard.who_am_i())
        #print(conn)

        #srv = Server('dc-g01.ad0.bblabs', get_info=ALL)
        #conn = Connection(server=srv, )
        #server.info 

        print("starting")

        with Connection(Server('dc-g01.ad0.bblabs', port=636, use_ssl=True),
                    auto_bind=AUTO_BIND_NO_TLS,
                    read_only=True,
                    check_names=True,
                    user='ldapreader', password='ld@pr3ad3r!') as c:
 
            c.search(search_base='OU=RIMNET_ILM,DC=ad0,DC=bblabs',
                 search_filter='(&(samAccountName=' + username + '))',
                 search_scope=SUBTREE,
                 attributes=ALL_ATTRIBUTES,
                 get_operational_attributes=True)
 
        response = c.response
        print(response[0]['dn'])



        print(c.result)
        print("done in here")
 
    def get_id(self):
        return self.id
 
 
class LoginForm(Form):
    username = TextField('Username', [InputRequired()])
    password = PasswordField('Password', [InputRequired()])
