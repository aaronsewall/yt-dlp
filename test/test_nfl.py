import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from test.helper import FakeYDL
from yt_dlp.extractor.nfl import NFLBaseIE


class TestNFLLogin(unittest.TestCase):
    def test_realm_scoped_authentication_flow(self):
        ie = NFLBaseIE(FakeYDL())
        auth_url = None

        def download_json(url, *args, **kwargs):
            nonlocal auth_url
            note = args[1] if len(args) > 1 else kwargs.get('note')
            if note == 'Starting login':
                auth_url = url
                return {
                    'callbacks': [
                        {
                            'input': [
                                {'name': 'IDToken1', 'value': ''},
                                {'name': 'IDToken2', 'value': ''},
                            ],
                        },
                    ],
                }
            if note == 'Submitting login':
                submitted = json.loads(kwargs['data'])
                self.assertEqual(
                    submitted['callbacks'][0]['input'],
                    [
                        {'name': 'IDToken1', 'value': 'test-user'},
                        {'name': 'IDToken2', 'value': 'test-password'},
                    ],
                )
                return {'tokenId': 'offline-test-token'}
            if note == 'Downloading login token':
                return {'access_token': 'offline-access-token'}
            if note == 'Downloading access token':
                return {'accessToken': 'offline-api-token', 'expiresIn': 3600, 'refreshToken': 'offline-refresh-token'}
            self.fail(f'Unexpected JSON request: {url}')

        with (
            patch.object(ie, '_download_json', side_effect=download_json) as download_mock,
            patch.object(
                ie,
                '_request_webpage',
                side_effect=lambda *args, **kwargs: SimpleNamespace(
                    url=f"https://id.nfl.com/account?code=offline-code&state={kwargs['query']['state']}",
                ),
            ),
        ):
            ie._perform_login('test-user', 'test-password')

        self.assertIn('/json/realms/root/realms/alpha/authenticate?', auth_url)
        self.assertEqual([c.args[0] for c in download_mock.call_args_list[:2]], [auth_url, auth_url])
        self.assertEqual(
            ie._ACCOUNT_INFO, {'oidcAccessToken': 'offline-access-token', 'refreshToken': 'offline-refresh-token'},
        )


if __name__ == '__main__':
    unittest.main()
