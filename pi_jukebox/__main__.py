#!/usr/bin/env python3

from .pi_jukebox import PiJukebox

if __name__ == "__main__":
    app = PiJukebox()
    app.init()
    app.run()
