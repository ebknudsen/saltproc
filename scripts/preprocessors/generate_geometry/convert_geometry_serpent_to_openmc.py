import re
import os
import sys
from pyne import nucname as pyname
import numpy as np
import openmc
import openmc.model

COMMENT_IGNORE_BEG_REGEX="^\s*[^%]*\s*"
COMMENT_IGNORE_END_REGEX="\s*[^%]*"
SURF_REGEX_CORE = "surf\s+[a-zA-Z0-9]+\s+[a-z]{2,}(\s+[0-9]+(\.[0-9]+)?\s*)*"
CELL_REGEX1_CORE = "cell(\s+[a-zA-Z0-9]+){3}"
CELL_REGEX2_CORE = "cell(\s+[a-zA-Z0-9]+){2}\s+fill\s+[a-zA-Z0-9]+"
CELL_REGEX3_CORE = "cell(\s+[a-zA-Z0-9]+){2}\s+outside\s+[a-zA-Z0-9]+"
CELL_SURFACE_REGEX = "(\s+\-?\:?\#?[a-zA-Z0-9]+)+"
TRANS_REGEX_CORE = "trans\s+[A-Z]{1}\s+[a-zA-Z0-9]+(\s+-?[0-9]+(\.[0-9]+)?)+"
LAT_REGEX_CORE = ...

SURF_REGEX=COMMENT_IGNORE_BEG_REGEX + \
    SURF_REGEX_CORE + \
    COMMENT_IGNORE_END_REGEX
CELL_REGEX1 = COMMENT_IGNORE_BEG_REGEX + \
    CELL_REGEX1_CORE + \
    CELL_SURFACE_REGEX + \
    COMMENT_IGNORE_END_REGEX
CELL_REGEX2 = COMMENT_IGNORE_BEG_REGEX + \
    CELL_REGEX2_CORE + \
    CELL_SURFACE_REGEX + \
    COMMENT_IGNORE_END_REGEX
CELL_REGEX3 = COMMENT_IGNORE_BEG_REGEX + \
    CELL_REGEX3_CORE + \
    CELL_SURFACE_REGEX + \
    COMMENT_IGNORE_END_REGEX
CELL_REGEX_ALL = COMMENT_IGNORE_BEG_REGEX + \
    f"({CELL_REGEX2_CORE}|{CELL_REGEX3_CORE}|{CELL_REGEX1_CORE})" + \
    CELL_SURFACE_REGEX + \
    COMMENT_IGNORE_END_REGEX
TRANS_REGEX = COMMENT_IGNORE_BEG_REGEX + \
    TRANS_REGEX_CORE + \
    COMMENT_IGNORE_END_REGEX
LAT_REGEX = COMMENT_IGNORE_BEG_REGEX + \
    TRANS_REGEX_CORE + \
    COMMENT_IGNORE_END_REGEX


geo_dict = {
    "surf": {
        "px": openmc.XPlane,
        "py": openmc.YPlane,
        "pz": openmc.ZPlane,
        "plane": openmc.Plane,
        "cylx": openmc.XCylinder,
        "cyly":, openmc.YCylinder,
        "cylz": openmc.ZCylinder,
        "cyl": openmc.ZCylinder,
        "cylv": openmc.model.cylinder_from_points,
        "sph": openmc.Sphere,
        "cone": openmc.ZCone, # to implement
        "quadratic": openmc.Quadric,
        "torx": openmc.XTorus,
        "tory": openmc.YTorus,
        "torz": openmc.ZTorus,
        "sqc": openmc.model.rectangular_prism,
        "rect": openmc.model.rectangualr_prism,
        "hexxc": openmc.model.hexagonal_prism, #to implement
        "hexyc": openmc.model.hexagonal_prism  #to implement
    },
    "cell": openmc.Cell,
    "lat": {
        "1": openmc.RectLattice,    # Square lattice
        "2": openmc.HexLattice,     # X-type hexagonal lattice (y type in openmc)
        "3": openmc.HexLattice,     # Y-type hexagonal lattice (x type in openmc)
        "4": None,                  # Circular cluster array
        "5": None,                  # Does not exist
        "6": openmc.RectLattice,    # Same as 1 but infinite
        "7": openmc.HexLattice,     # Same as 3 but infinite
        "8": openmc.HexLattice,     # Same as 2 but infinite
        "9": None,                  # Vertical stack
        "10": None,                 # Does not exist
        "11": None,                 # Cuboidal lattice
        "12": None,                 # X-type hexagonal prism lattice
        "13": None,                 # Y-type hexagonal prism lattice
        "14": None                  # X-type triangular lattice
    }
}

