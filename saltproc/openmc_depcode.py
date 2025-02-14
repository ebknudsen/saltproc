import subprocess
import os
import shutil
import re
import json

from pyne import nucname as pyname
from pyne import serpent
import openmc

from saltproc import Materialflow
from saltproc.abc import Depcode

class OpenMCDepcode(Depcode):
    """Class contains information about input, output, geometry, and
    template files for running OpenMC depletion simulations.
    Also contains neutrons population, active, and inactive cycles.
    Contains methods to read template and output files,
    write new input files for OpenMC.

    Attributes
    ----------
    param : dict of str to type
        Holds depletion step parameter information. Parameter names are keys
        and parameter values are values.
    sim_info : dict of str to type
        Holds simulation settings information. Setting names are keys
        and setting values are values.
    iter_inputfile : dict of str to str
        Paths to OpenMC input files for OpenMC rerunning.
    iter_matfile : str
        Path to iterative, rewritable material file for OpenMC
        rerunning. This file is modified during the simulation.



    """

    def __init__(self,
                 exec_path="openmc_deplete.py",
                 template_input_file_path={"geometry": "./geometry.xml",
                                           "settings": "./settings.xml",
                                           "chain_file": "./chain_simple.xml"},
                 geo_files=None,
                 npop=50,
                 active_cycles=20,
                 inactive_cycles=20):
        """Initializes the OpenMCDepcode object.

           Parameters
           ----------
           exec_path : str
               Path to OpenMC depletion script.
           template_input_file_path : dict of str to str
               Path to user input files (``.xml`` file for geometry,
               material, and settings) for OpenMC. File type as strings
               are keys (e.g. 'geometry', 'settings', 'material'), and
               file path as strings are values.
           geo_files : str or list, optional
               Path to file that contains the reactor geometry.
               List of `str` if reactivity control by
               switching geometry is `On` or just `str` otherwise.
           npop : int, optional
               Size of neutron population per cycle for Monte Carlo.
           active_cycles : int, optional
               Number of active cycles.
           inactive_cycles : int, optional
               Number of inactive cycles.

        """
        super().__init__("openmc",
                         exec_path,
                         template_input_file_path,
                         geo_files,
                         npop,
                         active_cycles,
                         inactive_cycles)
        self.iter_inputfile = {'geometry': './geometry.xml',
                               'settings': './settings.xml'},
        self.iter_matfile = './materials.xml'

    def read_depcode_info(self):
        """Parses initial OpenMC simulation info from the OpenMC output files
        and stores it in the `Depcode` object's ``sim_info`` attribute.
        """

    def read_depcode_step_param(self):
        """Parses data from OpenMC depletion output for each step and stores
        it in `Depcode` object's ``param`` attributes.
        """

    def read_dep_comp(self, read_at_end=False):
        """Reads the depleted material data from the OpenMC depletion
        simulation and returns a dictionary with a `Materialflow` object for
        each burnable material.

        Parameters
        ----------
        read_at_end : bool, optional
            Controls at which moment in the depletion step to read the data.
            If `True`, the function reads data at the end of the
            depletion step. Otherwise, the function reads data at the
            beginning of the depletion step.

        Returns
        -------
        mats : dict of str to Materialflow
            Dictionary that contains `Materialflow` objects.

            ``key``
                Name of burnable material.
            ``value``
                `Materialflow` object holding composition and properties.

        """

    def run_depcode(self, cores, nodes):
        """Runs OpenMC depletion simulation as a subprocess with the given
        parameters.

        Parameters
        ----------
        cores : int
            Number of cores to use for depletion code run.
        nodes : int
            Number of nodes to use for depletion code run.
        """
        # need to add flow control for plots option
        args = (
            'mpiexec',
            '-n',
            str(nodes),
            'python',
            './deplete_openmc.py'
            '-mat',
            self.iter_matfile,
            '-geo',
            self.iter_inputfile['geometry'],
            '-set',
            self.iter_inputfile['settings'],
            '-tal',
            self.iter_inputfile['tallies'],
            '-dep',
            self.iter_inputfile['depletion_settings'])

        print('Running %s' % (self.codename))
        # TODO: Need to figure out how to adapt this to openmc
        try:
            subprocess.check_output(
                args,
                cwd=os.path.split(self.template_inputfile_path)[0],
                stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as error:
            print(error.output.decode("utf-8"))
            raise RuntimeError('\n %s RUN FAILED\n see error message above'
                               % (self.codename))
        print('Finished OpenMC Run')

    def switch_to_next_geometry(self):
        """Switches the geometry file for the OpenMC depletion simulation to
        the next geometry file in `geo_files`.
        """
        mats = openmc.Materials.from_xml(self.iter_matfile)
        next_geometry = openmc.Geometry.from_xml(
            path=self.geo_files.pop(0),
            materials=mats)
        next_geometry.export_to_xml(path=self.iter_inputfile['geometry'])
        del mats, next_geometry

    def write_depcode_input(self, reactor, dep_step, restart):
        """ Writes prepared data into OpenMC input file(s).

        Parameters
        ----------
        reactor : Reactor
            Contains information about power load curve and cumulative
            depletion time for the integration test.
        dep_step : int
            Current depletion time step.
        restart : bool
            Is the current simulation restarted?
        """

        if dep_step == 0 and not restart:
            materials = openmc.Materials.from_xml(
                self.template_input_file_path['materials'])
            geometry = openmc.Geometry.from_xml(
                self.geo_files[0], materials=materials)
            settings = openmc.Settings.from_xml(
                self.template_input_file_path['settings'])
            settings.particles = self.npop
            settings.inactive = self.inactive_cycles
            settings.batches = self.active_cycles + self.inactive_cycles
        else:
            materials = openmc.Materials.from_xml(self.iter_matfile)
            geometry = openmc.Geometry.from_xml(
                self.iter_inputfile['geometry'], materials=materials)
            settings = openmc.Settings.from_xml(
                self.iter_inputfile['settings'])

        materials.export_to_xml(self.iter_matfile)
        geometry.export_to_xml(self.iter_inputfile['geometry'])
        settings.export_to_xml(self.iter_inputfile['settings'])
        self.write_depletion_settings(reactor, dep_step)
        self.write_saltproc_openmc_tallies(materials, geometry)
        del materials, geometry, settings

    def write_depletion_settings(self, reactor, current_depstep_idx):
        """Write the depeletion settings for the ``openmc.deplete``
        module.

        Parameters
        ----------
        reactor : Reactor
            Contains information about power load curve and cumulative
            depletion time for the integration test.
        current_depstep_idx : int
            Current depletion step.

        """
        depletion_settings = {}
        current_depstep_power = reactor.power_levels[current_depstep_idx]

        # Get current depletion step length
        if current_depstep_idx == 0:
            current_depstep = reactor.dep_step_length_cumulative[0]
        else:
            current_depstep = \
                reactor.dep_step_length_cumulative[current_depstep_idx] - \
                reactor.dep_step_length_cumulative[current_depstep_idx - 1]

        out_path = os.path.dirname(self.iter_inputfile['settings'])
        depletion_settings['directory'] = out_path
        depletion_settings['timesteps'] = [current_depstep]

        operator_kwargs = {}

        try:
            operator_kwargs['chain_file'] = \
                self.template_input_file_path['chain_file']
        except KeyError:
            raise SyntaxError("No chain file defined. Please provide \
            a chain file in your saltproc input file")

        integrator_kwargs = {}
        integrator_kwargs['power'] = current_depstep_power
        integrator_kwargs['timestep_units'] = 'd'  # days

        depletion_settings['operator_kwargs'] = operator_kwargs
        depletion_settings['integrator_kwargs'] = integrator_kwargs

        self.iter_inputfile['depletion_settings'] = \
            os.path.join(out_path, 'depletion_settings.json')
        json_dep_settings = json.JSONEncoder().encode(depletion_settings)
        with open(self.iter_inputfile['depletion_settings'], 'w') as f:
            f.writelines(json_dep_settings)

    def write_mat_file(self, dep_dict, dep_end_time):
        """Writes the iteration input file containing the burnable materials
        composition used in OpenMC depletion runs and updated after each
        depletion step.

        Parameters
        ----------
        dep_dict : dict of str to Materialflow
            Dictionary that contains `Materialflow` objects.

            ``key``
                Name of burnable material.
            ``value``
                `Materialflow` object holding composition and properties.
        dep_end_time : float
            Current time at the end of the depletion step (d).

        """

    def write_saltproc_openmc_tallies(self, materials, geometry):
        """
        Write tallies for calculating burnup and delayed neutron
        parameters.

        Parameters
        ----------
        materials : `openmc.Materials` object
            The materials for the depletion simulation
        geometry : `openmc.Geometry` object
            The geometry for the depletion simulation

        """
        tallies = openmc.Tallies()

        tally = openmc.Tally(name='delayed-fission-neutrons')
        tally.filters = [openmc.DelayedGroupFilter([1, 2, 3, 4, 5, 6])]
        tally.scores = ['delayed-nu-fission']
        tallies.append(tally)

        tally = openmc.Tally(name='total-fission-neutrons')
        tally.filters = [openmc.UniverseFilter(geometry.root_universe)]
        tally.scores = ['nu-fission']
        tallies.append(tally)

        tally = openmc.Tally(name='precursor-decay-constants')
        tally.filters = [openmc.DelayedGroupFilter([1, 2, 3, 4, 5, 6])]
        tally.scores = ['decay-rate']
        tallies.append(tally)

        tally = openmc.Tally(name='fission-energy')
        tally.filters = [openmc.UniverseFilter(geometry.root_universe)]
        tally.scores = [
            'fission-q-recoverable',
            'fission-q-prompt',
            'kappa-fission']
        tallies.append(tally)

        tally = openmc.Tally(name='normalization-factor')
        tally.filters = [openmc.UniverseFilter(geometry.root_universe)]
        tally.scores = ['heating']
        tallies.append(tally)

        out_path = os.path.dirname(self.iter_inputfile['settings'])
        self.iter_inputfile['tallies'] = \
            os.path.join(out_path, 'tallies.xml')
        tallies.export_to_xml(self.iter_inputfile['tallies'])
        del tallies


