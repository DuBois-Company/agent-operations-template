"""Executable check on the module docstrings (node T5).

T5 was a prose node: write the module docstrings for the auth core. Prose is
the easiest thing in a repository to let rot, so its acceptance criterion is
not "the docstrings read well" -- it is that every example inside them runs
and produces what it claims. doctest turns that into an exit code.
"""

import doctest
import unittest

from example.src import auth, config, middleware, revocation

MODULES = (auth, config, middleware, revocation)


def load_tests(loader, tests, ignore):
    """unittest discovery hook: fold the docstring examples into the suite."""
    for module in MODULES:
        tests.addTests(doctest.DocTestSuite(module, optionflags=doctest.ELLIPSIS))
    return tests


class DocstringPresenceTest(unittest.TestCase):
    """The docstrings themselves are the deliverable, so their absence fails."""

    def test_every_module_carries_a_docstring(self):
        for module in MODULES:
            self.assertTrue((module.__doc__ or "").strip(),
                            "%s has no module docstring" % module.__name__)

    def test_the_public_entry_points_are_documented(self):
        for func in (auth.issue_token, auth.verify_token,
                     middleware.require_token, middleware.login_response_headers):
            self.assertTrue((func.__doc__ or "").strip(),
                            "%s has no docstring" % func.__name__)


if __name__ == "__main__":
    unittest.main()
