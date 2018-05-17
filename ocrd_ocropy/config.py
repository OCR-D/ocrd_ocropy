import json

from pkg_resources import resource_string

OCRD_OCROPY_TOOL = json.loads(resource_string(__name__, 'ocrd-tool.json'))
