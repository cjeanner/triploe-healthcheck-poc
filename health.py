#!/usr/bin/env python3

# Script exits with the following return code, depending on the status:
# 0 if everything's fine
# 1 if the healthcheck is failing
# 2 if there's a configuration or runtime error
# In addition, everything will be logged as follow:
# Debug() for runtime information
# Info() for the actual healthcheck output
# Info() when restart request is successful
# Critical() in case of configuration error
# Critical() if the healthcheck can't connect to the service

import argparse
import configparser
import dbus
import json
import logging
import os
import requests
import sys


class Healthcheck():
    '''Provides methods to run healthchecks and act on failure.
    The endpoint is expected to return a valid JSON, as described in
    oslo.middleware.healthcheck:
    https://opendev.org/openstack/oslo.middleware/src/branch/master/oslo_middleware/healthcheck/__init__.py#L485
    The present class will:
        - check the value of the "healthy" field
        - if configured, restart the failed service
        - stringify the JSON and forward it as-is to the logging system
    '''

    def __init__(self, parsed_args):
        '''Create object'''
        self.__srv = os.path.splitext(parsed_args.service)[0]
        self.__debug = parsed_args.debug

        self.__cfg = configparser.ConfigParser()

        log_format = ('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        if self.__debug:
            logging.basicConfig(level=logging.DEBUG, format=log_format)
        else:
            logging.basicConfig(level=logging.INFO, format=log_format)

        self.logger = logging.getLogger(name=('healthcheck.'
                                              '{}').format(self.__srv))

    def load_config(self):
        '''Load configuration file'''
        cfile = './tripleo-healthchecks.conf'
        if os.path.exists(cfile):
            self.__cfg.read(cfile)
        else:
            raise FileNotFoundError(('Configuration file not found at '
                                     '{}').format(cfile))
        if not self.__cfg.has_section(self.__srv):
            raise LookupError(('No configuration found for '
                               '{}').format(self.__srv))

    def run_check(self):
        proto = 's' if self.__cfg.getboolean(self.__srv,
                                             'tls', fallback=False) else ''

        uri = 'http{}://{}:{}{}'.format(proto,
                                        self.__cfg.get(self.__srv, 'host'),
                                        self.__cfg.getint(self.__srv, 'port'),
                                        self.__cfg.get(self.__srv, 'endpoint')
                                        )
        self.logger.debug('Running check against %s', uri)
        resp = None
        try:
            resp = requests.get(uri)
        except requests.exceptions.ConnectionError as e:
            self.logger.critical(e)
            return 1

        on_failure_classes = self.__cfg.get(self.__srv,
                                            'on_failure_classes',
                                            fallback='')
        on_failure_classes = on_failure_classes.split(',')

        status = json.loads(resp.text)
        # oslo.middleware returns either 200 or 204 in case of healthy, else
        # 503. We can therefore use that status code.
        healthy = resp.status_code in [200, 204]
        self.logger.info(json.dumps(status)) # ensure we get a one-liner

        failure_action = self.__cfg.get(self.__srv,
                                        'failure_action',
                                        fallback='')
        if not healthy and failure_action == 'restart':
            self.__restart_service()

        return not healthy

    def __restart_service(self):
        '''Restart the service if requested. It will use DBus, since
        the script is launched via systemd as root, and python3-dbus is
        a standard package on the hosts.
        DBus API: https://wiki.freedesktop.org/www/Software/systemd/dbus/'''
        sysbus = dbus.SystemBus()
        systemd1 = sysbus.get_object('org.freedesktop.systemd1',
                                     '/org/freedesktop/systemd1')
        manager = dbus.Interface(systemd1, 'org.freedesktop.systemd1.Manager')
        self.logger.debug("Trying to request restart on %s service",
                           self.__srv)
        try:
            manager.RestartUnit('{}.service'.format(self.__srv), 'fail')
        except dbus.exceptions.DBusException as e:
            self.logger.critical(e)
            sys.exit(1)
        self.logger.info("Successfuly requested restart on %s service",
                         self.__srv)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Healthcheck monitoring')
    parser.add_argument('service', metavar='SERVICE', type=str,
                        help='Systemd unit name, without the .service.')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='Toggle debug level')
    args = parser.parse_args()

    check = Healthcheck(args)
    check.logger.debug('Loading healthcheck for %s', args.service)
    try:
        check.load_config()
    except FileNotFoundError as e:
        check.logger.critical(e)
        sys.exit(2)
    except LookupError as e:
        check.logger.critical(e)
        sys.exit(2)

    sys.exit(check.run_check())
