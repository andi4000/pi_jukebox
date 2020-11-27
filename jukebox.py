#!/usr/bin/env python3

import RPi.GPIO as GPIO
from signal import pause
from time import sleep
import sys
import logging

IS_DEBUG = False
LOOP_HZ = 20

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
SONG_END_POSITION = 0.990  # for VLC get_position()

SONGS = [
        "music/beetje_bang.mp3",
        "music/fitlala.mp3",
        "music/hello_dangdut.mp3",
        "music/maja_tanz.mp3",
        "music/skj88.mp3"
        ]
## Songs END

logging_level = logging.INFO
if IS_DEBUG: logging_level = logging.DEBUG

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s",
        level=logging_level)

logging.info("Initializing GPIO")

g_led_states = [False] * len(PIN_LEDS)

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(PIN_LEDS, GPIO.OUT)
GPIO.output(PIN_LEDS, g_led_states)

GPIO.setup(PIN_BUTTONS, GPIO.IN, pull_up_down=GPIO.PUD_UP)
logging.info("GPIO Pins initialized")

logging.info("Initializing VLC")
import vlc
g_vlc_instance = vlc.Instance("--aout=alsa")
g_player = g_vlc_instance.media_player_new()
g_player.audio_set_volume(100)
logging.info("VLC initialized")

g_active_song_idx = None


def _play_song(song_path: str):
    logging.info(f"playing media: {song_path}")
    g_player.stop()
    g_player.set_media(g_vlc_instance.media_new(song_path))
    g_player.play()
    if IS_DEBUG: g_player.set_position(0.97)


def _cb(channel):
    global g_active_song_idx

    idx = PIN_BUTTONS.index(channel)
    logging.debug(f"button press {idx}")

    assert idx < len(SONGS), f"song index non-existent: {idx}"
    song_path = SONGS[idx]

    if g_active_song_idx is None:
        logging.info(f"Playing new song #{idx}")
        g_active_song_idx = idx
        _play_song(song_path)
    elif g_active_song_idx is idx:
        if g_player.is_playing():
            logging.info("Stopping active playback")
            g_player.stop()
            g_active_song_idx = None
    else:
        logging.info(f"Stopping playback and playing new song #{idx}")
        g_active_song_idx = idx
        _play_song(song_path)


def _shutdown_routine():
    logging.debug("Turning off LEDS")
    GPIO.output(PIN_LEDS, [False]*len(PIN_LEDS))


def main():
    global g_active_song_idx

    logging.info("Initializing songs")
    for i in range(len(SONGS)):
        logging.info(f"Initializing song {SONGS[i]}")
        GPIO.add_event_detect(PIN_BUTTONS[i], GPIO.RISING,
                callback=_cb, bouncetime=DEFAULT_BOUNCE_TIME_MS)
        GPIO.output(PIN_LEDS[i], True)
        sleep(0.1)
        GPIO.output(PIN_LEDS[i], False)

    logging.info("ready")

    while True:
        try:
            g_led_states = [False]*len(PIN_LEDS)

            if g_active_song_idx is not None:
                song_position = g_player.get_position()
                logging.debug(f"song position = {song_position:.4f}")
                if -1 < song_position < SONG_END_POSITION:
                    g_led_states[g_active_song_idx] = True
                elif song_position > SONG_END_POSITION:
                    logging.info("Song reaches end")
                    g_active_song_idx = None

            GPIO.output(PIN_LEDS, g_led_states)
            sleep(1.0/float(LOOP_HZ))
        except KeyboardInterrupt:
            logging.info("Exiting program")
            _shutdown_routine()
            sys.exit()

if __name__ == "__main__":
    main()
