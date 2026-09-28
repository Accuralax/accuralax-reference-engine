from __future__ import annotations
from datetime import datetime, timezone
import copy

class OmegaFinalConvergence:
    """APEX final Ω8→Ω15 convergence gate.

    Ω13 optimizes, Ω14 scopes globally, Ω15 certifies enterprise readiness.
    Ω9 remains execution authority; every upstream stage is fail-closed.
    """
    STAGES=tuple(f"omega{i}" for i in range(8,16))

    def __init__(self, omega8=None, omega9=None, omega10=None, omega11=None,
                 omega12=None, omega13=None, omega14=None, omega15=None):
        self.stages={f"omega{i}":x for i,x in enumerate(
            [omega8,omega9,omega10,omega11,omega12,omega13,omega14,omega15],8)}
        self.history=[]

    @staticmethod
    def _now(): return datetime.now(timezone.utc).isoformat()

    def health(self):
        return {"status":"ok" if all(self.stages.values()) else "degraded",
                "stages":{k:bool(v) for k,v in self.stages.items()},
                "execution_authority":"omega9","fail_closed":True,
                "timestamp":self._now()}

    def _gate(self,name,obj,*args,**kwargs):
        if obj is None:
            return {"status":"blocked","release_allowed":False,"reason":f"{name}_missing"}
        fn=getattr(obj,"release_gate",None)
        if not fn:
            fn=getattr(obj,"production_readiness",None)
        if not fn:
            return {"status":"blocked","release_allowed":False,"reason":f"{name}_gate_missing"}
        try:
            result=fn(*args,**kwargs)
            allowed=bool(result.get("release_allowed",result.get("ready",False)))
            return {"status":"ready" if allowed else "blocked","release_allowed":allowed,"result":result}
        except Exception as exc:
            return {"status":"blocked","release_allowed":False,"reason":f"{name}_gate_error","error":type(exc).__name__}

    def convergence(self):
        results={}
        for name,obj in self.stages.items():
            if name=="omega15":
                continue
            results[name]=self._gate(name,obj)
        missing=[k for k,v in results.items() if not v["release_allowed"]]
        self.history.append({"event":"omega.convergence","at":self._now(),"results":copy.deepcopy(results)})
        return {"status":"ready" if not missing else "blocked",
                "release_allowed":not missing,"results":results,"blocked_stages":missing}

    def final_gate(self):
        upstream=self.convergence()
        if not upstream["release_allowed"]:
            return {"status":"blocked","release_allowed":False,
                    "reason":"upstream_stage_blocked","upstream":upstream}
        final=self.stages.get("omega15")
        if final is None:
            return {"status":"blocked","release_allowed":False,"reason":"omega15_missing"}
        layers={k:{"ready":True} for k in self.STAGES}
        try:
            result=final.final_gate(layers)
        except Exception:
            result=final.production_readiness(layers).get("final_gate",{})
        allowed=bool(result.get("release_allowed",False))
        return {"status":"ready" if allowed else "blocked",
                "release_allowed":allowed,"upstream":upstream,"omega15":result,
                "execution_authority":"omega9"}

    def production_readiness(self):
        gate=self.final_gate()
        return {"ready":gate["release_allowed"],"status":gate["status"],
                "final_gate":gate,"health":self.health(),
                "stages":self.STAGES}

    def layer_status(self):
        rows=[]
        for stage,obj in self.stages.items():
            rows.append({"stage":stage,"configured":obj is not None,
                         "status":"configured" if obj is not None else "missing"})
        return rows
