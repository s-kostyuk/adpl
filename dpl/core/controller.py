# Include standard modules
import asyncio
import os
import logging
import argparse

# Include 3rd-party modules
from sqlalchemy import create_engine
import appdirs

# Include DPL modules
from dpl import api
from dpl import auth
from dpl.core.configuration import Configuration
from dpl.integrations.binding_bootstrapper import BindingBootstrapper

from dpl.repo_impls.sql_alchemy.session_manager import SessionManager
from dpl.repo_impls.sql_alchemy.db_mapper import DbMapper
from dpl.repo_impls.sql_alchemy.placement_repository import PlacementRepository

from dpl.repo_impls.sql_alchemy.connection_settings_repo import ConnectionSettingsRepository
from dpl.repo_impls.sql_alchemy.thing_settings_repo import ThingSettingsRepository

from dpl.repo_impls.in_memory.connection_repository import ConnectionRepository
from dpl.repo_impls.in_memory.thing_repository import ThingRepository

from dpl.service_impls.placement_service import PlacementService
from dpl.service_impls.thing_service import ThingService


module_logger = logging.getLogger(__name__)
dpl_root_logger = logging.getLogger(name='dpl')

# Path to the folder with everpl configuration used by default
DEFAULT_CONFIG_DIR = appdirs.user_config_dir(
    appname='everpl'
)

CONFIG_NAME = 'everpl_config.yaml'
MAIN_DB_NAME = 'everpl_db.sqlite'

# Path to the configuration file to be used by default
# like ~/.config/everpl/everpl_config.yaml)
DEFAULT_CONFIG_PATH = os.path.join(DEFAULT_CONFIG_DIR, CONFIG_NAME)

# Path to the main database file to be used by default
DEFAULT_MAIN_DB_PATH = os.path.join(DEFAULT_CONFIG_DIR, MAIN_DB_NAME)


