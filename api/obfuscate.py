from http.server import BaseHTTPRequestHandler
import json, base64, subprocess, tempfile, os

BIN = os.path.join(os.path.dirname(__file__), 'luajit')

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            n = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(n)
            try:
                data = json.loads(raw)
                code  = data.get('code', '')
                strip = bool(data.get('strip', True))
            except Exception:
                code, strip = raw.decode('utf-8', 'replace'), True

            if not code.strip():
                return self._j({'ok': False, 'error': 'kode kosong'})

            if not os.path.exists(BIN):
                return self._j({'ok': False, 'error': 'binary luajit belum ada, tunggu action selesai'})

            with tempfile.TemporaryDirectory() as td:
                src = os.path.join(td, 'in.lua')
                out = os.path.join(td, 'out.luac')
                with open(src, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(code)

                os.chmod(BIN, 0o755)
                cmd = [BIN, "-b"]
                if strip: cmd.append('-s')
                cmd += [src, out]

                r = subprocess.run(cmd, capture_output=True, timeout=8)
                if r.returncode != 0:
                    err = (r.stderr or b'').decode('utf-8', 'replace') or 'luajit gagal'
                    return self._j({'ok': False, 'error': err.strip()})

                with open(out, 'rb') as f:
                    bc = f.read()

            self._j({
                'ok':   True,
                'size': len(bc),
                'b64':  base64.b64encode(bc).decode(),
                'lua':  ''.join('\\%03d' % b for b in bc),
                'hex':  bc.hex(),
            })
        except subprocess.TimeoutExpired:
            self._j({'ok': False, 'error': 'timeout'})
        except Exception as e:
            self._j({'ok': False, 'error': str(e)})

    def _j(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a): pass
