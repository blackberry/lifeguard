import xmlrpc.client
import xml.etree.ElementTree as etree
import ssl

# http://docs.opennebula.org/4.10/integration/system_interfaces/api.html

# These objects returned by this module are bare bones
# and only contain the base attributes required by the
# current features.  As more attributes are required
# the maintainer should set them accordingly by finding
# the elements in the XML returned by ONE instead of
# accessing the XML directly as it could be ONE API
# version dependent.

# Dave Ariens <dariens@blackberry.com>

CURRENT_USER = -3
UNLIMITED = -1


class OneProxy:
  def __init__(self, api_url, session_string, verify_certs = True):
    self.api_url = api_url
    self.session_string = session_string
    self.verify_certs = verify_certs

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

    if self.verify_certs:
      ssl_context.verify_mode = ssl.CERT_OPTIONAL
    else:
      ssl_context.verify_mode = ssl.CERT_NONE

    self.proxy = xmlrpc.client.ServerProxy(api_url, verbose=False, context=ssl_context)

  def renameImage(self, id, new_name):
    """
    Renames an image in a given zone
    :param id:
    :param new_name:
    :return:
    """
    response = self.proxy.one.image.rename(self.session_string, id, new_name)
    if response[0] is not True:
      raise (Exception("one.image.rename id {} rename to {} failed (error code: {}) {}".format(
        id,
        new_name,
        response[2],
        response[1])))


  def getImage(self, id):
    """
    Returns an image in a given zone
    :param id:
    :return:
    """
    response = self.proxy.one.image.info(self.session_string, id)
    if response[0] is not True:
      raise (Exception("one.image.info id {} info failed (error code: {}) {}".format(
        id,
        response[2],
        response[1])))
    xml = etree.fromstring(response[1])
    return {
      'id': int(xml.find('ID').text),
      'name': xml.find('ID').text,
      'description': xml.find('DESC').text
    }


  def findInListByAttrKeyVal(self, list, attr_name, attr_val):
    for item in list:
      if item[attr_name] == attr_val:
        return item


  def getAllImages(self):
    """
    Retuns all the images in a given zone
    :return:
    """
    response = self.proxy.one.imagepool.info(self.session_string, CURRENT_USER, UNLIMITED, UNLIMITED)
    if response[0] is not True:
      raise (Exception("one.imagepool.info failed (error code: {}) {}".format(
        response[2],
        response[1])))
    items = []
    for child in etree.fromstring(response[1]):
      desc_el = child.find('TEMPLATE').find('DESCRIPTION')
      description = desc_el.text if desc_el is not None else None
      items.append({
        'id': int(child.find('ID').text),
        'name': child.find('NAME').text,
        'description': description
      })
    return items


  def getAllDatastores(self):
    """
    Returns all the datastores in a given zone
    :return:
    """
    response = self.proxy.one.datastorepool.info(self.session_string)
    if response[0] is not True:
      raise (Exception("one.datastorepool.info failed (error code: {}) {}".format(
        response[2],
        response[1])))
    items = []
    for child in etree.fromstring(response[1]):
      items.append({
        'id': int(child.find('ID').text),
        'name': child.find('NAME').text,
        'cluster_name': child.find('CLUSTER').text,
        'type': child.find('DS_MAD').text
      })
    return items


  def getAllClusters(self):
    """
    Returns all the datastores in a given zone
    :return:
    """
    response = self.proxy.one.clusterpool.info(self.session_string)
    if response[0] is not True:
      raise (Exception("one.clusterpool.info failed (error code: {}) {}".format(
        response[2],
        response[1])))
    items = []
    for child in etree.fromstring(response[1]):
      items.append({
        'id': int(child.find('ID').text),
        'name': child.find('NAME').text
      })
    return items


  def createImage(self, datastore, template):
    """
    Createa an image defined by template in a given zone
    :param datastore:
    :param template:
    :return:
    """
    response = self.proxy.one.image.allocate(self.session_string, template, datastore['id'])
    if response[0] is not True:
      raise (Exception("one.image.allocate failed (error code: {}) {} with template {}".format(
        response[2],
        response[1],
        template)))
