#!/usr/bin/env python

from .conftest import bm_binary


def test_tls_server(crowdsec, certs_dir, api_key_factory, bouncer, bm_cfg_factory):
    """TLS with server-only certificate"""

    api_key = api_key_factory()

    lapi_env = {
        'CACERT_FILE': '/etc/ssl/crowdsec/ca.crt',
        'LAPI_CERT_FILE': '/etc/ssl/crowdsec/lapi.crt',
        'LAPI_KEY_FILE': '/etc/ssl/crowdsec/lapi.key',
        'USE_TLS': 'true',
        'LOCAL_API_URL': 'https://localhost:8080',
        'BOUNCER_KEY_custom': api_key,
    }

    certs = certs_dir(lapi_hostname='lapi')

    volumes = {
        certs: {'bind': '/etc/ssl/crowdsec', 'mode': 'ro'},
    }

    with crowdsec(environment=lapi_env, volumes=volumes) as cs:
        cs.wait_for_log("*CrowdSec Local API listening*")
        # TODO: wait_for_https
        cs.wait_for_http(8080, '/health', want_status=None)

        port = cs.probe.get_bound_port('8080')
        cfg = bm_cfg_factory()
        cfg['crowdsec_config']['lapi_url'] = f'https://localhost:{port}'
        cfg['crowdsec_config']['lapi_key'] = api_key

        with bouncer(bm_binary, cfg) as bm:
            bm.wait_for_lines_fnmatch([
                "*Using API key auth*",
                "*auth-api: auth with api key failed*",
                "*tls: failed to verify certificate: x509: certificate signed by unknown authority*",
            ])

        cfg['crowdsec_config']['ca_cert_path'] = (certs / 'ca.crt').as_posix()

        with bouncer(bm_binary, cfg) as bm:
            bm.wait_for_lines_fnmatch([
                "*Using API key auth*",
                "*Starting server at 127.0.0.1:*"
            ])


def test_tls_mutual(crowdsec, certs_dir, api_key_factory, bouncer, bm_cfg_factory):
    """TLS with two-way bouncer/lapi authentication"""

    lapi_env = {
        'CACERT_FILE': '/etc/ssl/crowdsec/ca.crt',
        'LAPI_CERT_FILE': '/etc/ssl/crowdsec/lapi.crt',
        'LAPI_KEY_FILE': '/etc/ssl/crowdsec/lapi.key',
        'USE_TLS': 'true',
        'LOCAL_API_URL': 'https://localhost:8080',
    }

    certs = certs_dir(lapi_hostname='lapi')

    volumes = {
        certs: {'bind': '/etc/ssl/crowdsec', 'mode': 'ro'},
    }

    with crowdsec(environment=lapi_env, volumes=volumes) as cs:
        cs.wait_for_log("*CrowdSec Local API listening*")
        # TODO: wait_for_https
        cs.wait_for_http(8080, '/health', want_status=None)

        port = cs.probe.get_bound_port('8080')
        cfg = bm_cfg_factory()
        cfg['crowdsec_config']['lapi_url'] = f'https://localhost:{port}'
        cfg['crowdsec_config']['cert_path'] = (certs / 'bouncer.crt').as_posix()
        cfg['crowdsec_config']['key_path'] = (certs / 'bouncer.key').as_posix()
        cfg['crowdsec_config']['ca_cert_path'] = (certs / 'ca.crt').as_posix()

        with bouncer(bm_binary, cfg) as bm:
            bm.wait_for_lines_fnmatch([
                "*Using CA cert*",
                "*Using cert auth with cert*",
                "*Starting server at 127.0.0.1:*"
            ])