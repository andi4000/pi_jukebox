#!/usr/bin/env python3
"""
Raspberry Pi Jukebox
"""

import configparser
import glob
import json
import logging
import os
import sys
from time import sleep
from typing import Union

import pkg_resources
from appdirs import AppDirs  # type: ignore

try:
    import RPi.GPIO as GPIO  # type: ignore
except RuntimeError:
    import Mock.GPIO as GPIO  # type: ignore

import vlc  # type: ignore

from .button_handler import ButtonHandler

IS_DEBUG = True
LOOP_HZ = 20

# IO Definitions
PIN_TAILSWITCH = -1
PIN_BUTTONS = []
PIN_LEDS = []
BTN_BOUNCE_TIME_MS = -1

DEFAULT_SONG_END_POSITION = 0.990  # for VLC get_position()
DEFAULT_MUSIC_FOLDER_NAME = "pi_jukebox"
DEFAULT_CONFIG_FILENAME = "pi_jukebox.conf"

g_vlc_instance = None  # type: vlc.Instance
g_player = None  # type: vlc.MediaPlayer

g_active_song_idx = None  # type: Union[None, int]
g_songs = []  # to hold mp3 file paths


def _init_gpio():
    logging.info("Initializing GPIO")

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    GPIO.setup(PIN_LEDS, GPIO.OUT)
    GPIO.output(PIN_LEDS, [False] * len(PIN_LEDS))  # Turn off all LEDs

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


def _find_songs(music_folder: str) -> list:
    if not os.path.isdir(music_folder):
        raise FileNotFoundError(f"Music folder does not exists: {music_folder}")

    # TODO: add support for other audio files
    found_files = glob.glob(f"{music_folder}/*.mp3")

    logging.info(f"Found {len(found_files)} songs")
    logging.debug(f"found following files: {found_files}")
    found_files.sort()
    return found_files


def _init_songs_button_binding(config: configparser.ConfigParser):
    global g_songs
    logging.info("Initializing songs")

    music_folder = config["default"]["music_folder"]

    g_songs = _find_songs(music_folder)

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
            ButtonHandler(
                PIN_BUTTONS[i],
                _cb_buttonpress,
                edge="falling",
                bouncetime=BTN_BOUNCE_TIME_MS,
            )
        )

        # bouncetime here is buggy, therefore extra callback wrapper ButtonHandler
        GPIO.add_event_detect(
            PIN_BUTTONS[i], GPIO.RISING, callback=button_handlers[i], bouncetime=10
        )

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
    GPIO.output(PIN_LEDS, [False] * len(PIN_LEDS))
    GPIO.cleanup()


def _is_song_ending(song_end_position: float) -> bool:
    is_song_ending = False
    song_position = g_player.get_position()
    logging.debug(f"song position = {song_position:.4f}")
    # value between 0.0 and 1.0
    # -1 means playback is stopped

    if song_position > song_end_position:
        is_song_ending = True

    return is_song_ending


def _loop_routine(config: configparser.ConfigParser):
    """
    Routine for each loop, sets LED status based on playback status (playing or
    ends)
    """
    global g_active_song_idx

    led_states = [False] * len(PIN_LEDS)

    song_end_position = config["player"].getfloat("song_end_position")
    assert abs(song_end_position - DEFAULT_SONG_END_POSITION) < 0.01

    if g_active_song_idx is not None:
        if _is_song_ending(song_end_position):
            logging.info("Song reaches end")
            g_active_song_idx = None
        else:
            led_states[g_active_song_idx] = True

    GPIO.output(PIN_LEDS, led_states)


def _get_default_config_file() -> str:
    str_config_file = ""

    app_name = __name__.split(".")[0]
    dirs = AppDirs(appname=app_name)

    # On Linux: $HOME/.config/pi_jukebox/pi_jukebox.conf
    str_config_file = dirs.user_config_dir + "/" + DEFAULT_CONFIG_FILENAME

    return str_config_file


def _create_initial_config_file(str_config_file: str):
    """
    Create initial config file with only one field: music_folder
    Defaults to $HOME/pi_jukebox
    """
    logging.info("Creating initial config file..")

    default_config_file = pkg_resources.resource_filename(__name__, "config/default.conf")

    config = configparser.ConfigParser()

    config.read(default_config_file)
    assert "default" in config
    assert "player" in config
    assert "GPIO" in config

    str_music_folder = os.path.expanduser("~") + "/" + DEFAULT_MUSIC_FOLDER_NAME

    config["default"] = {}
    config["default"]["music_folder"] = str_music_folder

    os.makedirs(os.path.dirname(str_config_file), exist_ok=True)

    with open(str_config_file, "w") as file_obj:
        config.write(file_obj)

    logging.info(f"Config file created: {str_config_file}")


def _load_GPIO_config(config: configparser.ConfigParser):
    global PIN_BUTTONS
    global PIN_LEDS
    global PIN_TAILSWITCH
    global BTN_BOUNCE_TIME_MS

    assert "GPIO" in config

    PIN_BUTTONS = json.loads(config.get("GPIO", "pin_buttons"))
    PIN_LEDS = json.loads(config.get("GPIO", "pin_leds"))
    PIN_TAILSWITCH = config["GPIO"].getint("pin_tailswitch")
    BTN_BOUNCE_TIME_MS = config["GPIO"].getint("bounce_time_ms")


def main():
    logging_level = logging.INFO
    if IS_DEBUG:
        logging_level = logging.DEBUG

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(message)s", level=logging_level
    )

    config_file = _get_default_config_file()

    if os.path.isfile(config_file):
        logging.info(f"Config file found: {config_file}")
    else:
        _create_initial_config_file(config_file)

    config = configparser.ConfigParser()
    config.read(config_file)

    if not config.has_option("default", "music_folder"):
        logging.error("Invalid config file! Remove config file and let me recreate it.")
        sys.exit(-1)

    music_folder = config["default"]["music_folder"]

    if os.path.isdir(music_folder):
        logging.info(f"Music folder found: {music_folder}")
    else:
        logging.info(f"Music folder nonexistent, creating: {music_folder}")
        os.makedirs(music_folder)

    _load_GPIO_config(config)
    _init_gpio()
    _init_music_player()
    _init_songs_button_binding(config)
    logging.info("Jukebox ready")

    while True:
        try:
            _loop_routine(config)
            sleep(1.0 / float(LOOP_HZ))
        except KeyboardInterrupt:
            logging.info("Exiting program")
            _shutdown_routine()
            sys.exit()
