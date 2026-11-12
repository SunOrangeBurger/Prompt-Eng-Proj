// Buildless frontend; all model/code output is rendered as text, never HTML.
const $ = (selector) => document.querySelector(selector);
let state, token, selectedIssue = null, selectedFile = null, mode = 'diff', rendered = '', activeStep = '';
const pad = n => String(n).padStart(2, '0');
function node(tag, text, className) { const el = document.createElement(tag); if(text != null) el.textContent=text; if(className) el.className=className; return el; }
function issueEvents() { return (state.events || []).filter(e => e.issue?.id === selectedIssue); }
function drawInspector() {
  const events = issueEvents();
  const proposal = events.filter(e => e.kind === 'proposal').at(-1);
  const validation = events.filter(e => e.kind === 'validation').at(-1);
  const baseline = events.find(e => e.kind === 'baseline');
  $('#explanation').textContent = proposal?.explanation || 'Start a run to see the model’s proposed changes and validation evidence.';
  let text = mode === 'diff' ? (proposal?.diff || 'No patch yet. The model will propose a real change here.') : (state.sources[selectedFile] || 'Select a source file.');
  $('#filename').textContent = mode === 'diff' ? (proposal?.issue.path || '') : (selectedFile || '');
  $('#code').replaceChildren(...text.split('\n').map(line => node('span', line || ' ', mode === 'diff' ? (line.startsWith('+') ? 'add' : line.startsWith('-') ? 'remove' : line.startsWith('@@') ? 'meta' : '') : '')));
  const checks = validation?.checks || baseline?.checks || [];
  $('#checks').replaceChildren();
  if (!checks.length) $('#checks').append(node('p','Syntax, security rules, scope, and cross-repo tests appear here.','empty'));
  if (baseline && !validation) $('#checks').append(node('p','Baseline results — failures are expected before the security fix.','empty'));
  for (const check of checks) {
    const detail=node('details',null,'check'); const summary=node('summary');
    summary.append(node('span',check.passed?'PASS':'FAIL',check.passed?'pass':'fail'),node('span',check.name));
    detail.append(summary,node('pre',check.output)); $('#checks').append(detail);
  }
  document.querySelectorAll('[data-mode]').forEach(b=>b.classList.toggle('selected',b.dataset.mode===mode));
}
function render() {
  $('#model').textContent=state.model; $('#status').textContent=state.status.toUpperCase();
  const running=state.status==='running'; $('#run').disabled=running; $('#reset').disabled=running;
  const labels={ready:'A clean starting point.',running:'The patch is on the bench.',completed:'Two fixes. All checks passed.',rejected:'A candidate needs more work.',error:'The run needs attention.'};
  $('#headline').textContent=labels[state.status]||state.status;
  const events=state.events||[]; const applied=events.filter(e=>e.kind==='applied');
  const step=events.filter(e=>e.kind==='issue_started').at(-1);
  const stepKey=step?`${step.time}:${step.issue.id}`:'';
  if(stepKey!==activeStep){activeStep=stepKey;if(step){selectedIssue=step.issue.id;selectedFile=step.issue.path;mode='diff';}}
  $('#repos-count').textContent=pad(Object.keys(state.repos).length); $('#remaining').textContent=pad(state.issues.length); $('#fixed').textContent=pad(applied.length);
  $('#prompt').textContent=state.system_prompt;
  const last=events.at(-1); $('#phase').textContent=last?.kind.replaceAll('_',' ').toUpperCase()||'AWAITING RUN';
  $('#graph').replaceChildren(...Object.entries(state.repos).map(([name,repo])=>{const el=node('div',null,'repo'+(repo.depends_on.length?' downstream':''));el.append(node('strong',name),node('small',repo.depends_on.length?'↳ '+repo.depends_on.join(' + '):'Independent shared library'));return el;}));
  const sources=Object.keys(state.sources).filter(p=>!p.includes('/tests/'));
  if(!sources.includes(selectedFile))selectedFile=sources[0];
  $('#files').replaceChildren(...sources.map(path=>{const b=node('button',path.split('/').at(-1),path===selectedFile?'active':'');b.onclick=()=>{selectedFile=path;mode='source';render();};return b;}));
  const known=new Map(); for(const e of events)if(e.issue)known.set(e.issue.id,e.issue);for(const i of state.issues)known.set(i.id,i);
  if(!known.has(selectedIssue))selectedIssue=known.keys().next().value;
  $('#issue-tabs').replaceChildren(...[...known.values()].map(issue=>{const done=applied.some(e=>e.issue.id===issue.id);const b=node('button',(done?'✓ ':'')+issue.rule,issue.id===selectedIssue?'active':'');b.onclick=()=>{selectedIssue=issue.id;selectedFile=issue.path;mode='diff';render();};return b;}));
  const labelsEvent={reset:'Files restored',issue_started:'Issue selected',baseline:'Baseline checked',context:'Context retrieved',generating:'Ollama generating',proposal:'Patch proposed',validation:'Checks completed',rejected:'Attempt rejected',repair_finished:'Repair finished',applied:'Fix applied',finished:'Run finished',error:'Run error'};
  $('#event-count').textContent=events.length+' EVENTS';
  $('#timeline').replaceChildren(...events.map(e=>{const li=node('li');let text=e.issue?.rule||e.message||'';if(e.kind==='validation')text=`${e.checks.filter(c=>c.passed).length}/${e.checks.length} checks passed`;if(e.kind==='generating')text+=` · attempt ${e.attempt}`;if(e.kind==='rejected')text=e.error;if(e.kind==='finished')text=e.status+' · '+e.remaining_findings+' findings remain';li.append(node('time',new Date(e.time*1000).toLocaleTimeString()),node('b',labelsEvent[e.kind]||e.kind),node('span',text));return li;}));
  if(!events.length)$('#timeline').append(node('li','Ready to begin. Each real pipeline event will be recorded here.','empty'));
  const error=events.filter(e=>e.kind==='error').at(-1); $('#error').textContent=error?.message||'';
  drawInspector(); updateClock();
}
function updateClock(){if(!state)return;const ev=state.events||[];if(!ev.length){$('#elapsed').textContent='—';return;}const end=state.status==='running'?Date.now()/1000:ev.at(-1).time;$('#elapsed').textContent=Math.max(0,end-ev[0].time).toFixed(1);}
async function refresh(){try{const response=await fetch('/api/state');if(!response.ok)throw Error('Dashboard connection failed');const next=await response.json();token=next.token;const signature=JSON.stringify(next);state=next;if(signature!==rendered){rendered=signature;render();}}catch(e){$('#error').textContent=e.message;}}
async function action(path){$('#run').disabled=true;$('#reset').disabled=true;try{const response=await fetch(path,{method:'POST',headers:{'X-Demo-Token':token}});if(!response.ok)throw Error((await response.json()).error||'A run is already active');await refresh();}catch(e){$('#error').textContent=e.message;$('#run').disabled=false;$('#reset').disabled=false;}}
$('#run').onclick=()=>action('/api/run');$('#reset').onclick=()=>action('/api/reset');
document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>{mode=b.dataset.mode;drawInspector();});
setInterval(refresh,600);setInterval(updateClock,100);refresh();
