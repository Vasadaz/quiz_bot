import logging
import redis

logger = logging.getLogger(__file__)

from environs import Env

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s:%(levelname)s:%(message)s')
    logger.setLevel(logging.DEBUG)

    env = Env()
    env.read_env()
    db_host = env.str('REDIS_HOST')
    db_port = env.str('REDIS_PORT')
    db_password = env.str('REDIS_PASSWORD')


    db = redis.StrictRedis(
        host=db_host,
        port=db_port,
        password=db_password,
        charset='utf-8',
        decode_responses=True
    )

    db.set('test key', 'test_value', 20)