import docker
import time
import signal
import sys
import re

# Create a Docker client instance
client = docker.from_env()


# Define a callback function to handle events
def event_callback(event):
  if event["Action"] == "start":
    container_name = event["Actor"]["Attributes"]["name"]
    container = client.containers.get(container_name)
    labels = container.labels

    traefik_host_labels = {
      k: v for k, v in labels.items() if k.startswith("traefik.http.routers.")
    }

    if traefik_host_labels:
      fqdns = []
      for label_key, label_value in traefik_host_labels.items():
        match = re.search(r"rule=Host\(`(.+?)`\)", label_value)
        if match:
          fqdn = match.group(1)
          fqdns.append(fqdn)

      print(f"Container {container_name} started with Traefik FQDNs: {', '.join(fqdns)}")
    else:
      print(f"Container {container_name} started without Traefik host labels.")

  elif event["Action"] == "stop":
    print(f"Container {event['Actor']['Attributes']['name']} stopped.")


# Define a signal handler function
def signal_handler(signal, frame):
  print("Received signal, stopping event listener...")
  sys.exit(0)


# Set up signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Start listening for events
print("Listening for Docker events...")
try:
  for event in client.events(decode=True):
    event_callback(event)
    # Flush the output buffer to ensure the message is printed immediately
    time.sleep(0.1)
except KeyboardInterrupt:
  print("Keyboard interrupt received, stopping event listener...")
