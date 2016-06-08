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

  def __str__(self):
    return 'VirtualMachinePool: id={}, name={}, cluster_id={}, cluster={}, ' \
           'zone_number={}, template={}, vars={}, cardinality={}'.format(
      self.id,
      self.name,
      self.cluster_id,
      self.cluster,
      self.zone_number,
      self.template,
      self.vars,
      self.cardinality)

  def __repr__(self):
    self.__str__()

  def get_memberships(self, vms=None):
    """
    Get the PoolMembership objects that are associated with the pool
    :param vms: If a collection of VMs is provided, the vm attribute of member is assigned
    :return:
    """
    memberships =  PoolMembership.query.filter_by(pool=self).all()
    if vms is not None:
      vms_dict = {vm.id: vm for vm in vms}
      for m in memberships:
        m.vm = vms_dict[m.vm_id]
    return memberships

  def name_for_number(self, number):
    pattern = re.compile("^([^\.]+)\.(.*)$")
    match = pattern.match(self.name)
    if match is None:
      raise Exception("Failed to parse pool name for hostname of number: {}".format(number))
    return '{}{}.{}'.format(match.group(1), number, match.group(2))

  def num_done_vms(self, members):
    done = 0
    for m in members:
      if m.is_done():
        done += 1
    return done

  def get_cluster(self):
    return Cluster.query.filter_by(zone_number=self.zone_number, id=self.cluster_id).first()

  def get_members_to_shrink(self, members, confirm_vm_ids=None):
    if len(members) <= self.cardinality:
      return None
    shrink = []
    num_2_member = {m.parse_number(): m for m in members}
    sorted_numbers = sorted(num_2_member)
    while len(sorted_numbers) > self.cardinality:
      candidate = num_2_member[sorted_numbers.pop()]
      print('confirm list: {}'.format(confirm_vm_ids))
      if confirm_vm_ids is not None and candidate.vm.id not in confirm_vm_ids:
        raise Exception("member (name={}, vm_id={}) not in confirm list".format(
          candidate.vm.name, candidate.vm.id))
      shrink.append(candidate)
    return shrink

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

  def __init__(self, pool_id=None, pool=None, vm_id=None, date_added=None, vm=None):
    self.pool_id = pool_id
    self.pool = pool
    self.vm_id = vm_id
    self.date_added = date_added
    self.vm = vm

  def is_done(self):
    if self.vm.state_id >= 4:
      return True

  @staticmethod
  def get_all(zone):
    return db.session.query(PoolMembership).join(
      PoolMembership.pool, aliased=True).filter_by(zone=zone)

  def parse_number(self):
    if self.vm is None:
      raise Exception("cannot determine number from virtual machine name when vm is None")
    num_pattern = re.compile("^[\dA-Za-z]+\D(\d+)\.")
    match = num_pattern.match(self.vm.name)
    if match is not None:
      return int(match.group(1))
    else:
      raise Exception("cannot determine number from virtual machine name {}".format(self.vm.name))

  def __str__(self):
    return 'PoolMembership: pool_id={}, pool={}, vm_id={}, vm={}, date_added={}'.format(
      self.pool_id,
      self.pool,
      self.vm_id,
      self.vm,
      self.date_added)

  def __repr__(self):
    self.__str__()



class PoolEditForm(Form):
  name = StringField('Name', [InputRequired()])
  cardinality = StringField('Cardinality', [InputRequired()])
  template = TextAreaField('Zone Template')
  vars = TextAreaField('Zone Variables')


class GenerateTemplateForm(Form):
  pass
