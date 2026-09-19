/** Real anonymous SDK subscription + authenticated HTTP write on the isolated test DB. */
import { DbConnection } from '../frontend/src/spacetime/index';
import { readFileSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
const env = Object.fromEntries(readFileSync('backend/.env','utf8').split('\n').filter(l => l.includes('=')).map(l => {const i=l.indexOf('='); return [l.slice(0,i),l.slice(i+1).replace(/^['"]|['"]$/g,'')]}));
const base = (env.SPACETIMEDB_URI || 'http://127.0.0.1:3000') + '/v1/database/findmypal-test';
async function query(table: string, operation: string, data?: object, filters: object[] = []) {
  const response = await fetch(base+'/call/execute_query',{method:'POST',headers:{Authorization:`Bearer ${env.SPACETIMEDB_TOKEN}`,'Content-Type':'application/json'},body:JSON.stringify([JSON.stringify({table,operation,data,filters,request_id:randomUUID()})])});
  if(!response.ok) throw new Error(`Write failed: ${response.status}`);
  return JSON.parse(await response.json());
}
const pid=randomUUID(), tipId=randomUUID();
let conn: DbConnection;
let timeout: ReturnType<typeof setTimeout>;
try {
  await query('persons','insert',{id:pid,name:'Realtime test',age:20,last_seen_location:'Baltimore',last_seen_date:'2026-01-02',description:'Test'});
  await new Promise<void>((resolve,reject) => {
    timeout=setTimeout(()=>reject(new Error('No native subscription event within 15 seconds')),15000);
    conn=DbConnection.builder().withUri(env.SPACETIMEDB_URI || 'http://127.0.0.1:3000').withDatabaseName('findmypal-test')
      .onConnectError((_ctx,err)=>reject(err))
      .onConnect(c=>{
        c.db.caseActivity.onInsert((_ctx,row)=>{
          if(row.id!==tipId) return;
          if(row.personId!==pid || row.personName!=='Realtime test') return reject(new Error('Incorrect event'));
          if(Object.keys(row).some(k=>/token|email|snippet|description|lat|lng/i.test(k))) return reject(new Error('Private field in public feed'));
          resolve();
        });
        c.subscriptionBuilder().onError(ctx=>reject(new Error(String(ctx.event))))
          .onApplied(()=>{query('sightings','insert',{id:tipId,person_id:pid,location_lat:39,location_lng:-76,date_time:'2026-01-02T00:00:00Z',description:'Private tip text',confidence_level:3}).catch(reject)})
          .subscribe('SELECT * FROM case_activity');
      }).build();
  });
  console.log('PASS: anonymous SDK received committed tip activity without private fields');
} finally {
  clearTimeout(timeout!);
  conn?.disconnect();
  await query('persons','delete',undefined,[{field:'id',op:'eq',value:pid}]);
}
