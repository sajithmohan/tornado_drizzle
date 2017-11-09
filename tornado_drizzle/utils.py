from tornado import gen

from concurrent.futures import ThreadPoolExecutor
drizzle_thread_pool = ThreadPoolExecutor(4)


class DrizzleLogger(object):
    """logger to use thread poll to write"""

    @gen.coroutine
    def __call__(self, logger_method, log_message, exc_info=None):
        yield drizzle_thread_pool.submit(
            logger_method,
            "message: {}".format(log_message),
            exc_info=exc_info
        )
