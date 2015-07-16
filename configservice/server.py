from __future__ import absolute_import
from flask import Flask
from flask.ext.cors import CORS
from conf.appconfig import CORS_SETTINGS
from configservice.views import root, hypermedia, provider, config, error

app = Flask(__name__)

# app.config['PROPAGATE_EXCEPTIONS'] = True
hypermedia.register_schema_api(app).register_error_handlers(app)

if CORS_SETTINGS['enabled']:
    CORS(app, resources={'/*': {'origins': CORS_SETTINGS['origins']}})

for module in [root, provider, config, error]:
    module.register(app)
