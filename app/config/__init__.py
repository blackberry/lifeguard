import configparser
import logging
from app import marketplace
from app.sync import GoldImageSync
from app.one import OneProxy


class Config:
  def __init__(self, config_ini=None):
    self.config_ini = config_ini if config_ini else 'config.ini'
    self.config = configparser.ConfigParser(allow_no_value=True)
    self.config.read(self.config_ini)

  def getOneProxy(self, zone):
    zone_override = 'zone-config-{}'.format(zone)
    ss_file = self.config['one']['default_ss_file']
    session_string = None
    if zone_override in self.config:
      if 'ss_file' in  self.config[zone_override]:
        ss_file = self.config[zone_override]['ss_file']
    with open(ss_file) as fh:
      session_string = fh.read().strip()
    return OneProxy(
      self.config['zones-all'][zone],
      session_string,
      self.verifyOneCerts())

  def getApiUrl(self, zone):
    """
    Returns the XML-RPC API URL for a given zone
    :param zone:
    :return:
    """
    return self.config['zones-all'][zone]


  def getMarketplaceUrl(self):
    """
    Returns the base URL of the configured marketplace instance
    :return:
    """
    return self.config['marketplace']['base_url']


  def getImageSyncZones(self):
    return [GoldImageSync(zone, self.getOneProxy(zone)) for zone in self.getZones()]


  def getGoldImages(self):
    """
    Returns all the appliance IDs configured
    :return:
    """
    return [marketplace.getApplianceByUrl(
      "{}/{}".format(self.getMarketplaceUrl(), imageId),
      self.config['gold-images'][imageId])
            for imageId in self.config['gold-images']]


  def getZones(self):
    """
    Returns all the zones configured
    """
    return self.config['zones-enabled']


  def skipDatastore(self, datastore):
    """
    Returns true if we're skipping the datastore
    :return:
    """
    if datastore['type'] != 'fs':
      logging.debug('datastore %s is not for filesystems (type: %s)',
                    datastore['name'], datastore['type'])
      return True
    if datastore['cluster_name'] in self.config['omitted-clusters']:
      logging.debug('datastore %s is attached to non-supported cluster (%s)',
                    datastore['name'], datastore['cluster'])
      return True

    return datastore['name'] in self.config['omitted-datastores']


  def skipCluster(self, cluster):
    """
    Returns true if we're skipping the cluster
    :return:
    """
    return cluster['name'] in self.config['omitted-clusters']


  def getCurrentVersionKey(self, datastore, app):
    """
    Returns the config entry name where a current version is associated to a datastore
    :param datastore:
    :param app:
    :return:
    """
    return "ds_'{}',app-id_'{}'".format(datastore['name'], app['id'])

  def getCurrentVersion(self, datastore, app):
    """
    Returns the current version of an application installed in a datastore
    :param ds_name:
    :param app_id:
    :return:
    """
    key = self.getCurrentVersionKey(datastore, app)
    if key in self.versions['current-versions']:
      return self.versions['current-versions'][key]
    else:
      return None


  def verifyOneCerts(self):
    """
    Returns true if we are going to verify the integrity of TLS certificates we are presented with
    :return:
    """
    return 'verify_certs' in self.config['one'] and self.config['one']['verify_certs'] is True


  def getZoneSessionStringFile(self, zone):
    """
    Returns the appropriate session string filename for a given zone
    :param zone:
    :return:
    """
    section = "zone-config-{}".format(zone)
    if section in self.config and 'ss_file' in self.config[section]:
      return self.config[section]['ss_file']
    else:
      return self.config['one']['default_ss_file']
