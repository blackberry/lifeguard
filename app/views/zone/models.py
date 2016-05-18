from flask_wtf import Form
from wtforms import StringField, PasswordField, TextAreaField
from wtforms.validators import InputRequired
from app import db
from app.views.cluster.models import Cluster


class Zone(db.Model):
  number = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(100), unique=True, nullable=False)
  xmlrpc_uri = db.Column(db.String(100), nullable=False)
  session_string = db.Column(db.String(100), nullable=False)
  template = db.Column(db.Text())
  vars = db.Column(db.Text())

  def __init__(self, number=None, name=None, xmlrpc_uri=None, session_string=None):
    self.name = name
    self.xmlrpc_uri = xmlrpc_uri
    self.session_string = session_string
    self.number = number

  def parsed_vars(self, overwrite_vars=None):
    parsed = {}
    for var in self.vars.split("\n"):
      k, v = var.split("=", 2)
      parsed[k.strip()] = v.strip()
    for k, v in overwrite_vars.items():
      parsed[k.strip()] = v.strip()
    return parsed

  def get_clusters(self):
    return Cluster.query.filter_by(zone_number=self.number).all()

  def get_cluster(self, cluster_id):
    return Cluster.query.filter_by(zone_number=self.number, id=cluster_id).first()


class ZoneForm(Form):
  name = StringField('Name', [InputRequired()])
  number = StringField('Number', [InputRequired()])
  xmlrpc_uri = StringField('XML-RPC URI', [InputRequired()])
  session_string = PasswordField('Session String', [InputRequired()])


class ZoneTemplateForm(Form):
  template = TextAreaField('Zone Template')
  vars = TextAreaField('Zone Variables')