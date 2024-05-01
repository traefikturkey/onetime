import os
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class ReloadHandler(FileSystemEventHandler):
  def on_any_event(self, event):
    if event.is_directory:
      return
    elif event.event_type == 'created':
      print(f"Created file: {event.src_path}")
    elif event.event_type == 'modified':
      print(f"Modified file: {event.src_path}")
      self.reload()

  def reload(self):
    python = sys.executable
    args = sys.argv[:]
    print(f"Reloading {' '.join(args)}")
    args.insert(0, python)
    os.execvp(python, args)


def start_observer(paths):
  observer = Observer()
  event_handler = ReloadHandler()
  for path in paths:
    observer.schedule(event_handler, path, recursive=True)
  observer.start()
  return observer


if __name__ == "__main__":
  paths = ['.']
  observer = start_observer(paths)
  try:
    while True:
      pass
  except KeyboardInterrupt:
    observer.stop()
  observer.join()
