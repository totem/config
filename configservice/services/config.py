import json
from parser import ParserError
from yaml.error import MarkedYAMLError
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, filter, map, zip)

from jsonschema.exceptions import SchemaError
import repoze.lru
from conf.appconfig import CONFIG_PROVIDERS, CONFIG_PROVIDER_LIST, API_PORT
from configservice.cluster_config.effective import MergedConfigProvider
from configservice.cluster_config.etcd import EtcdConfigProvider
from configservice.cluster_config.github import GithubConfigProvider
from configservice.cluster_config.s3 import S3ConfigProvider
from configservice.services.exceptions import ConfigProviderNotFound, \
    ConfigParseError
from configservice.util import dict_merge


__author__ = 'sukrit'


def get_provider_types():
    for provider_type in CONFIG_PROVIDER_LIST:
        provider_type = provider_type.strip()
        if provider_type in CONFIG_PROVIDERS:
            yield provider_type


def get_providers_meta_info():
    return [CONFIG_PROVIDERS[provider_type]['meta-info']
            for provider_type in get_provider_types()]


def _get_effective_provider():
    """
    Gets the effective config provider.

    :return: Effective Config provider.
    :rtype: orchestrator.cluster_config.effective.MergedConfigProvider
    """
    providers = list()
    for provider_type in get_provider_types():
        if provider_type not in ('effective', 'default'):
            provider = get_provider(provider_type)
            if provider:
                providers.append(provider)

    if CONFIG_PROVIDERS['effective']['cache']['enabled']:
        cache_provider = _get_etcd_provider(
            ttl=CONFIG_PROVIDERS['effective']['cache']['ttl'])
    else:
        cache_provider = None
    return MergedConfigProvider(*providers, cache_provider=cache_provider)


def _get_etcd_provider(ttl=None):
    """
    Gets the etcd config provider.

    :keyword ttl: time to live in seconds
    :type ttl: number
    :return: Instance of EtcdConfigProvider
    :rtype: EtcdConfigProvider
    """
    return EtcdConfigProvider(
        etcd_host=CONFIG_PROVIDERS['etcd']['host'],
        etcd_port=CONFIG_PROVIDERS['etcd']['port'],
        config_base=CONFIG_PROVIDERS['etcd']['base']+'/config',
        ttl=ttl
    )


def _get_s3_provider():
    """
    Gets S3 Config Provider

    :return: Instance of S3ConfigProvider
    :rtype: S3ConfigProvider
    """
    return S3ConfigProvider(
        bucket=CONFIG_PROVIDERS['s3']['bucket'],
        config_base=CONFIG_PROVIDERS['s3']['base']
    )


def _get_github_provider():
    """
    Gets Github Config Provider

    :return: Instance of GithubConfigProvider
    :rtype: GithubConfigProvider
    """
    return GithubConfigProvider(
        token=CONFIG_PROVIDERS['github']['token'],
        config_base=CONFIG_PROVIDERS['github']['config_base']
    )


@repoze.lru.lru_cache(1)
def _load_job_schema(schema_name=None):
    """
    Helper function that loads given schema

    :param schema_name:
    :return:
    """
    base_url = 'http://localhost:%d' % API_PORT
    schema_name = schema_name or 'job-config-v1'
    fname = 'schemas/{0}.json'.format(schema_name)
    with open(fname) as schema_file:
        data = schema_file.read().replace('${base_url}', base_url)
        return json.loads(data)


def get_provider(provider_type):
    """
    Factory method to create config provider instance.

    :param provider_type:
    :type provider_type: str
    :param args: Arguments for the provider
    :param kwargs: Keyword arguments for the provider.
    :return: AbstractConfigProvider instance.
    :rtype: AbstractConfigProvider
    """
    if provider_type == 'default':
        return get_provider(CONFIG_PROVIDERS['default']['ref'])
    if provider_type not in get_provider_types():
        raise ConfigProviderNotFound(provider_type)

    locator = '_get_%s_provider' % (provider_type)
    if locator in globals():
        return globals()[locator]()


def _json_compatible_config(config):
    """
    Converts the config to json compatible config for schema validation.
    This is needed because json schema does not handle a non-valid json
    config (like non string keys) which may be valid in other types like yaml.

    :return:
    """
    return json.loads(json.dumps(config))


def load_config(*paths, **kwargs):
    """
    Loads config for given path and provider type.

    :param paths: Tuple consisting of nested level path
    :type paths: tuple
    :keyword default_variables: Variables to be applied during template
    evaluation
    :type default_variables: dict
    :keyword provider_type: Type of provider
    :type provider_type: str
    :keyword config_names: List of config names to be loaded. Defaults to
        CONFIG_NAMES defined in appconfig
    :type config_names: list
    :return: Parsed configuration
    :rtype: dict
    """
    provider_type = kwargs.get('provider_type', 'effective')
    config_names = kwargs.get('config_names', ['totem'])
    provider = get_provider(provider_type)
    try:
        configs = [provider.load(name+'.yml', *paths) for name in config_names]
        return _json_compatible_config(dict_merge(*configs))

    except (MarkedYAMLError, ParserError, SchemaError) as error:
        raise ConfigParseError(str(error), paths)


def write_config(name, config, *paths, **kwargs):
    """
    Writes config for given path

    :param config: Dictionary based configuration
    :type config: dict
    :param provider_type: Type of provider
    :type provider_type: str
    :return: None
    """
    provider_type = kwargs.get('provider_type', 'effective')
    provider = get_provider(provider_type)
    if provider:
        provider.write(name, config, *paths)
