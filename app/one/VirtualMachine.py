class VirtualMachine():
  def __init__(self,
               id=None,
               name=None,
               state=None,
               lcm_state=None,
               stime=None,
               memory=None,
               cpu=None,
               vcpu=None,
               disk_cluster=None,
               disk_cluster_id=None,
               disk_datastore_id=None,
               disk_datastore_name = None,
               image_name=None,
               image_id=None,
               ip_address=None):
    self.id = id
    self.name = name
    self.state = state
    self.lcm_state = lcm_state
    self.stime = stime
    self.memory = memory
    self.cpu = cpu
    self.vcpu = vcpu
    self.disk_cluster = disk_cluster
    self.disk_cluster_id = disk_cluster_id
    self.disk_datastore_id = disk_datastore_id
    self.disk_datastore_name = disk_datastore_name
    self.image_name = image_name
    self.image_id = image_id
    self.ip_address = ip_address

  @staticmethod
  def state_by_id(id):
    state = {0: 'INIT',
             1: 'PENDING',
             2: 'HOLD',
             3: 'ACTIVE',
             4: 'STOPPED',
             5: 'SUSPENDED',
             6: 'DONE',
             7: 'FAILED',
             8: 'POWEROFF',
             9: 'UNDEPLOYED'}
    return state[id]

  @staticmethod
  def lcm_state_by_id(id):
    state = {0: 'LCM_INIT',
             1: 'PROLOG',
             2: 'BOOT',
             3: 'RUNNING',
             4: 'MIGRATE',
             5: 'SAVE_STOP',
             6: 'SAVE_SUSPEND',
             7: 'SAVE_MIGRATE',
             8: 'PROLOG_MIGRATE',
             9: 'PROLOG_RESUME',
             10: 'EPILOG_STOP',
             11: 'EPILOG',
             12: 'SHUTDOWN',
             13: 'CANCEL',
             14: 'FAILURE',
             15: 'CLEANUP_RESUBMIT',
             16: 'UNKNOWN',
             17: 'HOTPLUG',
             18: 'SHUTDOWN_POWEROFF',
             19: 'BOOT_UNKNOWN',
             20: 'BOOT_POWEROFF',
             21: 'BOOT_SUSPENDED',
             22: 'BOOT_STOPPED',
             23: 'CLEANUP_DELETE',
             24: 'HOTPLUG_SNAPSHOT',
             25: 'HOTPLUG_NIC',
             26: 'HOTPLUG_SAVEAS',
             27: 'HOTPLUG_SAVEAS_POWEROFF',
             28: 'HOTPLUG_SAVEAS_SUSPENDED',
             29: 'SHUTDOWN_UNDEPLOY',
             30: 'EPILOG_UNDEPLOY',
             31: 'PROLOG_UNDEPLOY',
             32: 'BOOT_UNDEPLOY'}
    return state[id]

  @staticmethod
  def from_xml_etree(etree):
    vm = VirtualMachine(
      id=int(etree.find('ID').text),
      name=etree.find('NAME').text,
      state=VirtualMachine.state_by_id(int(etree.find('STATE').text)),
      lcm_state=VirtualMachine.lcm_state_by_id(int(etree.find('LCM_STATE').text)),
      stime=int(etree.find('STIME').text),
      memory=int(etree.find('TEMPLATE').find('MEMORY').text),
      cpu=float(etree.find('TEMPLATE').find('CPU').text),
      disk_cluster_id=int(etree.find('TEMPLATE').find('DISK').find('CLUSTER_ID').text),
      disk_datastore_id=int(etree.find('TEMPLATE').find('DISK').find('DATASTORE_ID').text),
      disk_datastore_name=etree.find('TEMPLATE').find('DISK').find('DATASTORE').text,
      image_name=etree.find('TEMPLATE').find('DISK').find('IMAGE').text,
      image_id=int(etree.find('TEMPLATE').find('DISK').find('IMAGE_ID').text),
      ip_address=etree.find('TEMPLATE').find('NIC').find('IP').text)
    if etree.find('TEMPLATE').find('VCPU') is not None:
      vm.vcpu = float(etree.find('TEMPLATE').find('VCPU').text)
    return vm

  def memory_gb(self):
    return round(self.memory / 1024, 0)

  def state_desc(self):
    if self.state is "ACTIVE":
      return self.lcm_state
    else:
      return self.state

  def cpu_desc(self):
    if self.vcpu is None or self.vcpu == self.cpu:
      return self.cpu
    else:
      return '{}/{}'.format(self.cpu, self.vcpu)
