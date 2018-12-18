import glob
import hashlib
import json
import logging
from collections import OrderedDict
from copy import deepcopy

from ocdskit.cli.commands.base import BaseCommand

logger = logging.getLogger('ocdskit')

'''
Script to transform JSON releases in OCDS schema v1.0 to v1.1
'''


def generate_party(parties, org, role=None):
    """
    Update the parties array, returning an updated organisation
    reference block to use.
    """
    if role is None:
        role = []
    try:
        # If we have a schema AND id, we can generate a suitable ID.
        if len(org['identifier']['id']) > 0:
            orgid = org['identifier']['id']
        else:
            raise Exception("No identifier was found")
        if 2 < len(org['identifier']['scheme']) < 20:
            scheme = org['identifier']['scheme']
        else:
            raise Exception("Schemes need to be between 2 and 20 characters")
        identifier = scheme + "-" + orgid
    except Exception as err:
        # Otherwise, generate an ID based on a hash of the
        # who organisation object.
        # ToDo: Check if we should do this from name instead.
        identifier = hashlib.md5(json.dumps(org).encode('utf8')).hexdigest()

    # Then check if this organisation was already in the parties array.
    if parties.get(identifier, False):
        name = parties.get(identifier).get('name', '')
        contact = parties.get(identifier).get('contactPoint', '')
        # If it is there, but the organisation name and contact point
        # doesn't match, we need to add a separate organisation entry
        # for this sub-unit or department.
        if not(name == org.get('name', '')) \
           or not(contact == org.get('contactPoint', '')):
            n = json.dumps(org.get('name', '')).encode('utf8')
            c = json.dumps(org.get('contactPoint', '')).encode('utf8')
            identifier += "-" + hashlib.md5(n + c).hexdigest()

    # Now fetch existing list of roles and merge.
    roles = parties.get(identifier, {}).get('roles', [])
    org['roles'] = list(set(roles + role))
    # And add the identifier to the organisation object
    # before adding/updating the parties object.
    org['id'] = identifier
    parties[identifier] = deepcopy(org)
    return {"id": identifier, "name": org.get('name', '')}


def upgrade_parties(release):
    parties = {}
    try:
        release['buyer'] = generate_party(parties, release['buyer'], ['buyer'])
    except Exception as err:
        pass
    try:
        release['tender']['procuringEntity'] = \
            generate_party(parties, release['tender']['procuringEntity'],
                           ['procuringEntity'])
    except Exception as err:
        pass
    try:
        for num, tenderer in enumerate(release['tender']['tenderers']):
            release['tender']['tenderers'][num] = \
                generate_party(parties, tenderer, ['tenderer'])
    except Exception as err:
        pass
    # Update award and contract suppliers
    try:
        for anum, award in enumerate(release['awards']):
            suppliers = release['awards'][anum]['suppliers']
            for snum, supplier in enumerate(suppliers):
                release['awards'][anum]['suppliers'][snum] = \
                    generate_party(parties, supplier, ['supplier'])
    except Exception as err:
        pass
    # (Although contract suppliers is not in the standard, some
    # implementations have been using this.)
    try:
        for anum, award in enumerate(release['contracts']):
            suppliers = release['contracts'][anum]['suppliers']
            for snum, supplier in enumerate(suppliers):
                release['contracts'][anum]['suppliers'][snum] = \
                    generate_party(parties, supplier, ['supplier'])
    except Exception as err:
        pass

    # Now format the parties into a simple array. Get rid of
    # empty arrays if needed.
    release['parties'] = []
    for key in parties:
        release['parties'].append(parties[key])
    if not release['parties']:
        del release['parties']
    return release


def upgrade_transactions(release):
    try:
        for contract in release['contracts']:
            for transaction in contract['implementation']['transactions']:
                payer_id = transaction['providerOrganization']['scheme']\
                    + "-" + transaction['providerOrganization']['id']
                transaction['payer'] = {
                    "id": payer_id,
                    "name": transaction['providerOrganization']['legalName']
                }
                payee_id = transaction['receiverOrganization']['scheme']\
                    + "-" + transaction['receiverOrganization']['id']
                transaction['payee'] = {
                    "id": payee_id,
                    "name": transaction['receiverOrganization']['legalName']
                }
                transaction['value'] = transaction['amount']
                del(transaction['providerOrganization'])
                del(transaction['receiverOrganization'])
                del(transaction['amount'])
    except Exception as e:
        # traceback.print_tb(e.__traceback__)
        pass

    return release


def upgrade_amendments(release):
    try:
        release['tender'] = upgrade_amendment(release['tender'])
        for award in release['awards']:
            upgrade_amendment(award)
        for contract in release['contracts']:
            upgrade_amendment(contract)
    except Exception as e:
        pass
    return release


def upgrade_amendment(parent):
    try:
        amendment = {'date': parent['amendment']['date'], 'rationale': parent['amendment']['rationale']}
        parent['amendments'] = []
        parent['amendments'].append(amendment)
    except Exception as e:
        pass
    return parent


def remove_empty_arrays(data, keys=None):
    """
    Drill doesn't cope well with empty arrays. Remove them.
    """
    if not keys:
        keys = data.keys()
    keys_to_remove = []
    for key in keys:
        if isinstance(data[key], dict):
            remove_empty_arrays(data[key])
        else:
            if isinstance(data[key], list) and len(data[key]) == 0:
                keys_to_remove.append(key)
    for key in keys_to_remove:
        del data[key]
    return data


def upgrade(release):
    release = OrderedDict(release)
    release = upgrade_amendments(release)
    release = upgrade_parties(release)
    release = upgrade_transactions(release)
    if 'parties' in release:
        release.move_to_end('parties', last=False)
    if 'initiationType' in release:
        release.move_to_end('initiationType', last=False)
    if 'tag' in release:
        release.move_to_end('tag', last=False)
    if 'language' in release:
        release.move_to_end('language', last=False)
    if 'date' in release:
        release.move_to_end('date', last=False)
    if 'id' in release:
        release.move_to_end('id', last=False)
    if 'ocid' in release:
        release.move_to_end('ocid', last=False)
    return release


def convert(path):
    files = glob.glob('%s/*.json' % path)
    for filename in files:
        if not filename.endswith('.json'):
            continue
        with open(filename, 'r') as file:
            try:
                data = json.loads(file.read())
            except json.decoder.JSONDecodeError:
                continue
            data = remove_empty_arrays(data)
            data = OrderedDict(data)
            data.update({"version": "1.1"})
            if 'records' in data:
                # Handle record packages.
                for record in data['records']:
                    if 'compiledRelease' in record:
                        record['compiledRelease'] = \
                            upgrade(record['compiledRelease'])
            else:
                # Handle release packages.
                if 'releases' in data:
                    releases = []
                    for release in data['releases']:
                        releases.append(upgrade(release))
                    data['releases'] = releases
                else:
                    # Handle releases.
                    data = upgrade(data)
            with open(filename, 'w') as writefile:
                writefile.write(json.dumps(data, indent=2))


class Command(BaseCommand):
    name = 'update-to-v1_1'
    help = 'transform a 1.0 version of OCDS json into a 1.1 version of it'

    def add_arguments(self):
        self.add_argument('directory', help='path to directory containing standard 1.0 JSON files')

    def handle(self):
        if self.args.directory:
            convert(self.args.directory)
        else:
            logger.error('You must specify the path')
