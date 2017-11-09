
from tornado.websocket import WebSocketHandler
from tornado_drizzle.conf import MESSAGE_SCHEMA
from jsonschema import validate as jsonschema_validate
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
import logging
from tornado import gen
from tornado_drizzle.utils import DrizzleLogger
import tornado.ioloop
import json
import types
from tornado_drizzle.subscriber import subscribe, unsubscribe
import sys

logger = logging.getLogger('drizzle')


class MissingDrizzleHandler(Exception):
    pass


class MissingDrizzleAction(Exception):
    pass


class DrizzleHandler(object):

    def __init__(self, socket):
        self.client_socket = socket

    @gen.coroutine
    def subscribe(self, key):
        yield subscribe(key, self.client_socket)


class DrizzleWebSocket(WebSocketHandler):

    def __init__(self, *args, **kwargs):
        super(DrizzleWebSocket, self).__init__(*args, **kwargs)
        self.drizzle_logger = DrizzleLogger()
        self.subscribed_keys = set()

    def check_origin(self, origin):
        return True

    @gen.coroutine
    def open(self):
        yield subscribe('__all__', self)

    @gen.coroutine
    def on_close(self):
        for key in list(self.subscribed_keys):
            unsubscribe(key, self)

    @gen.coroutine
    def on_message(self, message):
        tornado.ioloop.IOLoop.current().spawn_callback(
            self.drizzle_logger, logger.info, message
        )
        request_id = None
        try:
            response = {}
            message = json.loads(message)
            self._validate_incoming_message(message)
            request_id = message['request_id']
            handler = self._find_handler(message['resource'])
            handler_obj = handler(self)
            handler_action = self._find_handler_action(
                handler_obj,
                message['action']
            )
            tornado.ioloop.IOLoop.current().spawn_callback(
                self.drizzle_logger,
                logger.debug,
                "handler {} found for resource {}".format(
                    handler.__name__,
                    message['resource']
                )
            )
            response['data'] = yield handler_action(message)
        except json.decoder.JSONDecodeError as e:
            tornado.ioloop.IOLoop.current().spawn_callback(
                self.drizzle_logger,
                logger.exception, e, exc_info=sys.exc_info()
            )
            response = self._make_error_response(
                "Expected Json encodable string"
            )
        except JsonSchemaValidationError as e:
            tornado.ioloop.IOLoop.current().spawn_callback(
                self.drizzle_logger,
                logger.exception, e, exc_info=sys.exc_info()
            )
            response = self._make_error_response(
                str(e)
            )
        except MissingDrizzleHandler as e:
            tornado.ioloop.IOLoop.current().spawn_callback(
                self.drizzle_logger,
                logger.exception, e, exc_info=sys.exc_info()
            )
            response = self._make_error_response(
                str(e),
                code="RESOURCE_NOT_FOUND"
            )
        except MissingDrizzleAction as e:
            tornado.ioloop.IOLoop.current().spawn_callback(
                self.drizzle_logger,
                logger.exception, e, exc_info=sys.exc_info()
            )
            response = self._make_error_response(
                str(e),
                code="ACTION_NOT_FOUND"
            )
        except Exception as e:
            tornado.ioloop.IOLoop.current().spawn_callback(
                self.drizzle_logger,
                logger.exception, e, exc_info=sys.exc_info()
            )
            response = self._make_error_response("Unknown error")
        finally:
            response['request_id'] = request_id
            tornado.ioloop.IOLoop.current().spawn_callback(
                self.drizzle_logger,
                logger.debug,
                "sending response: {} message: {}".format(
                    message,
                    response
                )
            )
            self.write_message(response)

    def _find_handler_action(self, handler, action):
        try:
            hanlder_action = getattr(handler, action)
            if isinstance(hanlder_action, types.MethodType):
                return hanlder_action
            else:
                raise MissingDrizzleAction(
                    (
                        "action definition '{}' "
                        "not found in handler {}"
                    ).format(action, handler.__class__.__name__)
                )
        except AttributeError:
            raise MissingDrizzleAction(
                (
                    "action definition '{}' "
                    "not found in handler {}"
                ).format(action, handler.__class__.__name__)
            )

    def _find_handler(self, resource):
        try:
            return self.application.drizzle_handler_routes[resource]
        except KeyError as e:
            raise MissingDrizzleHandler(
                (
                    "resource '{}' not found "
                    "in drizzle_handler_routes"
                ).format(resource)
            )

    def _make_error_response(self, message, code='VALIDATION_ERROR'):
        return {'error': message, 'code': code}

    def _validate_incoming_message_schema(self, message):
        jsonschema_validate(message, MESSAGE_SCHEMA)

    def _validate_incoming_message(self, message):
        self._validate_incoming_message_schema(message)
