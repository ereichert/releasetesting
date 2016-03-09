#!/usr/bin/env python

import logging
import argparse
from os import sys
from git import Repo
import contoml
import semantic_version
import re
import subprocess
import datetime

RELEASE_TYPE_SNAPSHOT = 'snapshot'
RELEASE_TYPE_FINAL = 'final'
# testfinal is used to test final releases without committing to master.
RELEASE_TYPE_TEST_FINAL = 'testfinal'
SNAPSHOT = 'SNAPSHOT'
BRANCH_DEVELOP = 'develop'
BUILD_CMD = 'cargo build --release'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('release_type', help='[ snapshot | final | testfinal]')
    parser.add_argument('--cargo-file', default='Cargo.toml', help='The Cargo.toml file to use. Default = ./Cargo.toml')
    parser.add_argument('--version-file', default='./src/version.txt', help='The version.txt file to update. Default = ./src/version.txt')
    parser.add_argument('--readme-file', default='README.md', help='The readme file to update. Default = ./README.md')
    parser.add_argument('--disable-checks', action='store_true', default=False, help='Disable checks for testing purposes.')
    parser.add_argument('--dry-run', action='store_true', default=False, help='Run all commands that do no permanently alter the repository.')
    args = parser.parse_args()

    release_context = ReleaseContext(
        args.release_type,
        args.cargo_file,
        args.version_file,
        args.readme_file,
        args.disable_checks,
        args.dry_run
    )

    if (release_context.release_type != RELEASE_TYPE_SNAPSHOT
        and release_context.release_type != RELEASE_TYPE_FINAL
        and release_context.release_type != RELEASE_TYPE_TEST_FINAL):
        print 'You must specify the relase type: [snapshot xor final xor testfinal]'
        sys.exit(1)

    if not release_context.disable_checks and release_context.repo_active_branch().lower() != BRANCH_DEVELOP:
        print 'You must be on the develop branch in order to do a release. You are on branch {}'.format(release_context.repo_active_branch())
        sys.exit(1)

    if not release_context.disable_checks and release_context.repo_is_dirty():
        print 'There are uncommited changes on the active branch.'
        sys.exit(1)

    starting_version, package_name = read_cargo_file(release_context)
    release_version = confirm_version(release_context, semantic_version.Version(starting_version))
    print 'Releasing {} v{}'.format(package_name, str(release_version))

    update_version_in_files(release_context, release_version, package_name)

    build_result, error = attempt_build()
    if build_result == 1:
        print >>sys.stderr, 'Failed to build {}.  See build output for more information'.format(package_name)
        sys.exit(1)

    if build_result == 2:
        print >>sys.stderr, 'An exception occurred while trying to build {}:', error
        sys.exit(2)

    print 'Successfully built {}.'.format(package_name)

    if not release_context.dry_run:
        release_context.commit_release('Release commit for {}.'.format(str(release_version)))

    print 'Committed release v{} to {}.'.format(
        str(release_version),
        release_context.repo_active_branch()
    )

    tag = 'v{}'.format(str(release_version))
    if not release_context.dry_run:
        release_context.tag_release(tag, tag)

    print 'Tagged release v{} to {}.'.format(
        str(release_version),
        release_context.repo_active_branch()
    )

    if release_context.is_snapshot_release():
        snapshot_version = to_snapshot_version(release_version)
        update_version_in_files(release_context, snapshot_version, package_name)
        print 'Updated files with SNAPSHOT specifier.'
        if not release_context.dry_run:
            release_context.commit_release('Rewrite version to SNAPSHOT.')

    if release_context.is_final_release() or release_context.is_test_final_release():
        if release_context.is_final_release():
            release_context.checkout_master()
        else:
            release_context.checkout_test_master()
        release_context.merge_develop()
        release_context.checkout_develop()
        next_version = to_next_patch_snapshot_version(release_version)
        update_version_in_files(release_context, next_version, package_name)
        print 'Updated files with SNAPSHOT specifier.'
        if not release_context.dry_run:
            release_context.commit_release('Bumped version to {}.'.format(next_version))

    if not release_context.dry_run:
        print "Pushing release to origin."
        release_context.push_to_origin()

# end of main

class ReleaseContext:
    def __init__(
        self,
        release_type,
        cargo_file,
        version_file,
        readme_file,
        disable_checks,
        dry_run
    ):
        # Either final or snapshot
        self.release_type = release_type.lower()
        # This should be the path to the Cargo.toml file.
        self.cargo_file = cargo_file
        # This should be the path to the version.txt file.
        self.version_file = version_file
        # This should be the path to the README.md file.
        self.readme_file = readme_file
        # disable_checks is useful for testing of the release script.
        # It should not be used normally.
        self.disable_checks = disable_checks
        # Do everything non destructively.  That is, the script will run with
        # output but nothing will actually be committed.
        self.dry_run = dry_run
        # The git repo.
        self._repo = Repo('.')

    def repo_active_branch(self):
        return self._repo.active_branch.name

    def repo_is_dirty(self):
        return self._repo.is_dirty()

    def commit_release(self, message):
        self._repo.git.add(update=True)
        self._repo.index.commit(message)

    def tag_release(self, tag, tag_message):
        self._repo.create_tag(tag, message=tag_message)

    def push_to_origin(self):
        self._repo.remotes.origin.push('refs/heads/*:refs/heads/*', tags=True)

    def is_snapshot_release(self):
        return self.release_type == RELEASE_TYPE_SNAPSHOT

    def is_final_release(self):
        return self.release_type == RELEASE_TYPE_FINAL

    def is_test_final_release(self):
        return self.release_type == RELEASE_TYPE_TEST_FINAL

    def checkout_master(self):
        self._repo.heads.master.checkout()

    def checkout_test_master(self):
        self._repo.heads.testmaster.checkout()

    def checkout_develop(self):
        self._repo.heads.develop.checkout()

    def merge_develop(self):
        self._repo.git.merge(BRANCH_DEVELOP)

