import copy
import json
from parser import ParserError
import types
from jinja2 import TemplateSyntaxError
from jinja2.environment import get_spontaneous_environment
from jsonschema import validate, ValidationError
from yaml.error import MarkedYAMLError
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, filter, map, zip)

from jsonschema.exceptions import SchemaError
import repoze.lru
from conf.appconfig import CONFIG_PROVIDERS, CONFIG_PROVIDER_LIST, \
    BOOLEAN_TRUE_VALUES
from configservice.cluster_config.effective import MergedConfigProvider
from configservice.cluster_config.etcd import EtcdConfigProvider
from configservice.cluster_config.github import GithubConfigProvider
from configservice.cluster_config.s3 import S3ConfigProvider
from configservice.jinja import conditions
from configservice.services.exceptions import ConfigProviderNotFound, \
    ConfigParseError, ConfigValueError, ConfigValidationError
from configservice.util import dict_merge


__author__ = 'sukrit'


def get_providers():
    for provider_type in CONFIG_PROVIDER_LIST:
        provider_type = provider_type.strip()
        if provider_type in CONFIG_PROVIDERS:
            yield provider_type
    yield 'effective'


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


@repoze.lru.lru_cache(50, timeout=5*60)
def _load_job_schema(schema_name, groups=None, provider_type=None):
    """
    Helper function that loads given schema

    :param schema_name:
    :return:
    """
    groups = list(groups or [])
    return load_config(meta={
        'groups': groups,
        'config-names': [schema_name],
        'provider-type': provider_type
    })


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
    if provider_type not in get_provider_types():
        raise ConfigProviderNotFound(provider_type)

    locator = '_get_%s_provider' % provider_type
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


def validate_schema(config, schema_config=None):
    """
    Validates schema for given configuration.

    :param config: Config dictionary
    :type config: dict
    :return: config if validation passes
    :rtype: dict
    """
    if not schema_config or 'schema' not in schema_config:
        return config
    schema_name = schema_config.get('schema')
    schema = _load_job_schema(schema_name, groups=schema_config.get('groups'),
                              provider_type=schema_config.get('provider'))
    try:
        validate(config, schema)
    except ValidationError as ex:
        message = 'Failed to validate config against schema {0}. ' \
                  'Reason: {1}'.format(schema_name, ex.message)
        raise ConfigValidationError(message, '/'.join(ex.schema_path),
                                    ex.schema)
    return config


def _expand_groups(groups):
    """
    Expand group path
    :param groups: Groups that needs to be expanded
    :type groups: list
    :return: Expanded groups
    :rtype: list
    """
    expanded = []
    for group in groups:
        if group == '..':
            if expanded:
                expanded.pop()
        else:
            expanded.append(group)
    return expanded


def _expand_parent_groups(groups, parent_groups):
    """
    Expand group path for parent config
    :param groups: Config groups for current config
    :type groups: list
    :param parent_groups: Config groups for parent config
    :type groups: list
    :return: Expanded groups
    :rtype: list
    """
    if not parent_groups:
        return []
    if parent_groups[0] == '..':
        parent_groups = groups[:-1] + parent_groups[1:]
    return _expand_groups(parent_groups)


