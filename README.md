# Jukebox with GPIO Buttons

Simple jukebox with Raspberry Pi. Songs will be played when buttons are pressed.

## Requirements
- `sudo apt install gpiozero python3-vlc vlc-bin vlc-plugin-base python3-rpi.gpio`
- ALSA volume defaults to 50%, crank it up with `alsamixer`. This is persistent.

## Tested on
- Raspberry Pi 1 (2011). 3.5mm Audio Output FTW!
- Raspbian v10 (Buster) (`cat /etc/os-release`)
- `python3-vlc` v3.0.4106

## Hardware and Wiring
1. Get Raspberry Pi
2. Get push buttons with LEDs and wire them properly with resistors
3. Use `gpio readall` and `pinout` to find out pin numbering (see "Useful Development Tools" below)
4. Configure the BCM pin numbering for the buttons and LEDs(from `gpio readall`) in `jukebox.py` script

## Usage
- clone repo
- add `mp3` files into `music` folder
- start the script: `python3 jukebox.py`
- or make it autostart with adding this entry to `/etc/rc.local`

```bash
su pi -c "python3 /path/to/jukebox.py > /dev/null 2>&1"
```

## Notes
- For some reason `gpiozero`'s `when_pressed()` doesn't register button press properly, events are often missed. Older `RPi.GPIO` (v0.7) works much better and reliable.

## Open TODOs
- Organize the files like a proper Python project
- Generalize method to playback song X on button press Y, so that user can skip button order
- Make button blink on song playback, or
- some LED gimmick for fun
- check if `python3-vlc` apt package is enough or are the following packages really required `vlc-bin vlc-plugin-base`

## References
- https://raspberrypi.stackexchange.com/a/94207

## Useful Development Tools
- `pinout` command from `gpiozero` package
- `gpio readall` from `wiringpi` package, to get GPIO readings. Call with `watch -n 0.1 gpio readall` to do 10Hz polling read.

## Interesting Similar Projects
- From: https://raspberrytips.com/play-spotify-on-raspberry-pi/#Play_Spotify_with_MusicBox
    - https://volumio.org/
    - https://www.pimusicbox.com/
    - https://mopidy.com/