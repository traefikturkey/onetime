from enum import Enum
from typing import Set
from jinja2 import Environment, FileSystemLoader


class docker:
  class ActionType(Enum):
    START = 1
    STOP = 2

  class Event:
    def __init__(self, fqdn_name: str, action_type):
      self._fqdn_name = fqdn_name
      self._action_type = action_type

    @property
    def fqdn_name(self) -> str:
      return self._fqdn_name

    @property
    def action_type(self):
      return self._action_type


class CorefileGenerator:
  def __init__(self, template_path: str):
    self.template_path = template_path
    self.active_fqdns: Set[str] = set()
    self.env = Environment(loader=FileSystemLoader('templates'))

  def process_event(self, event: docker.Event):
    fqdn_name = event.fqdn_name
    action_type = event.action_type

    if action_type == docker.ActionType.START:
      self.active_fqdns.add(fqdn_name)
    elif action_type == docker.ActionType.STOP:
      self.active_fqdns.discard(fqdn_name)

  def generate_corefile(self, output_path: str):
    template = self.env.get_template('Corefile.template')
    corefile_content = template.render(active_fqdns=self.active_fqdns)

    with open(output_path, 'w') as corefile:
      corefile.write(corefile_content)
