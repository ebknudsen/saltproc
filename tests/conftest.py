from pathlib import Path
import pytest

from saltproc.app import read_main_input, _create_depcode_object
from saltproc import Simulation


@pytest.fixture(scope='session')
def cwd():
    return Path(__file__).parents[0]


@pytest.fixture(scope='session')
def proc_test_file(cwd):
    filename = (cwd / 'tap_processes.json')
    return filename


@pytest.fixture(scope='session')
def path_test_file(cwd):
    filename = (cwd / 'tap_paths.dot')
    return filename


@pytest.fixture(scope='session')
def serpent_depcode(cwd):
    """SerpentDepcode object for unit tests"""
    saltproc_input = (cwd / 'serpent_data' / 'tap_input.json').as_posix()
    _, _, _, object_input = read_main_input(saltproc_input)
    depcode = _create_depcode_object(object_input[0])
    depcode.iter_inputfile = (cwd / 'serpent_data' / 'tap_reference').as_posix()

    return depcode


@pytest.fixture(scope='session')
def openmc_depcode(cwd):
    """OpenMCDepcode object for unit tests"""
    saltproc_input = (cwd / 'openmc_data' / 'tap_input.json').as_posix()
    _, _, _, object_input = read_main_input(saltproc_input)
    depcode = _create_depcode_object(object_input[0])

    # Openmc initlialization
    openmc_input_path = (cwd / 'openmc_data')

    openmc_iter_inputfiles = {
        "geometry": "geometry.xml",
        "settings": "settings.xml",
    }

    for key in openmc_iter_inputfiles:
        openmc_iter_inputfiles[key] = \
            (openmc_input_path / openmc_iter_inputfiles[key]).as_posix()

    depcode.iter_inputfile = openmc_iter_inputfiles
    depcode.iter_matfile = (openmc_input_path / 'materials.xml').as_posix()

    return depcode


@pytest.fixture(scope='session')
def simulation(cwd, serpent_depcode):
    """Simulation object for unit tests"""
    simulation = Simulation(
        sim_name='test_simulation',
        sim_depcode=serpent_depcode,
        core_number=1,
        node_number=1,
        db_path=(
            cwd /
            'serpent_data' /
            'tap_reference_db.h5').as_posix())
    return simulation
