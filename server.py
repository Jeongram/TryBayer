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

    def do_OPTIONS(self):
        # CORS preflight
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

    def do_GET(self):
        # ── /api/ranking → 라쿠텐 랭킹 API 프록시
        if self.path.startswith('/api/ranking'):
            self.proxy_rakuten()
        # ── /api/search → 라쿠텐 상품검색 API 프록시
        elif self.path.startswith('/api/search'):
            self.proxy_rakuten_search()
        # ── /api/genre → 라쿠텐 장르 탐색 API 프록시
        elif self.path.startswith('/api/genre'):
            self.proxy_rakuten_genre()
        # ── /api/shopee → Shopee 비공식 프론트엔드 API 프록시
        elif self.path.startswith('/api/shopee'):
            self.proxy_shopee()
        # ── /api/amazon → Amazon PA-API 프록시
        elif self.path.startswith('/api/amazon'):
            self.proxy_amazon()
        # ── /api/domeggook → 도매꾹 상품조회 API 프록시
        elif self.path.startswith('/api/domeggook'):
            self.proxy_domeggook()
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

            # 추가 파라미터
            genre_id = params.get('genreId', [''])[0]
            sex      = params.get('sex',     [''])[0]   # 0=전체,1=남,2=여
            age      = params.get('age',     [''])[0]

            # 라쿠텐 API 호출
            rakuten_url = (
                f"https://openapi.rakuten.co.jp/ichibaranking/api/IchibaItem/Ranking/20220601"
                f"?format=json&applicationId={urllib.parse.quote(app_id)}"
                f"&accessKey={urllib.parse.quote(access_key)}"
                f"&hits={hits}&formatVersion=2"
            )
            if genre_id:
                rakuten_url += f"&genreId={urllib.parse.quote(genre_id)}"
            if sex:
                rakuten_url += f"&sex={urllib.parse.quote(sex)}"
            if age:
                rakuten_url += f"&age={urllib.parse.quote(age)}"

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

    def proxy_rakuten_genre(self):
        """라쿠텐 장르 탐색 API 프록시 (applicationId만 필요)"""
        try:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            app_id   = params.get('applicationId', [''])[0]
            genre_id = params.get('genreId', ['0'])[0]

            if not app_id:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'applicationId 필요'}).encode())
                return

            url = (
                f"https://app.rakuten.co.jp/services/api/IchibaGenre/Search/20120723"
                f"?format=json&applicationId={urllib.parse.quote(app_id)}&genreId={genre_id}"
            )
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'TryBayer/1.0')

            with urllib.request.urlopen(req, timeout=10) as res:
                data = res.read()

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

    def proxy_rakuten_search(self):
        """라쿠텐 상품검색 API 프록시 (키워드 + 인기순)"""
        try:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)

            app_id   = params.get('applicationId', [''])[0]
            keyword  = params.get('keyword', [''])[0]
            hits     = params.get('hits', ['5'])[0]
            sort     = params.get('sort', ['-reviewCount'])[0]
            genre_id = params.get('genreId', [''])[0]

            if not app_id or not keyword:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'applicationId와 keyword가 필요합니다.'}).encode())
                return

            search_url = (
                f"https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601"
                f"?format=json&formatVersion=2"
                f"&applicationId={urllib.parse.quote(app_id)}"
                f"&keyword={urllib.parse.quote(keyword)}"
                f"&hits={hits}"
                f"&sort={urllib.parse.quote(sort)}"
            )
            if genre_id:
                search_url += f"&genreId={urllib.parse.quote(genre_id)}"

            req = urllib.request.Request(search_url)
            req.add_header('User-Agent', 'TryBayer/1.0')

            with urllib.request.urlopen(req, timeout=10) as res:
                data = res.read()

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

    def proxy_shopee(self):
        """Shopee 비공식 프론트엔드 API 프록시 (인증 불필요)"""
        try:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            keyword  = params.get('keyword',  ['korean beauty'])[0]
            country  = params.get('country',  ['sg'])[0]
            limit    = params.get('limit',    ['20'])[0]

            # Shopee 공개 검색 API (프론트엔드에서 사용하는 동일 엔드포인트)
            url = (
                f"https://shopee.{country}/api/v4/search/search_items"
                f"?keyword={urllib.parse.quote(keyword)}"
                f"&limit={limit}&order=sales&page_type=search"
                f"&scenario=PAGE_GLOBAL_SEARCH&version=2"
            )

            req = urllib.request.Request(url)
            req.add_header('User-Agent',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/124.0.0.0 Safari/537.36')
            req.add_header('Referer',
                f'https://shopee.{country}/search?keyword={urllib.parse.quote(keyword)}')
            req.add_header('Accept', 'application/json')
            req.add_header('Accept-Language', 'en-US,en;q=0.9,ko;q=0.8')
            req.add_header('X-Requested-With', 'XMLHttpRequest')
            req.add_header('af-ac-enc-dat', 'null')

            with urllib.request.urlopen(req, timeout=12) as res:
                raw = res.read()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(raw)

        except Exception as e:
            # 실패 시 fallback 신호 반환 (HTML은 demo 데이터로 graceful 처리)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'error': str(e),
                'fallback': True,
                'items': []
            }).encode())

    def proxy_amazon(self):
        """Amazon PA-API 5.0 프록시 (AccessKey + SecretKey 필요)"""
        try:
            import hmac, hashlib, datetime, base64

            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)

            access_key = params.get('accessKey', [''])[0]
            secret_key = params.get('secretKey', [''])[0]
            partner_tag = params.get('partnerTag', [''])[0]
            keyword     = params.get('keyword',   ['korean beauty'])[0]
            marketplace = params.get('marketplace', ['www.amazon.com'])[0]

            if not access_key or not secret_key or not partner_tag:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': 'accessKey, secretKey, partnerTag 가 모두 필요합니다.',
                    'needsSetup': True
                }).encode())
                return

            # PA-API 5.0 SearchItems 요청
            host    = 'webservices.amazon.com'
            region  = 'us-east-1'
            service = 'ProductAdvertisingAPI'
            endpoint = f'https://{host}/paapi5/searchitems'

            now = datetime.datetime.utcnow()
            amz_date  = now.strftime('%Y%m%dT%H%M%SZ')
            date_stamp = now.strftime('%Y%m%d')

            payload = json.dumps({
                "Keywords": keyword,
                "Marketplace": marketplace,
                "PartnerTag": partner_tag,
                "PartnerType": "Associates",
                "Resources": [
                    "ItemInfo.Title",
                    "ItemInfo.ByLineInfo",
                    "Offers.Listings.Price",
                    "BrowseNodeInfo.BrowseNodes"
                ]
            })

            # AWS Signature V4
            content_type = 'application/json; charset=UTF-8'
            target = 'com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems'

            canonical_headers = (
                f'content-encoding:amz-1.0\n'
                f'content-type:{content_type}\n'
                f'host:{host}\n'
                f'x-amz-date:{amz_date}\n'
                f'x-amz-target:{target}\n'
            )
            signed_headers = 'content-encoding;content-type;host;x-amz-date;x-amz-target'

            payload_hash = hashlib.sha256(payload.encode()).hexdigest()
            canonical_req = '\n'.join([
                'POST', '/paapi5/searchitems', '',
                canonical_headers, signed_headers, payload_hash
            ])

            credential_scope = f'{date_stamp}/{region}/{service}/aws4_request'
            string_to_sign = '\n'.join([
                'AWS4-HMAC-SHA256', amz_date, credential_scope,
                hashlib.sha256(canonical_req.encode()).hexdigest()
            ])

            def sign(key, msg):
                return hmac.new(key, msg.encode(), hashlib.sha256).digest()

            signing_key = sign(
                sign(sign(sign(
                    f'AWS4{secret_key}'.encode(), date_stamp),
                    region), service),
                'aws4_request'
            )
            signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()
            authorization = (
                f'AWS4-HMAC-SHA256 Credential={access_key}/{credential_scope}, '
                f'SignedHeaders={signed_headers}, Signature={signature}'
            )

            req = urllib.request.Request(endpoint, data=payload.encode(), method='POST')
            req.add_header('content-encoding', 'amz-1.0')
            req.add_header('content-type', content_type)
            req.add_header('host', host)
            req.add_header('x-amz-date', amz_date)
            req.add_header('x-amz-target', target)
            req.add_header('Authorization', authorization)

            with urllib.request.urlopen(req, timeout=15) as res:
                raw = res.read()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(raw)

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

    def proxy_domeggook(self):
        """도매꾹 OpenAPI 상품조회 프록시 (ver 4.1)"""
        try:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)

            api_key = params.get('aid', [''])[0]
            keyword = params.get('kw', [''])[0]
            size    = params.get('sz', ['20'])[0]
            page    = params.get('pg', ['1'])[0]
            sort    = params.get('so', ['rd'])[0]
            org     = params.get('org', [''])[0]   # kr=국내산, fr=국외산
            market  = params.get('market', ['dome'])[0]

            if not api_key:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'aid(API Key) 가 필요합니다.', 'needsSetup': True}).encode())
                return

            # 도매꾹 API URL 구성
            url = (
                f"https://domeggook.com/ssl/api/"
                f"?ver=4.1&mode=getItemList"
                f"&aid={urllib.parse.quote(api_key)}"
                f"&market={market}"
                f"&om=json"
                f"&sz={size}&pg={page}&so={sort}"
            )
            if keyword:
                url += f"&kw={urllib.parse.quote(keyword)}"
            if org:
                url += f"&org={org}"

            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'TryBayer/1.0')
            req.add_header('Accept', 'application/json')

            with urllib.request.urlopen(req, timeout=12) as res:
                raw = res.read()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(raw)

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
        # 깔끔한 로그 출력 (args 개수 안전하게 처리)
        try:
            print(f"  {' '.join(str(a) for a in args)}")
        except Exception:
            pass


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
