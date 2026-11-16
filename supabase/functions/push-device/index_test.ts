import {handler as baseHandler} from './index.ts';
const tasks: Promise<unknown>[] = [];
const handler = (env: (key: string) => string | undefined, request = fetch) =>
  baseHandler(env, request, task => tasks.push(task), () => Promise.resolve());
const id = '10000000-0000-4000-8000-000000000001';
const owner = '10000000-0000-4000-8000-000000000002';
const assert = (value: unknown) => {if (!value) throw Error('assertion failed');};
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), {status});
const env = (key: string) => ({SUPABASE_URL: 'https://test.supabase.co', SUPABASE_ANON_KEY: 'public', SUPABASE_SERVICE_ROLE_KEY: 'server'} as Record<string,string>)[key];
const req = (body: unknown, auth = 'Bearer fixture') => new Request('https://test/push-device', {method:'POST', headers:{Authorization:auth}, body:JSON.stringify(body)});

Deno.test('plan publication checks own device and takes owner only from Auth', async () => {
  let published: Record<string,unknown>={};
  const request=(async (url:string,init:RequestInit)=>{
    if(url.endsWith('/user'))return json({id:owner,email_confirmed_at:'now'});
    if(url.includes('push_devices?')) {assert(url.includes('owner_id=eq.'+owner));return json([{device_id:id}]);}
    published=JSON.parse(String(init.body));return json({revision:4});
  }) as typeof fetch;
  const result=await handler(env,request)(req({action:'plan_save',device_id:id,owner_id:'victim',revision:3,
    payload:{enabled:true,timezone:'America/Santiago',routines:[]}}));
  assert(result.status===200 && published.p_owner===owner && published.p_revision===3);
});
Deno.test('unregistered device cannot enable calendar and conflicts are explicit', async () => {
  let publications=0;
  const request=(async(url:string)=>{
    if(url.endsWith('/user'))return json({id:owner,email_confirmed_at:'now'});
    if(url.includes('push_devices?'))return json([]);
    publications++;return new Response('plan_conflict',{status:400});
  }) as typeof fetch;
  const body={action:'plan_save',device_id:id,revision:0,payload:{enabled:true,timezone:'UTC',routines:[]}};
  assert((await handler(env,request)(req(body))).status===409 && publications===0);
  body.payload.enabled=false;
  const result=await handler(env,request)(req(body));
  assert(result.status===409 && (await result.json()).error==='plan_conflict');
});

Deno.test('unauthenticated caller cannot register or send', async () => {
  let calls = 0;
  const run = handler(env, (()=>{calls++; return Promise.resolve(json({},401));}) as typeof fetch);
  assert((await run(req({action:'test',device_id:id}, ''))).status === 401);
  assert(calls === 0);
  assert((await run(req({action:'test',device_id:id}))).status === 401);
  assert(calls === 1);
});
Deno.test('registration always uses authenticated owner, not supplied owner', async () => {
  let written: Record<string,unknown> = {};
  const request = (async (url: string, init: RequestInit) => {
    if(url.endsWith('/user')) return json({id:owner,email_confirmed_at:'now'});
    if(init.method === 'GET') return json([]);
    written = JSON.parse(String(init.body));
    return new Response(null,{status:204});
  }) as typeof fetch;
  const result = await handler(env, request)(req({action:'register',device_id:id,owner_id:'victim',token:'t'.repeat(64)}));
  assert(result.status===200 && written.p_owner===owner && written.p_device===id);
});
Deno.test('missing Firebase config does not consume quota or send', async () => {
  let calls=0;
  const request = (()=>{calls++;return Promise.resolve(json({id:owner,email_confirmed_at:'now'}));}) as typeof fetch;
  assert((await handler(env,request)(req({action:'test',device_id:id}))).status===503);
  assert(calls===1);
});
Deno.test('server enforces test cooldown before Google request', async () => {
  let calls=0;
  const request = (()=>{calls++;return Promise.resolve(calls===1 ? json({id:owner,email_confirmed_at:'now'}) : new Response('test_rate_limited',{status:400}));}) as typeof fetch;
  assert((await handler(k=>k==='FIREBASE_SERVICE_ACCOUNT_JSON'?'configured':env(k),request)(req({action:'test',device_id:id}))).status===429);
  assert(calls===2);
});
Deno.test('test sends fixed data-only message to stored token of authenticated account', async () => {
  const pair = await crypto.subtle.generateKey({name:'RSASSA-PKCS1-v1_5',modulusLength:2048,publicExponent:new Uint8Array([1,0,1]),hash:'SHA-256'},true,['sign','verify']);
  const pkcs8=new Uint8Array(await crypto.subtle.exportKey('pkcs8',pair.privateKey));
  const service=JSON.stringify({type:'service_account',project_id:'test-project',client_email:'fixture@test.invalid',private_key:'-----BEGIN PRIVATE KEY-----\n'+btoa(String.fromCharCode(...pkcs8))+'\n-----END PRIVATE KEY-----'});
  let message: Record<string,any> = {};
  const request = (async (url: string, init: RequestInit) => {
    if(url.endsWith('/user')) return json({id:owner,email_confirmed_at:'now'});
    if(url.includes('/rpc/')) {assert(JSON.parse(String(init.body)).p_owner===owner);return json('stored-device-token');}
    if(url.includes('/push_devices?')) return json([{token:'stored-device-token'}]);
    if(url.includes('oauth2.googleapis.com')) return json({access_token:'fake-access'});
    assert(url==='https://fcm.googleapis.com/v1/projects/test-project/messages:send');
    message=JSON.parse(String(init.body)).message;
    return json({name:'accepted'});
  }) as typeof fetch;
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  const deferred: Promise<unknown>[] = [];
  const result = await baseHandler(k=>k==='FIREBASE_SERVICE_ACCOUNT_JSON'?service:env(k),request,
    task => deferred.push(task), ms => {assert(ms===30000); return gate;})(
      req({action:'test',device_id:id,token:'victim-token',text:'sensitive text'}));
  assert(result.status===202 && (await result.json()).delay_seconds===30);
  assert(!message.token && deferred.length===1); // No FCM send before response/minimizing.
  release();
  await deferred[0];
  assert(message.token==='stored-device-token' && !message.notification && message.data.kind==='care' && message.data.test==='true');
  assert(!JSON.stringify(message).includes('sensitive text'));
  message = {};
  const revoked = (async (url: string, init: RequestInit) => url.includes('/push_devices?') ? json([]) : request(url,init)) as typeof fetch;
  const cancelled: Promise<unknown>[]=[];
  assert((await baseHandler(k=>k==='FIREBASE_SERVICE_ACCOUNT_JSON'?service:env(k),revoked,
    task=>cancelled.push(task),()=>Promise.resolve())(req({action:'test',device_id:id}))).status===202);
  await cancelled[0];
  assert(!message.token); // Withdrawal during waiting cancels the send.
});
