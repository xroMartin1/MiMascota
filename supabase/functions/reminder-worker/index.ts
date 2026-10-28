import {googleAccess} from '../push-device/index.ts';
const respond = (value: unknown, status = 200) => new Response(JSON.stringify(value), {
  status, headers: {'Content-Type':'application/json', 'Cache-Control':'no-store'},
});
export function worker(env: (key:string)=>string|undefined, request=fetch,
    access=googleAccess) {
 return async (req: Request): Promise<Response> => {
  if(req.method!=='POST') return respond({error:'method_not_allowed'},405);
  const authorization=req.headers.get('Authorization')||'';
  if(!/^Bearer [a-f0-9]{64}$/.test(authorization)) return respond({error:'worker_unauthorized'},401);
  const key=authorization.slice(7);
  const service=env('SUPABASE_SERVICE_ROLE_KEY')||JSON.parse(env('SUPABASE_SECRET_KEYS')||'{}').default;
  async function rpc(name:string,body:unknown) {
   const response=await request(env('SUPABASE_URL')+'/rest/v1/rpc/'+name, {
    method:'POST',headers:{apikey:service!,Authorization:'Bearer '+service,'Content-Type':'application/json'},
    body:JSON.stringify(body),signal:AbortSignal.timeout(10000)});
   if(!response.ok) throw Error((await response.text()).includes('worker_unauthorized')?'worker_unauthorized':'database_error');
   return response.status===204 ? null : response.json();
  }
  let jobs: {id:string;token:string}[];
  try { jobs=await rpc('claim_reminder_jobs',{p_key:key}); }
  catch(error) { return respond({error:'worker_unauthorized'}, error instanceof Error && error.message==='worker_unauthorized'?401:503); }
  if(!jobs.length) return respond({processed:0});
  const finish=(id:string,result:string,token?:string)=>rpc('finish_reminder_job',{p_key:key,p_id:id,p_result:result,p_token:token??null});
  let google: {access:string;project:string};
  try { google=await access(env('FIREBASE_SERVICE_ACCOUNT_JSON')||'',request); }
  catch { await Promise.allSettled(jobs.map(job=>finish(job.id,'retry'))); return respond({error:'firebase_unavailable'},503); }
  let processed=0;
  async function run() {
   for(let job=jobs.shift();job;job=jobs.shift()) {
    let result='uncertain';
    try {
     const allowed=await rpc('prepare_reminder_job',{p_key:key,p_id:job.id,p_token:job.token});
     if(!allowed) { await finish(job.id,'cancelled'); continue; }
     const sent=await request('https://fcm.googleapis.com/v1/projects/'+google.project+'/messages:send',{
      method:'POST',headers:{Authorization:'Bearer '+google.access,'Content-Type':'application/json'},
      body:JSON.stringify({message:{token:job.token,data:{kind:'care',event_id:job.id},
        android:{priority:'high',ttl:'900s',collapse_key:job.id}}}),signal:AbortSignal.timeout(10000)});
     if(sent.ok) result='sent';
     else {
      const failure=await sent.json();
      result=failure.error?.details?.some((d:{errorCode?:string})=>d.errorCode==='UNREGISTERED') ? 'unregistered'
        : [429,500,503].includes(sent.status) ? 'retry' : 'failed';
     }
    } catch { /* Respuesta ambigua: no reenviar sin saber si Firebase aceptó. */ }
    try { await finish(job.id,result,job.token); processed++; } catch { /* Se conserva sending y el próximo ciclo marca uncertain. */ }
   }
  }
  await Promise.all(Array.from({length:Math.min(4,jobs.length)},run));
  return respond({processed});
 };
}
if(import.meta.main) Deno.serve(worker(key=>Deno.env.get(key)));
