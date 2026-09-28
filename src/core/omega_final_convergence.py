from __future__ import annotations
from datetime import datetime, timezone
import copy

class OmegaFinalConvergence:
    """APEX final Ω8→Ω15 convergence gate; Ω9 remains execution authority."""
    STAGES=tuple(f"omega{i}" for i in range(8,16))
    def __init__(self, omega8=None, omega9=None, omega10=None, omega11=None, omega12=None, omega13=None, omega14=None, omega15=None):
        self.stages={f"omega{i}":x for i,x in enumerate([omega8,omega9,omega10,omega11,omega12,omega13,omega14,omega15],8)}
        self.history=[]
    @staticmethod
    def _now(): return datetime.now(timezone.utc).isoformat()
    def health(self):
        return {"status":"ok" if all(self.stages.values()) else "degraded","stages":{k:bool(v) for k,v in self.stages.items()},"execution_authority":"omega9","fail_closed":True,"timestamp":self._now()}
    def _gate(self,name,obj):
        if obj is None:return {"status":"blocked","release_allowed":False,"reason":f"{name}_missing"}
        release=getattr(obj,"release_gate",None); readiness=getattr(obj,"production_readiness",None)
        if release:
            try:
                result=release()
                return {"status":"ready" if result.get("release_allowed",False) else "blocked","release_allowed":bool(result.get("release_allowed",False)),"result":result}
            except TypeError:
                pass
            except Exception as exc:
                return {"status":"blocked","release_allowed":False,"reason":f"{name}_gate_error","error":type(exc).__name__}
        if readiness:
            try:
                result=readiness()
                allowed=bool(result.get("ready",result.get("release_allowed",False)))
                return {"status":"ready" if allowed else "blocked","release_allowed":allowed,"result":result}
            except Exception as exc:
                return {"status":"blocked","release_allowed":False,"reason":f"{name}_readiness_error","error":type(exc).__name__}
        return {"status":"blocked","release_allowed":False,"reason":f"{name}_gate_missing"}
    def convergence(self):
        results={k:self._gate(k,v) for k,v in self.stages.items() if k!="omega15"}
        blocked=[k for k,v in results.items() if not v["release_allowed"]]
        self.history.append({"event":"omega.convergence","at":self._now(),"results":copy.deepcopy(results)})
        return {"status":"ready" if not blocked else "blocked","release_allowed":not blocked,"results":results,"blocked_stages":blocked}
    def final_gate(self):
        upstream=self.convergence()
        if not upstream["release_allowed"]:return {"status":"blocked","release_allowed":False,"reason":"upstream_stage_blocked","upstream":upstream}
        final=self.stages.get("omega15")
        if final is None:return {"status":"blocked","release_allowed":False,"reason":"omega15_missing"}
        layers={k:{"ready":True} for k in self.STAGES}
        try: result=final.final_gate(layers)
        except Exception: result=final.production_readiness(layers).get("final_gate",{})
        allowed=bool(result.get("release_allowed",False))
        return {"status":"ready" if allowed else "blocked","release_allowed":allowed,"upstream":upstream,"omega15":result,"execution_authority":"omega9"}
    def production_readiness(self):
        gate=self.final_gate()
        return {"ready":gate["release_allowed"],"status":gate["status"],"final_gate":gate,"health":self.health(),"stages":self.STAGES}
    def layer_status(self):
        return [{"stage":s,"configured":self.stages[s] is not None,"status":"configured" if self.stages[s] is not None else "missing"} for s in self.STAGES]
