"""
TryBayer — 로컬 프록시 서버
실행: python server.py
접속: http://localhost:8000
"""

import http.server
import urllib.request
import urllib.parse
import json
import os

PORT = int(os.environ.get('PORT', 8000))

class ProxyHandler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        # ── /api/ranking → 라쿠텐 API 프록시
        if self.path.startswith('/api/ranking'):
            self.proxy_rakuten()
        else:
            # 정적 파일 서빙 (HTML, CSS, JS 등)
            super().do_GET()

    def proxy_rakuten(self):
        try:
            # 쿼리 파라미터 파싱
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)

            app_id    = params.get('applicationId', [''])[0]
            access_key = params.get('accessKey', [''])[0]
            hits      = params.get('hits', ['30'])[0]

            if not app_id or not access_key:
                self.send_error(400, 'applicationId와 accessKey가 필요합니다.')
                return

            # 라쿠텐 API 호출
            rakuten_url = (
                f"https://openapi.rakuten.co.jp/ichibaranking/api/IchibaItem/Ranking/20220601"
                f"?format=json&applicationId={urllib.parse.quote(app_id)}"
                f"&accessKey={urllib.parse.quote(access_key)}"
                f"&hits={hits}&formatVersion=2"
            )

            req = urllib.request.Request(rakuten_url)
            req.add_header('User-Agent', 'TryBayer/1.0')
            req.add_header('Referer', 'https://test.com')
            req.add_header('Origin', 'https://test.com')

            with urllib.request.urlopen(req, timeout=10) as res:
                data = res.read()

            # CORS 헤더 추가 후 응답
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data)

        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='ignore')
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(err_body.encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def log_message(self, format, *args):
        # 깔끔한 로그 출력
        print(f"  {args[0]} {args[1]}")


if __name__ == '__main__':
    # HTML 파일이 있는 폴더에서 서버 실행
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print("=" * 50)
    print("  TryBayer — 로컬 서버 시작")
    print(f"  주소: http://localhost:{PORT}")
    print(f"  폴더: {os.getcwd()}")
    print("  종료: Ctrl+C")
    print("=" * 50)

    with http.server.HTTPServer(('0.0.0.0', PORT), ProxyHandler) as httpd:
        httpd.serve_forever()
