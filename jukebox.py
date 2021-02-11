#!/usr/bin/env python3

import RPi.GPIO as GPIO
from time import sleep
import sys
import os
import glob
import logging
from button_handler import ButtonHandler
import vlc

IS_DEBUG = False
LOOP_HZ = 20

# IO Definitions BEGIN
PIN_TAILSWITCH = 2
PIN_BUTTONS = [
        7,   # 0
        8,   # 1
        11,  # 2
        9,   # 3
        10,  # 4
        15,  # 5
        14,  # 6
        3    # 7
        ]

DEFAULT_BOUNCE_TIME_MS = 100

PIN_LEDS = [
        17,  # 0
        18,  # 1
        27,  # 2
        22,  # 3
        23,  # 4
        24,  # 5
        25,  # 6
        4    # 7
        ]

# IO Definitions END

# Songs BEGIN
SONG_END_POSITION = 0.990  # for VLC get_position()
SONGS_DIR = "music"
# Songs END

g_vlc_instance = None
g_player = None

g_active_song_idx = None
g_songs = []  # to hold mp3 file paths


def _init_gpio():
    logging.info("Initializing GPIO")

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    GPIO.setup(PIN_LEDS, GPIO.OUT)
    GPIO.output(PIN_LEDS, [False]*len(PIN_LEDS))  # Turn off all LEDs

    GPIO.setup(PIN_BUTTONS, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    logging.info("GPIO Pins initialized")


def _init_music_player():
    global g_vlc_instance
    global g_player
    logging.info("Initializing VLC")
    g_vlc_instance = vlc.Instance("--aout=alsa")
    g_player = g_vlc_instance.media_player_new()
    g_player.audio_set_volume(100)
    logging.info("VLC initialized")


def _find_songs() -> list:
    pwd = os.path.dirname(os.path.realpath(__file__))
    found_files = glob.glob(f"{pwd}/{SONGS_DIR}/*.mp3")
    logging.info(f"Found {len(found_files)} songs")
    logging.debug(f"found following files: {found_files}")
    found_files.sort()
    return found_files


def _init_songs_button_binding():
    global g_songs
    logging.info("Initializing songs")
    g_songs = _find_songs()

    # TODO: figure out if lifecycle of this could cause problem
    button_handlers = []

    for i in range(len(g_songs)):
        if i >= len(PIN_BUTTONS):
            logging.info(f"Ignoring song because no button left: {g_songs[i]}")
            continue

        logging.info(f"Initializing button for {g_songs[i]}")

        # Wrapper for button callback, workaround for buggy GPIO library
        # "falling" because of the Pull-Up (button state defaults to 1)
        button_handlers.append(
                ButtonHandler(PIN_BUTTONS[i], _cb_buttonpress, edge="falling",
                              bouncetime=DEFAULT_BOUNCE_TIME_MS)
                )

        GPIO.add_event_detect(PIN_BUTTONS[i], GPIO.RISING,
                              callback=button_handlers[i])

        GPIO.output(PIN_LEDS[i], True)
        sleep(0.1)
        GPIO.output(PIN_LEDS[i], False)


def _play_song(song_path: str):
    logging.info(f"playing media: {song_path}")
    g_player.stop()
    g_player.set_media(g_vlc_instance.media_new(song_path))
    g_player.play()

    if IS_DEBUG:
        g_player.set_position(0.97)


def _stop_playback():
    """wrapper for vlc.stop()"""
    g_player.stop()


def _cb_buttonpress(channel):
    """
    Logic for playing song, considering the status of playback (is currently
    playing or not)
    """
    global g_active_song_idx
    global g_songs

    idx = PIN_BUTTONS.index(channel)
    logging.debug(f"button press {idx}")

    assert idx < len(g_songs), f"song index non-existent: {idx}"
    song_path = g_songs[idx]

    if g_active_song_idx is None:
        logging.info(f"Playing new song #{idx}")
        g_active_song_idx = idx
        _play_song(song_path)
    elif g_active_song_idx is idx:
        if g_player.is_playing():
            logging.info("Stopping active playback")
            g_active_song_idx = None
            _stop_playback()
    else:
        logging.info(f"Stopping playback and playing new song #{idx}")
        g_active_song_idx = idx
        _play_song(song_path)


def _shutdown_routine():
    logging.debug("Turning off LEDS and shutting down")
    GPIO.output(PIN_LEDS, [False]*len(PIN_LEDS))
    GPIO.cleanup()


def _is_song_ending() -> bool:
    is_song_ending = None
    song_position = g_player.get_position()
    logging.debug(f"song position = {song_position:.4f}")

    if -1 < song_position < SONG_END_POSITION:
        is_song_ending = False
    elif song_position > SONG_END_POSITION:
        is_song_ending = True

    assert is_song_ending is not None, "Error in determining song position"

    return is_song_ending


def _loop_routine():
    """
    Routine for each loop, sets LED status based on playback status (playing or
    ends)
    """
    global g_active_song_idx

    led_states = [False]*len(PIN_LEDS)

    if g_active_song_idx is not None:
        if _is_song_ending():
            logging.info("Song reaches end")
            g_active_song_idx = None
        else:
            led_states[g_active_song_idx] = True

    GPIO.output(PIN_LEDS, led_states)


def main():
    logging_level = logging.INFO
    if IS_DEBUG:
        logging_level = logging.DEBUG

    logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s",
                        level=logging_level)

    _init_gpio()
    _init_music_player()
    _init_songs_button_binding()
    logging.info("Jukebox ready")

    while True:
        try:
            _loop_routine()
            sleep(1.0/float(LOOP_HZ))
        except KeyboardInterrupt:
            logging.info("Exiting program")
            _shutdown_routine()
            sys.exit()


if __name__ == "__main__":
    main()
