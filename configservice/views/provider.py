import flask
from flask.views import MethodView
from conf.appconfig import SCHEMA_ROOT_V1, MIME_JSON, \
    CONFIG_PROVIDERS
from configservice.services.config import get_providers_meta_info, \
    get_provider_types
from configservice.views import hypermedia
from configservice.views.util import build_response


class ProviderApi(MethodView):

    """
    Provider API
    """

    @hypermedia.produces({
        MIME_JSON: SCHEMA_ROOT_V1
    }, default=MIME_JSON)
    def get(self, name=None, **kwargs):
        """
        Lists all providers.

        :param kwargs:
        :return:
        """
        provider_types = get_provider_types()
        if name:
            if name not in provider_types:
                flask.abort(404)
            else:
                provider = CONFIG_PROVIDERS[name]['meta-info']
                return build_response(provider)
        else:
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
