# Jukebox with GPIO Buttons

## Requirements
- `sudo apt install gpiozero vlc-bin vlc-plugin-base`
- ALSA volume defaults to 50%, crank it up with `alsamixer`. This is persistent.

## References
- https://raspberrypi.stackexchange.com/a/94207

## Useful Development Tools
- `pinout` command from `gpiozero` package
- `gpio readall` from `wiringpi` package, to get GPIO readings. Call with `watch -n 1 gpio readall` to do 1s polling read.
