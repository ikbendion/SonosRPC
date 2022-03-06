from soco import discover
from soco import SoCo
from pypresence import Presence
import time
import random
print("[INIT] Initializing connections to discord and sonos")
sonos = SoCo('ipofsonos')        # Sonos IP, put it here.
client_id = 'noyouwontconnecttomyapp'  # Fake ID, put your real one here
RPC = Presence(client_id)  
RPC.connect()
start_time=time.time()
def get_track():
    print('[INFO] Getting Track info')
    track = sonos.get_current_track_info()
    return track

def update_rpc():
    while True:
        track = get_track()
        album = 'pic'+str(random.randrange(1,3))
        title = track['title']
        details = str('By: '+track['artist']+"  On: "+track['album'])
        RPC.update(state=str(details), details=str(title),large_image=album,start=start_time)
        print('[OK] Updated spotify RPC.')
        time.sleep(15)

update_rpc()
