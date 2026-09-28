import os, tempfile, unittest, gc
from src.core.agent_learning import AgentLearningEngine
from src.core.persistent_memory import PersistentMemory

class TestAgentLearning(unittest.TestCase):
    def test_record_and_recall_are_scoped(self):
        with tempfile.TemporaryDirectory() as td:
            mem=PersistentMemory(os.path.join(td,"m.sqlite3")); e=AgentLearningEngine(mem)
            out=e.record("t1","w1","agent","PLN-1",{"outcome":"failure","counts":{"failed":1}})
            self.assertTrue(out["allowed"]); self.assertTrue(e.recall("agent","t1","w1","failure")); self.assertEqual(e.recall("agent","t2","w2","failure"),[])
            del e, mem
            gc.collect()

if __name__ == "__main__": unittest.main()