def load_config(meta, processed_paths=None):
    """
    Loads config for given path and provider type.
    :param meta: Meta information for config loading
    :type meta: dict
    :keyword processed_paths: List of paths that are already processed
    :type processed_paths: List
    :return: Parsed configuration
    :rtype: dict
    """
    meta = meta or {}
    processed_paths = processed_paths or []
    provider_type = meta.get('provider-type', 'effective')
    config_name = meta.get('name', 'totem')
    default_config = meta.get('default-config')
    processed_paths = copy.deepcopy(processed_paths)
    groups = list(meta.get('groups') or [])
    process_path = '{}:'.format(provider_type).join(groups)
    if process_path in processed_paths:
        return load_config(dict_merge({
            'name': 'cluster-def'
        }, meta)) if meta.get('name') == 'totem' else {}
    processed_paths.append(process_path)
    provider = get_provider(provider_type)
    try:
        merged_config = provider.load(config_name+'.yml', *groups)
        merged_config.setdefault('.parent', {})
        merged_config['.parent'] = dict_merge(merged_config['.parent'], {
            'provider-type': provider_type,
            'name': config_name,
            'groups': ['..'],
            'enabled': True,
        })
        merged_config['.parent']['evaluate'] = False
        merged_config['.parent']['groups'] = _expand_parent_groups(
            groups, merged_config['.parent']['groups'])

        merged_config = dict_merge(
            merged_config,
            load_config(merged_config['.parent'],
                        processed_paths=processed_paths)
        ) if merged_config['.parent']['enabled'] else merged_config
        merged_config = dict_merge(merged_config, default_config)
        del(merged_config['.parent'])

        if not meta.get('evaluate'):
            return _json_compatible_config(merged_config)
        return dict(normalize_config(
            validate_schema(
                evaluate_config(
                    _json_compatible_config(merged_config),
                    default_variables=meta.get('default-variables'),
                    transformations=meta.get('transformations')),
                schema_config=meta.get('schema-config')),
            encrypted_keys=meta.get('encrypted-keys')
        ))
    except (MarkedYAMLError, ParserError, SchemaError) as error:
        raise ConfigParseError(str(error), groups)


def write_config(name, config, *groups, **kwargs):
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
        provider.write(name, config, *groups)


def evaluate_config(config, default_variables={}, var_key='variables',
                    transformations=None):
    """
    Performs rendering of all template values defined in config. Also takes
    user defined variables nd default variables for substitution in the config
    .
    :param config:
    :param default_variables:
    :param var_key:
    :return: Evaluated config
    :rtype: dict
    """
    updated_config = copy.deepcopy(config)
    updated_config.setdefault(var_key, {})
    if 'defaults' in updated_config:
        # We do not want to do any processing ind efaults section.
        # It is only used for YAML substitution which at this point is already
        # done.
        del(updated_config['defaults'])
    updated_config = transform_string_values(
        evaluate_value(updated_config, default_variables),
        transformations=transformations)

    return updated_config


def _normalize_encrypted_config(env_config):
    if isinstance(env_config, dict):
        return {
            'value': str(env_config.get('value') or ''),
            'encrypted': env_config.get('encrypted', False)
        }
    return {
        'value': str(env_config),
        'encrypted': False
    }


def normalize_config(config, encrypted_keys=None):
    """
    Normalizes the config
    :param config:
    :return:
    """
    encrypted_keys = encrypted_keys or ()
    for config_key, config_val in config.items():
        if isinstance(config_val, dict):
            if config_key in encrypted_keys:
                yield config_key, {
                    env_key: _normalize_encrypted_config(env_val)
                    for env_key, env_val in config_val.items()
                }
            else:
                yield config_key, dict(normalize_config(
                    config_val, encrypted_keys=encrypted_keys))
        else:
            yield config_key, config_val


def _get_jinja_environment():
    """
    Creates Jinja env for evaluating config

    :return: Jinja Environment
    """
    env = get_spontaneous_environment()
    env.line_statement_prefix = '#'
    return conditions.apply_conditions(env)


def evaluate_template(template_value, variables={}):
    env = _get_jinja_environment()
    return env.from_string(str(template_value)).render(**variables).strip()


