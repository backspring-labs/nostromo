#!/usr/bin/python3 -I
import sys
sys.path.insert(0, "/usr/local/lib/nostromo")
from campaigns.host import startup_check
sys.exit(startup_check())