special_case_surfaces = tuple(['inf'])

def _construct_surface_helper(surf_card):
    """
    Helper function for creating `openmc.Surface` objects
    corresponding to Serpent `surf` cards

    Parameters
    ----------
    surf_card : str
        A string containing a Serpent `surf` card

    """
    surf_data = surf_card.split()
    surface_name = surf_data[1]
    surface_type = surf_data[2]
    surface_args = surf_data[3:]
    surface_params = []
    for i in range(0,len(surface_args)):
        p = float(surface_params[i])
        surfce_params[i] = p

    # generic case
    skip_attributes = True
    if bool(geo_dict['surf'][surface_type]):
        surface_object = geo_dict['surf'][surface_type]
        if surface_type == "plane":
            # convert 3-point form to ABCD form for
            # equation of a plane
            if len(surface_params) == 9:
                p1 = np.array([surface_params[0],
                               surface_params[3],
                               surface_params[6]])
                p2 = np.array([surface_params[1],
                               surface_params[4],
                               surface_params[7]])
                p3 = np.array([surface_params[2],
                               surface_params[5],
                               surface_params[8]])
                n = np.cross(p2 - p1, p3 - p1)
                n0 = -p1
                A = n[0]
                B = n[1]
                C = n[2]
                D = np.dot(n, n0)[0]

                surface_params = [A, B, C, D]

        elif surface_type == "cylv":
           p1 = tuple(surface_params[:3])
           p2 = tuple(surface_params[3:6])
           r = surface_params[-1]
           surface_params = [p1, p2, r]

       # elif surface_type == "cone":
       #      ...
       #     surface_params = []

        elif surface_type == "sqc":
           width = surface_params[2] * 2
           height = surface_params[2] * 2
           axis = 'z',
           origin = surface_params[:2]
           surface_params = [width, height, axis, origin]

        elif surface_type == "rect":
           width = surface_params[3] - surface_params[2]
           height = surface_params[1] - surface_params[0]
           axis = 'z',
           xc = surface_params[3] - (width/2)
           yc = surface_params[1] - (height/2)
           origin = [xc, yc]
           surface_params = [width, height, axis, origin]

       # elif surface_type == "hexxc":
       #      ...
       #     surface_params = []

       # elif surface_type == "hexyc":
       #     ...
       #     surface_params = []


    # handle special cases
    elif bool(special_case_surfaces.count(surface_type)):
        set_attributes = False
        if surface_type == "inf":
            surface_object = "inf" # We'll replace this later
    else:
        raise ValueError(f"Surfaces of type {surface_type} are currently unsupported")

    if set_attributes:
        surface_params = tuple(surface_params)
        surface_object = surface_object(*surface_params)
        surface_object.name = surface_name
    surf_dict[surface_name] = surface_object

