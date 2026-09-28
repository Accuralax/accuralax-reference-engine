from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json, uuid
from typing import Any
from .master_entity_registry import MasterEntityRegistry

class EnterpriseEntityModel:
    def __init__(self, db_path: str | None = None, registry: MasterEntityRegistry | None = None):
        root = Path(__file__).resolve().parents[2]
        self.path = Path(db_path) if db_path else root / "data" / "enterprise_entities.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.registry = registry or MasterEntityRegistry()
        if not self.path.exists(): self._save({"entities": {}, "relationships": {}})

    def _load(self): return json.loads(self.path.read_text(encoding="utf-8"))
    def _save(self, data): self.path.write_text(json.dumps(data, sort_keys=True, indent=2), encoding="utf-8")
    @staticmethod
    def _now(): return datetime.now(timezone.utc).isoformat()
    @staticmethod
    def _scope(t,w):
        if not t or not w: raise ValueError("tenant_id_and_workspace_id_required")
        return str(t), str(w)

    def upsert(self,t,w,entity_type,payload:dict[str,Any]):
        t,w=self._scope(t,w); check=self.registry.validate(entity_type,payload)
        if not check["valid"]: raise ValueError(";".join(check["errors"]))
        key=str(payload[self.registry.get(entity_type)["key"]]); data=self._load()
        compound=f"{t}:{w}:{entity_type}:{key}"; old=data["entities"].get(compound); now=self._now()
        eid=old["entity_id"] if old else "ENT-"+uuid.uuid4().hex[:16].upper()
        data["entities"][compound]={"entity_id":eid,"tenant_id":t,"workspace_id":w,"entity_type":entity_type,"stable_key":key,"payload":dict(payload),"created_at":old["created_at"] if old else now,"updated_at":now}
        self._save(data)
        return {"status":"updated" if old else "created","entity_id":eid,"entity_type":entity_type,"stable_key":key}

    def get(self,t,w,eid):
        t,w=self._scope(t,w)
        for r in self._load()["entities"].values():
            if r["entity_id"]==eid and r["tenant_id"]==t and r["workspace_id"]==w: return r
        return None

    def list(self,t,w,entity_type=None):
        t,w=self._scope(t,w)
        return [r for r in self._load()["entities"].values() if r["tenant_id"]==t and r["workspace_id"]==w and (entity_type is None or r["entity_type"]==entity_type)]

    def link(self,t,w,source_id,target_id,relationship_type):
        t,w=self._scope(t,w); source=self.get(t,w,source_id); target=self.get(t,w,target_id)
        if not source or not target: raise ValueError("entity_not_found_in_scope")
        if not self.registry.relationship(source["entity_type"],target["entity_type"]): raise ValueError("relationship_not_allowed_by_registry")
        data=self._load(); key=f"{t}:{w}:{source_id}:{target_id}:{relationship_type}"
        if key in data["relationships"]: return {"status":"already_exists","relationship_id":data["relationships"][key]["relationship_id"]}
        rid="REL-"+uuid.uuid4().hex[:16].upper(); data["relationships"][key]={"relationship_id":rid,"tenant_id":t,"workspace_id":w,"source_entity_id":source_id,"target_entity_id":target_id,"relationship_type":relationship_type,"created_at":self._now()}; self._save(data)
        return {"status":"created","relationship_id":rid}

    def links(self,t,w,eid):
        t,w=self._scope(t,w)
        return [r for r in self._load()["relationships"].values() if r["tenant_id"]==t and r["workspace_id"]==w and (r["source_entity_id"]==eid or r["target_entity_id"]==eid)]

    def health(self):
        d=self._load(); return {"status":"ok","entity_types":len(self.registry.list_entities()),"entities":len(d["entities"]),"relationships":len(d["relationships"]),"tenant_scoped":True,"registry_backed":True}
