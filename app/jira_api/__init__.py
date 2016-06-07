from jira import JIRA
from collections import Counter
from app import app
from datetime import datetime
from flask.ext.login import current_user


class JiraApi():

  def __init__(self, instance=None):
    self.instance = instance

  @staticmethod
  def get_datetime_now():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.0+0000")


  def connect(self):
    options = {'server': app.config['JIRA_HOSTNAME'],'verify':False}
    self.instance = JIRA(options,
                basic_auth=(app.config['JIRA_USERNAME'], app.config['JIRA_PASSWORD']))


  @staticmethod
  def ticket_link(issue):
    return '<a href="{}/browse/{}">{}</a>'.format(app.config['JIRA_HOSTNAME'], issue.key, issue.key)

  def defect_for_exception(self, summary_title, e):
    return self.instance.create_issue(
      project='IPGBD',
      summary='[auto-{}] Problem: {}'.format(current_user.username, summary_title),
      description="Exception: {}".format(e),
      customfield_13842=JiraApi.get_datetime_now(),
      customfield_13838= {
        "self": "https://jira.rim.net/rest/api/2/customFieldOption/16680",
        "value": "No",
        "id": "16680"
      },
      customfield_13831 =  [
      {
        "self": "https://jira.rim.net/rest/api/2/customFieldOption/16592",
        "value": "Quality",
        "id": "16592"
      },
      {
        "self": "https://jira.rim.net/rest/api/2/customFieldOption/16594",
        "value": "Risk Avoidance",
        "id": "16594"
      }],
      issuetype={'name': 'Defect'})





