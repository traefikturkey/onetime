import os
import docker
import re
import threading
from typing import Set


class DockerMonitor:
  is_manager: bool = False
  host_ip: str
  active_names: Set[str] = set()
  _stop_event = threading.Event()

  def __init__(self):
    self.client = docker.from_env()
    self.host_ip = os.environ.get('HOSTIP', '127.0.0.1')
    self.get_running_containers_with_traefik_labels()

  def update_core_dns(self, host_ip, fqdns):
    print("Updating CoreDNS with new FQDNs...")

  def extract_fqdns_from_labels(self, container, action):
    labels = container.labels
    traefik_host_labels = {k: v for k, v in labels.items() if k.startswith('traefik.http.routers.')}
    onetime_enabled = any(label.startswith('onetime.enabled=false') for label in labels)
    if not onetime_enabled:
      return False

    changed = False
    for _, label_value in traefik_host_labels.items():
      match = re.search(r'rule=Host\(`(.+?)`\)', label_value)
      if match and match.group(1).strip() not in self.active_names:
        fqdn = match.group(1).strip()
        if action == 'start' and fqdn not in self.active_names:
          self.active_names.add(fqdn)
          changed = True
        if action == 'stop' and fqdn in self.active_names:
          self.active_names.discard(fqdn)
          changed = True
    return changed

  def event_callback(self, event):
    container_name = event['Actor']['Attributes']['name']
    container = self.client.containers.get(container_name)
    changed = self.extract_fqdns_from_labels(container, event['Action'])
    if changed:
      self.update_core_dns(self.host_ip, self.active_names)

  def get_running_containers_with_traefik_labels(self):
    for container in self.client.containers.list(filters={'status': 'running'}):
      if 'coredns' in container.image.tags:
        self.is_manager = True
        next
      self.extract_fqdns_from_labels(container, 'start')
    self.update_core_dns(self.host_ip, self.active_names)

  def start(self):
    print("Listening for Docker events...")
    event_thread = threading.Thread(target=self.event_loop)
    event_thread.start()
    return event_thread

  def stop(self):
    self._stop_event.set()

  def event_loop(self):
    while not self._stop_event.is_set():
      try:
        events = self.client.events(decode=True)
        for event in events:
          if self._stop_event.is_set():
            break
          self.event_callback(event)
          events.close()
      except KeyboardInterrupt:
        self.stop()
        break
