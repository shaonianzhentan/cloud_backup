import os
from homeassistant.util.json import load_json

class Manifest():

    def __init__(self, domain):
        self.domain = domain
        self.manifest_path = self.custom_components_path(f'{domain}/manifest.json')
        self.update()

    def custom_components_path(self, file_path):
        return os.path.abspath('./custom_components/' + file_path)

    def update(self):
        data = load_json(self.manifest_path)
        self.name = data.get('name')
        self.version = data.get('version')
        self.documentation = data.get('documentation')

manifest = Manifest('cloud_backup')