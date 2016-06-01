from flask_wtf import Form
from app import db
from sqlalchemy.schema import ForeignKeyConstraint
from wtforms import StringField
from wtforms.validators import InputRequired


class Cluster(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  zone = db.relationship('Zone', backref=db.backref('zone_ref', lazy='dynamic'))
  zone_number = db.Column(db.Integer, db.ForeignKey('zone.number'), primary_key=True)
  name = db.Column(db.String(100), unique=True, nullable=False)
  template = db.Column(db.Text())
  vars = db.Column(db.Text())
  ForeignKeyConstraint('zone_number', 'zone.number')

  def __init__(self, id=id, zone_number=None, zone=None, name=None, template=None, vars=None):
    self.id = id
    self.zone = zone
    self.zone_number = zone_number
    self.name = name
    self.template = template
    self.vars=vars

  def parsed_vars(self, additional=None):
    parsed = {}
    # Start with zone default variables
    for var in self.zone.vars.split("\n"):
      k, v = var.split("=", 2)
      parsed[k.strip()] = v.strip()
    # Overwrite/add with any defined for the cluster
    for var in self.vars.split("\n"):
      k, v = var.split("=", 2)
      parsed[k.strip()] = v.strip()
    # Overwrite/add any additional
    for k, v in additional.items():
      parsed[k.strip()] = v.strip()
    return parsed


  def __str__(self):
    return 'Cluster: id={}, name={}, zone_number={}, zone={}'.format(
      self.id, self.name, self.zone_number, self.zone)

  def __repr__(self):
    self.__str__()

class ClusterTemplateForm(Form):
  pass

class GenerateTemplateForm(Form):
  pass


class CreateVmForm(Form):
  hostname = StringField('Hostname', [InputRequired()], default='<somename>.log82.altus.bblabs')
  cpu = StringField('CPU', [InputRequired()], default='.25')
  vcpu = StringField('VCPU', [InputRequired()], default='1')
  memory_megabytes = StringField('Memory (MB)', [InputRequired()], default='2048')