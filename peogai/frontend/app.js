// Buildless IDE. Repository and model content is rendered as text, never HTML.
const $ = selector => document.querySelector(selector);
let state = null, token = '', selectedFile = null, selectedIssue = null;
let mode = 'source', panel = 'problems', openFiles = [], signature = '', activeStep = '', pendingId = '';
let sending = false, filter = '', errorText = '';
const closedRepos = new Set();
const eventNames = {reset:'Workspace reset',issue_started:'Issue selected',context:'Context retrieved',baseline:'Baseline checked',generating:'Generating fix',proposal:'Candidate proposed',validation:'Validation',rejected:'Attempt rejected',repair_finished:'Proposal checked',awaiting_review:'Review required',human_decision:'Review decision',applied:'Fix applied',chat_error:'Chat error',error:'Error'};
const el = (tag, text, cls) => { const n=document.createElement(tag); if(text!=null)n.textContent=text; if(cls)n.className=cls; return n; };
const shortName = path => path?.split('/').at(-1) || 'Select a file';
const busy = () => sending || state?.status==='running' || !!state?.chat_busy;
const issue = () => state?.issues.find(i=>i.id===selectedIssue) || null;
function relatedEvents(){return (state?.events||[]).filter(e=>e.issue?.path===selectedFile && (!selectedIssue||e.issue.id===selectedIssue));}
function proposal(){return relatedEvents().filter(e=>e.kind==='proposal').at(-1);}
function setError(text){errorText=text;$('#error').textContent=text;$('#error').hidden=!text;}
function openFile(path, issueId=null, jump=false){
  if(!(path in state.sources))return;
  selectedFile=path;
  selectedIssue=issueId||state.issues.find(i=>i.path===path)?.id||null;
  if(!openFiles.includes(path))openFiles.push(path);
  mode='source';render();
  if(jump)requestAnimationFrame(()=>$('#code').querySelector('.problem')?.scrollIntoView({block:'center',behavior:'smooth'}));
}
function openDiff(path=selectedFile, issueId=selectedIssue){
  if(path)openFile(path,issueId);
  mode='diff';render();
}
function highlight(text){
  const frag=document.createDocumentFragment();
  const pattern=/(#[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:def|class|return|if|else|elif|for|while|in|not|and|or|is|None|True|False|import|from|as|raise|with|try|except|finally|pass|async|await|yield)\b|\b\d+(?:\.\d+)?\b|\b[A-Za-z_]\w*(?=\())/g;
  let last=0;
  for(const match of text.matchAll(pattern)){
    frag.append(document.createTextNode(text.slice(last,match.index)));
    const value=match[0];let cls='tok-keyword';
    if(value.startsWith('#'))cls='tok-comment';else if(/^["']/.test(value))cls='tok-string';else if(/^\d/.test(value))cls='tok-number';else if(text[match.index+value.length]==='(')cls='tok-function';
    frag.append(el('span',value,cls));last=match.index+value.length;
  }
  frag.append(document.createTextNode(text.slice(last)));return frag;
}
function renderTree(){
  const tree=$('#file-tree');tree.replaceChildren();
  const paths=Object.keys(state.sources).filter(p=>p.toLowerCase().includes(filter.toLowerCase()));
  for(const [repo,info] of Object.entries(state.repos)){
    const children=paths.filter(p=>p.startsWith(info.path+'/'));if(!children.length)continue;
    const folder=el('details',null,'repo-folder');folder.open=filter?true:!closedRepos.has(repo);
    folder.addEventListener('toggle',()=>{if(!filter){if(folder.open)closedRepos.delete(repo);else closedRepos.add(repo);}});
    const label=el('summary');label.append(el('span','▱','folder-icon'),el('span',repo),el('span',String(state.issues.filter(i=>i.repo===repo).length),'count'));folder.append(label);
    for(const path of children){
      const b=el('button',null,'file-button'+(path===selectedFile?' active':''));b.title=path;
      const name=path.slice(info.path.length+1);b.append(el('span','py','python-icon'),el('span',name,'file-name'));
      const count=state.issues.filter(i=>i.path===path).length;if(count)b.append(el('span',String(count),'file-problems'));
      b.onclick=()=>openFile(path,null,true);folder.append(b);
    }
    tree.append(folder);
  }
  if(!paths.length)tree.append(el('p','No matching files.','empty'));
  $('#dependencies').replaceChildren(...Object.entries(state.repos).filter(([,r])=>r.depends_on.length).map(([name,r])=>el('div',name+' → '+r.depends_on.join(', '),'dependency')));
  $('#repos-count').textContent=Object.keys(state.repos).length+' repos';
}
function renderEditor(){
  $('#editor-tabs').replaceChildren(...openFiles.map(path=>{
    const b=el('button',null,'editor-tab'+(path===selectedFile?' selected':''));b.setAttribute('role','tab');b.setAttribute('aria-selected',String(path===selectedFile));b.title=path;
    b.append(el('span','py','python-icon'),el('span',shortName(path)));if(state.issues.some(i=>i.path===path))b.append(el('span',null,'tab-dot'));
    b.onclick=()=>openFile(path);return b;
  }));
  $('#breadcrumb').textContent=selectedFile?.replaceAll('/','  ›  ')||'parcel-shop';
  const finding=issue(), candidate=proposal();
  $('#finding-banner').hidden=!finding;
  if(finding){$('#finding-title').textContent=finding.rule+' · '+finding.kind;$('#finding-summary').textContent=finding.message;}
  const code=$('#code'),scroll=$('#editor'),top=scroll.scrollTop,left=scroll.scrollLeft;
  code.replaceChildren();
  const source=mode==='source'?(state.sources[selectedFile]||''):(candidate?.diff||'No proposed patch for this selection.\nChoose a problem and use Propose fix in AI Assistant.');
  for(const [index,line] of source.split('\n').entries()){
    let cls='code-line';if(mode==='source'&&finding&&index+1>=finding.line&&index+1<=finding.end_line)cls+=' problem';
    if(mode==='diff')cls+=line.startsWith('+')?' add':line.startsWith('-')?' remove':line.startsWith('@@')?' meta':'';
    const row=el('div',null,cls);row.dataset.line=String(index+1);row.append(el('span',mode==='source'?String(index+1):'','line-number'));
    const content=el('span',null,'line-content');if(mode==='source')content.append(highlight(line||' '));else content.textContent=line||' ';row.append(content);code.append(row);
  }
  scroll.scrollTop=top;scroll.scrollLeft=left;
  $('#diff-dot').hidden=!candidate;
  $('#file-state').textContent=mode==='source'?'Read-only workspace source':state.pending?.issue.path===selectedFile&&state.pending.issue.id===selectedIssue?'Validated candidate · awaiting your approval':'Proposed diff · see review decision in chat';
  document.querySelectorAll('[data-mode]').forEach(b=>b.classList.toggle('selected',b.dataset.mode===mode));
}
function showPanel(name){panel=name;renderBottom();}
function renderBottom(){
  const problems=$('#problems');problems.replaceChildren();
  for(const finding of state.issues){
    const b=el('button',null,'problem-row'+(finding.id===selectedIssue?' selected':''));b.title=finding.message;
    b.append(el('span',finding.kind==='security'?'△':'◇','severity '+finding.kind));
    const text=el('div');text.append(el('strong',finding.rule),el('p',finding.message));b.append(text,el('span',shortName(finding.path)+':'+finding.line,'problem-location'));
    b.onclick=()=>openFile(finding.path,finding.id,true);problems.append(b);
  }
  if(!state.issues.length)problems.append(el('p','No findings from the current five AST rules. This is not a complete security audit.','empty'));
  $('#problem-count').textContent=state.issues.length;
  const events=relatedEvents(),validation=events.filter(e=>e.kind==='validation').at(-1),baseline=events.filter(e=>e.kind==='baseline').at(-1);
  const checks=validation?.checks||baseline?.checks||[];
  $('#validation-count').textContent=checks.length;$('#checks').replaceChildren();
  if(!checks.length)$('#checks').append(el('p','Propose a fix to run syntax, scope, security and cross-repo test gates in a separate copy.','empty'));
  if(baseline&&!validation)$('#checks').append(el('p','Baseline evidence. Known security failures are expected before repair.','empty'));
  for(const check of checks){const d=el('details',null,'check'),s=el('summary');s.append(el('span',check.baseline_failures?'BASELINE':check.passed?'PASS':'FAIL',check.baseline_failures?'warning':check.passed?'pass':'fail'),el('span',check.name));d.append(s,el('pre',check.output));$('#checks').append(d);}
  const pipeline=(state.events||[]).filter(e=>eventNames[e.kind]);$('#timeline').replaceChildren(...pipeline.map(e=>{
    const row=el('div',null,'pipeline-row');row.append(el('time',new Date(e.time*1000).toLocaleTimeString()),el('b',eventNames[e.kind]),el('span',e.issue?.rule||e.message||e.decision||''));return row;
  }));
  if(!pipeline.length)$('#timeline').append(el('p','Pipeline events will appear when you invoke the assistant.','empty'));
  for(const name of ['problems','validation','pipeline'])$(name==='validation'?'#checks':name==='pipeline'?'#timeline':'#problems').hidden=panel!==name;
  document.querySelectorAll('[data-panel]').forEach(b=>b.classList.toggle('selected',b.dataset.panel===panel));
  $('#panel-summary').textContent=panel==='validation'?(validation?'Candidate gates':baseline?'Baseline results':'No candidate yet'):panel==='pipeline'?pipeline.length+' events':'Five AST rules · limited coverage';
}
function messageShell(label,time,cls='assistant'){
  const box=el('article',null,'message '+cls),head=el('div',null,'message-header');head.append(el('span',cls==='user'?(label==='Demo task'?'D':'Y'):'✧','avatar'),el('span',label));if(time)head.append(el('time',new Date(time*1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})));box.append(head);return box;
}
function richText(parent,text){
  function inline(target,line){
    const pattern=/(\*\*[^*]+\*\*|`[^`]+`)/g;let end=0;
    for(const match of line.matchAll(pattern)){target.append(document.createTextNode(line.slice(end,match.index)));const bold=match[0].startsWith('**');target.append(el(bold?'strong':'code',match[0].slice(bold?2:1,bold?-2:-1)));end=match.index+match[0].length;}
    target.append(document.createTextNode(line.slice(end)));
  }
  let fenced=false,lines=[];
  const flush=()=>{parent.append(el('pre',lines.join('\n'),'chat-code'));lines=[];};
  for(const line of String(text).split('\n')){
    if(/^\s*```/.test(line)){if(fenced)flush();fenced=!fenced;continue;}
    if(fenced){lines.push(line);continue;}
    if(!line.trim())continue;
    const heading=/^#{1,4}\s+(.*)/.exec(line),element=el(heading?'h4':'p');inline(element,heading?heading[1]:line);parent.append(element);
  }
  if(fenced)flush();
}
function renderChat(){
  const list=$('#chat-messages'),nearBottom=list.scrollHeight-list.scrollTop-list.clientHeight<100,oldTop=list.scrollTop;list.replaceChildren();
  const welcome=el('div',null,'welcome');welcome.append(el('div','✧','welcome-icon'),el('h3','A second pair of eyes.','welcome-title'),el('p','Select a problem or a file. Ask a question here, or describe a change and choose Propose fix. I’ll explain it, prepare a patch and check it in a separate copy.'),el('p','Nothing is applied until you review the diff and approve it.','welcome-note'));if(!(state.events||[]).some(e=>['user_message','assistant_message','proposal'].includes(e.kind)))list.append(welcome);
  for(const e of state.events||[]){
    if(e.kind==='user_message'||e.kind==='assistant_message'){
      const box=messageShell(e.kind==='user_message'?(e.origin==='demo'?'Demo task':'You'):'Local assistant',e.time,e.kind==='user_message'?'user':'assistant');if(e.path)box.append(el('div',shortName(e.path)+(e.mode==='propose'?' · propose fix':''),'message-path'));const body=el('div',null,'message-body');if(e.kind==='assistant_message')richText(body,e.text);else body.textContent=e.text;box.append(body);list.append(box);
    }else if(e.kind==='proposal'){
      const box=messageShell('Local assistant · proposed fix',e.time);box.append(el('div',e.issue.path,'message-path'));
      for(const [label,key] of [['What’s wrong','diagnosis'],['Proposed change','explanation'],['Residual risk','risk'],['Suggested verification, not test results','verification']])if(e[key]){const body=el('div',null,'message-body');richText(body,e[key]);box.append(el('div',label,'message-label'),body);}
      const view=el('button','Inspect proposed diff ↗','text-button');view.onclick=()=>openDiff(e.issue.path,e.issue.id);box.append(view);list.append(box);
    }else if(e.kind==='context'){list.append(el('div','Retrieved context from '+e.files.length+' related files.','message system'));
    }else if(e.kind==='validation'){const existing=e.checks.filter(c=>c.baseline_failures).length,failed=e.checks.filter(c=>!c.passed).length;const box=el('div',(failed?'Candidate failed '+failed+' validation gates.':'Candidate passed '+e.checks.length+' validation gates.')+(existing?' '+existing+' repo(s) still have disclosed baseline failures.':''),'message system');const b=el('button','See executed evidence ↗','text-button');b.onclick=()=>{openFile(e.issue.path,e.issue.id);showPanel('validation');};box.append(b);list.append(box);
    }else if(e.kind==='awaiting_review'){list.append(el('div','Validated proposal ready. Your workspace is unchanged; review it before choosing Apply or Reject.','message system'));
    }else if(e.kind==='human_decision'){list.append(el('div',(e.decision==='approved'?'You approved the patch.':'You rejected the patch; source is unchanged.')+(e.reason?' Note: '+e.reason:''),'message system'));
    }else if(e.kind==='rejected'||e.kind==='chat_error'||e.kind==='error'){list.append(el('div',e.error||e.message,'message system fail'));}
  }
  if(state.status==='running'||state.chat_busy)list.append(el('div',state.chat_busy?'Reading the selected code…':(state.events||[]).at(-1)?.kind==='generating'?'Generating and checking a candidate…':'Preparing repository context…','thinking'));
  if(nearBottom||!(state.events||[]).length)requestAnimationFrame(()=>{list.scrollTop=list.scrollHeight;});else list.scrollTop=oldTop;
}
function renderControls(){
  const pending=state.pending,isBusy=busy();$('#model').textContent=state.model;
  const reviewingPending=!!pending&&selectedFile===pending.issue.path&&selectedIssue===pending.issue.id&&mode==='diff';
  const statuses={ready:'Ready',running:'Preparing proposal',awaiting_review:'Awaiting your review',completed:'All findings resolved',rejected:'Validation rejected candidate',error:'Run needs attention'};
  $('#status').textContent=state.chat_busy?'Assistant is responding':statuses[state.status]||state.status;
  $('#remaining').textContent=state.issues.length+' findings';$('#fixed').textContent=(state.events||[]).filter(e=>e.kind==='applied').length+' applied';$('#rail-count').textContent=state.issues.length;
  $('#chat-context').textContent=shortName(selectedFile);$('#chat-context').title=selectedFile||'';
  $('#reset').disabled=isBusy;$('#ask').disabled=isBusy||!selectedFile;
  $('#prepare').disabled=isBusy||!!pending||!issue();$('#investigate').disabled=isBusy||!issue();
  $('#review-panel').hidden=!pending;
  if(pending){
    $('#review-context').textContent=shortName(pending.issue.path)+' · '+pending.issue.rule+'. The candidate is validated; source has not been changed.';
    $('#review-hint').textContent=reviewingPending?'This applies only the displayed validated patch.':'Open the validated diff to enable Apply.';
  }
  $('#approve').disabled=isBusy||!reviewingPending;$('#reject').disabled=isBusy||!pending;
  if((pending?.id||'')!==pendingId){pendingId=pending?.id||'';$('#reason').value='';}
  $('#chat-state').replaceChildren(el('i'),document.createTextNode(isBusy?'Working locally':pending?'Review pending':'Read-only questions'));
  $('#prompt').textContent=state.system_prompt||'';
  setError(errorText);
}
function render(){if(!state)return;renderTree();renderEditor();renderBottom();renderChat();renderControls();}
async function refresh(){
  try{const response=await fetch('/api/state');if(!response.ok)throw Error('Workspace connection failed');const next=await response.json();token=next.token;
    const nextSignature=JSON.stringify(next);state=next;
    if(nextSignature===signature)return;signature=nextSignature;
    openFiles=openFiles.filter(p=>p in state.sources);
    if(!selectedFile||!(selectedFile in state.sources)){selectedFile=state.issues[0]?.path||Object.keys(state.sources)[0];selectedIssue=state.issues.find(i=>i.path===selectedFile)?.id||null;}
    if(!openFiles.includes(selectedFile))openFiles.push(selectedFile);
    const step=(state.events||[]).filter(e=>e.kind==='issue_started').at(-1),key=step?step.time+':'+step.issue.id:'';
    if(key!==activeStep){activeStep=key;if(step){selectedFile=step.issue.path;selectedIssue=step.issue.id;mode='source';if(!openFiles.includes(selectedFile))openFiles.push(selectedFile);}}
    render();
  }catch(e){setError(e.message+' — start the local demo server.');}
}
async function action(path,data={}){
  if(sending)return; sending=true;setError('');renderControls();
  try{const response=await fetch(path,{method:'POST',headers:{'X-Demo-Token':token,'Content-Type':'application/json'},body:JSON.stringify(data)});const result=await response.json();if(!response.ok)throw Error(result.error||'Another operation is active');await refresh();return true;
  }catch(e){setError(e.message);return false;}finally{sending=false;renderControls();}
}
async function askQuestion(text){
  const message=(text||$('#message').value).trim();if(!message){$('#message').focus();return;}
  if(await action('/api/chat',{path:selectedFile,message}))$('#message').value='';
}
$('#chat-form').onsubmit=e=>{e.preventDefault();askQuestion();};
$('#prepare').onclick=async()=>{if(!issue())return;const message=$('#message').value.trim()||'Explain the selected issue and propose a minimal fix, preserving existing behavior.';if(await action('/api/prepare',{issue_id:selectedIssue,message}))$('#message').value='';};
$('#investigate').onclick=()=>askQuestion('Explain the '+issue().rule+' finding in this file. Point out the problematic lines and what can go wrong.');
$('#review-diff').onclick=()=>{if(state.pending)openDiff(state.pending.issue.path,state.pending.issue.id);};
$('#approve').onclick=()=>action('/api/approve',{review_id:state.pending?.id,reason:$('#reason').value});
$('#reject').onclick=()=>action('/api/reject',{review_id:state.pending?.id,reason:$('#reason').value});
$('#reset').onclick=async()=>{if(await action('/api/reset')){selectedIssue=state.issues[0]?.id||null;if(state.issues[0])openFile(state.issues[0].path,selectedIssue,true);}};
document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>{mode=b.dataset.mode;renderEditor();renderControls();});
document.querySelectorAll('[data-panel]').forEach(b=>b.onclick=()=>showPanel(b.dataset.panel));
$('#search').oninput=e=>{filter=e.target.value;renderTree();};
$('#search').onkeydown=e=>{if(e.key==='Enter'){const path=Object.keys(state.sources).find(p=>p.toLowerCase().includes(filter.toLowerCase()));if(path)openFile(path,null,true);}};
$('#message').onkeydown=e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();askQuestion();}};
$('#toggle-explorer').onclick=()=>{if(matchMedia('(max-width:850px)').matches)document.body.classList.toggle('mobile-explorer');else document.body.classList.toggle('explorer-hidden');};
$('#show-problems').onclick=()=>{showPanel('problems');$('#problems').scrollIntoView({block:'nearest'});};
$('#show-ai').onclick=()=>{$('#message').focus();$('#chat-form').scrollIntoView({block:'nearest'});};
$('#prompt-toggle').onclick=()=>$('#prompt-dialog').showModal();$('#prompt-close').onclick=()=>$('#prompt-dialog').close();
$('#wrap').onclick=()=>{const wrapped=$('#editor').classList.toggle('wrapped');$('#wrap').setAttribute('aria-pressed',String(wrapped));$('#wrap').classList.toggle('selected',wrapped);};
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='p'){e.preventDefault();$('#search').focus();$('#search').select();}});
setInterval(refresh,650);refresh();
