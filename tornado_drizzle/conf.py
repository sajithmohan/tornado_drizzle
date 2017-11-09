from tornado_drizzle.subscriber import subscriber


MESSAGE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "required": [
        "resource",
        "action",
        "request_id"
    ],
    "properties": {
        "request_id": {
            "oneOf": [
                {
                    "type": "string"
                },
                {
                    "type": "number"
                }
            ]
        },
        "resource": {
            "type": "string"
        },
        "action": {
            "type": "string"
        },
        "data": {
            "type": "object"
        }
    }
}


def init_drizzle(application, drizzle_handler_routes, ioloop):
    ioloop.spawn_callback(subscriber)
    application.drizzle_handler_routes = drizzle_handler_routes
