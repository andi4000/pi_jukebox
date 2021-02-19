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
from typing import List, Union

import pkg_resources
from appdirs import AppDirs  # type: ignore

try:
    import RPi.GPIO as GPIO  # type: ignore
except (RuntimeError, ModuleNotFoundError):
    import Mock.GPIO as GPIO  # type: ignore

import vlc  # type: ignore

from .button_handler import ButtonHandler


class PiJukebox:
    IS_DEBUG = False
    LOOP_HZ = 20

    DEFAULT_MUSIC_FOLDER_NAME = "pi_jukebox"
    DEFAULT_CONFIG_FILENAME = "pi_jukebox.conf"

    def __init__(self):
        # IO Definitions
        self.pin_tailswitch = -1
        self.pin_buttons: List[int] = []
        self.pin_leds: List[int] = []
        self.btn_bounce_time_ms = -1

        self.song_end_position = -1.0  # for VLC get_position()

        self._vlc_instance: vlc.Instance = None
        self._player: vlc.MediaPlayer = None

        self._active_song_idx: Union[None, int] = None

        # to hold mp3 file paths
        self._songs: List[str] = []

    @staticmethod
    def _init_music_folder(config: configparser.ConfigParser):
        if not config.has_option("default", "music_folder"):
            logging.error(
                "Invalid config file! Remove config file and let me recreate it."
            )
            sys.exit(-1)

        music_folder = config["default"]["music_folder"]

        if os.path.isdir(music_folder):
            logging.info("Music folder found: %s", music_folder)
        else:
            logging.info("Music folder nonexistent, creating: %s", music_folder)
            os.makedirs(music_folder)

    def _init_gpio(self, config: configparser.ConfigParser):
        logging.info("Initializing GPIO")

        self._load_gpio_config(config)

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        GPIO.setup(self.pin_leds, GPIO.OUT)
        GPIO.output(self.pin_leds, [False] * len(self.pin_leds))  # Turn off all LEDs

        GPIO.setup(self.pin_buttons, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        logging.info("GPIO Pins initialized")

    def _init_music_player(self, config: configparser.ConfigParser):
        self._load_player_config(config)

        logging.info("Initializing VLC")
        self._vlc_instance = vlc.Instance("--aout=alsa")
        self._player = self._vlc_instance.media_player_new()
        self._player.audio_set_volume(100)
        logging.info("VLC initialized")

    def _load_gpio_config(self, config: configparser.ConfigParser):
        assert "GPIO" in config

        self.pin_buttons = json.loads(config.get("GPIO", "pin_buttons"))
        self.pin_leds = json.loads(config.get("GPIO", "pin_leds"))
        self.pin_tailswitch = config["GPIO"].getint("pin_tailswitch")
        self.btn_bounce_time_ms = config["GPIO"].getint("bounce_time_ms")

        logging.debug("GPIO configurations:")
        logging.debug("PIN_BUTTONS: %s", str(self.pin_buttons))
        logging.debug("PIN_LEDS: %s", str(self.pin_leds))

    def _load_player_config(self, config: configparser.ConfigParser):
        assert "player" in config
        self.song_end_position = config["player"].getfloat("song_end_position")

    @staticmethod
    def _find_songs(music_folder: str) -> list:
        if not os.path.isdir(music_folder):
            raise FileNotFoundError(f"Music folder does not exists: {music_folder}")

        # TODO: add support for other audio files
        found_files = glob.glob(f"{music_folder}/*.mp3")

        logging.info("Found %d songs", len(found_files))
        logging.debug("found following files: %s", str(found_files))
        found_files.sort()
        return found_files

    def _init_songs_button_binding(self, config: configparser.ConfigParser):
        logging.info("Initializing songs")

        music_folder = config["default"]["music_folder"]

        self._songs = self._find_songs(music_folder)

        # TODO: figure out if lifecycle of this could cause problem
        button_handlers = []

        for i, song in enumerate(self._songs):
            if i >= len(self.pin_buttons):
                logging.info("Ignoring song because no button left: %s", song)
                continue

            logging.info("Initializing button for %s", song)

            # Wrapper for button callback, workaround for buggy GPIO library
            # "falling" because of the Pull-Up (button state defaults to 1)
            button_handlers.append(
                ButtonHandler(
                    self.pin_buttons[i],
                    self._cb_buttonpress,
                    edge="falling",
                    bouncetime=self.btn_bounce_time_ms,
                )
            )

            # bouncetime here is buggy, therefore extra callback wrapper ButtonHandler
            GPIO.add_event_detect(
                self.pin_buttons[i],
                GPIO.RISING,
                callback=button_handlers[i],
                bouncetime=10,
            )

            GPIO.output(self.pin_leds[i], True)
            sleep(0.1)
            GPIO.output(self.pin_leds[i], False)

    def _play_song(self, song_path: str):
        logging.info("playing media: %s", str(song_path))
        self._player.stop()
        self._player.set_media(self._vlc_instance.media_new(song_path))
        self._player.play()

        if self.IS_DEBUG:
            self._player.set_position(0.97)

    def _stop_playback(self):
        """wrapper for vlc.stop()"""
        self._player.stop()

    def _cb_buttonpress(self, channel: int):
        """
        Logic for playing song, considering the status of playback (is currently
        playing or not)
        """
        idx = self.pin_buttons.index(channel)
        logging.debug("button press %d", idx)

        assert idx < len(self._songs), f"song index non-existent: {idx}"
        song_path = self._songs[idx]

        if self._active_song_idx is None:
            logging.info("Playing new song #%d", idx)
            self._active_song_idx = idx
            self._play_song(song_path)
        elif self._active_song_idx is idx:
            if self._player.is_playing():
                logging.info("Stopping active playback")
                self._active_song_idx = None
                self._stop_playback()
        else:
            logging.info("Stopping playback and playing new song #%d", idx)
            self._active_song_idx = idx
            self._play_song(song_path)

    def _shutdown_routine(self):
        logging.debug("Turning off LEDS and shutting down")
        GPIO.output(self.pin_leds, [False] * len(self.pin_leds))
        GPIO.cleanup()

    def _is_song_ending(self, song_end_position: float) -> bool:
        assert song_end_position > 0.0

        is_song_ending = False
        song_position = self._player.get_position()
        logging.debug("song position = %.4f", song_position)
        # value between 0.0 and 1.0
        # -1 means playback is stopped

        if song_position > song_end_position:
            is_song_ending = True

        return is_song_ending

    def _loop_routine(self):
        """
        Routine for each loop, sets LED status based on playback status (playing or
        ends)
        """
        led_states = [False] * len(self.pin_leds)

        if self._active_song_idx is not None:
            if self._is_song_ending(self.song_end_position):
                logging.info("Song reaches end")
                self._active_song_idx = None
            else:
                led_states[self._active_song_idx] = True

        GPIO.output(self.pin_leds, led_states)

    def _get_default_config_file(self) -> str:
        app_name = __name__.split(".")[0]
        dirs = AppDirs(appname=app_name)

        # On Linux: $HOME/.config/pi_jukebox/pi_jukebox.conf
        str_config_file = dirs.user_config_dir + "/" + self.DEFAULT_CONFIG_FILENAME

        return str_config_file

    def _create_initial_config_file(self, str_config_file: str):
        """
        Create initial config file with only one field: music_folder
        Defaults to $HOME/pi_jukebox
        """
        logging.info("Creating initial config file..")

        default_config_file = pkg_resources.resource_filename(
            __name__, "config/default.conf"
        )

        config = configparser.ConfigParser()

        config.read(default_config_file)
        assert "default" in config
        assert "player" in config
        assert "GPIO" in config

        str_music_folder = (
            os.path.expanduser("~") + "/" + self.DEFAULT_MUSIC_FOLDER_NAME
        )

        config["default"] = {}
        config["default"]["music_folder"] = str_music_folder

        os.makedirs(os.path.dirname(str_config_file), exist_ok=True)

        with open(str_config_file, "w") as file_obj:
            config.write(file_obj)

        logging.info("Config file created: %s", str_config_file)

    def init(self):
        logging_level = logging.INFO
        if self.IS_DEBUG:
            logging_level = logging.DEBUG

        logging.basicConfig(
            format="%(asctime)s %(levelname)s %(message)s", level=logging_level
        )

        config_file = self._get_default_config_file()

        version = pkg_resources.get_distribution("pi_jukebox").version
        logging.info("Initializing pi_jukebox v%s", version)

        if os.path.isfile(config_file):
            logging.info("Config file found: %s", config_file)
        else:
            self._create_initial_config_file(config_file)

        config = configparser.ConfigParser()
        config.read(config_file)

        self._init_music_folder(config)
        self._init_gpio(config)
        self._init_music_player(config)
        self._init_songs_button_binding(config)
        logging.info("Jukebox ready")

    def run(self):
        logging.info("Entering main loop")
        while True:
            try:
                self._loop_routine()
                sleep(1.0 / float(self.LOOP_HZ))
            except KeyboardInterrupt:
                logging.info("Exiting program")
                self._shutdown_routine()
                sys.exit()
