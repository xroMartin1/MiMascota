// Sin librerías externas. Autenticación verificada por Supabase Auth en cada petición.
const respond = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
});
const enc = new TextEncoder();
const b64 = (bytes: Uint8Array) => btoa(String.fromCharCode(...bytes)).replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '');

export async function googleAccess(raw: string, request = fetch): Promise<{access: string; project: string}> {
  const key = JSON.parse(raw);
  if (key.type !== 'service_account' || !/^[a-z0-9-]+$/.test(key.project_id)
      || typeof key.client_email !== 'string' || typeof key.private_key !== 'string') throw Error('firebase_config');
  const pem = key.private_key.replace(/-----[^-]+-----/g, '').replace(/\s/g, '');
  const privateKey = await crypto.subtle.importKey('pkcs8', Uint8Array.from(atob(pem), c => c.charCodeAt(0)),
    { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['sign']);
  const now = Math.floor(Date.now() / 1000);
  const message = b64(enc.encode(JSON.stringify({alg: 'RS256', typ: 'JWT'}))) + '.' +
    b64(enc.encode(JSON.stringify({iss: key.client_email, scope: 'https://www.googleapis.com/auth/firebase.messaging',
      aud: 'https://oauth2.googleapis.com/token', iat: now, exp: now + 3600})));
  const signature = await crypto.subtle.sign('RSASSA-PKCS1-v1_5', privateKey, enc.encode(message));
  const response = await request('https://oauth2.googleapis.com/token', {method: 'POST',
    body: new URLSearchParams({grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer', assertion: message + '.' + b64(new Uint8Array(signature))}),
    signal: AbortSignal.timeout(10000)});
  if (!response.ok) throw Error('firebase_auth');
  const result = await response.json();
  if (typeof result.access_token !== 'string') throw Error('firebase_auth');
  return {access: result.access_token, project: key.project_id};
}

declare const EdgeRuntime: { waitUntil(task: Promise<unknown>): void };
type Background = (task: Promise<unknown>) => void;
const runtimeBackground: Background | undefined = typeof EdgeRuntime === 'undefined'
  ? undefined : task => EdgeRuntime.waitUntil(task);

export function handler(env: (key: string) => string | undefined, request = fetch,
    background: Background | undefined = runtimeBackground,
    sleep = (ms: number) => new Promise<void>(resolve => setTimeout(resolve, ms))) {
  return async (req: Request): Promise<Response> => {
    if (req.method !== 'POST') return respond({error: 'method_not_allowed'}, 405);
    const authorization = req.headers.get('Authorization') || '';
    if (!/^Bearer [^\s]+$/i.test(authorization)) return respond({error: 'authentication_required'}, 401);
    const url = env('SUPABASE_URL');
    const publicKey = env('SUPABASE_ANON_KEY') || JSON.parse(env('SUPABASE_PUBLISHABLE_KEYS') || '{}').default;
    const service = env('SUPABASE_SERVICE_ROLE_KEY') || JSON.parse(env('SUPABASE_SECRET_KEYS') || '{}').default;
    try {
      const auth = await request(url + '/auth/v1/user', {headers: {apikey: publicKey, Authorization: authorization}, signal: AbortSignal.timeout(10000)});
      if (!auth.ok) return respond({error: 'authentication_required'}, 401);
      const user = await auth.json();
      if (!user.id || !user.email_confirmed_at) return respond({error: 'confirmed_account_required'}, 403);
      const text = await req.text();
      if (text.length > 210000) return respond({error: 'invalid_request'}, 400);
      let body;
      try { body = JSON.parse(text); } catch { return respond({error: 'invalid_request'}, 400); }
      if (!body || typeof body !== 'object' || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(body.device_id || '')
          || !['register', 'unregister', 'test', 'status', 'plan_save', 'plan_status'].includes(body.action)) return respond({error: 'invalid_request'}, 400);
      // owner_id, mensajes y destinatarios nunca se toman del cuerpo del cliente.
      const query = 'owner_id=eq.' + encodeURIComponent(user.id) + '&device_id=eq.' + body.device_id;
      async function db(path: string, method = 'GET', payload?: unknown) {
        const response = await request(url + '/rest/v1/' + path, {method, headers: {
          apikey: service!, Authorization: 'Bearer ' + service, 'Content-Type': 'application/json',
          Prefer: 'resolution=merge-duplicates,return=minimal'}, body: payload === undefined ? undefined : JSON.stringify(payload), signal: AbortSignal.timeout(10000)});
        if (!response.ok) {
          const failure = await response.text();
          if (failure.includes('test_rate_limited')) throw Error('test_rate_limited');
          if (failure.includes('plan_conflict')) throw Error('plan_conflict');
          if (failure.includes('invalid_plan')) throw Error('invalid_plan');
          if (failure.includes('device_limit')) throw Error('device_limit');
          throw Error('database_error');
        }
        return response.status === 204 || response.headers.get('content-length') === '0' ? null : response.json();
      }
      if (body.action === 'plan_status') {
        const plans = await db('reminder_plans?select=revision&owner_id=eq.' + encodeURIComponent(user.id));
        return respond({revision: plans.length ? plans[0].revision : 0});
      }
      if (body.action === 'plan_save') {
        if (!Number.isSafeInteger(body.revision) || body.revision < 0 || !body.payload
            || typeof body.payload.enabled !== 'boolean' || typeof body.payload.timezone !== 'string'
            || !Array.isArray(body.payload.routines)) return respond({error:'invalid_plan'},400);
        if (body.payload.enabled) {
          const devices = await db('push_devices?select=device_id&' + query + '&updated_at=gte.' +
            encodeURIComponent(new Date(Date.now()-30*86400000).toISOString()));
          if (!devices.length) return respond({error:'device_not_registered'},409);
        }
        return respond(await db('rpc/save_reminder_plan','POST',{
          p_owner:user.id,p_revision:body.revision,p_payload:body.payload}));
      }
      if (body.action === 'unregister') {
        await db('push_devices?' + query, 'DELETE');
        return respond({registered: false});
      }
      if (body.action === 'register') {
        if (typeof body.token !== 'string' || body.token.length < 32 || body.token.length > 4096 || /\s/.test(body.token)) return respond({error: 'invalid_token'}, 400);
        await db('rpc/register_push_device', 'POST', {p_owner: user.id, p_device: body.device_id, p_token: body.token});
        return respond({registered: true});
      }
      if (body.action === 'status') {
        const devices = await db('push_devices?select=device_id&' + query);
        return respond({registered: devices.length > 0, firebase_configured: !!env('FIREBASE_SERVICE_ACCOUNT_JSON')});
      }
      const raw = env('FIREBASE_SERVICE_ACCOUNT_JSON');
      if (!raw) return respond({error: 'firebase_config'}, 503);
      if (!background) return respond({error: 'service_unavailable'}, 503);
      const token = await db('rpc/claim_push_test', 'POST', {p_owner: user.id, p_device: body.device_id});
      if (!token) return respond({error: 'device_not_registered'}, 409);
      const google = await googleAccess(raw, request);
      // Prueba corta, no un planificador de recordatorios persistente.
      // La respuesta termina antes de esperar; el teléfono ya puede minimizarse.
      const task = async () => {
        try {
          await sleep(30000);
          // Si se retiró el teléfono o cambió de token durante la espera, cancelar.
          const current = await db('push_devices?select=token&' + query + '&updated_at=gte.' +
            encodeURIComponent(new Date(Date.now() - 30 * 86400000).toISOString()));
          if (current.length !== 1 || current[0].token !== token) return;
      const sent = await request('https://fcm.googleapis.com/v1/projects/' + google.project + '/messages:send', {
        method: 'POST', headers: {Authorization: 'Bearer ' + google.access, 'Content-Type': 'application/json'},
        body: JSON.stringify({message: {token, data: {kind: 'care', test: 'true'}, android: {priority: 'high', ttl: '120s'}}}), signal: AbortSignal.timeout(10000)});
      if (!sent.ok) {
        const failure = await sent.json();
        if (failure.error?.details?.some((d: {errorCode?: string}) => d.errorCode === 'UNREGISTERED')) {
          await db('push_devices?' + query, 'DELETE');
          return respond({error: 'device_not_registered'}, 409);
        }
        return respond({error: 'firebase_send'}, 502);
      }

        } catch {
          // No registrar credenciales o tokens ni reintentar una prueba duplicada.
        }
      };
      background(task());
      return respond({scheduled: true, delay_seconds: 30}, 202);
    } catch (error) {
      // No registrar excepciones, credenciales, JWT ni tokens FCM.
      const reason = error instanceof Error ? error.message : '';
      if (reason === 'test_rate_limited') return respond({error: reason}, 429);
      if (reason === 'plan_conflict') return respond({error:reason},409);
      if (reason === 'invalid_plan') return respond({error:reason},400);
      if (reason === 'device_limit') return respond({error: reason}, 409);
      return respond({error: ['firebase_config', 'firebase_auth'].includes(reason) ? reason : 'service_unavailable'}, 503);
    }
  };
}

if (import.meta.main) Deno.serve(handler(key => Deno.env.get(key)));
