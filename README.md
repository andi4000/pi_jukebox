# Jukebox with GPIO Buttons

Simple jukebox with Raspberry Pi. Songs will be played when buttons are pressed.

## Background
My 3 y.o. kid likes to listen to music, but I couldn't find music player with
easy enough UI for her to operate by herself. I've got some free time after
work, so why not?

## Disclaimer
This is a home project, code is shit.

## Requirements
- `sudo apt install gpiozero python3-vlc vlc-bin vlc-plugin-base python3-rpi.gpio`
- ALSA volume defaults to 50%, crank it up with `alsamixer`. This is persistent.

## Tested on
- Raspberry Pi 1 (2011).
- Raspbian v10 (Buster) (`cat /etc/os-release`)
- `python3-vlc` v3.0.4106

## Hardware and Wiring
1. Get Raspberry Pi
2. Get push buttons with LEDs and wire them properly with resistors
3. Use `gpio readall` and `pinout` to find out pin numbering (see "Useful
   Development Tools" below)
4. Configure the BCM pin numbering for the buttons and LEDs(from `gpio readall`)
   in `jukebox.py` script

TODO: show my setup

## Installation
```bash
pip3 install git+ssh://git@gitlab.com/bagong/pi_jukebox#egg=pi_jukebox
```

## Usage
- Put mp3 files into to default location: `$HOME/pi_jukebox/`
- Music location is configurable in `$HOME/.config/pi_jukebox/pi_jukebox.conf`
- Start jukebox:
```bash
pi_jukebox
```

- or make it autostart with adding this entry to `/etc/rc.local` before `exit 0`

```bash
su pi -c "pi_jukebox > /dev/null 2>&1"
```

## Notes
- For some reason `gpiozero`'s `when_pressed()` doesn't register button press
  properly, events are often missed. Older `RPi.GPIO` (v0.7) works much better
  and reliable.

## References
- https://raspberrypi.stackexchange.com/a/94207

## Useful Development Tools
- `pinout` command from `gpiozero` package
- `gpio readall` from `wiringpi` package, to get GPIO readings. Call with `watch
  -n 0.1 gpio readall` to do 10Hz polling read.
