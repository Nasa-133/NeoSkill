import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { createServer } from 'node:net';
import { setTimeout as delay } from 'node:timers/promises';
import test from 'node:test';

test('the production frontend starts independently and serves core routes', async () => {
  const reservation=createServer(); reservation.listen(0,'127.0.0.1'); await once(reservation,'listening'); const port=reservation.address().port; await new Promise((resolve,reject)=>reservation.close(error=>error?reject(error):resolve()));
  const server=spawn(process.execPath,['.next/standalone/server.js'],{env:{PATH:process.env.PATH,NODE_ENV:'production',PORT:String(port),HOSTNAME:'127.0.0.1'},stdio:['ignore','pipe','pipe']}); let output=''; server.stdout.on('data',chunk=>{output+=chunk}); server.stderr.on('data',chunk=>{output+=chunk}); const stopped=once(server,'exit');
  try { let origin; for(let attempt=0;attempt<150;attempt++){assert.equal(server.exitCode,null,output);origin=output.match(/http:\/\/127\.0\.0\.1:(\d+)/)?.[0];if(origin&&/Ready/i.test(output))break;await delay(100)} assert.ok(origin,`Server did not start: ${output}`);
    const health=await fetch(`${origin}/health`,{signal:AbortSignal.timeout(5000)}); assert.equal(health.status,200); assert.deepEqual(await health.json(),{status:'ok',service:'neoskill-frontend'});
    for(const path of ['/','/courses','/courses/python-asoslari','/preview/lesson-1?course=python-asoslari','/about','/contact','/privacy','/terms','/login','/register','/forgot-password','/reset-password','/dashboard','/my-courses','/learn/python-asoslari','/learn/python-asoslari/lesson/lesson-2','/learn/python-asoslari/test/topic-1','/profile','/admin','/admin/statistics?view=enrollments','/admin/referrals','/admin/courses','/admin/courses/new','/admin/courses/course-python/edit','/admin/categories','/admin/instructors','/admin/enrollment-requests','/admin/users','/admin/tests','/admin/testimonials','/admin/settings','/forbidden']){const response=await fetch(`${origin}${path}`,{signal:AbortSignal.timeout(5000)});assert.equal(response.status,200,path);assert.match(response.headers.get('content-type')??'',/text\/html/,path);assert.equal(response.headers.get('x-powered-by'),null)}
    for(const path of ['/does-not-exist','/design-system']){const response=await fetch(`${origin}${path}`,{signal:AbortSignal.timeout(5000)});assert.equal(response.status,404,path)}
    // The API proxy must own /api/v1, otherwise browser calls land on the HTML 404 page.
    const proxied=await fetch(`${origin}/api/v1/auth/session`,{signal:AbortSignal.timeout(5000)});
    assert.notEqual(proxied.status,404,'/api/v1 must be handled by the proxy route');
    assert.match(proxied.headers.get('content-type')??'',/application\/json/,'the proxy must answer in JSON');
  } finally {server.kill('SIGTERM');await stopped}
});