def read_cargo_file(release_context):
    with open(release_context.cargo_file) as cargo_file:
        cargo_content = contoml.loads(cargo_file.read())
        return (cargo_content['package']['version'], cargo_content['package']['name'])

def confirm_version(release_context, current_version):
    confirmed_version = None
    presentation_version = to_presentation_version(release_context, current_version)
    while confirmed_version == None:
        # We confirm current_version if the user does not specify a version
        # because current_version may not be valid for the type of release the
        # user specified.
        input_version = raw_input('Set version [{}]: '.format(presentation_version)) or str(presentation_version)
        confirmed_version = is_valid_proposed_version(release_context, input_version)
        if confirmed_version == None:
            print '{} does not fit the semantic versioning spec or is not valid given the specified release type of {}.'.format(input_version, release_context.release_type)

    if release_context.is_snapshot_release():
        return to_snapshot_release_version(confirmed_version)
    elif release_context.is_test_final_release():
        return to_test_final_release_version(confirmed_version)
    else:
        return confirmed_version

def to_presentation_version(release_context, version):
    if release_context.is_snapshot_release():
        return to_snapshot_version(version)
    else:
        return to_final_release_version(version)

def is_valid_proposed_version(release_context, proposed_version):
    validations = []
    sv = None
    if semantic_version.validate(proposed_version):
        sv = semantic_version.Version(proposed_version)
        if release_context.is_snapshot_release():
            validations.append(
                sv.prerelease
                and sv.prerelease[0].upper() == SNAPSHOT
            )
        else:
            validations.append(
                not sv.prerelease
            )

    if all(v for v in validations):
        return sv
    else:
        None

def to_next_patch_snapshot_version(original_version):
    return semantic_version.Version(
        '{}.{}.{}-{}'.format(
            original_version.major,
            original_version.minor,
            original_version.patch + 1,
            SNAPSHOT
        )
    )

def to_snapshot_version(original_version):
    return semantic_version.Version(
        '{}.{}.{}-{}'.format(
            original_version.major,
            original_version.minor,
            original_version.patch,
            SNAPSHOT
        )
    )

def to_snapshot_release_version(original_version, now=datetime.datetime.now()):
    return semantic_version.Version(
        '{}.{}.{}-{}'.format(
            original_version.major,
            original_version.minor,
            original_version.patch,
            now.strftime('%Y%m%d%H%M%S')
        )
    )

def to_test_final_release_version(original_version):
    return semantic_version.Version(
        '{}.{}.{}-{}'.format(
            original_version.major,
            original_version.minor,
            original_version.patch,
            'TESTFINALRELEASE'
        )
    )

def to_final_release_version(original_version):
    return semantic_version.Version(
        '{}.{}.{}'.format(
            original_version.major,
            original_version.minor,
            original_version.patch
        )
    )

def update_version_in_files(release_context, version, package_name):
    version_string = str(version)
    update_cargo_file_version(release_context, version_string)
    print 'Updated {} with the release version.'.format(release_context.cargo_file)

    update_version_file(release_context, version_string)
    print 'Updated {} with the release version.'.format(release_context.version_file)

    update_readme_file_version(release_context, package_name, version_string)
    print 'Updated {} with the release version.'.format(release_context.readme_file)

def update_cargo_file_version(release_context, version):
    with open(release_context.cargo_file, 'r+') as cargo_file:
        cargo_content = contoml.loads(cargo_file.read())
        cargo_content['package']['version'] = version
        cargo_content.dump(release_context.cargo_file)

def update_version_file(release_context, version):
    with open(release_context.version_file, 'w') as version_file:
        version_file.write(version)

def update_readme_file_version(release_context, package_name, version):
    final_readme_version = '{} = {}\n'.format(package_name, version)
    readme_version_regex = re.compile('{}\s*=\s*\d.\d.\d.*\n'.format(package_name))
    final_readme_content = ''
    with open(release_context.readme_file, 'r') as readme_file:
        final_readme_content = readme_version_regex.sub(final_readme_version, readme_file.read())

    with open(release_context.readme_file, 'w') as readme_file:
        readme_file.write(final_readme_content)

def attempt_build():
    try:
        retcode = subprocess.call(BUILD_CMD, shell=True)
        if retcode == 0:
            return (0, None)
        else:
            return (1, None)
    except OSError as e:
        return (2, e)

if __name__=='__main__':
    main()
