from flask_wtf import Form
from wtforms import TextAreaField, StringField
from wtforms.validators import InputRequired
from app.views.cluster.models import Cluster
from app import db
from app.one import OneProxy
from app.one import INCLUDING_DONE
import re


class ExpandException(Exception):
  pass


class VirtualMachinePool(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(100), unique=True, nullable=False)
  cluster_id = db.Column(db.Integer, nullable=False)
  zone_number = db.Column(db.Integer, nullable=False)
  template = db.Column(db.Text(), default='{% extends cluster.template %}')
  vars = db.Column(db.Text(), default='')
  cardinality = db.Column(db.Integer, nullable=False, default=1)
  cluster = db.relationship(
    'Cluster',
    primaryjoin="and_(VirtualMachinePool.cluster_id == Cluster.id, VirtualMachinePool.zone_number == Cluster.zone_number)",
    foreign_keys=[cluster_id, zone_number])

  def __init__(self, id=None, name=None, zone_number=None, cluster_id=None, cardinality=None):
    self.id = id
    self.name = name
    self.cluster_id = cluster_id
    self.zone_number = zone_number
    self.cardinality = cardinality

  def get_memberships(self):
    return PoolMembership.query.filter_by(pool=self).all()

  def get_memberships_by_vm_id(self):
    memberships = {}
    for membership in self.get_memberships():
      memberships[membership.vm_id] = membership
    return memberships

  def name_for_number(self, number):
    pattern = re.compile("^([^\.]+)\.(.*)$")
    match = pattern.match(self.name)
    if match is None:
      raise Exception("Failed to parse pool name for hostname of number: {}".format(number))
    return '{}{}.{}'.format(match.group(1), number, match.group(2))

  @staticmethod
  def get_num_from_name(name):
    num_pattern = re.compile("^[^\.]+(\d+)\.")
    match = num_pattern.match(name)
    if match is not None:
      return int(match.group(1))
    else:
      return None

  def get_member_vms_by_num(self):
    memberships_by_vm_id = self.get_memberships_by_vm_id()
    vms_by_num = {}
    one_proxy = OneProxy(self.cluster.zone.xmlrpc_uri, self.cluster.zone.session_string, verify_certs=False)
    for vm in one_proxy.get_vms(INCLUDING_DONE):
      if vm.id in memberships_by_vm_id:
        num = VirtualMachinePool.get_num_from_name(vm.name)
        if num is not None:
          vms_by_num[num] = vm
        else:
          raise Exception("Cannot determine number from name {}".format(name))
    return vms_by_num

  def get_cluster(self):
    return Cluster.query.filter_by(zone_number=self.zone_number, id=self.cluster_id).first()

  def get_shrink_collections(self):
    members = self.get_memberships()
    if (len(members) == self.cardinality):
      raise ExpandException("Cannot shrink {} ({}/{} members already exist)".format(
        self.name, len(members), self.cardinality))
    if (len(members) < self.cardinality):
      raise ExpandException("Cannot shrink {} ({}/{} members, need to expand)".format(
        self.name, len(members), self.cardinality))
    member_vms_by_num = self.get_member_vms_by_num()

    sorted_existing_numbers = list(member_vms_by_num.keys())
    sorted_existing_numbers.sort()
    shrink_names_by_number = {}
    num_to_shrink_by = len(members) - self.cardinality
    for i in range(0, num_to_shrink_by):
      num_to_shrink = sorted_existing_numbers.pop()
      shrink_names_by_number[num_to_shrink] = member_vms_by_num[num_to_shrink]

    numbers = {}
    for number in range(1, self.cardinality + 1):
      numbers[number] = number

    return shrink_names_by_number, member_vms_by_num, members, numbers

  def get_expansion_collections(self):
    """
    Checks if there are hosts that are required for expansion and if so generates their new
    names by creating lowest missing values of 'N' in poolname<N>.domain.tld.  Other required
    collections for error checking are also returned
    of n
    :return:
    new_names_by_num dict: the new hostnames keyed off their 'N' value
    member_vms_by_num dict: existing member hostnames keyed off their 'N' value
    members PoolMembership[]: array of existing members
    numbers dict: simple dict for all host numbers in range of 1 to cardinality
    """
    members = self.get_memberships()
    if (len(members) == self.cardinality):
      raise ExpandException("Cannot expand {} ({}/{} members already exist)".format(
        self.name, len(members), self.cardinality))
    if (len(members) > self.cardinality):
      raise ExpandException("Cannot expand {} ({}/{} members, need to shrink)".format(
        self.name, len(members), self.cardinality))
    member_vms_by_num = self.get_member_vms_by_num()
    new_names_by_num = {}
    for number in range(1, self.cardinality + 1):
      if number not in member_vms_by_num:
        new_names_by_num[int(number)] = self.name_for_number(number)

    # Ensure that the number of new names we have matches the number we needed to expand with
    needed = self.cardinality - len(member_vms_by_num)
    if len(new_names_by_num) != needed:
      raise ExpandException("Error: needed {} new VMs but could only infer {} misssing names".format(
        needed, len(new_names_by_num)))

    # Check that for each number that we require in our range from 1 to cardinality
    # that we have either an existing member that matches the name or that a new name has
    # been generated for it
    numbers = {}
    for number in range(1, self.cardinality + 1):
      if number in new_names_by_num and number in member_vms_by_num:
        raise Exception("VM number {} found in members and new names".format(number))
      if number not in new_names_by_num and number not in member_vms_by_num:
        raise Exception("VM number {} not found in members or new names".format(number))
      numbers[number] = number

    return new_names_by_num, member_vms_by_num, members, numbers



  @staticmethod
  def get_all(cluster):
    return db.session.query(VirtualMachinePool).filter_by(cluster=cluster)

  def get_peer_pools(self):
    return db.session.query(VirtualMachinePool).filter_by(cluster=self.cluster)


class PoolMembership(db.Model):
  vm_id = db.Column(db.Integer, primary_key=True)
  pool_id = db.Column(db.Integer, db.ForeignKey('virtual_machine_pool.id'), primary_key=True)
  pool = db.relationship('VirtualMachinePool', backref=db.backref('virtual_machine_pool', lazy='dynamic'))
  date_added = db.Column(db.DateTime, nullable=False)

  def __init__(self, pool_id=None, pool=None, vm_id=None, date_added=None):
    self.pool_id = pool_id
    self.pool = pool
    self.vm_id = vm_id
    self.date_added = date_added

  @staticmethod
  def get_all(zone):
    return db.session.query(PoolMembership).join(
      PoolMembership.pool, aliased=True).filter_by(zone=zone)


class PoolEditForm(Form):
  name = StringField('Name', [InputRequired()])
  cardinality = StringField('Cardinality', [InputRequired()])
  template = TextAreaField('Zone Template')
  vars = TextAreaField('Zone Variables')


class GenerateTemplateForm(Form):
  pass
