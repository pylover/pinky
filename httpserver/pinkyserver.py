import pickle

import RPi.GPIO as gpio
import nanohttp


__version__ = '0.1.0'
pwm = None


class Speed(int):
    @classmethod
    def fromdutycycle(cls, v):
        return cls((v - 30) * 100 / 70)

    def todutycycle(self):
        return (self * 70 / 100) + 30


class CoolendFan(nanohttp.RestController):

    @nanohttp.json
    def get(self):
        return nanohttp.settings.coolend.fan.speed

    @nanohttp.json
    def start(self):
        pwm.start(Speed(nanohttp.settings.coolend.fan.speed).todutycycle())

    @nanohttp.json
    def stop(self):
        pwm.stop()
        io_ = nanohttp.settings.coolend.fan.gpio
        gpio.output(io_, False)
        
    @nanohttp.json
    def update(self):
        value = nanohttp.context.form.get('speed')

        if value is None:
            value = nanohttp.context.query.get('speed')

        if value is None:
            raise nanohttp.HTTPBadRequest('speed field is required')

        nanohttp.settings.coolend.fan.speed = value
        pwm.ChangeDutyCycle(Speed(value).todutycycle())


class Root(nanohttp.Controller):
    coolendfan = CoolendFan()

    @nanohttp.json
    def index(self):
        return dict(message='hello')


BUILTIN_SETTINGS = '''
coolend:
  fan:
    speed: 90
    gpio: 16
    pwm_frequency: 1000

'''

def configure(filename=None):
    global pwm
    nanohttp.configure(BUILTIN_SETTINGS)

    if filename:
        nanohttp.settings.load_file(filename)

    # GPIO Initialization
    fan = nanohttp.settings.coolend.fan
    gpio.setwarnings(False)
    gpio.cleanup(fan.gpio)
    gpio.setmode(gpio.BOARD)
    gpio.setup(fan.gpio, gpio.OUT, initial=False)
    pwm = gpio.PWM(fan.gpio, fan.pwm_frequency)


class PinkyServer(nanohttp.Application):
    __root__ = Root()


