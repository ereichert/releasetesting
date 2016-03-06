import release
import semantic_version
import datetime

def test_to_presentation_version_converts_a_final_version_to_a_final_version_when_the_context_specifies_a_final_release():
    release_context = release.ReleaseContext(
        release_type = 'final',
        cargo_file = 'Cargo.toml',
        version_file = 'version.txt',
        readme_file = 'README.md',
        disable_checks = False,
        dry_run = False
    )
    original_version = semantic_version.Version('1.0.0')

    presentation_version = release.to_presentation_version(release_context, original_version)

    assert presentation_version == semantic_version.Version('1.0.0')

def test_to_presentation_version_converts_a_final_version_to_a_snapshot_version_when_the_context_specifies_a_snapshot_release():
    release_context = release.ReleaseContext(
        release_type = 'snapshot',
        cargo_file = 'Cargo.toml',
        version_file = 'version.txt',
        readme_file = 'README.md',
        disable_checks = False,
        dry_run = False
    )
    original_version = semantic_version.Version('1.0.0')

    presentation_version = release.to_presentation_version(release_context, original_version)

    assert presentation_version == semantic_version.Version('1.0.0-SNAPSHOT')

def test_to_presentation_version_converts_a_snapshot_version_to_a_final_version_when_the_context_specifies_a_final_release():
    release_context = release.ReleaseContext(
        release_type = 'final',
        cargo_file = 'Cargo.toml',
        version_file = 'version.txt',
        readme_file = 'README.md',
        disable_checks = False,
        dry_run = False
    )
    original_version = semantic_version.Version('1.0.0-SNAPSHOT')

    presentation_version = release.to_presentation_version(release_context, original_version)

    assert presentation_version == semantic_version.Version('1.0.0')


def test_to_presentation_version_converts_a_snapshot_version_to_a_snapshot_version_when_the_context_specifies_a_snapshot_release():
    release_context = release.ReleaseContext(
        release_type = 'snapshot',
        cargo_file = 'Cargo.toml',
        version_file = 'version.txt',
        readme_file = 'README.md',
        disable_checks = False,
        dry_run = False
    )
    original_version = semantic_version.Version('1.0.0-SNAPSHOT')

    presentation_version = release.to_presentation_version(release_context, original_version)

    assert presentation_version == semantic_version.Version('1.0.0-SNAPSHOT')

def test_is_valid_proposed_version_returns_false_when_proposed_is_not_semantic_version():
    release_context = release.ReleaseContext(
        release_type = 'final',
        cargo_file = 'Cargo.toml',
        version_file = 'version.txt',
        readme_file = 'README.md',
        disable_checks = False,
        dry_run = False
    )
    proposed_version = '1.0'

    assert release.is_valid_proposed_version(release_context, proposed_version) == None

def test_is_valid_proposed_version_returns_true_when_context_specifies_a_snapshot_release_and_proposed_is_a_snapshot_version():
    release_context = release.ReleaseContext(
        release_type = 'snapshot',
        cargo_file = 'Cargo.toml',
        version_file = 'version.txt',
        readme_file = 'README.md',
        disable_checks = False,
        dry_run = False
    )
    proposed_version = '1.0.0-SNAPSHOT'

    assert release.is_valid_proposed_version(release_context, proposed_version) == semantic_version.Version(proposed_version)

def test_is_valid_proposed_version_returns_true_when_context_specifies_a_final_release_and_proposed_is_a_final_version():
    release_context = release.ReleaseContext(
        release_type = 'final',
        cargo_file = 'Cargo.toml',
        version_file = 'version.txt',
        readme_file = 'README.md',
        disable_checks = False,
        dry_run = False
    )
    proposed_version = '1.0.0'

    assert release.is_valid_proposed_version(release_context, proposed_version) == semantic_version.Version(proposed_version)

def test_is_valid_proposed_version_returns_false_when_context_specifies_a_snapshot_release_and_proposed_is_a_final_version():
    release_context = release.ReleaseContext(
        release_type = 'snapshot',
        cargo_file = 'Cargo.toml',
        version_file = 'version.txt',
        readme_file = 'README.md',
        disable_checks = False,
        dry_run = False
    )
    proposed_version = '1.0.0'

    assert release.is_valid_proposed_version(release_context, proposed_version) == None

def test_is_valid_proposed_version_returns_false_when_context_specifies_a_final_release_and_proposed_is_a_snapshot_version():
    release_context = release.ReleaseContext(
        release_type = 'final',
        cargo_file = 'Cargo.toml',
        version_file = 'version.txt',
        readme_file = 'README.md',
        disable_checks = False,
        dry_run = False
    )
    proposed_version = '1.0.0-SNAPSHOT'

    assert release.is_valid_proposed_version(release_context, proposed_version) == None

def test_to_next_patch_snapshot_version_bumps_patch_specifier():
    original_version = semantic_version.Version('1.0.0-SNAPSHOT')

    bumped_version = release.to_next_patch_snapshot_version(original_version)

    assert bumped_version == semantic_version.Version('1.0.1-SNAPSHOT')


def test_to_snapshot_version_converts_a_version_to_a_snapshot_version():
    now = datetime.datetime.now()
    original_version = semantic_version.Version('1.0.0-{}'.format(now.strftime('%Y%m%d%H%M%S')))

    snapshot_version = release.to_snapshot_version(original_version)

    assert snapshot_version == semantic_version.Version('1.0.0-SNAPSHOT')

def test_to_snapshot_release_version_converts_a_version_to_a_snapshot_release_version():
    original_version = semantic_version.Version('1.0.0-SNAPSHOT')
    now = datetime.datetime.now()

    release_version = release.to_snapshot_release_version(original_version, now=now)

    assert release_version == semantic_version.Version('1.0.0-{}'.format(now.strftime('%Y%m%d%H%M%S')))


def test_to_final_release_version_converts_snapshot_to_final_version():
    original_version = semantic_version.Version('1.0.0-SNAPSHOT')

    final_version = release.to_final_release_version(original_version)

    assert final_version == semantic_version.Version('1.0.0')
