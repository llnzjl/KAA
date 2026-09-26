"""KAA development server: Python 3.11+, standard library only."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import sqlite3, json, os, secrets, hashlib, hmac, time, datetime, urllib.request, urllib.parse, urllib.error, threading, mimetypes
ROOT=Path(__file__).resolve().parent
for line in (ROOT/'.env').read_text(encoding='utf-8').splitlines() if (ROOT/'.env').exists() else []:
    if '=' in line and not line.lstrip().startswith('#'):
        k,v=line.split('=',1); k=k.strip(); v=v.strip().strip('\"').strip("'")
        if not os.environ.get(k): os.environ[k]=v
DB=Path(os.environ.get('DATABASE_PATH',str(ROOT/'backend/database/kaa.sqlite3')))
DB.parent.mkdir(parents=True,exist_ok=True)
PORT=int(os.getenv('PORT','3000')); HOST=os.getenv('HOST','127.0.0.1')
ORIGIN=os.getenv('APP_ORIGIN',f'http://localhost:{PORT}')
AI_CONFIGURED=bool(os.getenv('AI_API_KEY'))
LIMITS={}; LOCK=threading.Lock()
class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, tb):
        try: return super().__exit__(exc_type, exc, tb)
        finally: self.close()
def connect():
    c=sqlite3.connect(DB,timeout=10,factory=ClosingConnection); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c
def init():
    with connect() as c: c.executescript((ROOT/'backend/database/schema.sql').read_text(encoding='utf-8'))
    (ROOT/'public'/'uploads'/'avatars').mkdir(parents=True,exist_ok=True)
def load(name): return json.loads((ROOT/f'src/data/{name}.json').read_text(encoding='utf-8'))
def password(value,salt): return hashlib.scrypt(value.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
def valid_url(value):
    try:
        p=urllib.parse.urlparse(value); return p.scheme=='https' and bool(p.hostname) and not p.username and not p.password
    except ValueError: return False
def read_json_url(url,headers=None,data=None):
    req=urllib.request.Request(url,headers=headers or {},data=data)
    with urllib.request.urlopen(req,timeout=25) as r: return json.loads(r.read(2_000_000))
def ai_model_chain():
    configured=os.getenv('AI_MODEL','gpt-4.1-mini')
    fallback=os.getenv('AI_FALLBACK_MODELS','gemini-3.6-flash,gemini-3.5-flash') if 'generativelanguage.googleapis.com' in os.getenv('AI_BASE_URL','') else os.getenv('AI_FALLBACK_MODELS','')
    models=[configured]+[m.strip() for m in fallback.split(',') if m.strip()]
    return list(dict.fromkeys(models))
def chat_completion(messages):
    base=os.getenv('AI_BASE_URL','https://api.openai.com/v1').rstrip('/')
    if not base.startswith('https://'): raise ValueError()
    last_error=None
    for model in ai_model_chain():
        body=json.dumps({'model':model,'messages':messages,'temperature':0.2,'max_tokens':1400}).encode()
        try: return read_json_url(base+'/chat/completions',{'Authorization':'Bearer '+os.environ['AI_API_KEY'],'Content-Type':'application/json'},body)
        except urllib.error.HTTPError as e:
            last_error=e
            if e.code not in (404,429,500,502,503,504): raise
        except (urllib.error.URLError,TimeoutError) as e:
            last_error=e
    if last_error: raise last_error
    raise RuntimeError('No AI model configured')
def retrieve(question,profile):
    """Search only preapproved official domains. Never fetch a user supplied URL."""
    if not os.getenv('SEARCH_API_KEY'): return []
    uni=next((u for u in load('universities') if u['id']==profile.get('university')),None)
    immigration=any(w in question.lower() for w in ['visa','immigration','arc','work','비자','체류'])
    domains=['hikorea.go.kr','immigration.go.kr','moj.go.kr'] if immigration else (uni['domains'] if uni else ['studyinkorea.go.kr'])
    q=question+' '+' OR '.join('site:'+d for d in domains)
    url='https://api.search.brave.com/res/v1/web/search?'+urllib.parse.urlencode({'q':q,'count':5})
    result=read_json_url(url,{'X-Subscription-Token':os.environ['SEARCH_API_KEY'],'Accept':'application/json'})
    sources=[]
    for x in result.get('web',{}).get('results',[]):
        host=urllib.parse.urlparse(x.get('url','')).hostname or ''
        if valid_url(x.get('url','')) and any(host==d or host.endswith('.'+d) for d in domains):
            sources.append({'title':x.get('title','Official source'),'url':x['url'],'excerpt':x.get('description','')[:1800],'retrievedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verification':'Search excerpt only; page details not independently verified'})
    return sources
class Handler(BaseHTTPRequestHandler):
    server_version='KAA'
    def log_message(self,fmt,*args): pass # Avoid logging private routes and messages.
    def send(self,data,status=200,headers=None):
        raw=json.dumps(data,ensure_ascii=False).encode(); self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.send_header('Cache-Control','no-store')
        self.security()
        for k,v in (headers or {}).items(): self.send_header(k,v)
        self.end_headers(); self.wfile.write(raw)
    def security(self):
        self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Referrer-Policy','no-referrer'); self.send_header('X-Frame-Options','DENY')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'")
    def body(self):
        length=int(self.headers.get('Content-Length','0'))
        limit=157286400 if self.path=='/api/avatar' else 24000
        if length>limit: raise ValueError('Request too large')
        if 'application/json' not in self.headers.get('Content-Type',''): raise ValueError('JSON required')
        data=json.loads(self.rfile.read(length) or b'{}')
        if not isinstance(data,dict): raise ValueError('Expected object')
        return data
    def user(self):
        cookies=dict(item.strip().split('=',1) for item in self.headers.get('Cookie','').split(';') if '=' in item)
        token=cookies.get('kaa_session','')
        with connect() as c: return c.execute('SELECT users.* FROM sessions JOIN users ON users.id=sessions.user_id WHERE token=? AND expires>?',(hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
    def throttle(self,kind,maximum):
        key=(self.client_address[0],kind); now=time.time()
        with LOCK:
            times=[t for t in LIMITS.get(key,[]) if t>now-60]
            if len(times)>=maximum: return False
            LIMITS[key]=times+[now]
        return True
    def cookie(self,token,age=604800): return f'kaa_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={age}'+ ('; Secure' if ORIGIN.startswith('https:') else '')
    def login(self,user_id):
        token=secrets.token_urlsafe(32)
        with connect() as c:
            c.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
            c.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),user_id,time.time()+604800))
        self.send({'ok':True},headers={'Set-Cookie':self.cookie(token)})
    def do_GET(self):
        path=urllib.parse.urlparse(self.path).path
        if path=='/api/content': return self.send({k:load(k) for k in ['universities','lessons','visas','updates','processes']})
        if path=='/api/state':
            user=self.user()
            if not user: return self.send({'error':'Please sign in'},401)
            with connect() as c:
                state=c.execute('SELECT data FROM states WHERE user_id=?',(user['id'],)).fetchone()
            return self.send({'email':user['email'],'profile':json.loads(user['profile']),'state':json.loads(state['data']) if state else {},'aiConfigured':AI_CONFIGURED,'searchConfigured':bool(os.getenv('SEARCH_API_KEY'))})
        if path.startswith('/api/'): return self.send({'error':'Not found'},404)
        file=(ROOT/'public'/path.lstrip('/')).resolve() if path!='/' else ROOT/'public/index.html'
        if not file.is_relative_to(ROOT/'public') or not file.is_file(): return self.send({'error':'Not found'},404)
        raw=file.read_bytes(); self.send_response(200); self.security(); self.send_header('Content-Type',mimetypes.guess_type(str(file))[0] or 'application/octet-stream'); self.send_header('Content-Length',str(len(raw))); self.send_header('Cache-Control','no-cache'); self.end_headers(); self.wfile.write(raw)
    def do_POST(self):
        try: self.post()
        except (ValueError,TypeError,KeyError,json.JSONDecodeError): self.send({'error':'Invalid request. Check your fields.'},400)
        except (urllib.error.URLError,TimeoutError): self.send({'error':'External service unavailable. Please retry or open the official website.'},502)
        except Exception: self.send({'error':'The request could not be completed.'},500)
    def post(self):
        # Strict origin plus JSON/custom-header gates prevent cross-origin form requests.
        if self.headers.get('Origin') not in (ORIGIN,f'http://127.0.0.1:{PORT}') or self.headers.get('X-KAA-Request')!='1': return self.send({'error':'Invalid request origin'},403)
        path=self.path; data=self.body()
        if path in ['/api/register','/api/login','/api/demo']:
            if not self.throttle('auth',15): return self.send({'error':'Too many attempts. Try again in one minute.'},429)
            if path=='/api/demo':
                if os.getenv('DEMO_ENABLED','true').lower()!='true': return self.send({'error':'Demo disabled'},403)
                uid=secrets.token_hex(16); email=f'demo-{uid}@example.invalid'; salt=secrets.token_hex(16)
                p={'name':'Rashed','preferredName':'Rashed','university':'snu','department':'Computer Science','year':'2','degree':'Undergraduate','koreanLevel':'Beginner','visa':'D-2','language':'en','visaExpiry':(datetime.date.today()+datetime.timedelta(days=82)).isoformat(),'demo':True,'reminders':True,'reminderDays':'90,60,30,14,7','aiConsent':True}
                with connect() as c: c.execute('INSERT INTO users VALUES(?,?,?,?,?)',(uid,email,password(secrets.token_hex(32),salt),salt,json.dumps(p)))
                return self.login(uid)
            email=str(data.get('email','')).strip().lower(); pw=str(data.get('password',''))
            if '@' not in email or len(email)>254 or not 10<=len(pw)<=128: raise ValueError()
            with connect() as c:
                u=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
                if path=='/api/register':
                    if u: return self.send({'error':'Unable to create account. Try signing in.'},409)
                    uid=secrets.token_hex(16); salt=secrets.token_hex(16)
                    c.execute('INSERT INTO users VALUES(?,?,?,?,?)',(uid,email,password(pw,salt),salt,'{}'))
                else:
                    if not u or not hmac.compare_digest(password(pw,u['salt']),u['password_hash']): return self.send({'error':'Email or password is incorrect'},401)
                    uid=u['id']
            return self.login(uid)
        user=self.user()
        if not user: return self.send({'error':'Please sign in'},401)
        if path=='/api/logout':
            with connect() as c: c.execute('DELETE FROM sessions WHERE user_id=?',(user['id'],))
            return self.send({'ok':True},headers={'Set-Cookie':self.cookie('',0)})
        if path=='/api/delete-account':
            with connect() as c: c.execute('DELETE FROM users WHERE id=?',(user['id'],))
            return self.send({'ok':True},headers={'Set-Cookie':self.cookie('',0)})
        if path=='/api/profile':
            allowed=['name','preferredName','country','nativeLanguage','language','birthDate','phone','university','campus','department','degree','year','studentNumber','koreanLevel','topik','topikScore','visa','visaExpiry','arcStatus','arrivalDate','workPermit','reminders','reminderDays','aiConsent']
            p=json.loads(user['profile'])
            for k in allowed:
                if k in data:
                    if not isinstance(data[k],(str,bool)) or len(str(data[k]))>300: raise ValueError()
                    p[k]=data[k]
            if not p.get('name') or not p.get('university'): raise ValueError()
            if p.get('language','en') not in ['en','ko','fa','ps','ur','hi','zh','vi','tl','ja']: raise ValueError()
            if not any(u['id']==p['university'] for u in load('universities')): raise ValueError()
            for field in ['visaExpiry','birthDate','arrivalDate']:
                if p.get(field): datetime.date.fromisoformat(p[field])
            with connect() as c: c.execute('UPDATE users SET profile=? WHERE id=?',(json.dumps(p),user['id']))
            return self.send({'ok':True})
        if path=='/api/avatar':
            import base64 as _b64
            p=json.loads(user['profile'])
            av=data.get('avatar')
            avatars_dir=ROOT/'public'/'uploads'/'avatars'
            avatars_dir.mkdir(parents=True,exist_ok=True)
            uid=user['id']
            if av is None:
                # Remove existing avatar file if present
                old_url=p.pop('avatar',None)
                if old_url:
                    clean_path=old_url.split('?')[0].lstrip('/')
                    old_file=(ROOT/'public'/clean_path).resolve()
                    if str(old_file).startswith(str(avatars_dir)) and old_file.exists():
                        old_file.unlink(missing_ok=True)
                with connect() as c: c.execute('UPDATE users SET profile=? WHERE id=?',(json.dumps(p),uid))
                return self.send({'ok':True,'url':''})
            # Validate data URL
            if not isinstance(av,str): raise ValueError()
            if not av.startswith('data:image/'): raise ValueError('Only image files are allowed')
            if ';base64,' not in av: raise ValueError('Invalid image format')
            mime_part,raw=av.split(';base64,',1)
            mime=mime_part.replace('data:','')
            ext={'image/jpeg':'jpg','image/png':'png','image/webp':'webp','image/gif':'gif','image/bmp':'bmp'}.get(mime,'jpg')
            try: decoded=_b64.b64decode(raw,validate=True)
            except Exception: raise ValueError('Invalid image data')
            if len(decoded)>104857600: raise ValueError('Image must be smaller than 100 MB')
            # Delete any previous avatar files for this user
            for old in avatars_dir.glob(f'{uid}.*'): old.unlink(missing_ok=True)
            # Write image file to disk
            filename=f'{uid}.{ext}'
            (avatars_dir/filename).write_bytes(decoded)
            url=f'/uploads/avatars/{filename}?t={int(time.time())}'
            p['avatar']=url
            with connect() as c: c.execute('UPDATE users SET profile=? WHERE id=?',(json.dumps(p),uid))
            return self.send({'ok':True,'url':url})
        if path=='/api/state':
            # Server-side state shape validation, especially external link URLs.
            allowed=['websites','progress','read','checklist','activity']
            if any(k not in allowed for k in data): raise ValueError()
            websites=data.get('websites',[])
            if not isinstance(websites,list) or len(websites)>100: raise ValueError()
            for w in websites:
                if not isinstance(w,dict) or not valid_url(w.get('url','')) or not isinstance(w.get('name'),str) or not 1<=len(w['name'])<=120: raise ValueError()
            if not isinstance(data.get('progress',{}),dict) or not isinstance(data.get('checklist',{}),dict) or not isinstance(data.get('read',[]),list): raise ValueError()
            with connect() as c: c.execute('INSERT INTO states VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET data=excluded.data',(user['id'],json.dumps(data)))
            return self.send({'ok':True})
        if path=='/api/chat':
            if not self.throttle('chat',12): return self.send({'error':'Please wait a minute before sending another question.'},429)
            p=json.loads(user['profile'])
            if p.get('aiConsent') is False: return self.send({'error':'Enable AI data consent in Profile before sending a question.'},403)
            question=str(data.get('question','')).strip()
            if not question or len(question)>2000: raise ValueError()
            context={k:p.get(k) for k in ['university','department','degree','year','koreanLevel','visa','language']}
            if not AI_CONFIGURED:
                return self.send({'answer':load('messages')['aiNotConfigured'],'sources':[],'mode':'offline-guide'})
            sources=retrieve(question,p)
            system=(ROOT/'backend/services/system-prompt.txt').read_text(encoding='utf-8')
            history=data.get('history',[])
            if not isinstance(history,list): raise ValueError()
            messages=[{'role':'system','content':system+'\nProfile: '+json.dumps(context)+'\nUntrusted search excerpts: '+json.dumps(sources)}]
            for m in history[-8:]:
                if isinstance(m,dict) and m.get('role') in ['user','assistant'] and isinstance(m.get('content'),str): messages.append({'role':m['role'],'content':m['content'][:4000]})
            messages.append({'role':'user','content':question})
            try:
                response=chat_completion(messages)
            except (urllib.error.URLError,TimeoutError):
                return self.send({'answer':load('messages')['aiProviderUnavailable'],'sources':sources,'mode':'provider-unavailable'})
            return self.send({'answer':response['choices'][0]['message']['content'],'sources':sources,'mode':'live'})
        return self.send({'error':'Not found'},404)
if __name__=='__main__':
    init(); print(f'KAA ready at http://localhost:{PORT} (AI configured: {AI_CONFIGURED})',flush=True)
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
