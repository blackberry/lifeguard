from jira import JIRA
from collections import Counter
from app import app
from datetime import datetime, timedelta, timezone
from flask.ext.login import current_user
import pytz
from datetime import datetime, timedelta


class JiraApi():

  str_jira_scheduled = "%Y-%m-%dT%H:%M:%S.0%z"

  def __init__(self,
               instance=None,
               approver_instance=None):
    self.instance = instance
    self.approver_instance = approver_instance

  @staticmethod
  def next_immediate_window_dates():
    tz = pytz.timezone(app.config['CM_TZ'])
    now_utc = datetime.utcnow()
    now_tz = tz.localize(now_utc)
    start = None
    if now_tz.hour <= app.config['CM_DEADLINE_HOUR']  and now_tz.minute < app.config['CM_DEADLINE_MIN']:
      start = tz.localize(datetime(now_tz.year, now_tz.month, now_tz.day, app.config['CM_SAME_DAY_START_HOUR']))
    else:
      delay_hours = timedelta(hours=app.config['CM_DEADLINE_MISSED_DELAY_HOURS'])
      start_day = now_tz + delay_hours
      start = tz.localize(datetime(
        start_day.year, start_day.month, start_day.day, app.config['CM_DEADLINE_MISSED_START_HOUR']))
    end = start + timedelta(hours=app.config['CM_WINDOW_LEN_HOURS'])
    return start.strftime(JiraApi.str_jira_scheduled), \
           end.strftime(JiraApi.str_jira_scheduled)

  @staticmethod
  def get_datetime_now():
    tz = pytz.timezone(app.config['CM_TZ'])
    now = pytz.utc.localize(datetime.utcnow()).astimezone(tz)
    return now.strftime(JiraApi.str_jira_scheduled)

  def connect(self):
    options = {'server': app.config['JIRA_HOSTNAME'], 'verify': False, 'check_update': False}
    self.instance = JIRA(options,
                basic_auth=(app.config['JIRA_USERNAME'], app.config['JIRA_PASSWORD']))
    self.approver_instance = JIRA(options,
                basic_auth=(app.config['JIRA_APPROVER_USERNAME'], app.config['JIRA_APPROVER_PASSWORD']))

  @staticmethod
  def ticket_link(issue):
    return '<a href="{}/browse/{}">{}</a>'.format(app.config['JIRA_HOSTNAME'], issue.key, issue.key)

  def resolve(self, issue):
    self.instance.transition_issue(
      issue,
      app.config['JIRA_RESOLVE_TRANSITION_ID'],
      assignee={'name': app.config['JIRA_USERNAME']},
      resolution={'id': app.config['JIRA_RESOLVE_STATE_ID']})

  def defect_for_exception(self, summary_title, e):
    return self.instance.create_issue(
      project=app.config['JIRA_PROJECT'],
      summary='[auto-{}] Problem: {}'.format(current_user.username, summary_title),
      description="Exception: {}".format(e),
      customfield_13842=JiraApi.get_datetime_now(),
      customfield_13838= {"value": "No"},
      customfield_13831 =  [
        {"value": "Quality"},
        {"value": "Risk Avoidance"}
      ],
      issuetype={'name': 'Defect'})