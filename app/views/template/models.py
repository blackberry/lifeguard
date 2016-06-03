from jinja2 import BaseLoader, TemplateNotFound

class ObjectLoader(BaseLoader):

  def get_source(self, environment, obj):
    return obj, None, None

class VarParser():

  @staticmethod
  def parse_kv_strings_to_dict(*args):
    """
    Parse 1 or more string/dict objects containing template
    variables in a final dict object.

    Subsequent parameters will overwrite existing values if
    previously defined.

    String args can be none or blank and they will be skipped
    otherwise they are expected to be in key=val (one per line).

    Dict objects can be empty and they will be skipped,
    otherwise they are expected to be 1 level deep (cannot be
    nested).

    For example if zone vars are overwritten by cluster vars,
    which are overwritten by pool vars, which are overwritten
    by VM vars, call:

    parsed_vars = parse_kv_strings_to_dict(
      zone_vars,
      cluster_vars,
      pool_vars,
      vm_vars)

    :param args:
    :return:
    """
    parsed = {}
    for i in range(len(args)):
      if args[i] is None:
        continue
      if type(args[i]) is dict:
        for k, v in args[i].items():
          parsed[k] = v
      elif type(args[i]) is str:
        if args[i]  == "":
          continue
        for kv in args[i].split("\n"):
          k, v = kv.split("=", 2)
          parsed[k.strip()] = v.strip()
      else:
        raise Exception('arg {} is {} (not a string or dict)'
                        .format(i, type(args[i])))
    return parsed




