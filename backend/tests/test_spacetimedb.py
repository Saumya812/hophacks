"""Run with RUN_SPACETIME_TESTS=1 SPACETIMEDB_DATABASE=findmypal-test; publish test module first."""
import json, os, unittest
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import httpx
from database import SpacetimeDatabase, DatabaseError, get_database
BASE = dict(name='Test %_ Person', age=30, last_seen_location='Baltimore, MD', last_seen_date='2026-01-02', description='Integration test case')
class AdapterTest(unittest.TestCase):
    def test_retry(self):
        bodies=[]
        def request(req):
            bodies.append(req.content)
            if len(bodies)==1: raise httpx.ReadError('lost response')
            return httpx.Response(200,json=json.dumps({'data':[{'id':'ok'}]}))
        db=SpacetimeDatabase('http://test','test','test',client=httpx.Client(transport=httpx.MockTransport(request)))
        self.assertEqual(db.table('persons').insert(BASE).execute().data,[{'id':'ok'}])
        self.assertEqual(bodies[0],bodies[1])
@unittest.skipUnless(os.getenv('RUN_SPACETIME_TESTS')=='1','requires native test database')
class NativeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getenv('SPACETIMEDB_DATABASE')!='findmypal-test': raise RuntimeError('Refusing non-test database')
        cls.db=get_database()
    def setUp(self): self.pid=self.db.table('persons').insert(BASE).execute().data[0]['id']
    def tearDown(self): self.db.table('persons').delete().eq('id',self.pid).execute()
    def person(self): return self.db.table('persons').eq('id',self.pid).execute().data[0]
    def test_filters_timestamps_concurrent_increment(self):
        self.assertIsNone(self.person()['photo_url'])
        self.assertIn(self.pid,[r['id'] for r in self.db.table('persons').ilike('name',r'%\%\_%').execute().data])
        self.assertFalse(self.db.table('persons').eq('id',self.pid).not_.is_('photo_url','null').execute().data)
        stamp='2026-01-02T03:04:05.123456+00:00'
        self.db.table('persons').update({'last_verified_at':stamp}).eq('id',self.pid).execute()
        self.assertEqual(self.person()['last_verified_at'],stamp)
        with ThreadPoolExecutor(max_workers=5) as pool:
            list(pool.map(lambda _:self.db.table('persons').increment({'shares_count':1}).eq('id',self.pid).execute(),range(15)))
        self.assertEqual(self.person()['shares_count'],15)
    def test_counters_idempotency_cascade(self):
        write=self.db.table('sightings').insert(dict(person_id=self.pid,location_lat=39.,location_lng=-76.,date_time='2026-01-02T00:00:00Z',description='test tip',confidence_level=3))
        self.assertEqual(write.execute().data,write.execute().data)
        self.assertEqual(self.person()['tips_count'],1)
        data=dict(person_id=self.pid,kind='case_watch',email='test@example.com',active=True)
        watch=self.db.table('alert_subscriptions').insert(data).execute().data[0]
        self.assertEqual(self.person()['watchers_count'],1)
        with self.assertRaises(DatabaseError): self.db.table('alert_subscriptions').insert({**data,'email':'TEST@example.com'}).execute()
        self.db.table('alert_subscriptions').update({'active':False}).eq('id',watch['id']).execute()
        self.assertEqual(self.person()['watchers_count'],0)
        self.db.table('persons').delete().eq('id',self.pid).execute()
        for name in ['sightings','alert_subscriptions']:
            self.assertFalse(self.db.table(name).eq('person_id',self.pid).execute().data)
    def test_rollback(self):
        first=str(uuid4())
        with self.assertRaises(DatabaseError): self.db.table('case_updates').insert([dict(id=first,person_id=self.pid,body='valid'),dict(person_id=str(uuid4()),body='invalid')]).execute()
        self.assertFalse(self.db.table('case_updates').eq('id',first).execute().data)
    def test_secondary_tables(self):
        samples={
            'case_updates':dict(person_id=self.pid,body='update'),
            'case_coordinators':dict(person_id=self.pid,email='coord@example.com',role='coordinator'),
            'tip_clusters':dict(person_id=self.pid,center_lat=39.,center_lng=-76.,tip_count=3,window_start='2026-01-01T00:00:00Z',window_end='2026-01-02T00:00:00Z'),
            'profile_flags':dict(person_id=self.pid,reason='test'),
            'search_memory':dict(participant_key=str(uuid4()),filters_json={'age_min':18,'city':'Baltimore'}),
            'email_outbox_log':dict(to_email='test@example.com',subject='Test',body='Test',meta={'nested':[1,True,None]}),
            'live_tip_events':dict(person_id=self.pid,person_name='Test',snippet='test'),
            'case_source_links':dict(person_id=self.pid,title='Test source',url='https://example.org/test',source_type='agency_listing'),
            'users':dict(email=str(uuid4())+'@example.com',role='public')}
        for name,data in samples.items():
            with self.subTest(table=name):
                row=self.db.table(name).insert(data).execute().data[0]
                try:
                    loaded=self.db.table(name).eq('id',row['id']).execute().data[0]
                    for key,value in data.items(): self.assertEqual(loaded[key],value)
                finally: self.db.table(name).delete().eq('id',row['id']).execute()
    def test_anonymous_permissions(self):
        base=f'{self.db.uri}/v1/database/{self.db.database}'
        with httpx.Client() as client:
            self.assertFalse(client.post(base+'/sql',content='SELECT * FROM persons').is_success)
            self.assertFalse(client.post(base+'/call/execute_query',json=[json.dumps({'table':'persons','operation':'select'})]).is_success)
            self.assertTrue(client.post(base+'/sql',content='SELECT * FROM case_activity').is_success)
    def test_fastapi_lifecycle(self):
        from fastapi.testclient import TestClient
        from main import app
        with TestClient(app) as client, patch('routers.persons.notify_zip_alerts_for_new_case',return_value=0):
            result=client.post('/persons',json={**BASE,'contact_email':'family@example.com'})
            self.assertEqual(result.status_code,201,result.text)
            row=result.json(); pid=row['id']; token=row['owner_token']; headers={'X-Owner-Token':token}
            try:
                self.assertTrue(token)
                public=client.get('/persons/'+pid).json()
                self.assertIsNone(public['owner_token']); self.assertIsNone(public['contact_email'])
                self.assertEqual(client.post('/persons/'+pid+'/renew').status_code,403)
                self.assertEqual(client.post('/persons/'+pid+'/renew',headers=headers).status_code,200)
                with patch('routers.sightings.score_sighting_credibility',return_value={'credibility_score':5,'family_review_flag':False,'reasons':['test']}),patch('routers.sightings.match_nl_alerts_against_tip',return_value=None):
                    tip=client.post('/persons/'+pid+'/sightings',json=dict(location_lat=39.,location_lng=-76.,date_time='2026-01-02T03:04:05Z',description='Test observation near station',confidence_level=3))
                    self.assertEqual(tip.status_code,201,tip.text)
                self.assertEqual(client.get('/persons/'+pid).json()['tips_count'],1)
                found=client.post('/persons/'+pid+'/found',json={'message':'Found safely'},headers=headers)
                self.assertEqual(found.status_code,200,found.text)
                self.assertNotIn(pid,[r['id'] for r in client.get('/persons').json()['persons']])
                self.assertEqual(client.get('/health/database').status_code,200)
            finally: self.db.table('persons').delete().eq('id',pid).execute()
