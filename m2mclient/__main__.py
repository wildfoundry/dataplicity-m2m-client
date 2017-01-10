import logging

from . import M2MClient


FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format='%(message)s', level=logging.DEBUG)

log = logging.getLogger('m2m')


m2m_client = M2MClient(
    'ws://127.0.0.1:8080/m2m/',
    'dataplicity',
    'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX'
)


with m2m_client:
    m2m_client.log("Hello, World").get()

