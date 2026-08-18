# NoorBrain Pi audio node deployment

Deploy from the NoorBrain repository without installing anything into the Pi's
system Python:

```bash
./tools/deploy_noorbrain_pi_audio_node.sh jshome@192.168.2.29
```

The deployer creates a 384-bit shared token on first use at
`~/.config/noorbrain/pi-audio-node.token`, transfers it without printing it,
and stores the Pi copy in `/etc/noorbrain/pi-audio-node.env` with mode `0600`.
Subsequent runs reuse the same token and are idempotent.

The service always runs with:

```text
~/Projects/NoorCameraNode/venv/bin/python
```

It installs and enables `/etc/systemd/system/noorbrain-pi-audio.service`, which
starts on boot and restarts on failure. The configured hardware remains:

- Playback: `plughw:CARD=Headphones,DEV=0`
- Capture: `plughw:CARD=Device,DEV=0`

In NoorBrain, open **Rooms & Speakers**, manage `existing-pi-audio`, paste the
token from the local token file into **Trust token**, and save. Updating the node
merges the token into the existing configuration; the node does not need to be
deleted or recreated. API responses expose only the `trusted` boolean, never the
stored token.
