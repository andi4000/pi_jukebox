#!/usr/bin/env python3

from gpiozero import Button
from signal import pause
from time import sleep
import logging

import vlc

SONG = "music/beetje_bang.mp3"

logging.basicConfig(level=logging.DEBUG)

logging.info("initializing")

vlc_instance = vlc.Instance('--aout=alsa')

player = vlc_instance.media_player_new()
player.audio_set_volume(100)

def action_1():
    if player.is_playing():
        logging.info("stopping playback")
        player.stop()
    else:
        logging.info("loading media and playing")
        player.set_media(vlc_instance.media_new(SONG))
        player.stop()
        player.play()


btn = Button(18)
btn.when_pressed = action_1

logging.info("ready")
pause()
