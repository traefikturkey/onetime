import time
import signal
import sys
from docker_monitor import DockerMonitor

monitor = None


def signal_handler(received_signal: signal.Signals, frame):
  print(f"\nReceived signal: {signal.Signals(received_signal).name}, stopping event listener...")
  if monitor:
    monitor.stop()
  sys.exit(0)


def main():
    # Set up signal handlers
  signal.signal(signal.SIGTERM, signal_handler)
  signal.signal(signal.SIGINT, signal_handler)

  # Create a DockerMonitor instance
  global monitor
  monitor = DockerMonitor()

  # Start the event listener in a separate thread
  event_thread = monitor.start()

  try:
    # Keep the main thread alive
    while True:
      pass
  except KeyboardInterrupt:
    print("Keyboard interrupt received, stopping event listener...")
    monitor.stop()


if __name__ == "__main__":
  main()
