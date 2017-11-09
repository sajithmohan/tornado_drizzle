import tornado
import unittest
from tornado.testing import AsyncHTTPTestCase
from tornado_drizzle.drizzle_web_socket import DrizzleWebSocket, DrizzleHandler
from tornado_drizzle.subscriber import subscriptions, publish
from tornado_drizzle.conf import init_drizzle
from tornado import gen
from tornado.ioloop import IOLoop
import json
from copy import deepcopy
from datetime import timedelta


class TestDrizzleWebSocket(DrizzleWebSocket):
    pass

client_msg = {
    'resource': 'test',
    'action': 'get',
}
client_sockets = []
request_id = 99


class TestHandler(DrizzleHandler):

    test_prop = None

    @gen.coroutine
    def get(self, message):
        return {'testkey': 'testval'}

    @gen.coroutine
    def test_exception(self, message):
        0/0

    @gen.coroutine
    def test_subscribe(self, message):
        yield self.subscribe('__test__')
        return {}

    @gen.coroutine
    def test_publish(self, message):
        yield publish("__test__", {"key": "val"})


class TestWebSockets(AsyncHTTPTestCase):

    @property
    def ws_url(self):
        if not hasattr(self, '_ws_url'):
            self._ws_url = "ws://127.0.0.1:{}/ws".format(self.get_http_port())
        return self._ws_url

    def get_new_ioloop(self):
        return IOLoop.instance()

    def get_app(self):

        resournce_handlers = {
            "test": TestHandler
        }
        app = tornado.web.Application([
            (r'/ws', TestDrizzleWebSocket)
        ])
        init_drizzle(app, resournce_handlers, self.io_loop)
        return app

    @tornado.testing.gen_test
    def test_websocket_client_subscription_to_global_key(self):
        """
            websocket should subscribe to global subscription key __all__
            while opening a new connection
        """

        client_count = 100
        old_global_subscriber_count = len(subscriptions.get('__all__', []))
        for i in range(client_count):
            client_socket = yield tornado.websocket.websocket_connect(self.ws_url)
            client_sockets.append(client_socket)
        global_subscriber_count_after_all_connection = len(subscriptions['__all__'])
        self.assertEqual(
            old_global_subscriber_count,
            global_subscriber_count_after_all_connection - client_count
        )
        client_socket.close()
        yield gen.sleep(0.01)
        new_global_subscriber_after_close = len(subscriptions['__all__'])
        self.assertEqual(
            global_subscriber_count_after_all_connection,
            new_global_subscriber_after_close + 1
        )

    @tornado.testing.gen_test
    def test_execution_of_drizzle_handler_function(self):

        """
            websocket should subscribe to global subscription key __all__
            while opening a new connection
        """
        global request_id
        client_socket = yield tornado.websocket.websocket_connect(self.ws_url)
        client_msg['request_id'] = 'test123'
        client_socket.write_message(json.dumps(client_msg))
        msg = yield client_socket.read_message()
        json_msg = json.loads(msg)
        self.assertEqual(
            json_msg,
            {
                "data": {
                    "testkey": 'testval'
                },
                "request_id": 'test123'
            }
        )

    @tornado.testing.gen_test
    def test_expected_json_encodable_string(self):
        """
            request should be in json format
        """
        client_socket = yield tornado.websocket.websocket_connect(self.ws_url)
        client_msg = "normal string, not json encodable"
        client_socket.write_message(client_msg)
        msg = yield client_socket.read_message()
        json_msg = json.loads(msg)
        self.assertEqual(
            json_msg,
            {
                'code': 'VALIDATION_ERROR',
                'error': 'Expected Json encodable string',
                'request_id': None
            }
        )

    @tornado.testing.gen_test
    def test_expected_msg_validate_required_fields(self):
        """
            request should be in valid against schema
        """
        global request_id

        client_socket = yield tornado.websocket.websocket_connect(self.ws_url)
        required_fields = [
            "resource",
            "action",
            "request_id"
        ]

        for required_field in required_fields:
            req_msg = deepcopy(client_msg)
            request_id = request_id + 1
            req_msg['request_id'] = request_id
            req_msg.pop(required_field)
            client_socket.write_message(json.dumps(req_msg))
            res_msg = yield client_socket.read_message()
            json_msg = json.loads(res_msg)
            self.assertTrue(
                "'{}' is a required property".format(required_field) in json_msg['error']
            )

    @tornado.testing.gen_test
    def test_expected_msg_validate_string_key(self):
        """
            request should be in valid against schema
        """
        global request_id
        str_type_validation_key = [
            "resource",
            "action",
        ]
        client_socket = yield tornado.websocket.websocket_connect(self.ws_url)
        for k in str_type_validation_key:
            req_msg = deepcopy(client_msg)
            request_id = request_id + 1
            req_msg['request_id'] = request_id
            req_msg[k] = 100
            client_socket.write_message(json.dumps(req_msg))
            res_msg = yield client_socket.read_message()
            json_msg = json.loads(res_msg)
            self.assertTrue(
                "{} is not of type 'string'".format(req_msg[k]) in json_msg['error'] and
                k in json_msg['error']
            )

    @tornado.testing.gen_test
    def test_expected_msg_invalid_resource(self):
        """
            request should be in valid against schema
        """
        global request_id
        client_socket = yield tornado.websocket.websocket_connect(self.ws_url)
        req_msg = deepcopy(client_msg)
        req_msg['resource'] = 'invalid_resource'
        request_id = request_id + 1
        req_msg['request_id'] = request_id
        client_socket.write_message(json.dumps(req_msg))
        res_msg = yield client_socket.read_message()
        json_msg = json.loads(res_msg)
        self.assertTrue(
            "resource 'invalid_resource' not found in drizzle_handler_routes" in json_msg['error']
        )

    @tornado.testing.gen_test
    def test_expected_msg_invalid_action(self):
        """
            request should be in valid against schema
        """
        global request_id
        client_socket = yield tornado.websocket.websocket_connect(self.ws_url)
        req_msg = deepcopy(client_msg)
        req_msg['action'] = 'invalid_action'
        request_id = request_id + 1
        req_msg['request_id'] = request_id
        client_socket.write_message(json.dumps(req_msg))
        res_msg = yield client_socket.read_message()
        json_msg = json.loads(res_msg)
        self.assertTrue(
            "action definition 'invalid_action' not found in handler" in json_msg['error']
        )

    @tornado.testing.gen_test
    def test_expected_msg_invalid_action_prop(self):
        """
            request should be in valid against schema
        """
        global request_id
        client_socket = yield tornado.websocket.websocket_connect(self.ws_url)
        req_msg = deepcopy(client_msg)
        req_msg['action'] = 'test_prop'
        request_id = request_id + 1
        req_msg['request_id'] = request_id
        client_socket.write_message(json.dumps(req_msg))
        res_msg = yield client_socket.read_message()
        json_msg = json.loads(res_msg)
        self.assertTrue(
            "action definition 'test_prop' not found in handler" in json_msg['error']
        )

    @tornado.testing.gen_test
    def test_expected_msg_unknown_error(self):
        """
            request should be in valid against schema
        """
        global request_id
        client_socket = yield tornado.websocket.websocket_connect(self.ws_url)
        req_msg = deepcopy(client_msg)
        req_msg['action'] = 'test_exception'
        request_id = request_id + 1
        req_msg['request_id'] = request_id
        client_socket.write_message(json.dumps(req_msg))
        res_msg = yield client_socket.read_message()
        json_msg = json.loads(res_msg)
        self.assertEqual(
            "Unknown error",
            json_msg['error']
        )

    @tornado.testing.gen_test
    def test_publish_broadcasts(self):
        global request_id

        client_socket_1 = yield tornado.websocket.websocket_connect(self.ws_url)
        client_socket_2 = yield tornado.websocket.websocket_connect(self.ws_url)
        client_socket_3 = yield tornado.websocket.websocket_connect(self.ws_url)
        client_socket_4 = yield tornado.websocket.websocket_connect(self.ws_url)
        subscription_msg = {
            'resource': 'test',
            'action': 'test_subscribe'

        }
        request_id = request_id + 1
        subscription_msg['request_id'] = request_id
        client_socket_1.write_message(json.dumps(subscription_msg))
        yield client_socket_1.read_message()
        request_id = request_id + 1
        subscription_msg['request_id'] = request_id
        client_socket_2.write_message(json.dumps(subscription_msg))

        yield client_socket_2.read_message()
        publish_msg = {
            'resource': 'test',
            'action': 'test_publish'
        }
        request_id = request_id + 1
        publish_msg['request_id'] = request_id
        client_socket_3.write_message(json.dumps(publish_msg))
        yield client_socket_3.read_message()
        client_socket_1_msg = yield client_socket_1.read_message()
        self.assertEqual(
            json.loads(client_socket_1_msg),
            {"key": "val"}

        )
        client_socket_2_msg = yield client_socket_2.read_message()
        self.assertEqual(
            json.loads(client_socket_2_msg),
            {"key": "val"}
        )
        # only client 1, 2 subscribed to test
        # client_socket_4 should not recieve broadcast
        # wait 2 second to recive
        try:
            client_socket_4_msg = yield gen.with_timeout(
                timedelta(seconds=2),
                client_socket_4.read_message()
            )
            self.assertTrue(
                False,
                "client_socket_4 not subscribed but recieved msg " + client_socket_4_msg
            )
        except gen.TimeoutError as e:
            pass


if __name__ == '__main__':
    unittest.main()