class Controller(object):
    def __init__(self):
        # FIXME: Initialize configuration externally
        self._conf = Configuration()

        args = self.parse_arguments()

        if args.config_dir is None:
            self._config_dir = DEFAULT_CONFIG_DIR
        else:
            self._config_dir = args.config_dir

        if args.config_path is None:
            self._config_path = os.path.join(self._config_dir, CONFIG_NAME)
        else:
            self._config_path = args.config_path

        self._conf.load_or_create_config(self._config_path)
        self.apply_arguments(args)

        self._core_config = self._conf.get_by_subsystem('core')
        self._apis_config = self._conf.get_by_subsystem('apis')
        self._integrations_config = self._conf.get_by_subsystem('integrations')

        logging_level_str = self._core_config['logging_level']  # type: str
        dpl_root_logger.setLevel(level=logging_level_str.upper())

        if self._core_config.get('main_db_path') is None:
            self._core_config['main_db_path'] = os.path.join(self._config_dir, MAIN_DB_NAME)

        main_db_path = self._core_config.get('main_db_path')
        echo_db_requests = (logging_level_str == 'debug')

        if not os.path.exists(main_db_path):
            logging.warning("There is no DB file present by the specified path. "
                            "A new one will be created: %s" % main_db_path)

        self._engine = create_engine("sqlite:///%s" % main_db_path, echo=echo_db_requests)
        self._db_mapper = DbMapper()
        self._db_mapper.init_tables()
        self._db_mapper.init_mappers()
        self._db_mapper.create_all_tables(bind=self._engine)
        self._db_session_manager = SessionManager(engine=self._engine)

        self._con_settings_repo = ConnectionSettingsRepository(self._db_session_manager)
        self._thing_settings_repo = ThingSettingsRepository(self._db_session_manager)

        self._placement_repo = PlacementRepository(self._db_session_manager)
        self._connection_repo = ConnectionRepository()
        self._thing_repo = ThingRepository()

        self._placement_service = PlacementService(self._placement_repo)
        self._thing_service = ThingService(self._thing_repo)

        self._auth_manager = auth.AuthManager()

        self._api_gateway = api.ApiGateway(self._auth_manager, self._thing_service, self._placement_service)
        self._rest_api = api.RestApi(self._api_gateway)

    def parse_arguments(self):
        """
        Parses command-line arguments and alters everpl configuration
        correspondingly. Returns values of cmdline arguments

        :return: Any
        """
        # FIXME: Move argument parsing to the run.py script
        arg_parser = argparse.ArgumentParser(
            description="everpl runner script"
        )

        arg_parser.add_argument(
            '--is-safe', help='if everpl must to be started in the safe mode',
            type=bool, dest='is_safe', default=None
        )

        arg_parser.add_argument(
            '--log-level', help='minimum level of logging messages to be displayed',
            type=bool, dest='log_level', default=None
        )

        arg_parser.add_argument(
            '--is-api-enabled', help='if any API access must to be enabled',
            type=bool, dest='is_api_enabled', default=None
        )

        arg_parser.add_argument(
            '--config-dir', help='a path to the configuration directory',
            type=str, dest='config_dir', default=None
        )

        arg_parser.add_argument(
            '--config-path', help='a path to the everpl config file',
            type=str, dest='config_path', default=None
        )

        arg_parser.add_argument(
            '--db-path', help='a path to the main DB file to be used',
            type=str, dest='db_path', default=None
        )

        arg_parser.add_argument(
            '--rest-api-host', help='a hostname used for REST API listening',
            type=str, dest='rest_api_host', default=None
        )

        arg_parser.add_argument(
            '--rest-api-port', help='a listening port for REST API',
            type=int, dest='rest_api_port', default=None
        )

        return arg_parser.parse_args()

    def apply_arguments(self, args) -> None:
        """
        Applies cmdline arguments to the configuration

        :param args: arguments to be applied
        :return: None
        """
        if args.is_safe is not None:
            self._core_config['is_safe'] = args.is_safe

        if args.log_level is not None:
            self._core_config['logging_level'] = args.log_level

        if args.is_api_enabled is not None:
            self._core_config['is_api_enabled'] = args.is_api_enabled

        if args.db_path is not None:
            self._core_config['main_db_path'] = args.db_path

        if args.rest_api_host is not None:
            self._apis_config['rest_api']['host'] = args.rest_api_host

        if args.rest_api_port is not None:
            self._apis_config['rest_api']['port'] = args.rest_api_port

    async def start(self):
        is_safe_mode = self._core_config['is_safe_mode']

        if is_safe_mode:
            module_logger.warning("\n\n\nSafe mode is enabled, the most of everpl capabilities will be disabled\n\n")
            module_logger.warning("\n!!! REST API access will be enabled in the safe mode !!!\n")

            # Only REST API will be enabled in the safe mode
            self._apis_config['enabled_apis'] = ('rest_api', )

            # Force enable API access
            self._core_config['is_api_enabled'] = True
        else:
            await self._bootstrap_integrations()

        # FIXME: Only for testing purposes
        self._auth_manager.create_root_user("admin", "admin")

        is_api_enabled = self._core_config['is_api_enabled']

        if is_api_enabled:
            await self._start_apis()
        else:
            module_logger.warning("All APIs was disabled by everpl configuration. "
                                  "Connections from client devices will be blocked")

    async def _start_apis(self):
        """
        Starts all APIs enabled in everpl configuration

        :return: None
        """
        enabled_apis = self._apis_config['enabled_apis']

        if 'rest_api' in enabled_apis:
            await self._start_rest_api()

    async def _start_rest_api(self):
        """
        Starts REST API server

        :return: None
        """
        rest_api_config = self._apis_config['rest_api']
        rest_api_host = rest_api_config['host']
        rest_api_port = rest_api_config['port']

        asyncio.ensure_future(
            self._rest_api.create_server(host=rest_api_host, port=rest_api_port)
        )

    async def _bootstrap_integrations(self):
        enabled_integrations = self._integrations_config['enabled_integrations']

        connection_settings = self._con_settings_repo.load_all()
        thing_settings = self._thing_settings_repo.load_all()

        binding_bootstrapper = BindingBootstrapper(
            connection_repo=self._connection_repo,
            thing_repo=self._thing_repo
        )

        binding_bootstrapper.init_integrations(enabled_integrations)
        binding_bootstrapper.init_connections(connection_settings)
        binding_bootstrapper.init_things(thing_settings)

        self._db_session_manager.remove_session()

        self._thing_service.enable_all()

    async def shutdown(self):
        await self._rest_api.shutdown_server()
        self._thing_service.disable_all()