def _construct_cell_helper(cell_card, cell_card_splitter, cell_type):
    """Helper function for creating cells

    Parameters
    ----------
    cell_card : str
        A string representing a serpent `cell` card
    cell_card_splitter : str
        A regular expresion used for extracting the surface data
        from the rest of the cell card.
    cell_type :
        A string representing the type of cell. Can be
        `'material'`, `'fill'`, or `'outside'`

    Returns
    -------
    cell_object : openmc.Cell object
        An openmc.Cell object corresponding to a Serpent cell card
    cell_name : str
        The name of the cell
    cell_fill_object : openmc.Material, openmc.Universe, or None
        Object to fill the cell. Variable type of cell_fill_object depends
        on the value of cell_type:
            'material' -> openmc.Material
            'fill' -> openmc.Universe
            'outside' -> openmc.Universe
    cell_region : openmc.Region or None
        Region assigned to the cell. Can be None in certain special
        cases (e.g. declaring material cell using the complement of an
        `inf` surface)
    """
    cell_data = cell_card.split()
    cell_name = cell_data[1]
    cell_universe_name = cell_data[2]
    cell_fill_object_name = ''
    cell_args = []

    # store universe-cell mapping for later
    if bool(universe_to_cells_dict.get(cell_universe_name)):
        universe_to_cell_names_dict[cell_universe_name] += [cell_name]
    else:
        universe_to_cell_names_dict[cell_universe_name] = [cell_name]
        universe_dict[cell_universe_name] = openmc.Universe(name=cell_universe_name)

    cell_object = openmc.Cell()
    cell_fill_object = None
    cell_region = None

    if cell_type == 'material':
        fill_object_name_index = 3
        arg_index = 4
        cell_fill_obj_dict = mat_dict
    else:
        if cell_type == 'fill':
            fill_object_name_index = 4
            arg_index = 5
        elif cell_type == 'outside':
            fill_object_name_index = 2 # This might give us an error later when we try to run
            arg_index = 4
        else:
            raise ValueError(f"cell_type: {cell_type} is erroneous")

        cell_fill_obj_dict = universe_dict
        filling_universe_name = cell_data[fill_object_name_index]
        if not bool(universe_dict.get(filling_universe_name)):
            universe_dict[filling_universe_name] = openmc.Universe(name=filling_universe_name)

    cell_fill_object_name = cell_data[fill_object_name_index]
    cell_args = cell_data[arg_index:]
    cell_fill_object = cell_fill_object_dict[cell_fill_object_name]


    # Handle special cases #
    ########################
    # material cells in a null region
    if cell_type == 'material' and \
            surface_object == "inf" and \
            len(cell_args) == 1:
        mat_null_cell = openmc.Cell()
        cell_object = mat_null_cell
    # generic case
    else:
        cell_surf_dict = {}
        surf_name_to_surf_id = {}
        csg_expression = ""
        for surf_name in cell_args:
            surf_name = re.split("(-|#|:|\s*)", surf_name)[-1]
            surface_object = surf_dict[surf_name]
            if cell_type == 'outside':
                surface_object.boundary_type = surface_bc
                surf_dict[surf_name] = surface_object
            surf_id = surface_object.id
            cell_surf_dict[surf_id] = surface_object
            surf_name_to_surf_id[surface_object.name] = str(surf_id)

        csg_expression = re.split(cell_card_splitter, cell_card)[-1]
        # replace operators
        csg_expression = csg_expression.replace(":", "|")
        csg_expression = csg_expression.replace("#", "~")
        for surf_name in surf_name_to_surf_id:
            csg_expression = csg_expression.replace(surf_name,
                                                  surf_name_to_surf_id[surf_name])
        cell_region = openmc.Region.from_expression(csg_expression, cell_surf_dict)
    return cell_object, cell_name, cell_fill_object, cell_region

def _get_boundary_conditions():
    """
    Helper function that gets the serpent boundary conditions

    Returns
    -------
    surface_bc : str
        String that specified the Serpent boundary condtion
        in openmc format.
    """

    return surface_bc

def _check_for_offline_lattice_args(current_line_idx):
    """
    Helper function that looks for multi-line lattice arguments

    Parameters
    ----------
    current_line_idx : int
        Index of the current line in the geometry file

    Returns
    -------
    offlind_lattice_args_exist : bool
        True if multi-line lattice arguments exist.
        Otherwise False
    offline_lattice_args_list : list of str
        List containing all multi-line lattice arguments
    """

    return offline_lattice_args_exist, offline_lattice_args_list

# Read command line input
try:
    serpent_geo_path = str(sys.argv[1])
except IndexError:
    raise SyntaxError("No geo file specified")

try:
    serpent_geo_path = str(sys.argv[2])
except IndexError:
    raise SyntaxError("No material file specified")

# get filenames
fname = serpent_geo_path.split('/').pop(-1).split('.')[0]
path = os.path.dirname(serpent_geo_path)
openmc_mats = openmc.Materials.from_xml(sys.argv[2])
mat_dict = {}
for mat in openmc_mats:
    mat_dict[mat.name] = mat

geo_data = []
with open(serpent_geo_path, 'r') as file:
    geo_data = file.readlines()

surface_bc = _get_boundary_conditions() ### TO IMPLEMENT ###
surf_dict = {} # surf name to surface object
cell_dict = {} # cell name to cell object
universe_to_cell_names_dict = {}
universe_dict = {}

openmc_geometry = openmc.Geometry([])


