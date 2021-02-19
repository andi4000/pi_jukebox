#!/usr/bin/env python3

import sys
from .pi_jukebox import PiJukebox


def main():
    app = PiJukebox()
    app.init()
    app.run()


if __name__ == "__main__":
    sys.exit(main())
