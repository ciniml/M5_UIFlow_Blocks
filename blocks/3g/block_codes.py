
# start

import sys

if '/flash/res' not in sys.path:
    sys.path.append('/flash/res')

from gsm import Soracom3G, GSM
soracom_3g = Soracom3G()
soracom_3g.start('soracom.io', 'sora', 'sora')

# state
soracom_3g.state()

# wait_connected

while True:
    state = soracom_3g.wait_values()
    print(state)
    if state['state'] == GSM.STATE_CONNECTED:
        break

# disconnect_wlan

import network

if 'disconnect_wlan' not in locals():
    def disconnect_wlan():
        try:
            w = network.WLAN()
            w.disconnect()
        except: # OSError
            pass
disconnect_wlan()

# get_ifconfig
soracom_3g.values().get('ifconfig')

# get_ipaddr
soracom_3g.values().get('ifconfig', (None,))[0]

