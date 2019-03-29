#!/usr/bin/env python
"""
Script to generate aws configuration file for assume roles in an organization,
listing accounts from the root acount
"""
import jinja2
import os
import boto3
from argparse import ArgumentParser


def get_self_account_id():
    """
    :return: String()
    """
    client = boto3.client('sts')
    return client.get_caller_identity()['Account']


def get_organization_access(role_arn, mfa_serial=None, token=None, external_id=None):

    client = boto3.client('sts')
    try:
        args = {
            'RoleArn': role_arn,
            'RoleSessionName': 'TempAccess',
        }
        if mfa_serial is not None and token is not None:
            args['SerialNumber'] = mfa_serial
            args['TokenCode'] = token
        if external_id is not None:
            args['ExternalId'] = external_id
        creds = client.assume_role(**args)
        return creds['Credentials']
    except Exception as e:
        print (e)
        return None


def get_organization_accounts(creds, self_acct, accounts_list=None, next_token=None):

    if accounts_list is None:
        accounts_list = []
    client = boto3.client(
        'organizations',
        aws_access_key_id=creds['AccessKeyId'],
        aws_secret_access_key=creds['SecretAccessKey'],
        aws_session_token=creds['SessionToken']
    )
    if isinstance(next_token, str):
        accounts_r = client.list_accounts(NextToken=next_token)
    else:
        accounts_r = client.list_accounts()

    if 'NextToken' in accounts_r.keys():
        for account in accounts_r['Accounts']:
            if account['Id'] != self_acct and account['Status'] == 'ACTIVE':
                del account['JoinedTimestamp']
                accounts_list.append(account)
        return get_organization_accounts(creds, self_acct, accounts_list, accounts_r['NextToken'])
    else:
        for account in accounts_r['Accounts']:
            if account['Id'] != self_acct and account['Status'] == 'ACTIVE':
                del account['JoinedTimestamp']
                accounts_list.append(account)
    return accounts_list


if __name__ == '__main__':

    PARSER = ArgumentParser()
    PARSER.add_argument(
        '--account-id', required=True
    )
    PARSER.add_argument(
        '--root-role-name', required=True
    )
    PARSER.add_argument(
        '--user-name', required=True
    )
    PARSER.add_argument(
        '--token', required=False
    )
    PARSER.add_argument(
        '--external-id', required=False
    )
    PARSER.add_argument(
        '--role-name', required=True
    )

    ARGS = PARSER.parse_args()

    SOURCE_ACCOUNT = get_self_account_id()
    ROLE_ARN = f'arn:aws:iam::{ARGS.account_id}:role/{ARGS.root_role_name}'
    if ARGS.token:
            MFA_SERIAL = f'arn:aws:iam::{SOURCE_ACCOUNT}:mfa/{ARGS.user_name}'

    if ARGS.external_id and ARGS.token:
        CREDENTIALS = get_organization_access(ROLE_ARN, MFA_SERIAL, ARGS.token, ARGS.external_id)
    elif ARGS.external_id and not ARGS.token:
            CREDENTIALS = get_organization_access(ROLE_ARN, None, None, ARGS.external_id)
    elif ARGS.token and not ARGS.external_id:
        CREDENTIALS = get_organization_access(ROLE_ARN, MFA_SERIAL, ARGS.token)

    ACCOUNTS = get_organization_accounts(CREDENTIALS, SOURCE_ACCOUNT)
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath='./'))
    template = env.get_template('aws_config.j2')
    render = template.render(
        accounts=ACCOUNTS,
        source_account_id=SOURCE_ACCOUNT,
        username=ARGS.user_name,
        role_name=ARGS.role_name
    )

    with open('config', 'w') as config_fd:
        config_fd.write(render)

