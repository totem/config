import flask
from flask.views import MethodView
from conf.appconfig import MIME_JSON, MIME_YAML, \
    SCHEMA_CONFIG_META_V1

from configservice.services import config
from configservice.services.config import get_provider_types
from configservice.util import dict_merge
from configservice.views import hypermedia
from configservice.views.util import build_response


class ConfigApi(MethodView):
    """
    Config API
    """

    @hypermedia.produces({
        MIME_JSON: None,
        MIME_YAML: None
    }, default=MIME_JSON)
    def get(self, provider, groups, config_type, name, accept_mimetype=None,
            **kwargs):
        """
        Returns config for given provider, groups, config_type and name

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

    @hypermedia.consumes({
        MIME_JSON: SCHEMA_CONFIG_META_V1
    })
    @hypermedia.produces({
        MIME_JSON: None,
        MIME_YAML: None
    }, default=MIME_JSON)
    def post(self, provider, groups, name, accept_mimetype=None,
             request_data=None, **kwargs):
        """
        Generates evaluated config based on additional information specified in
        as part of request payload.
        :param kwargs:
        :return:
        """

        if provider not in get_provider_types():
            flask.abort(404)
        else:
            if groups == '_':
                groups = ''

            meta = dict_merge({
                'groups': [group for group in groups.split(',') if group],
                'name': name,
                'provider-type': provider,
                'evaluate':  True
            }, request_data)

            return build_response(
                config.load_config(meta=meta),
                mimetype=accept_mimetype)


def register(app, **kwargs):
    """
    Registers Config API

    :param app: Flask application
    :return: None
    """
    config_func = ConfigApi.as_view('config')
    for uri in ['/providers/<provider>/groups/<groups>/<config_type>/<name>']:
        app.add_url_rule(uri,  view_func=config_func, methods=['GET'])
    app.add_url_rule('/providers/<provider>/groups/<groups>/evaluated/<name>',
                     view_func=config_func, methods=['POST'])