def evaluate_variables(variables, default_variables={}):

    merged_vars = dict_merge({}, default_variables)

    def get_sort_key(item):
        return item[1]['priority']

    def as_tuple(vars):
        for variable_name, variable_val in vars.items():
            variable_val = copy.deepcopy(variable_val)
            if not hasattr(variable_val, 'items'):
                variable_val = {
                    'value': variable_val,
                    'template': False,
                    'priority': 0
                }
            variable_val.setdefault('template', True)
            variable_val.setdefault('priority', 1)
            variable_val.setdefault('value', '')
            val = variable_val['value']
            if isinstance(val, bool):
                variable_val['value'] = str(val).lower()
            yield (variable_name, variable_val)

    def expand(var_name, var_value):
        try:
            merged_vars[var_name] = evaluate_template(
                var_value['value'], merged_vars) if var_value['template'] \
                else var_value['value']
        except Exception as exc:
            raise ConfigValueError('/variables/%s/' % var_name, var_value,
                                   str(exc))

    sorted_vars = sorted(as_tuple(variables), key=get_sort_key)
    for sorted_var_name, sorted_var_value in sorted_vars:
        expand(sorted_var_name, sorted_var_value)

    return merged_vars


def evaluate_value(value, variables={}, location='/'):
    """
    Renders tokenized values (using nested strategy)

    :param value: Value that needs to be evaluated (str , list, dict, int etc)
    :param variables: Variables to be used for Jinja2 templates
    :param identifier: Identifier used to identify tokenized values. Only str
        values that begin with identifier are evaluated.
    :return: Evaluated object.
    """
    value = copy.deepcopy(value)
    if hasattr(value, 'items'):
        if 'variables' in value:
            variables = evaluate_variables(value['variables'], variables)
            del(value['variables'])

        if 'value' in value:
            value.setdefault('encrypted', False)
            value.setdefault('template', True)
            if value['template']:
                try:
                    value['value'] = evaluate_template(value['value'],
                                                       variables)
                except TemplateSyntaxError as error:
                    raise ConfigValueError(location, value['value'],
                                           reason=error.message)
            del(value['template'])
            if not value['encrypted']:
                value = value['value']
            return value

        else:
            if '.defaults' in value:
                defaults = value.get('.defaults')
                del(value['.defaults'])
            elif '__defaults__' in value:
                # Added for backward compatibility
                # __defaults__ is now deprecated and will be removed in next
                # release
                defaults = value.get('__defaults__')
                del(value['__defaults__'])
            else:
                defaults = None
            for each_k, each_v in value.items():
                if defaults and hasattr(each_v, 'items'):
                    each_v = dict_merge(each_v, defaults)
                value[each_k] = evaluate_value(each_v, variables,
                                               '%s%s/' % (location, each_k))
            return {
                each_k: evaluate_value(each_v, variables)
                for each_k, each_v in value.items()
            }

    elif isinstance(value, (list, tuple, set, types.GeneratorType)):
        return [evaluate_value(each_v, variables, '%s[]/' % (location, ))
                for each_v in value]

    return value.strip() if isinstance(value, (str,)) else value


def transform_string_values(config, transformations=None):
    """
    Transforms the string values to appropriate type in config

    :param config: dictionary configuration with evaluated template parameters
    :type config: dict
    :return: transformed config
    :rtype: dict
    """
    new_config = copy.deepcopy(config)
    transformations = transformations or {}

    def convert_keys(use_config, location='/'):
        if hasattr(use_config, 'items'):
            for each_k, each_v in use_config.items():
                try:
                    if each_v is None:
                        continue
                    elif each_k in transformations.get('boolean-keys', [])\
                            and isinstance(each_v, str):
                        use_config[each_k] = each_v.lower() in \
                            BOOLEAN_TRUE_VALUES
                    elif each_k in transformations.get('number-keys', [])\
                            and isinstance(each_v, str):
                        use_config[each_k] = int(each_v)
                    elif hasattr(each_v, 'items'):
                        convert_keys(each_v, '%s%s/' %
                                             (location, each_k))
                    elif isinstance(each_v,
                                    (list, tuple, set, types.GeneratorType)):
                        for idx, val in enumerate(each_v):
                            convert_keys(
                                val, '%s%s[%d]/' % (location, each_k, idx))
                except ValueError as error:
                    raise ConfigValueError(location + each_k, each_v,
                                           error.message)

    convert_keys(new_config)
    return new_config
