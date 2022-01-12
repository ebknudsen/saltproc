from __future__ import absolute_import, division, print_function
from saltproc import DepcodeSerpent
from saltproc import Simulation
import os
import sys
import shutil
path = os.path.realpath(__file__)
sys.path.append(os.path.dirname(os.path.dirname(path)))
# global class object
directory = os.path.dirname(path)
input_file = directory + '/test'
geo_test_input = directory + '/test_geometry_switch.inp'

serpent = DepcodeSerpent(
    exec_path='/home/andrei2/serpent/serpent2/src_2131/sss2',
    template_path=directory + '/template.inp',
    input_path=input_file,
    iter_matfile=directory + '/material',
    geo_file=[
        '../../examples/406.inp',
        '../../examples/988.inp'])

simulation = Simulation(sim_name='Simulation unit tests',
                        sim_depcode=serpent,
                        core_number=1,
                        node_number=1,
                        h5_file=directory + '/test_db.h5',
                        iter_matfile=serpent.iter_matfile)


def test_read_k_eds_delta():
    assert simulation.read_k_eds_delta(7, False) is False


def test_switch_to_next_geometry():
    shutil.copy2(geo_test_input, serpent.input_path + '_test')
    serpent.input_path = serpent.input_path + '_test'
    simulation.switch_to_next_geometry()
    d = serpent.read_depcode_template(serpent.input_path)
    assert d[5].split('/')[-1] == '988.inp"\n'
    os.remove(serpent.input_path)
