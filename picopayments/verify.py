# coding: utf-8
# Copyright (c) 2016 Fabian Barkhau <f483@storj.io>
# License: MIT (see LICENSE file)


import re
import jsonschema
from counterpartylib.lib.micropayments import validate
from . import err
from . import db
from . import cfg
from . import rpc
from . import ctrl


URL_REGEX = re.compile(

    r'^(?:http|ftp)s?://'  # http:// or https://

    # domain...
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)'
    r'+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'

    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE
)


PAYMENT_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "payer_handle": {"type": "string"},
            "payee_handle": {"type": "string"},
            "amount": {"type": "number"},
            "token": {"type": "string"}
        },
        "required": ["payer_handle", "payee_handle", "amount", "token"],
        "additionalProperties": False
    }
}


COMMIT_SCHEMA = {
    "type": "object",
    "properties": {
        "rawtx": {"type": "string"},
        "script": {"type": "string"},
    },
    "required": ["rawtx", "script"],
    "additionalProperties": False
}


REVOKES_SCHEMA = {
    "type": "array",
    "items": {"type": "string"}
}


def is_url(url):
    if not URL_REGEX.match(url):
        raise err.InvalidUrl(url)


def request_input(asset, pubkey, spend_secret_hash, hub_rpc_url):
    validate.pubkey(pubkey)
    validate.hash160(spend_secret_hash)
    if hub_rpc_url:
        is_url(hub_rpc_url)

    # asset must be in terms
    all_terms = ctrl.terms()
    if asset not in all_terms:
        raise err.AssetNotInTerms(asset)


def deposit_input(handle, deposit_script, next_revoke_secret_hash):
    validate.is_hex(handle)
    validate.hash160(next_revoke_secret_hash)
    recv_channel = db.receive_channel(handle)
    if not recv_channel:
        raise err.HandleNotFound(handle)
    expected_payee_pubkey = recv_channel["payee_pubkey"]
    expected_spend_secret_hash = recv_channel["spend_secret_hash"]
    validate.deposit_script(deposit_script, expected_payee_pubkey,
                            expected_spend_secret_hash)
    if recv_channel["meta_complete"]:
        raise err.DepositAlreadyGiven(handle)


def is_recv_commit(handle, commit_rawtx, commit_script):
    netcode = "XTN" if cfg.testnet else "BTC"
    recv_channel = db.receive_channel(handle)
    deposit_utxos = rpc.counterparty_call(
        method="get_unspent_txouts",
        params={"address": recv_channel["deposit_address"]}
    )
    validate.commit_rawtx(
        deposit_utxos, commit_rawtx, recv_channel["asset"],
        recv_channel["deposit_script"], commit_script, netcode
    )


def sync_input(handle, next_revoke_secret_hash, sends, commit, revokes):
    validate.is_hex(handle)
    validate.hash160(next_revoke_secret_hash)
    handles = [handle]

    if sends:
        jsonschema.validate(sends, PAYMENT_SCHEMA)
        for send in sends:
            validate.is_hex(send["token"])
            validate.is_hex(send["payee_handle"])
            validate.is_hex(send["payer_handle"])
            validate.is_quantity(send["amount"])
            handles += [send["payer_handle"], send["payee_handle"]]
            # FIXME validate assets match on both ends

    # make sure all handles actually exist
    if not db.handles_exist(handles):
        raise err.HandlesNotFound(handles)

    if revokes:
        jsonschema.validate(revokes, REVOKES_SCHEMA)

    if commit:
        jsonschema.validate(commit, COMMIT_SCHEMA)
        is_recv_commit(handle, commit["rawtx"], commit["script"])

    # FIXME validate channels not expired