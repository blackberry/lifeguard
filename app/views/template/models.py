from jinja2 import BaseLoader, TemplateNotFound

class ObjectLoader(BaseLoader):

  def get_source(self, environment, obj):
    return obj, None, None