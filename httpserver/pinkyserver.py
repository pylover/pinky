#! /usr/bin/env python3.6
import sys
import pickle

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


class OutputPin:
    def __init__(self, io_, initial=False):
        self.gpio = io_
        self.ishigh = initial
        gpio.setup(self.gpio, gpio.OUT, initial=initial)
    
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
    def status(self):
        result = super().status
        result.update(dict(
            on=not self.ishigh
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

'''

def configure(filename=None):
    global coolendfan_model, power_model, light_model
    nanohttp.configure(BUILTIN_SETTINGS)

    if filename:
        nanohttp.settings.load_file(filename)

    # GPIO Initialization
    gpio.setwarnings(False)
    gpio.setmode(gpio.BOARD)
    
    coolendfan_model = Fan(nanohttp.settings.coolend.fan)
    power_model = Relay(nanohttp.settings.power)
    light_model = Relay(nanohttp.settings.light)


if __name__ == '__main__':
    configure(None if len(sys.argv) <= 1 else sys.argv[1])

    class Root(nanohttp.Controller):
        coolendfan = CoolendFanController(coolendfan_model)
        power = RelayController(power_model)
        light = RelayController(light_model)

        @nanohttp.json
        def index(self):
            return total_status()


    listen = nanohttp.settings.listen
    nanohttp.quickstart(Root(), host=listen.host, port=listen.port) 

