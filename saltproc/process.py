from saltproc import Materialflow
from pyne import nucname as pyname
from math import *
import numpy as np


class Process():
    """Class describes process which must be applied to Materialflow to change
     burnable material composition.
     """

    def __init__(self, *initial_data, **kwargs):
        """ Initializes the Process object.

        Parameters
        ----------
        mass_flowrate : float
            mass flow rate of the material flow (g/s)
        capacity : float
            maximum mass flow rate of the material flow which current process
            can handle (g/s)
        volume : float
            total volume of the current facility (:math:`cm^3`)
        efficiency : dict of str to float

            ``key``
                element name for removal (not isotope)
            ``value``
                removal efficency for the isotope (weight fraction)
        optional_parameter : float
            user can define any castom parameter in the input file describing
            processes and use it in efficiency function
        """
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def calc_rem_efficiency(self, el_name):
        """Based on data from json file with Processes description calculate
        value (float) of the removal efficiency. If it was str describing
        efficiecny as a function (eps(x,m,t,P,L)) then calculating value. If it
        constant (float in processes.json) then just keep it as is.

        Parameters
        ----------
        el_name : str
            Name of target element to be removed.

        Returns
        -------
        efficiency : float
            Extraction efficiency for el_name element.

        """
        eps = self.efficiency[el_name]
        if isinstance(eps, str):
            for attr, value in self.__dict__.items():
                if attr in eps:
                    eps = eps.replace(attr, "self." + str(attr))
        else:
            eps = str(eps)
        efficiency = eval(eps)
        return efficiency

    def check_mass_conservation(self):
        """Checking that Process.outflow + Process.waste_stream is equal
        Process.inflow and the total mass is being conserved. Returns `True` if
        the mass conserved or `False` if its mismatched.
        """
        out_stream = self.outflow + self.waste_stream
        np.testing.assert_array_equal(out_stream, self.inflow)

    def rem_elements(self, inflow):
        """Updates Materialflow object `inflow` after removal target isotopes
        with specific efficiency in single component of fuel reprocessing
        system and returns waste stream Materialflow object.

        Parameters
        ----------
        inflow : Materialflow obj
            Target material stream to remove poisons from.

        Returns
        -------
        Materialflow object
            Waste stream from the reprocessing system component.

        """
        waste_nucvec = {}
        out_nucvec = {}
        # print("Xe concentration in inflow before % f g" % inflow['Xe136'])
        # print("Current time %f" % (t))
        for iso in inflow.comp.keys():
            el_name = pyname.serpent(iso).split('-')[0]
            if el_name in self.efficiency:
                # Evaluate removal efficiency for el_name (float)
                self.efficiency[el_name] = self.calc_rem_efficiency(el_name)
                out_nucvec[iso] = \
                    float(inflow.comp[iso]) * \
                    float(1.0 - self.efficiency[el_name])
                waste_nucvec[iso] = \
                    float(inflow[iso]) * self.efficiency[el_name]
            else:
                out_nucvec[iso] = float(inflow.comp[iso])
                waste_nucvec[iso] = 0.0  # zeroes everywhere else
        waste = Materialflow(waste_nucvec)
        inflow.mass = float(inflow.mass - waste.mass)
        inflow.comp = out_nucvec
        inflow.norm_comp()
        print("Xe concentration in inflow after %f g" % inflow['Xe136'])
        print("Waste mass %f g\n" % waste.mass)
        del out_nucvec, waste_nucvec, el_name
        return waste
