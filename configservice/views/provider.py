import flask
from flask.views import MethodView
from conf.appconfig import MIME_JSON, CONFIG_PROVIDERS, SCHEMA_PROVIDERS_V1, \
    SCHEMA_PROVIDER_V1, MIME_PROVIDER_V1, MIME_PROVIDERS_V1
from configservice.services.config import get_providers_meta_info, \
    get_provider_types
from configservice.views import hypermedia
from configservice.views.util import build_response


class ProviderApi(MethodView):

    """
    Provider API
    """

    def get(self, name=None):
        """
        Lists providers / fetches single provider information
        :param kwargs:
        :return:
        """
        if name:
            return self.get_provider(name)
        else:
            return self.list()

    @hypermedia.produces({
        MIME_JSON: SCHEMA_PROVIDER_V1,
        MIME_PROVIDER_V1: SCHEMA_PROVIDER_V1
    }, default=MIME_PROVIDER_V1)
    def get_provider(self, name, **kwargs):
        provider_types = get_provider_types()
        if name not in provider_types:
            flask.abort(404)
        else:
            provider = CONFIG_PROVIDERS[name]['meta-info']
            return build_response(provider)

    @hypermedia.produces({
        MIME_JSON: SCHEMA_PROVIDERS_V1,
        MIME_PROVIDERS_V1: SCHEMA_PROVIDERS_V1
    }, default=MIME_PROVIDERS_V1)
    def list(self, **kwargs):
        return build_response(get_providers_meta_info())


def register(app, **kwargs):
    """
    Registers Provider ('/providers')
    Only GET operation is available.

    :param app: Flask application
    :return: None
    """
    providers_func = ProviderApi.as_view('providers')
    for uri in ['/providers', '/providers/', '/providers/<name>',
                '/providers/<name>/']:
        app.add_url_rule(uri,  view_func=providers_func,
                         methods=['GET'])
