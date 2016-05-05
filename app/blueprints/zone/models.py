from flask_wtf import Form
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired
from app import db


class Zone(db.Model):
  number = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(100), unique=True, nullable=False)
  xmlrpc_uri = db.Column(db.String(100))
  session_string = db.Column(db.String(100))

  def __init__(self, number=None, name=None, xmlrpc_uri=None, session_string=None):
    self.name = name
    self.xmlrpc_uri = xmlrpc_uri
    self.session_string = session_string
    self.number = number


class ZoneForm(Form):
  name = StringField('Name', [InputRequired()])
  number = StringField('Number', [InputRequired()])
  xmlrpc_uri = StringField('XML-RPC URI', [InputRequired()])
  session_string = PasswordField('Session String', [InputRequired()])


class VmActionForm(Form):
  pass


class VirtualMachinePool(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(100), unique=True, nullable=False)
  zone_number = db.Column(db.Integer, nullable=False)
  cluster_id = db.Column(db.Integer, nullable=False)

  def __init__(self, id=None, name=None, zone_number=None, cluster_id=None):
    self.id = id
    self.name = name
    self.zone_number = zone_number
    self.cluster_id = cluster_id


class PoolMembership(db.Model):
  pool_id = db.Column(db.Integer, primary_key=True)
  vm_id = db.Column(db.Integer, primary_key=True)
  date_added = db.Column(db.DateTime, nullable=False)

  def __init__(self, pool_id=None, vm_id=None, date_added=None):
    self.pool_id = pool_id
    self.vm_id = vm_id
    self.date_added = date_added
