from configservice.exceptions import BusinessRuleViolation, ConfigServiceError


class ConfigProviderNotFound(ConfigServiceError):

    def __init__(self, provider_type):
        self.provider_type = provider_type
        code = 'CONFIG_PARSE_ERROR'
        details = {
            'provider_type': self.provider_type
        }
        message = 'Unable to find config provider: {0}'.format(provider_type)
        super(ConfigProviderNotFound, self).__init__(
            message, code=code, details=details)


class ConfigParseError(BusinessRuleViolation):

    def __init__(self, error_msg, paths):
        self.paths = paths
        self.error_msg = error_msg
        message = 'Failed to parse configuration for paths: {0}. ' \
                  'Reason: {1}'.format(paths, error_msg)
        code = 'CONFIG_PARSE_ERROR'
        details = {
            'paths': self.paths
        }
        super(ConfigParseError, self).__init__(message, code=code,
                                               details=details)
