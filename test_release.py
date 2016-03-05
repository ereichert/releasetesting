import release
import semantic_version
import datetime

def test_to_next_patch_snapshot_bumps_patch_specifier():
    original_version = semantic_version.Version('1.0.0-SNAPSHOT')

    bumped_version = release.to_next_patch_snapshot(original_version)

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


def test_to_final_version_converts_snapshot_to_final_version():
    original_version = semantic_version.Version('1.0.0-SNAPSHOT')

    final_version = release.to_final_version(original_version)

    assert final_version == semantic_version.Version('1.0.0')
