
import nanohttp


__version__ = '0.1.0'


class Root(nanohttp.Controller):

    @nanohttp.json
    def index(self):
        return dict(message='hello')


nanohttp.configure()
app = nanohttp.Application(Root())

