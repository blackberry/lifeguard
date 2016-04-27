from flask_wtf import Form
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired
from app import db


class Zone(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(100))
  xmlrpc_uri = db.Column(db.String(100))
  session_string = db.Column(db.String(100))
  zone_num = db.Column(db.Integer)

  def __init__(self, name, xmlrpc_uri, session_string, zone_num):
    self.name = name
    self.xmlrpc_uri = xmlrpc_uri
    self.session_string = session_string
    self.zone_num = zone_num


class ZoneForm(Form):
  name = StringField('Name', [InputRequired()])
  zone_num = StringField('Zone Number', [InputRequired()])
  xmlrpc_uri = StringField('XML-RPC URI', [InputRequired()])
  session_string = PasswordField('Password', [InputRequired()])

class ConfirmForm(Form):
  pass