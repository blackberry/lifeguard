import logging
#import config

def getApplianceByUrl(applianceUrl, nameOverride=None):
  """
  Returns a JSON object representing a marketplace appliance at a URL
  :param applianceUrl:
  :return:
  """
  import urllib.request
  import json
  headers = {'Accept': "application/json"}
  request = urllib.request.Request(applianceUrl, None, headers)
  response = urllib.request.urlopen(request)
  json = json.loads(response.read().decode('utf-8'))

  return {
    'name': nameOverride if nameOverride else json['name'],
    'version': json['version'],
    'id': json['_id']['$oid'],
    'download_link': json['links']['download']['href']
  }