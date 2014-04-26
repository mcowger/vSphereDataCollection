systemconfig = {
    'live_config_file':'config',  #will become config.db on most systems
    'data_dir':'.'
}

loggingconfig = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s|%(name)s|%(levelname)s|%(module)s:%(lineno)d|%(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'DEBUG',
            'propagate': True
        },
        'werkzeug': {
            'handlers': ['default'],
            'level': 'WARN'
        },
    }
}
