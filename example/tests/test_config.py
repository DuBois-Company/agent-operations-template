"""Settings and their environment overrides (node T7).

T7 was the experiment node: the cheapest agent tier implemented it from a
config-only brief. These are the criteria that brief was written against.
"""

import unittest

from example.src import config
from example.src.config import AuthConfig, ConfigError, load_config


class DefaultsTest(unittest.TestCase):

    def test_default_lifetime_is_twenty_four_hours(self):
        # D1 expressed once, in one place. If this fails, the decision moved
        # and graph.yaml has to move with it.
        self.assertEqual(config.DEFAULT_TTL_SECONDS, 86400)

    def test_load_with_empty_environment_uses_defaults(self):
        cfg = load_config(env={})
        self.assertEqual(cfg.ttl_seconds, config.DEFAULT_TTL_SECONDS)
        self.assertEqual(cfg.issuer, config.DEFAULT_ISSUER)
        self.assertEqual(cfg.clock_skew_seconds, config.DEFAULT_CLOCK_SKEW_SECONDS)
        self.assertEqual(cfg.secret, config.DEV_SECRET)

    def test_repr_does_not_leak_the_secret(self):
        cfg = AuthConfig(secret="unit-test-secret")
        self.assertNotIn("unit-test-secret", repr(cfg))
        self.assertIn("redacted", repr(cfg))


class OverrideTest(unittest.TestCase):

    def test_environment_overrides_every_field(self):
        cfg = load_config(env={
            "EXAMPLE_AUTH_SECRET": "from-the-environment",
            "EXAMPLE_AUTH_TTL_SECONDS": "3600",
            "EXAMPLE_AUTH_ISSUER": "staging-web-app",
            "EXAMPLE_AUTH_CLOCK_SKEW_SECONDS": "5",
        })
        self.assertEqual(cfg.secret, "from-the-environment")
        self.assertEqual(cfg.ttl_seconds, 3600)
        self.assertEqual(cfg.issuer, "staging-web-app")
        self.assertEqual(cfg.clock_skew_seconds, 5)

    def test_unrelated_environment_is_ignored(self):
        cfg = load_config(env={"TTL_SECONDS": "1", "SOMETHING_ELSE": "2"})
        self.assertEqual(cfg.ttl_seconds, config.DEFAULT_TTL_SECONDS)

    def test_blank_override_falls_back_to_the_default(self):
        cfg = load_config(env={"EXAMPLE_AUTH_TTL_SECONDS": "   "})
        self.assertEqual(cfg.ttl_seconds, config.DEFAULT_TTL_SECONDS)

    def test_strict_mode_refuses_the_placeholder_secret(self):
        with self.assertRaises(ConfigError):
            load_config(env={"EXAMPLE_AUTH_STRICT": "1"})

    def test_strict_mode_accepts_a_real_secret(self):
        cfg = load_config(env={"EXAMPLE_AUTH_STRICT": "1",
                               "EXAMPLE_AUTH_SECRET": "not-the-placeholder"})
        self.assertEqual(cfg.secret, "not-the-placeholder")


class ValidationTest(unittest.TestCase):

    def test_non_integer_lifetime_is_a_config_error(self):
        with self.assertRaises(ConfigError):
            load_config(env={"EXAMPLE_AUTH_TTL_SECONDS": "twenty-four hours"})

    def test_zero_lifetime_is_a_config_error(self):
        with self.assertRaises(ConfigError):
            load_config(env={"EXAMPLE_AUTH_TTL_SECONDS": "0"})

    def test_negative_skew_is_a_config_error(self):
        with self.assertRaises(ConfigError):
            load_config(env={"EXAMPLE_AUTH_CLOCK_SKEW_SECONDS": "-1"})

    def test_config_is_immutable(self):
        cfg = AuthConfig(secret="unit-test-secret")
        with self.assertRaises(AttributeError):
            cfg.ttl_seconds = 1

    def test_replace_builds_a_new_validated_config(self):
        cfg = AuthConfig(secret="unit-test-secret")
        other = cfg.replace(ttl_seconds=60)
        self.assertEqual(other.ttl_seconds, 60)
        self.assertEqual(cfg.ttl_seconds, config.DEFAULT_TTL_SECONDS)
        with self.assertRaises(ConfigError):
            cfg.replace(ttl_seconds=-60)
        with self.assertRaises(ConfigError):
            cfg.replace(lifetime=60)


if __name__ == "__main__":
    unittest.main()
