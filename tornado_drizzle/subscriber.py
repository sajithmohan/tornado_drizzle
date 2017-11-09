from tornado import gen
from tornado.queues import Queue
import tornado.ioloop


q = Queue()
subscriptions = {}


@gen.coroutine
def subscriber():
    while True:
        key, socket = yield q.get()
        try:
            if key not in subscriptions:
                subscriptions[key] = set()
            subscriptions[key].add(socket)
            socket.subscribed_keys.add(key)
        finally:
            q.task_done()


@gen.coroutine
def publish(key, message):
    if key in subscriptions:
        for socket in subscriptions[key]:
            tornado.ioloop.IOLoop.current().spawn_callback(
                socket.write_message,
                message
            )


@gen.coroutine
def subscribe(key, socket):
    yield q.put((key, socket, ))


def unsubscribe(key, socket):
    if key in subscriptions:
        subscriptions[key].discard(socket)
        socket.subscribed_keys.discard(key)
