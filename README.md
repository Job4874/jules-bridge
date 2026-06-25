# Jules Bridge

Local Flask bridge for shell, filesystem, and desktop automation, exposed via ngrok.

## Setup

```powershell
pip install -r requirements.txt
ngrok config add-authtoken <YOUR_NGROK_AUTHTOKEN>
```

## Run

```powershell
$env:PYTHONIOENCODING='utf-8'
python start.py
```

The bootstrapper starts `bridge.py` on port 5000 and opens an ngrok tunnel.

## Endpoints

- `GET /ping` — health check
- `POST /shell` — run PowerShell commands
- `POST /fs/read` — read a local file
- `POST /fs/write` — write a local file
- `GET /ui/screenshot` — desktop screenshot (base64)
- `POST /ui/click` — mouse click
- `POST /ui/type` — keyboard input
