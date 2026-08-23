import unittest
from pathlib import Path

from scripts.audit_player_identity import audit


class PlayerIdentityAuditTests(unittest.TestCase):
    def test_corroborated_identity_fixture(self):
        root = Path(__file__).resolve().parents[1]
        result = audit(root)
        self.assertEqual(result["failures"], [])
        self.assertEqual(result["registry_collision_count"], 0)
        self.assertEqual(result["precision"], 1.0)


if __name__ == "__main__":
    unittest.main()
