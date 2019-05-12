#! /usr/bin/env python3.6
import sys
import time
import pickle
import threading
import datetime

import RPi.GPIO as gpio
import nanohttp


__version__ = '0.1.0'
pwm = None


def total_status():
    return dict(
        power=power_model.status,
        light=light_model.status,
        coolendFan=coolendfan_model.status
    )


class Speed(int):
    @classmethod
    def fromdutycycle(cls, v):
        return cls((v - 30) * 100 / 70)

    def todutycycle(self):
        return (self * 70 / 100) + 30


class Pin:
    gpio = None

    def __init__(self, number, *a, **kw):
        self.gpio = number
        gpio.setup(number, *a, **kw)


class InputPin(Pin):
    oldvalue = None 

    def __init__(self, number, pull_updown=gpio.PUD_OFF):
        self.pull_updown = pull_updown
        super().__init__(number, gpio.IN, pull_up_down=pull_updown)
        self.reset()
    
    @property
    def high(self):
        return gpio.input(self.gpio)
    
    @property
    def changed(self):
        return self.oldvalue ^ self.high
    
    def reset(self):
        self.oldvalue = self.high

    
class OutputPin(Pin):
    def __init__(self, number, initial=False):
        self.ishigh = initial
        super().__init__(number, gpio.OUT, initial=initial)
    
    def render(self, status):
        gpio.output(self.gpio, status)
        self.ishigh = status

    def up(self):
        self.render(True)

    def down(self):
        self.render(False)
   
    @property
    def status(self):
        return dict(isHigh=self.ishigh)


class Relay(OutputPin):
    def __init__(self, settings):
        super().__init__(settings.gpio)
        
    def on(self):
        self.down()

    def off(self):
        self.up()
    
    @property
    def ison(self):
        return not self.ishigh

    @property
    def status(self):
        result = super().status
        result.update(dict(
            on=self.ison
        ))
        return result


class Fan(OutputPin):
    _ison = True 
    
    def __init__(self, settings):
        super().__init__(settings.gpio)
        self.frequency = settings.frequency
        self.speed = settings.speed
        self.pwm = gpio.PWM(self.gpio, self.frequency)
        if self._ison:
            self.on()
    
    @property
    def dutycycle(self):
        return Speed(self.speed).todutycycle()
    
    def on(self):
        self.pwm.start(self.dutycycle)
        self._ison = True
    
    def off(self):
        self.pwm.stop()
        self.down()
        self._ison = False
        
    def control(self, speed):
        self.speed = speed
        self.pwm.ChangeDutyCycle(Speed(speed).todutycycle())

    @property
    def status(self):
        result = super().status
        result.update(dict(
            speed=self.speed,
            frequency=self.frequency,
            dutyCycle=self.dutycycle,
            on=self._ison
        ))
        return result


class ModelController(nanohttp.RestController):
    def __init__(self, model):
        self.model = model


class CoolendFanController(ModelController):
   
    @nanohttp.json
    def get(self):
        return self.model.status 

    @nanohttp.json
    def start(self):
        self.model.on()
        return self.model.status 

    @nanohttp.json
    def stop(self):
        self.model.off()
        return self.model.status 

    @nanohttp.json
    def update(self):
        value = nanohttp.context.form.get('speed')

        if value is None:
            value = nanohttp.context.query.get('speed')

        if value is None:
            raise nanohttp.HTTPBadRequest('speed field is required')

        self.model.control(value)
        return self.model.status 


class RelayController(ModelController):
    @nanohttp.json
    def get(self):
        return total_status()

    @nanohttp.json
    def on(self):
        self.model.on()
        return total_status()

    @nanohttp.json
    def off(self):
        self.model.off()
        return total_status()


def worker():
    shuttingdown = None
    c = nanohttp.settings.worker
    delay = c.shutdown_delay
    interval = c.interval
    
    print('Starting Pinky worker')
    while True:
        if closing:
            break

        if m82_model.changed:
            m82_model.reset()
            print(f'M82 pin is changed: {m82_model.high}')

            if m82_model.high:
                if not power_model.ison:
                    print(f'Turning on main power')
                    power_model.on()
                
                if not light_model.ison:
                    print(f'Turning light on')
                    light_model.on()
            else:
                shuttingdown = datetime.datetime.now() \
                    if power_model.ison else None
            
        if shuttingdown is not None:
            remaining = int(
                    delay - (datetime.datetime.now() - shuttingdown).total_seconds()
                )
            print(f'Shutting down in {remaining} seconds')
            if remaining <= 0:
                power_model.off()
                light_model.off()
                shuttingdown = None

        time.sleep(interval)


BUILTIN_SETTINGS = '''
listen:
  host: 0.0.0.0
  port: 80
power:
  gpio: 24
light:
  gpio: 26
coolend:
  fan:
    speed: 90
    gpio: 16
    frequency: 1000
m82:
  gpio: 18 
worker:
  interval: 2 
  shutdown_delay: 4 
'''


def initialize_gpio():
    global coolendfan_model, power_model, light_model, m82_model
    c = nanohttp.settings

    # GPIO Initialization
    gpio.setwarnings(False)
    gpio.setmode(gpio.BOARD)
    
    coolendfan_model = Fan(c.coolend.fan)
    power_model = Relay(c.power)
    light_model = Relay(c.light)
    m82_model = InputPin(c.m82.gpio, pull_updown=gpio.PUD_UP)


def configure(filename=None):
    nanohttp.configure(BUILTIN_SETTINGS)

    if filename:
        nanohttp.settings.load_file(filename)


def main():
    global closing
    closing = False
    configure(None if len(sys.argv) <= 1 else sys.argv[1])
    initialize_gpio()
    
    # Start background thread
    worker_ = threading.Thread(target=worker, daemon=True, name='pinky-worker')
    worker_.start()

    class Root(nanohttp.Controller):
        coolendfan = CoolendFanController(coolendfan_model)
        power = RelayController(power_model)
        light = RelayController(light_model)

        @nanohttp.json
        def index(self):
            return total_status()

    listen = nanohttp.settings.listen
    try: 
        nanohttp.quickstart(Root(), host=listen.host, port=listen.port) 
    finally:
        closing = True
        worker_.join()


if __name__ == '__main__':
    main()
