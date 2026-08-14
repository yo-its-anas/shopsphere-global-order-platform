import asyncio
import json
import logging
import sys
from time import sleep

import httpx2

logger = logging.getLogger(__name__)

# Keycloak settings for local port forwarding or kind service access
# Since this script runs on the host, we should hit the api-gateway via port-forwarding or just use kubectl exec to curl internally.
# It's easier to run a kubectl exec bash script from within the api-gateway pod itself or another pod.
