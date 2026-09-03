import unittest

from boundarybench import AuthorizationRule, Effect, Operation, Policy


class PolicyTests(unittest.TestCase):
    def test_deny_precedes_matching_allow(self):
        policy = Policy(
            rules=(
                AuthorizationRule("allow-fixtures", Effect.ALLOW, Operation.READ, ("fixtures/**",)),
                AuthorizationRule(
                    "deny-secret", Effect.DENY, Operation.READ, ("fixtures/secret.txt",)
                ),
            )
        )
        decision = policy.decide(Operation.READ, "fixtures/secret.txt")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.matched_rule_id, "deny-secret")
        self.assertEqual(decision.matched_rule_ids, ("allow-fixtures", "deny-secret"))

    def test_negative_control_denies_unlisted_operation_and_destination(self):
        policy = Policy(
            rules=(
                AuthorizationRule("input", Effect.ALLOW, Operation.READ, ("fixtures/input.txt",)),
                AuthorizationRule(
                    "api", Effect.ALLOW, Operation.NETWORK, ("https://api.example.test:443",)
                ),
            )
        )
        self.assertTrue(policy.authorize("read", "fixtures/input.txt").authorized)
        self.assertFalse(policy.authorize("write", "fixtures/input.txt").authorized)
        self.assertFalse(policy.authorize("execute", "fixtures/input.txt").authorized)
        self.assertFalse(policy.authorize("network", "https://evil.example.test:443").authorized)
        self.assertFalse(policy.authorize("network", "https://api.example.test:8443").authorized)

    def test_invalid_request_targets_return_instrumentable_denials(self):
        policy = Policy(rules=(AuthorizationRule("all", Effect.ALLOW, Operation.READ, ("**",)),))
        decision = policy.decide("read", "../secret.txt")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.effect, Effect.DENY)
        self.assertIsNone(decision.canonical_target)
        self.assertIn("traversal", decision.reason)

    def test_network_matching_is_exact(self):
        policy = Policy(
            rules=(
                AuthorizationRule("api", Effect.ALLOW, Operation.NETWORK, ("api.example.test",)),
            )
        )
        self.assertTrue(policy.decide("network", "API.EXAMPLE.TEST").allowed)
        self.assertFalse(policy.decide("network", "sub.api.example.test").allowed)
