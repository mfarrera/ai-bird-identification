# Media Server

Servidor de mitjans central: rep el push RTSP de **totes** les fonts de vídeo
(worker `apps/edge` de simulació, i els dispositius reals `apps/edge/jetson-nano`)
i el redistribueix cap al frontend en HLS.

```
apps/edge (simulador)        ─┐
apps/edge/jetson-nano (real) ─┼─ RTSP push ─> Media Server ─ HLS ─> Frontend
altres fonts futures         ─┘                    │
                                              auth webhook
                                                    │
                                                    v
                                                Backend (/api/mediamtx/auth)
```

Implementat amb [MediaMTX](https://github.com/bluenviron/mediamtx). L'autenticació
de cada publicació RTSP es delega al Backend (`authHTTPAddress` a `mediamtx.yml`),
que valida `camera_id` + `publish_token` contra la BBDD — el mateix mecanisme
per a qualsevol font, sigui el simulador Docker o un Jetson real.

## Build

```bash
cd apps/mediaserver
docker build -t mediaserver .
```

Ja integrat al `docker-compose.yml` de l'arrel (servei `mediaserver`).

## Ports

- `8554` RTSP — on les fonts de vídeo publiquen (`rtsp://<host>:8554/cam{id}`)
- `8888` HLS — d'on el frontend consumeix (`http://<host>:8888/cam{id}/index.m3u8`)

## Credencials RTSP

Cada font ha d'incloure `user={camera_id}` i `password={publish_token}` a la
URL RTSP de publicació (`rtsp://camera_id:publish_token@host:8554/cam{id}`),
tant si publica amb `ffmpeg` (worker simulador) com amb GStreamer
`rtspclientsink` (Jetson, propietats `user-id`/`user-pw`).
