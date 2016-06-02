from ldap3 import Server, Connection, AUTO_BIND_NO_TLS, SUBTREE, ALL_ATTRIBUTES, LDAPException
from flask_wtf import Form
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired
from app import db, app

class User(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  is_authenticated = True
  is_anonymous = False
  is_active = True
  username = db.Column(db.String(100))

  def __init__(self, username):
    self.username = username

  @staticmethod
  def try_login(username, passwd):
    # Login with our read only account
    with Connection(Server(app.config['LDAP_PROVIDER_URL'], port=app.config['LDAP_PROVIDER_PORT'], use_ssl=True),
                    auto_bind=AUTO_BIND_NO_TLS,
                    read_only=True,
                    check_names=True,
                    user=app.config['LDAP_READER_USERNAME'], password=app.config['LDAP_READER_PASSWORD']) as c1:
      # Search for the user's DN which becomes the login username for the authentication connection
      c1.search(search_base=app.config['LDAP_USER_SEARCH_BASE'],
                search_filter='(&({}={}))'.format(app.config['LDAP_USER_SEARCH_FILTER'], username),
                search_scope=SUBTREE,
                attributes=ALL_ATTRIBUTES,
                get_operational_attributes=True)
    # Establish a connection with the user's DN and their password
    with Connection(Server(app.config['LDAP_PROVIDER_URL'], port=app.config['LDAP_PROVIDER_PORT'], use_ssl=True),
                    auto_bind=AUTO_BIND_NO_TLS,
                    read_only=True,
                    check_names=True,
                    user=c1.response[0]['dn'], password=passwd) as c2:
      # Connectons are lazily initialized, so try a search to validate successful authentication
      c2.search(search_base=app.config['LDAP_USER_SEARCH_BASE'],
                search_filter='(&({}={}))'.format(app.config['LDAP_USER_SEARCH_FILTER'], username),
                search_scope=SUBTREE,
                attributes=ALL_ATTRIBUTES,
                get_operational_attributes=True)

    if app.config['LDAP_ADMIN_GROUP'] not in c2.response[0]['attributes']['memberOf']:
      raise LDAPException("{} not a member of {}".format(username, app.config['LDAP_ADMIN_GROUP']))

  def get_id(self):
    return self.id


class LoginForm(Form):
  username = StringField('Username', [InputRequired()])
  password = PasswordField('Password', [InputRequired()])
