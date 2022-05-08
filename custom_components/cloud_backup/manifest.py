from .file_api import load_json, get_current_path

class Manifest():

    def __init__(self):
        self.update()

    def update(self):
        data = load_json(get_current_path('manifest.json'))
        self.domain = data.get('domain')
        self.name = data.get('name')
        self.version = data.get('version')
        self.documentation = data.get('documentation')

manifest = Manifest()