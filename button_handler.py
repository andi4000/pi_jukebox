#!/usr/bin/env python3
#
# Copied from: https://raspberrypi.stackexchange.com/a/76738
#

import threading

try:
    import RPi.GPIO as GPIO  # type: ignore
except RuntimeError:
    import Mock.GPIO as GPIO  # type: ignore


class ButtonHandler(threading.Thread):
    def __init__(self, pin, func, edge="both", bouncetime=200):
        super().__init__(daemon=True)

        self.edge = edge
        self.func = func
        self.pin = pin
        self.bouncetime = float(bouncetime) / 1000

        self.lastpinval = GPIO.input(self.pin)  # pylint: disable=E1111
        self.lock = threading.Lock()

    def __call__(self, *args):
        if not self.lock.acquire(blocking=False):
            return

        mythread = threading.Timer(self.bouncetime, self.read, args=args)
        mythread.start()

    def read(self, *args):
        pinval = GPIO.input(self.pin)  # pylint: disable=E1111

        # fmt: off
        if (
            (pinval == 0 and self.lastpinval == 1)
            and (self.edge in ["falling", "both"])
        ) or (
            (pinval == 1 and self.lastpinval == 0)
            and (self.edge in ["rising", "both"])
        ):
            self.func(*args)

        # fmt: on

        self.lastpinval = pinval
        self.lock.release()
