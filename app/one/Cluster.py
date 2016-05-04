class Cluster:
  def __init__(self,
               id=None,
               name=None):
    self.id = id
    self.name = name

  @staticmethod
  def from_xml_etree(etree):
    return Cluster(
      id=int(etree.find('ID').text),
      name=etree.find('NAME').text)
