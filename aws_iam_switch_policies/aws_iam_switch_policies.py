
from troposphere import (
    Template,
    Output,
    GetAtt,
    Ref,
    Sub
)

from troposphere.iam import (
    Policy
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

TEMPLATE = Template()
TEMPLATE.set_description('Template with the policies for switch roles to accounts')
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


OU_NAME = ''.join(x.lower().title() for x in ARGS.ou_name.split('/'))
OU_POLICY_NAME = '.'.join(x.lower() for x in ARGS.ou_name.split('/'))

def switch_policy(accounts, role_name):
    """
    Generates the template policy document for the switch role
    """

    policy_document = {
        'Version': '2017-10-17',
        'Statements': []
    }
    resources = []
    for account in accounts:
        resources.append(f'arn:aws:iam::{account["Id"]}:role/{role_name}')

    statement = {
        'Sid': f'{role_name.lower()}-to-{OU_POLICY_NAME}',
        'Effect': 'Allow',
        'Action': ['sts:AssumeRole'],
        'Resource': resources
    }
    policy_document['Statements'].append(statement)
    return policy_document


POLICIES = []

if accounts:
    for role in ROLE_NAMES:
        policy_res = TEMPLATE.add_resource(Policy(
            f'{role.title()}AccessTo{OU_NAME}',
            PolicyName=f'platform-dev.{role}.access',
            PolicyDocument=switch_policy(accounts, role)
        ))

print (TEMPLATE.to_yaml())
