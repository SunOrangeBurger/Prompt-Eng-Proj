// Buildless frontend; all model/code output is rendered as text, never HTML.
const $ = (selector) => document.querySelector(selector);
let state, token, selectedIssue = null, selectedFile = null, mode = 'diff', rendered = '', activeStep = '', reviewId = '';
const pad = n => String(n).padStart(2, '0');
function node(tag, text, className) { const el = document.createElement(tag); if(text != null) el.textContent=text; if(className) el.className=className; return el; }
function issueEvents() { return (state.events || []).filter(e => e.issue?.id === selectedIssue); }
function drawInspector() {
  const events = issueEvents();
  const proposal = events.filter(e => e.kind === 'proposal').at(-1);
  const validation = events.filter(e => e.kind === 'validation').at(-1);
  const baseline = events.find(e => e.kind === 'baseline');
  const pending=state.pending;
  const reviewed=events.filter(e=>e.kind==='awaiting_review').at(-1);
  const issue=state.issues.find(i=>i.id===selectedIssue)||events.find(e=>e.issue)?.issue;
  $('#diagnosis').textContent=proposal?.diagnosis||issue?.message||'Select an issue to investigate.';
  $('#risk').textContent=proposal?.risk?'AI risk assessment: '+proposal.risk:'';
  $('#verification').textContent=proposal?.verification?'AI verification plan (actual results below): '+proposal.verification:'';
  const source=proposal?.before||state.sources[issue?.path]||'';
  $('#location').textContent=issue?`${issue.repo} / ${issue.path} · lines ${issue.line}–${issue.end_line}`:'';
  $('#problem-code').replaceChildren(...source.split('\n').map((line,i)=>({line,n:i+1})).filter(({n})=>issue&&n>=Math.max(1,issue.line-2)&&n<=issue.end_line+2).map(({line,n})=>node('span',`${String(n).padStart(3)}  ${line}`,n>=issue.line&&n<=issue.end_line?'problem':'')));
  const relatedReview=pending?.issue.id===selectedIssue?pending:reviewed;
  $('#affected').textContent=relatedReview?'Affected repositories: '+relatedReview.affected_repos.join(' → '):'Read the original code above; proposed changes are shown below.';
  $('.review-heading').textContent=events.some(e=>e.kind==='applied')?'Applied fix (approved by you)':'Proposed fix';
  $('#review-panel').hidden=!pending;
  $('#approve').disabled=!pending||pending.issue.id!==selectedIssue;
  $('#reject').disabled=!pending||pending.issue.id!==selectedIssue;
  $('#prepare').disabled=state.status==='running'||!!pending||!state.issues.some(i=>i.id===selectedIssue);
  $('#review-id').textContent=pending?'Review '+pending.id+' · approve only the displayed pending patch':'';
  if((pending?.id||'')!==reviewId){reviewId=pending?.id||'';$('#reason').value='';}
  $('#explanation').textContent = proposal?.explanation || 'Choose an issue, then ask the AI to explain and propose a fix.';
  let text = mode === 'diff' ? (proposal?.diff || 'No patch yet. The model will propose a real change here.') : (state.sources[selectedFile] || 'Select a source file.');
  $('#filename').textContent = mode === 'diff' ? (proposal?.issue.path || '') : (selectedFile || '');
  $('#code').replaceChildren(...text.split('\n').map(line => node('span', line || ' ', mode === 'diff' ? (line.startsWith('+') ? 'add' : line.startsWith('-') ? 'remove' : line.startsWith('@@') ? 'meta' : '') : '')));
  const checks = validation?.checks || baseline?.checks || [];
  $('#checks').replaceChildren();
  if (!checks.length) $('#checks').append(node('p','Syntax, security rules, scope, and cross-repo tests appear here.','empty'));
  if (baseline && !validation) $('#checks').append(node('p','Baseline results — failures are expected before the security fix.','empty'));
  for (const check of checks) {
    const detail=node('details',null,'check'); const summary=node('summary');
    summary.append(node('span',check.baseline_failures?'BASELINE FAILURES':check.passed?'PASS':'FAIL',check.baseline_failures?'warning':check.passed?'pass':'fail'),node('span',check.name));
    detail.append(summary,node('pre',check.output)); $('#checks').append(detail);
  }
  document.querySelectorAll('[data-mode]').forEach(b=>b.classList.toggle('selected',b.dataset.mode===mode));
}
function render() {
  $('#model').textContent=state.model; $('#status').textContent=state.status.toUpperCase();
  const running=state.status==='running'; $('#run').disabled=running||!!state.pending; $('#reset').disabled=running;
  const labels={ready:'Choose an issue to investigate.',running:'Preparing a patch for review.',awaiting_review:'Your decision. No files changed.',completed:'All findings reviewed and fixed.',rejected:'Candidate failed validation.',error:'The run needs attention.'};
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
  $('#issue-tabs').replaceChildren(...[...known.values()].map(issue=>{const done=applied.some(e=>e.issue.id===issue.id);const b=node('button',(done?'✓ ':'')+issue.repo+' / '+issue.rule,issue.id===selectedIssue?'active':'');b.onclick=()=>{selectedIssue=issue.id;selectedFile=issue.path;mode='diff';render();};return b;}));
  const labelsEvent={reset:'Files restored',issue_started:'Issue selected',baseline:'Baseline checked',context:'Context retrieved',generating:'Ollama generating',proposal:'Patch proposed',validation:'Checks completed',rejected:'Attempt rejected',repair_finished:'Proposal checked',awaiting_review:'Awaiting human',human_decision:'Human decision',applied:'Approved fix applied',finished:'Run finished',error:'Run error'};
  $('#event-count').textContent=events.length+' EVENTS';
  $('#timeline').replaceChildren(...events.map(e=>{const li=node('li');let text=e.issue?.rule||e.message||'';if(e.kind==='validation')text=`${e.checks.filter(c=>c.passed).length}/${e.checks.length} gates passed · ${e.checks.filter(c=>c.baseline_failures).length} repos retain baseline failures`;if(e.kind==='generating')text+=` · attempt ${e.attempt}`;if(e.kind==='rejected')text=e.error;if(e.kind==='human_decision')text=e.decision+(e.reason?' · '+e.reason:'');if(e.kind==='finished')text=e.status+' · '+e.remaining_findings+' findings remain';li.append(node('time',new Date(e.time*1000).toLocaleTimeString()),node('b',labelsEvent[e.kind]||e.kind),node('span',text));return li;}));
  if(!events.length)$('#timeline').append(node('li','Ready to begin. Each real pipeline event will be recorded here.','empty'));
  const error=events.filter(e=>e.kind==='error').at(-1); $('#error').textContent=error?.message||'';
  drawInspector(); updateClock();
}
function updateClock(){if(!state)return;const ev=state.events||[];if(!ev.length){$('#elapsed').textContent='—';return;}const end=state.status==='running'?Date.now()/1000:ev.at(-1).time;$('#elapsed').textContent=Math.max(0,end-ev[0].time).toFixed(1);}
async function refresh(){try{const response=await fetch('/api/state');if(!response.ok)throw Error('Dashboard connection failed');const next=await response.json();token=next.token;const signature=JSON.stringify(next);state=next;if(signature!==rendered){rendered=signature;render();}}catch(e){$('#error').textContent=e.message;}}
async function action(path,data={}){for(const id of ['run','reset','prepare','approve','reject'])$('#'+id).disabled=true;try{const response=await fetch(path,{method:'POST',headers:{'X-Demo-Token':token,'Content-Type':'application/json'},body:JSON.stringify(data)});if(!response.ok)throw Error((await response.json()).error||'A run is already active');await refresh();render();}catch(e){render();$('#error').textContent=e.message;}}
$('#run').onclick=()=>action('/api/run');$('#reset').onclick=()=>action('/api/reset');
$('#prepare').onclick=()=>action('/api/prepare',{issue_id:selectedIssue});
$('#approve').onclick=()=>action('/api/approve',{review_id:state.pending?.id,reason:$('#reason').value});
$('#reject').onclick=()=>action('/api/reject',{review_id:state.pending?.id,reason:$('#reason').value});
document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>{mode=b.dataset.mode;drawInspector();});
setInterval(refresh,600);setInterval(updateClock,100);refresh();
