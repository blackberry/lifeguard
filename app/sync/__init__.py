import logging
import re
from datetime import datetime

class GoldImageSync:
  def __init__(self, zone, one_proxy):
    self.zone = zone
    self.one = one_proxy
    self.images = None
    self.datastore = None
    self.gold_image = None
    self.current_image = None

  def refresh(self, allowCached=False):
    if self.images is None or allowCached is False:
      self.images = self.one.getAllImages()
    self.current_image = self.one.find_by_attr_k_v(
      self.images, 'name', self.imageNameForDatastore())

  def imageNameForDatastore(self):
    return '{}-{}'.format(self.datastore['name'], self.gold_image['name'])

  def currentVersion(self):
    self.refresh(True)
    if self.current_image:
      pattern = '^application-ID-{}-gold-image-version-([^$]+)'.format(self.gold_image['id'])
      res = re.search(pattern, self.current_image['description'])
      if res is not None and res.group(1) is not None:
        return res.group(1)

  def deprecateCurrentImage(self):
    if self.currentVersion() is not None:
      new_name = '{}-old-version-{}'.format(
        self.imageNameForDatastore(),
        self.currentVersion())
    else:
      now = datetime.utcnow()
      new_name = '{}-unknown-version-replaced-{}-{}-{}-{}-{}'.format(
        self.imageNameForDatastore(),
        now.year,
        now.month,
        now.day,
        now.hour,
        now.minute)
    self.one.renameImage(self.current_image['id'], new_name)
    logging.info('{}.{} renamed old image to {}'.format(
      self.zone,
      self.datastore['name'],
      new_name))

  def syncIfRequired(self, gold_image):
    self.gold_image = gold_image
    self.refresh(True)
    logging.debug('{}.{} synchronizing image {}'.format(
      self.zone, self.datastore['name'], self.gold_image['name']))
    if self.isSyncRequired():
      if self.current_image is not None:
        self.deprecateCurrentImage()
      self.upload()

  def isSyncRequired(self):
    self.refresh(True)
    if self.current_image is None:
      logging.info('{}.{} does not contain image named {}'.format(
        self.zone,
        self.datastore['name'],
        self.imageNameForDatastore()))
      return True

    if self.currentVersion() is None:
      logging.info('{}.{} image {} unknown version found in datastore'.format(
        self.zone,
        self.datastore['name'],
        self.imageNameForDatastore()))
      return True

    if self.currentVersion() != self.gold_image['version']:
      logging.info('{}.{} image {} version {} does not match {}'.format(
        self.zone,
        self.datastore['name'],
        self.imageNameForDatastore(),
        self.currentVersion(),
        self.gold_image['version']))
      return True

    logging.info('{}.{} image {} version {} is current'.format(
      self.zone,
      self.datastore['name'],
      self.imageNameForDatastore(),
      self.gold_image['version']))

  def upload(self):
    desc = 'application-ID-{}-gold-image-version-{}'.format(
      self.gold_image['id'],
      self.gold_image['version'])
    template = ''.join([
      'name=', self.imageNameForDatastore(), '\n',
      'path=', self.gold_image['download_link'], '\n',
      'description=', desc, '\n',
      'persistent=no\n',
      'public=yes\n'])
    self.one.createImage(self.datastore, template)
    logging.debug('template for %s was %s', self.imageNameForDatastore(), template)
    logging.info('{}.{} created image {} for gold image {}'.format(
      self.zone,
      self.datastore['name'],
      self.imageNameForDatastore(),
      self.gold_image['name']))
