import {worker} from './index.ts';
const assert=(v:unknown)=>{if(!v)throw Error('assertion failed');};
const key='a'.repeat(64);
const env=(k:string)=>({SUPABASE_URL:'https://test.supabase.co',SUPABASE_SERVICE_ROLE_KEY:'server',FIREBASE_SERVICE_ACCOUNT_JSON:'fixture'} as Record<string,string>)[k];
const req=(auth='Bearer '+key)=>new Request('https://test/worker',{method:'POST',headers:{Authorization:auth}});
const json=(v:unknown,status=200)=>new Response(JSON.stringify(v),{status});
const access=()=>Promise.resolve({access:'fake',project:'fixture'});
Deno.test('worker rejects caller without key and ordinary user JWT',async()=>{
 let calls=0;
 const request=(()=>{calls++;return Promise.resolve(json('worker_unauthorized',400));}) as typeof fetch;
 assert((await worker(env,request,access)(req(''))).status===401 && calls===0);
 assert((await worker(env,request,access)(req('Bearer user-jwt'))).status===401 && calls===0);
 assert((await worker(env,request,access)(req('Bearer '+'b'.repeat(64)))).status===401 && calls===1);
});
Deno.test('cancelled reminder never calls FCM',async()=>{
 let fcm=0;let outcome='';
 const request=(async(url:string,init:RequestInit)=>{
  const body=JSON.parse(String(init.body));
  if(url.endsWith('claim_reminder_jobs')) return json([{id:'event',token:'own-token'}]);
  if(url.endsWith('prepare_reminder_job')) return json(false);
  if(url.endsWith('finish_reminder_job')){outcome=body.p_result;return json(null);}
  fcm++;return json({});
 }) as typeof fetch;
 assert((await worker(env,request,access)(req())).status===200);
 assert(fcm===0 && outcome==='cancelled');
});
Deno.test('fixed generic data-only event, bounded retry and ambiguous response',async()=>{
 for(const status of [200,429,400,0]) {
  let outcome='';
  const request=(async(url:string,init:RequestInit)=>{
   const body=JSON.parse(String(init.body));
   if(url.endsWith('claim_reminder_jobs'))return json([{id:'event-id',token:'own-token'}]);
   if(url.endsWith('prepare_reminder_job'))return json(true);
   if(url.endsWith('finish_reminder_job')){outcome=body.p_result;return json(null);}
   assert(body.message.token==='own-token' && !body.message.notification && body.message.data.event_id==='event-id');
   if(status===0)throw Error('timeout');
   return json({},status);
  }) as typeof fetch;
  await worker(env,request,access)(req());
  assert(outcome===({200:'sent',429:'retry',400:'failed',0:'uncertain'} as Record<number,string>)[status]);
 }
});

