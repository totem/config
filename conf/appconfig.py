import os

# Logging configuration
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s %(message)s'
LOG_DATE = '%Y-%m-%d %I:%M:%S %p'
LOG_ROOT_LEVEL = os.getenv('LOG_ROOT_LEVEL', 'INFO').upper()
LOG_IDENTIFIER = os.getenv('LOG_IDENTIFIER', 'config-service')

BOOLEAN_TRUE_VALUES = {"true", "yes", "y", "1", "on"}
API_PORT = int(os.getenv('API_PORT', '9003'))

DEFAULT_HIPCHAT_TOKEN = os.getenv('HIPCHAT_TOKEN', '')
DEFAULT_GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
BASE_URL = os.getenv('BASE_URL', 'http://localhost:{0}'.format(API_PORT))

TOTEM_ETCD_SETTINGS = {
    'base': os.getenv('ETCD_TOTEM_BASE', '/totem'),
    'host': os.getenv('ETCD_HOST', 'localhost'),
    'port': int(os.getenv('ETCD_PORT', '4001')),
    'yoda_base': os.getenv('ETCD_YODA_BASE', '/yoda'),
}

TOTEM_ENV = os.getenv('TOTEM_ENV', 'local')

CORS_SETTINGS = {
    'enabled': os.getenv('CORS_ENABLED', 'true').strip().lower() in
    BOOLEAN_TRUE_VALUES,
    'origins': os.getenv('CORS_ORIGINS', '*')
}

ENCRYPTION = {
    'store': os.getenv('ENCRYPTION_STORE', None),
    's3': {
        'bucket': os.getenv('ENCRYPTION_S3_BUCKET', 'not-set'),
        'base': os.getenv('ENCRYPTION_S3_BASE', 'totem/keys'),
    },
    'passphrase': os.getenv('ENCRYPTION_PASSPHRASE', None),
}

CONFIG_PROVIDER_DEFAULT = os.getenv('CONFIG_PROVIDER_DEFAULT', 'etcd')

CONFIG_PROVIDERS = {
    's3': {
        'bucket':  os.getenv('CONFIG_S3_BUCKET', 'not_set'),
        'base': os.getenv('CONFIG_S3_BUCKET_BASE', 'totem/config'),
        'meta-info': {
            'readonly': False,
            'name': 's3'
        }
    },
    'etcd': {
        'base': TOTEM_ETCD_SETTINGS['base'],
        'host': TOTEM_ETCD_SETTINGS['host'],
        'port': TOTEM_ETCD_SETTINGS['port'],
        'meta-info': {
            'readonly': False,
            'name': 'etcd',
            'type': 'etcd'
        }
    },
    'effective': {
        'cache': {
            'enabled': os.getenv('CONFIG_CACHE_ENABLED', 'true').strip()
            .lower() in BOOLEAN_TRUE_VALUES,
            'ttl': int(os.getenv('CONFIG_CACHE_TTL', '120'))
        },
        'meta-info': {
            'readonly': True,
            'name': 'effective',
            'type': 'effective'
        }
    },
    'github': {
        'token': os.getenv('GITHUB_TOKEN', None),
        'config_base': os.getenv('GITHUB_CONFIG_BASE', '/'),
        'meta-info': {
            'readonly': False,
            'name': 'github',
            'type': 'github'
        }
    },
    'default': {
        'ref': CONFIG_PROVIDER_DEFAULT,
        'meta-info': {
            'name': 'default',
            'type': CONFIG_PROVIDER_DEFAULT,
        }
    }
}

CONFIG_PROVIDER_LIST = os.getenv(
    'CONFIG_PROVIDER_LIST', 'default,etcd').split(',')

MIME_JSON = 'application/json'
MIME_HTML = 'text/html'
MIME_ROOT_V1 = 'application/vnd.configservice.root.v1+json'
MIME_HEALTH_V1 = 'application/vnd.configservice.health.v1+json'

SCHEMA_ROOT_V1 = 'root-v1'
SCHEMA_HEALTH_V1 = 'health-v1'

API_MAX_PAGE_SIZE = 1000
API_DEFAULT_PAGE_SIZE = 10

HEALTH_OK = 'ok'
HEALTH_FAILED = 'failed'
