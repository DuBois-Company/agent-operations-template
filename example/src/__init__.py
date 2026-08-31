"""Source modules for the example auth service.

    config.py      settings and their environment overrides   (T7)
    auth.py        token issue and verify, HMAC-SHA256        (T1, T8)
    revocation.py  the revocation list verify consults        (T9)
    middleware.py  the request wrapper and the login headers  (T2, T10)

Node ids in those comments point at example/graph.yaml, which is the source
of truth for what each module was built to do and who built it.
"""
