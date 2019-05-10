#!/usr/bin/env python

from troposphere import (
    Template,
    Output,
    GetAtt,
    Ref,
    Sub
)

from troposphere.iam import (
    ManagedPolicy
)

from ozone.outputs import object_outputs
from ozone.resolvers.organizations import (
    find_org_in_tree,
    get_ou_accounts,
    get_all_accounts_in_ou_and_sub
)

from argparse import ArgumentParser

PARSER = ArgumentParser('Create IAM Policies to switch roles for a given AWS Organization Unit')
PARSER.add_argument(
    '--ou-name', '--organization-unit-name', help="Name of the organization unit", required=True
)

PARSER.add_argument(
    '--as-root', '--org-as-root', help="Uses the organization as the root, using all sub OUs accounts", required=False, action="store_true"
)

PARSER.add_argument(
    '--role', help="Uses the organization as the root, using all sub OUs accounts", required=False, action="append"
)
ARGS = PARSER.parse_args()

OU_NAME = ARGS.ou_name
if not ARGS.ou_name.startswith('/'):
    OU_NAME = '/' + ARGS.ou_name

OU_NAME = ''.join(x.lower().title() for x in OU_NAME.split('/'))
POLICY_NAME_PREFIX = '.'.join(x.lower() for x in ARGS.ou_name.split('/'))
if POLICY_NAME_PREFIX.startswith('.'):
    POLICY_NAME_PREFIX = POLICY_NAME_PREFIX[1:]

ORG = find_org_in_tree(ARGS.ou_name)
if ARGS.as_root:
    accounts = get_all_accounts_in_ou_and_sub(ORG['Id'])
else:
    accounts = get_ou_accounts(ORG['Id'])

if not accounts:
    exit(f'No accounts found to create a policy for - OU Name: {ARGS.ou_name}')

if not ARGS.role:
    ROLE_NAMES = [
        'admin',
        'poweruser',
        'read'
    ]
else:
    ROLE_NAMES = ARGS.role


def switch_policy(accounts, role_name):
    """
    Generates the template policy document for the switch role
    """

    policy_document = {
        'Version': '2012-10-17',
        'Statement': []
    }
    resources = []
    for account in accounts:
        resources.append(f'arn:aws:iam::{account["Id"]}:role/{role_name}')

    statement = {
        'Sid': f'{role_name.lower()}To{OU_NAME}',
        'Effect': 'Allow',
        'Action': ['sts:AssumeRole'],
        'Resource': resources
    }
    policy_document['Statement'].append(statement)
    return policy_document



POLICIES = []
if accounts:
    for role in ROLE_NAMES:
        policy_res = ManagedPolicy(
            f'{role.title()}AccessTo{OU_NAME}',
            ManagedPolicyName=f'{POLICY_NAME_PREFIX}-{role}.access',
            PolicyDocument=switch_policy(accounts, role),
            Path=r'/SwitchTo/' + role + '/'
        )
        POLICIES.append(policy_res)


TEMPLATE = Template()
TEMPLATE.set_description('Template with the policies for switch roles to accounts')

for counti, policy in enumerate(POLICIES):
    TEMPLATE.add_resource(policy)
    TEMPLATE.add_output(object_outputs(policy, supports_arn=False))
print (TEMPLATE.to_yaml())
