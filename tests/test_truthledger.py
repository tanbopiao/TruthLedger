import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from truthledger.auth import Auth, redact
from truthledger.firewall import (TruthFirewall, is_allowed, is_high_level,
                                  load_whitelist, SUSPECT, TRUSTED, FETCH_FAIL)
from truthledger.governance import (p1_audit, p2_distill, p3_detect_invalid,
                                    run_cycle, score_candidate)
from truthledger.immortality import ImmortalityGuard
from truthledger.provenance import verify_one, verify_all, content_digest


class TestAuth(unittest.TestCase):
    def test_from_env_requires_token(self):
        self.assertRaises(RuntimeError, Auth.from_env)

    def test_redact(self):
        self.assertNotIn("SECRET123456", redact("tok=SECRET123456", "SECRET123456"))


class TestFirewall(unittest.TestCase):
    def test_is_high_level(self):
        self.assertTrue(is_high_level("RULE.META.X"))
        self.assertTrue(is_high_level("AXIOM.CORE"))
        self.assertFalse(is_high_level("DATA.note"))

    def test_is_allowed(self):
        wl = ["RULE.META.*", "EXACT.KEY"]
        self.assertTrue(is_allowed("RULE.META.ANY", wl))
        self.assertTrue(is_allowed("EXACT.KEY", wl))
        self.assertFalse(is_allowed("RULE.EVIL", wl))

    def test_check_suspect(self):
        fw = TruthFirewall(auth=Auth(), fetch=lambda k: {"truth": {}})
        r = fw.check_one("RULE.META.FAKE", whitelist=["OTHER.*"])
        self.assertEqual(r["verdict"], SUSPECT)

    def test_check_trusted(self):
        fw = TruthFirewall(auth=Auth(), fetch=lambda k: {"truth": {"version": 3}})
        r = fw.check_one("DATA.fine")
        self.assertEqual(r["verdict"], TRUSTED)

    def test_check_fetch_fail(self):
        def boom(k):
            raise IOError("down")
        fw = TruthFirewall(auth=Auth(), fetch=boom)
        self.assertEqual(fw.check_one("DATA.x")["verdict"], FETCH_FAIL)

    def test_load_whitelist_missing_file(self):
        self.assertEqual(load_whitelist("/nonexistent/path"), [])


class TestGovernance(unittest.TestCase):
    def test_audit_run_obs_share(self):
        rep = p1_audit(["HEARTBEAT.1", "HEARTBEAT.2", "RULE.A"])
        self.assertEqual(rep["total"], 3)
        self.assertEqual(rep["run_observation_share"], 66.7)

    def test_distill_threshold_and_cloud_dedup(self):
        cands = [{"key": "K1", "content": "x", "score": 90},
                 {"key": "K2", "content": "y", "score": 30},
                 {"key": "CLOUD", "content": "z", "score": 95}]
        out = p2_distill(cands, ["CLOUD"])
        self.assertEqual([c["key"] for c in out], ["K1"])

    def test_detect_invalid(self):
        keys = ["ok.KEY", "X.PROBE.1", "test.tmp", ""]
        self.assertEqual(len(p3_detect_invalid(keys)), 3)

    def test_score_bounds(self):
        self.assertLessEqual(score_candidate("x"), 100)
        self.assertGreaterEqual(score_candidate("x"), 0)

    def test_run_cycle_writes_report(self):
        with tempfile.TemporaryDirectory() as d:
            rep = run_cycle(["RULE.A", "PROBE.X"],
                            [{"key": "K1", "content": "valuable insight", "score": 80}],
                            out_dir=d)
            self.assertIn("verdict", rep)
            self.assertTrue(os.path.exists(rep["files"]["json"]))
            self.assertTrue(os.path.exists(rep["files"]["markdown"]))


def _write_reg(path, keys, content="c"):
    doc = {"nodes": [{"node_id": k, "content": content} for k in keys]}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f)


class TestImmortality(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.au = os.path.join(self.d.name, "authority.json")
        self.rt = os.path.join(self.d.name, "runtime.json")
        _write_reg(self.au, ["A", "B"], "v1")
        _write_reg(self.rt, ["A"], "v1")          # missing B
        self.g = ImmortalityGuard({"authority": self.au, "runtime": self.rt},
                                  authority="authority",
                                  backup_dir=os.path.join(self.d.name, "bk"))

    def test_verify_detects_missing(self):
        rep = self.g.verify()
        self.assertEqual(rep["sources"]["runtime"]["missing"], ["B"])

    def test_restore_fixes(self):
        fixed = self.g.restore()
        self.assertGreaterEqual(fixed, 1)
        self.assertEqual(self.g.verify()["issues"], [])

    def test_audit_index(self):
        a = self.g.audit()
        self.assertFalse(a["ok"])
        self.assertLess(a["immortality_index"], 100)

    def test_snapshot(self):
        ts = self.g.snapshot()
        self.assertTrue(ts)
        self.assertTrue(os.path.exists(os.path.join(self.g.backup_dir,
                                                    "snapshot_index.json")))


class TestProvenance(unittest.TestCase):
    def test_pass(self):
        r = verify_one("K", {"version": 2, "content": "c"},
                       {"version": 3, "updated_at": "t"},
                       {"success": True, "action": "updated"})
        self.assertEqual(r["verdict"], "PASS")

    def test_rollback_and_missing(self):
        r = verify_one("K", {"version": 5, "content": "c"}, {"version": 2}, None)
        self.assertEqual(r["checks"]["D2_version"], "rollback")
        r2 = verify_one("K", {"version": 1, "content": "c"}, None, None)
        self.assertEqual(r2["verdict"], "FAIL")

    def test_verify_all(self):
        res = verify_all({"K": {"version": 1, "content": "c"}},
                         fetch=lambda k: None)
        self.assertEqual(res[0]["verdict"], "FAIL")

    def test_digest(self):
        self.assertEqual(len(content_digest("abc")), 12)


if __name__ == "__main__":
    unittest.main()
