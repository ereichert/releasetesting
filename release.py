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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('release_type', help='[ snapshot | final ]')
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

    if release_context.release_type != 'snapshot' and release_context.release_type != 'final':
        print 'You must specify the relase type: [snapshot xor final]'
        sys.exit(1)

    if not release_context.disable_checks and release_context.repo_active_branch().lower() != 'develop':
        print 'You must be on the develop branch in order to do a release. You are on branch {}'.format(release_context.repo_active_branch())
        sys.exit(1)

    if not release_context.disable_checks and release_context.repo_is_dirty():
        print 'There are uncommited changes on the active branch.'
        sys.exit(1)

    starting_version, package_name = read_cargo_file(release_context)
    release_version = confirm_version(starting_version)
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

    if not release_context.dry_run:
        release_context.push_to_develop()
    print 'Pushed release v{} to develop.'.format(str(release_version))

    if release_context.is_snapshot_release():
        snapshot_version = '{}.{}.{}-{}'.format(
            release_version.major,
            release_version.minor,
            release_version.patch,
            'SNAPSHOT'
        )
        update_version_in_files(release_context, snapshot_version, package_name)
        print 'Updated files with SNAPSHOT specifier.'
        if not release_context.dry_run:
            release_context.commit_release('Rewrite version to SNAPSHOT.')
            release_context.push_to_develop()

    if release_context.is_final_release():
        release_context.checkout_master()
        release_context.merge_develop()
        #push to master
        #checkout develop
        #bump the patch version - with SNAPSHOT
        #commit
        #push to develop

# end of main

class ReleaseContext:
    def __init__(
        self,
        release_type,
        config_file,
        version_file,
        readme_file,
        disable_checks,
        dry_run
    ):
        # Either final or snapshot
        self.release_type = release_type.lower()
        # This should be the path to the Cargo.toml file.
        self.cargo_file = config_file
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

    def push_to_develop(self):
        self._repo.remotes.origin.push('refs/heads/develop:refs/heads/develop', tags=True)

    def is_snapshot_release(self):
        return self.release_type == 'snapshot'

    def is_final_release(self):
        return self.release_type == 'final'

    def checkout_master(self):
        self._repo.heads.master.checkout()

    def merge_develop(self):
        print 'getting master'
        master = self._repo.heads.master
        print 'getting develop'
        develop = self._repo.heads.develop
        print 'attempting merge'
        self._repo.index.merge_tree(master, develop)
        print 'committing merge'
        self._repo.index.commit('Final release merge commit.')

def read_cargo_file(release_context):
    with open(release_context.cargo_file) as cargo_file:
        cargo_content = contoml.loads(cargo_file.read())
        return (cargo_content['package']['version'], cargo_content['package']['name'])

#TODO If the release is a final release the default version number a user is prompted with should have the SNAPSHOT removed.
#TODO If the release is a final release the user specifies a snapshot version return an error message.
def confirm_version(current_version):
    version_set = False
    input_version = None
    confirmed_version = None
    while not version_set:
        input_version = raw_input('Set version [{}]: '.format(current_version)) or current_version
        version_set = semantic_version.validate(input_version)
        confirmed_version = semantic_version.Version(input_version)
        if confirmed_version.prerelease and confirmed_version.prerelease[0].upper() != 'SNAPSHOT':
            version_set = False
        if not version_set:
            print '{} does not fit the semantic versioning spec.'.format(input_version)
    return rewrite_snapshot_version(confirmed_version)

def rewrite_snapshot_version(version):
    if version.prerelease and version.prerelease[0].upper() == 'SNAPSHOT':
        now = datetime.datetime.now()
        return semantic_version.Version(
            '{}.{}.{}-{}'.format(
                version.major,
                version.minor,
                version.patch,
                now.strftime('%Y%m%d%H%M%S')
            )
        )
    else:
        return version

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
        retcode = subprocess.call('cargo build --release', shell=True)
        if retcode == 0:
            return (0, None)
        else:
            return (1, None)
    except OSError as e:
        return (2, e)

if __name__=='__main__':
    main()
