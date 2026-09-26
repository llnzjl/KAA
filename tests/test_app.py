import unittest, tempfile, os, sys, threading, json, urllib.request, urllib.error, http.cookiejar
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
server.AI_CONFIGURED=False
class API(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();server.DB=Path(cls.tmp.name)/'test.sqlite3';server.init();cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);cls.url='http://127.0.0.1:'+str(cls.http.server_port);threading.Thread(target=cls.http.serve_forever,daemon=True).start()
 @classmethod
 def tearDownClass(cls):cls.http.shutdown();cls.http.server_close();cls.tmp.cleanup()
 def setUp(self):self.client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()));server.LIMITS.clear()
 def request(self,path,data=None,origin=None):
  headers={'Content-Type':'application/json','X-KAA-Request':'1','Origin':origin or server.ORIGIN}
  req=urllib.request.Request(self.url+'/api/'+path,data=None if data is None else json.dumps(data).encode(),headers=headers)
  try:
   with self.client.open(req) as r:return r.status,json.loads(r.read())
  except urllib.error.HTTPError as e:return e.code,json.loads(e.read())
 def test_auth_persistence_logout(self):
  self.assertEqual(self.request('state')[0],401)
  self.assertEqual(self.request('register',{'email':'test@example.com','password':'LongPassword123!'})[0],200)
  self.assertEqual(self.request('profile',{'name':'Student','university':'snu','language':'fa'})[0],200)
  self.assertEqual(self.request('state')[1]['profile']['language'],'fa')
  self.assertEqual(self.request('logout',{})[0],200);self.assertEqual(self.request('state')[0],401)
  self.assertEqual(self.request('login',{'email':'test@example.com','password':'LongPassword123!'})[0],200)
 def test_csrf(self):self.assertEqual(self.request('demo',{},'https://evil.example')[0],403)
 def test_state_and_url_validation(self):
  self.request('demo',{});self.assertEqual(self.request('state',{'websites':[{'name':'bad','url':'javascript:alert(1)'}]})[0],400)
  self.assertEqual(self.request('state',{'websites':[{'id':'1','name':'Official','url':'https://www.snu.ac.kr/'}]})[0],200)
  self.assertEqual(self.request('state')[1]['state']['websites'][0]['name'],'Official')
 def test_account_isolation(self):
  self.request('demo',{});self.request('state',{'read':['private']});self.request('demo',{});self.assertEqual(self.request('state')[1]['state'],{})
 def test_consent(self):
  self.request('demo',{});self.assertEqual(self.request('chat',{'question':'Hi'})[1]['mode'],'offline-guide')
  self.request('profile',{'aiConsent':False});self.assertEqual(self.request('chat',{'question':'Hi'})[0],403)
  self.request('profile',{'aiConsent':True});self.assertEqual(self.request('chat',{'question':'Hi'})[1]['mode'],'offline-guide')
 def test_delete(self):
  self.request('demo',{});self.assertEqual(self.request('delete-account',{})[0],200);self.assertEqual(self.request('state')[0],401)
 def test_dates(self):
  self.request('demo',{});self.assertEqual(self.request('profile',{'visaExpiry':'bad'})[0],400)
 def test_content(self):
  c=self.request('content')[1];self.assertEqual(len(c['lessons']),12);self.assertEqual(len(c['universities']),2)
if __name__=='__main__':unittest.main()
