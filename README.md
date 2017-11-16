# Tornado Drizzle
----
Drizzle is microframework  for Tornado that enables websocket to perform restful action on top of resources. Drizzle redirects websocket request to corresponding functions that defined in the resource handler
#### sample code
```
import tornado.ioloop
import tornado.web
from tornado_drizzle.drizzle_web_socket import DrizzleWebSocket, DrizzleHandler
from tornado import gen
from tornado_drizzle.conf import init_drizzle


class ResourceHandler(DrizzleHandler):

    @gen.coroutine
    def get(self, message):
        return {"key": "val"}


def make_app():

    application = tornado.web.Application(
        [
            (r"/ws", DrizzleWebSocket),
        ],
        autoreload=True
    )
    return application


if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    drizzle_handler_routes = {
        'resource_name': ResourceHandler
    }
    ioloop = tornado.ioloop.IOLoop.current()
    init_drizzle(app, drizzle_handler_routes, ioloop)
    tornado.ioloop.IOLoop.current().start()

```
App we need to configure a route which drizzle will use to listen request.
here we added `/ws`. so every request to `/ws` will handle by `DrizzleWebSocket`
```
    application = tornado.web.Application(
        [
            (r"/ws", DrizzleWebSocket),
        ],
        autoreload=True
    )
```


we defined `ResourceHandler` to represent a resource.and one action `get` which will do restful action  on resource and return a list or dict.
```
class ResourceHandler(DrizzleHandler):

    @gen.coroutine
    def get(self, message):
        return {"key": "val"}

```
then we defined `drizzle_handler_routes` and added `ResourceHandler` to the resource name `resouce_name`
```
drizzle_handler_routes = {
        'resource_name': ResourceHandler
    }
```

we need initialize drizzle before starting the application
```
init_drizzle(app, drizzle_handler_routes, ioloop)
```

now we can open a websocket connection to `/ws`

then we can send message in Json format
```
{
    "resource": "resource_name",
    "action": "get",
    "data":{},
    "request_id": 1
}
```
`resource`, `action` and `request_id` are mandatory values. Complete message will pass to resource handler as an input param
`data` can be either dict or list object through which we can pass query params or other payload

drizzle find out resource handler for the resource and executes action function and reply back with return value and incoming `request_id` 
```
{
  "data": {
    "key": "val"
  },
  "request_id": 1
}
```

#### Subscription and broadcasting
To subscribe the client socket to any topic `DrizzleHandler` has `subscribe` function. see below code taken from test

To broadcast any message to all clients who subscribed to a topic use
`tornado_drizzle.subscriber.publish` function

```
class TestHandler(DrizzleHandler):

    @gen.coroutine
    def test_subscribe(self, message):
        yield self.subscribe('__test__')
        return {}

    @gen.coroutine
    def test_publish(self, message):
        yield publish("__test__", {"key": "val"})
```
