// Shared DOM helpers for read-only evidence panels. All artifact text uses textContent.
export function evidenceUI(ui) {
  const {el, json:read} = ui;
  const section = title => { const n=ui.section(title); n.querySelector('.panel-title').replaceWith(el('h3',title,'panel-title')); return n; };
  const inspect = (parent,title,value) => { const d=el('details'),p=ui.raw(value);p.tabIndex=0;d.append(el('summary',title),p);parent.append(d); };
  const choose = (label,id,options,value,change) => { const box=el('div',undefined,'analytics-control'),l=el('label',label),s=el('select');l.htmlFor=id;s.id=id;for(const [v,title] of options){const o=el('option',title);o.value=v;s.append(o);}s.value=value;s.addEventListener('change',()=>change(s.value));box.append(l,s);return box; };
  const table = (headers,rows,caption) => { const wrap=el('div',undefined,'analytics-table');wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label',caption);const t=el('table'),head=el('thead'),tr=el('tr');t.append(el('caption',caption));for(const h of headers){const th=el('th',h);th.scope='col';tr.append(th);}head.append(tr);t.append(head);const body=el('tbody');for(const row of rows){const r=el('tr');for(const value of row)r.append(el('td',value));body.append(r);}t.append(body);wrap.append(t);return wrap; };
  const origin = (file,label) => {const a=el('a',label+' ↗');a.href=read('upstream.json').artifacts.find(a=>a.file===file).source_url;return a;};
  const stages = (root,items,initial,render) => {const nav=el('nav',undefined,'release-stages');nav.setAttribute('aria-label','Evidence stages');const status=el('p',undefined,'release-announcement');status.setAttribute('role','status');const content=el('div',undefined,'release-detail');let selected=initial;
    function show(){for(const b of nav.querySelectorAll('button'))b.setAttribute('aria-pressed',String(b.dataset.evidenceStage===selected));status.textContent='Viewing '+items.find(x=>x[0]===selected)[1];content.replaceChildren(render(selected));}
    for(const [id,title] of items){const b=el('button',title);b.type='button';b.dataset.evidenceStage=id;b.addEventListener('click',()=>{selected=id;show();});nav.append(b);}root.append(nav,status,content);show();};
  return {section,inspect,choose,table,origin,stages};
}
export const usd = cents => new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',minimumFractionDigits:2}).format(cents/100);
export const number = value => new Intl.NumberFormat('en-US').format(value);