for line in geo_data:
    # Create openmc Surface objects
    # corresponding to serpent surf cards
    if re.search(SURF_REGEX, line):
        surf_card = re.search(SURF_REGEX, line).group(0)
        _construct_surface_helper(surf_card)

    # Create openmc Cell objects
    # corresponding to serpent cell cards
    elif re.search(CELL_REGEX_ALL, line):
        cell_card = re.search(CELL_REGEX_ALL, line).group(0) # get the cell card without comments
        if re.search(CELL_REGEX2_CORE, cell_card):
            split_regex = CELL_REGEX2_CORE
            cell_type = "fill"
        elif re.search(CELL_REGEX3_CORE, cell_card):
            split_regex = CELL_REGEX3_CORE
            cell_type = "outside"
        elif re.search(CELL_REGEX1_CORE, cell_card):
            split_regex = CELL_REGEX1_CORE
            cell_type = "material"
        else:
            raise ValueError("Erroneous cell card type")
        my_cell, cell_name, fill_obj, cell_region = _construct_region_helper(cell_card, split_regex, cell_type)
        my_cell.name = cell_name
        my_cell.fill = fill_obj
        my_cell.region = cell_region
        cell_dict[cell_name] = my_cell


    # transformations
    elif re.search(TRANSFORMATION_REGEX, line):
        trans_data = line.split()
        trans_object_type = trans_data[1]
        trans_object_name = trans_data[2]

        # look for transformation object type
        if trans_object_type == "U":
            trans_objects_dict = cell_dict
            trans_object_names = universe_to_cell_names_dict[trans_object_name]
        elif trans_type == "S":
            trans_objects_dict = surf_dict
            trans_objects_names = [surf_dict[trans_object_name]]
        else:
            raise ValueError(f"Transforming objects of type
                             {trans_type} is currently unsupported")

        trans_objects = []
        for name in trans_object_names:
            trans_objects += [trans_objects_dict[name]]

        # check type of transformation
        ### lattice transformations not currently supported ###
        trans_args = trans_data[3:]
        n_args = len(trans_args)
        trans_type = []
        translation_args = []
        rotation_args = []
        # LVL, and 'rot' transformations currently unsupported
        if n_args == 3: # transformation
            x, y, z = tuple(trans_args)
            translation_args = [x, y, z]
            trans_types = ['translation']
        elif n_args == 7: # transformation + rotation using angles wrt axis
            x, y, z, tx, ty, tz, ORD = tuple(trans_args)
            rotation_args = [tx, ty, tz]
            translation_args = [x, y, z]
            if int(ORD) == 1:
                trans_types = ['rotation', 'translation']
            elif int(ORD) == 2:
                trans_types = ['translation', 'rotation']
            else:
                raise ValueError(f"{ORD} is an invalid value for ORD")

        elif n_args == 13: # transformation + rotation using rotation matrix
            x, y, z, a1, a2, a3, a4, \
                a5, a6, a7, a8, a9, ORD = tuple(trans_args)
            rotation_args = [[a1, a2, a3],
                             [a4, a5, a6],
                             [a7, a8, a9]]
            translation_args = [x, y, z]
            if int(ORD) == 1:
                trans_types = ['rotation', 'translation']
            elif int(ORD) == 2:
                trans_types = ['translation', 'rotation']
            else:
                raise ValueError(f"{ORD} is an invalid value for ORD")
        else:
            raise SyntaxError("Incorrect number of arguments or unsupported
                              transformation type")

        transformed_objects = {}
        for trans_type in trans_types:
            if trans_type == 'translation':
                for obj in trans_objects:
                    transformed_objects[obj.name] = obj.translate(translation_args)
            elif trans_type == 'rotation':
                for obj in trans_objects:
                    transformed_objects[obj.name] = obj.rotate(rotation_args)

        for obj_name in transformed_objects:
            trans_objects_dict[obj_name] = transformed_objects[obj_name]

    elif re.search(LATTICE_REGEX, line):
        lat_data = line.split()
        lat_universe = lat_data[1]
        lat_type = lat_data[2]
        lat_args = lat_data[3:]

        # chech if all args are on one line
        current_line_idx = geo_data.index(line)
        offline_lattice_args_exist, offline_lattice_args_list = _check_for_offline_lattice_args(current_line_idx):
        if offline_lattice_args_exist: # to implement
            lat_args += office_lattice_args_list

        # flow control for different lattice types
        if lat_type == 1:

        else:
            raise ValueError(f"Type {lat_type} lattices are currently unsupported")
