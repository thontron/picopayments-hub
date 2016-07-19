import os
import shutil
import unittest
import tempfile
from pycoin.serialize import b2h
from counterpartylib.lib.micropayments import util
from counterpartylib.lib.micropayments.scripts import compile_deposit_script
from picopayments import ctrl
from picopayments import api


class TestCtrl(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="picopayments_test_")
        # TODO start mock counterparty service
        ctrl.initialize(["--testnet", "--root={0}".format(self.root)])

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_mpc_hub_terms(self):
        # TODO test input validation

        # test gets all
        terms = api.mpc_hub_terms()
        self.assertEqual(terms, {
            "BTC": {
                "deposit_ratio": 1.0,
                "fee_setup": 10,
                "timeout_limit": 0,
                "fee_sync": 1,
                "setup_ttl": 2,
                "deposit_limit": 0
            },
            "XCP": {
                "deposit_ratio": 1.0,
                "fee_setup": 10,
                "timeout_limit": 0,
                "fee_sync": 1,
                "setup_ttl": 2,
                "deposit_limit": 0
            },
            "A14456548018133352000": {
                "deposit_ratio": 1.0,
                "fee_setup": 10,
                "timeout_limit": 0,
                "fee_sync": 1,
                "setup_ttl": 2,
                "deposit_limit": 0
            }
        })

        # test limits to asset
        terms = api.mpc_hub_terms("XCP")
        self.assertEqual(terms, {
            "XCP": {
                "deposit_ratio": 1.0,
                "fee_setup": 10,
                "timeout_limit": 0,
                "fee_sync": 1,
                "setup_ttl": 2,
                "deposit_limit": 0
            }
        })

    def test_mpc_hub_request(self):
        # TODO test raises exception on no terms for asset
        # TODO test input validation

        asset = "XCP"
        client_key = ctrl.create_key(asset)
        secret_hash = util.hash160hex(util.b2h(os.urandom(32)))
        result = api.mpc_hub_request(asset, client_key["pubkey"],
                                     secret_hash, None)
        self.assertIsNotNone(result)

        # TODO test hub pubkey in db
        # TODO test recv spend secret in db
        # TODO test send micropayment channel created in db
        # TODO test recv micropayment channel created in db
        # TODO test hub connection created in db

    def test_mpc_hub_deposit(self):

        asset = "XCP"
        client_key = ctrl.create_key(asset)
        client_pubkey = client_key["pubkey"]
        client2hub_spend_secret_hash = util.hash160hex(
            util.b2h(os.urandom(32)))
        result = api.mpc_hub_request(asset, client_pubkey,
                                     client2hub_spend_secret_hash, None)
        handle = result["handle"]
        hub_pubkey = result["pubkey"]
        # hub2client_spend_secret_hash = result["spend_secret_hash"]

        client2hub_deposit_script = b2h(compile_deposit_script(
            client_pubkey, hub_pubkey, client2hub_spend_secret_hash, 1337
        ))

        result = api.mpc_hub_deposit(
            handle, client2hub_deposit_script,
            util.hash160hex(util.b2h(os.urandom(32)))
        )
        self.assertIsNotNone(result)

        # TODO test send channel updated
        # TODO test receive channel updated
        # TODO test secret saved


if __name__ == "__main__":
    unittest.main()
