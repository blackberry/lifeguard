from jira import JIRA
from collections import Counter
from app import app
from datetime import datetime


class JiraApi():

  def __init__(self,
               instance=None):
    self.instance = instance

  @staticmethod
  def get_datetime_now():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.0+0000")


  def connect(self):
    options = {'server': app.config['JIRA_HOSTNAME'],'verify':False}
    self.instance = JIRA(options,
                basic_auth=(app.config['JIRA_USERNAME'], app.config['JIRA_PASSWORD']))





