#!/usr/bin/python3 -I
import sys
sys.path.insert(0, "/usr/local/lib/nostromo")
from campaigns.host import Window
Window("/var/lib/nostromo-campaign-broker/squad-window").expire()
