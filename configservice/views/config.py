import flask
from flask.views import MethodView
from conf.appconfig import SCHEMA_ROOT_V1, MIME_JSON, MIME_YAML

from configservice.services import config
from configservice.services.config import get_provider_types
from configservice.views import hypermedia
from configservice.views.util import build_response


class ConfigApi(MethodView):
    """
    Config API
    """

    @hypermedia.produces({
        MIME_JSON: SCHEMA_ROOT_V1,
        MIME_YAML: SCHEMA_ROOT_V1
    }, default=MIME_JSON)
    def get(self, provider, groups, config_type, name, accept_mimetype=None,
            **kwargs):
        """
        Lists all providers.

        :param kwargs:
        :return:
        """

        if provider not in get_provider_types():
            flask.abort(404)
        else:
            if groups == '_':
                groups = ''

            return build_response(config.load_config(
                meta={
                    'groups': [group for group in groups.split(',') if group],
                    'name': name,
                    'provider-type': provider,
                    'evaluate':  config_type.lower() == 'evaluated'
                }
            ), mimetype=accept_mimetype)


def register(app, **kwargs):
    """
    Registers Provider ('/providers')
    Only GET operation is available.

    :param app: Flask application
    :return: None
    """
    config_func = ConfigApi.as_view('config')
    for uri in ['/providers/<provider>/groups/<groups>/<config_type>/<name>']:
        app.add_url_rule(uri,  view_func=config_func, methods=['GET'])
