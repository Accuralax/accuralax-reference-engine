import React from "react";
const API="http://127.0.0.1:8788";
export async function get(path:string){const r=await fetch(API+path);if(!r.ok)throw new Error(await r.text());return r.json()}
export async function post(path:string,body:any){const r=await fetch(API+path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});if(!r.ok)throw new Error(await r.text());return r.json()}
export function Pill({children,kind="neutral"}:any){return <span className={"pill "+kind}>{children}</span>}
export function Metric({label,value,icon:Icon}:any){return <div className="metric"><Icon size={18}/><div><strong>{value}</strong><span>{label}</span></div></div>}
export function StaticPanel({title,icon:Icon,children}:any){return <section className="card"><div className="card-title"><div><Icon size={17}/><b>{title}</b></div><Pill>Control ready</Pill></div>{children}</section>}
