# Jukebox with GPIO Buttons

Simple jukebox with Raspberry Pi. Songs will be played when buttons are pressed.

## Requirements
- `sudo apt install gpiozero vlc-bin vlc-plugin-base python3-rpi.gpio`
- ALSA volume defaults to 50%, crank it up with `alsamixer`. This is persistent.

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
python3 /path/to/jukebox.py > /dev/null 2>&1
```

## Notes
- For some reason `gpiozero`'s `when_pressed()` doesn't register button press properly, events are often missed. Older `RPi.GPIO` (v0.7) works much better and reliable.

## Open TODOs
- Make button blink on song playback, or
- some LED gimmick for fun

## References
- https://raspberrypi.stackexchange.com/a/94207

## Useful Development Tools
- `pinout` command from `gpiozero` package
- `gpio readall` from `wiringpi` package, to get GPIO readings. Call with `watch -n 0.1 gpio readall` to do 10Hz polling read.
