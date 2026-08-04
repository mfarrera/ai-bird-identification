import os

from redis import Redis
from rq import Queue

# El backend corre amb network_mode: host, així que Redis li arriba pel
# port publicat al host (localhost:6379). Els workers (dins la xarxa
# normal de Docker) hi arriben per REDIS_URL=redis://redis:6379/0,
# sobreescrit al docker-compose.yml per aquests serveis.
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_conn = Redis.from_url(REDIS_URL)

# Una cua per fase, perquè cadascuna pot tenir el seu propi nombre de
# workers escalat independentment.
queue_fase1 = Queue("fase1", connection=redis_conn)
queue_fase2 = Queue("fase2", connection=redis_conn)
