#!/usr/bin/env python3

import RPi.GPIO as GPIO
from signal import pause
from time import sleep
import logging

## IO Definitions BEGIN
PIN_TAILSWITCH = 2
PIN_BUTTONS = [
        7,  # 0
        8,  # 1
        11, # 2
        9,  # 3
        10, # 4
        15, # 5
        14, # 6
        3   # 7
        ]

DEFAULT_BOUNCE_TIME_MS = 200

PIN_LEDS = [
        17, # 0
        18, # 1
        27, # 2
        22, # 3
        23, # 4
        24, # 5
        25, # 6
        4 # 7
        ]

## IO Definitions END

## Songs BEGIN
songs = [
        "music/beetje_bang.mp3",
        "music/fitlala.mp3",
        "music/hello_dangdut.mp3",
        "music/maja_tanz.mp3",
        "music/skj88.mp3"
        ]
## Songs END

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s",
        level=logging.DEBUG)

logging.info("Initializing GPIO")

led_states = [False] * len(PIN_LEDS)

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(PIN_LEDS, GPIO.OUT)
GPIO.output(PIN_LEDS, led_states)

GPIO.setup(PIN_BUTTONS, GPIO.IN, pull_up_down=GPIO.PUD_UP)
logging.info("GPIO Pins initialized")

logging.info("Initializing VLC")
import vlc
vlc_instance = vlc.Instance("--aout=alsa")
player = vlc_instance.media_player_new()
player.audio_set_volume(100)
logging.info("VLC initialized")

g_active_song_idx = None

def play_song(song_path):
    logging.info(f"playing media: {song_path}")
    player.stop()
    player.set_media(vlc_instance.media_new(song_path))
    player.play()


def cb(channel):
    global g_active_song_idx

    idx = PIN_BUTTONS.index(channel)
    logging.debug(f"button press {idx}")
    led_states[idx] = not led_states[idx]
    GPIO.output(PIN_LEDS[idx], led_states[idx])


for i in range(len(PIN_LEDS)):
    GPIO.add_event_detect(PIN_BUTTONS[i], GPIO.RISING,
            callback=cb, bouncetime=DEFAULT_BOUNCE_TIME_MS)

pause()
