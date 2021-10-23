import os
import numpy as np
import pandas as pd

from kgcnn.data.base import MemoryGeometricGraphDataset
from kgcnn.utils.data import save_json_file, load_json_file
from kgcnn.mol.molgraph import MolecularGraphRDKit, OneHotEncoder


class MoleculeNetDataset(MemoryGeometricGraphDataset):
    r"""Base class for using deepchem molecule datasets style. The base class provides properties and methods for
    making graph features from smiles. The graph structure matches the molecular graph. The atomic coordinates
    are generated by a conformer guess. Since this require some computation time, it is only done once and the
    molecular coordinate or mol-blocks stored in a json-file named in :obj:`MoleculeNetDataset.mol_filename`.
    The selection of smiles and whether conformers should be generated is handled by sub-classes or specified in the
    the methods ``prepare_data`` and ``read_in_memory``.

    """

    mol_filename = "mol.json"

    def __init__(self, data_directory: str = None, dataset_name: str = None, file_name: str = None,
                 verbose=1):
        r"""Initialize a `MoleculeNetDataset` from file.

        Args:
            file_name (str): Filename for reading into memory. This must be the name of the '.csv' file.
                Default is None.
            data_directory (str): Full path to directory containing all dataset files. Default is None.
            dataset_name (str): Name of the dataset. Important for naming. Default is None.
            verbose (int): Print progress or info for processing, where 0 is silent. Default is 1.
        """

        self.file_name = file_name
        self.data_directory = data_directory
        self.dataset_name = dataset_name

        self.data_keys = None

        MemoryGeometricGraphDataset.__init__(self, verbose=verbose)

    def _smiles_to_mol_list(self, smiles: list, add_hydrogen: bool = True, sanitize: bool = True,
                            make_conformers: bool = True, verbose: int = 1):
        r"""Convert a list of smiles as string into a list of mol-information, namely mol-block as string.

        Args:
            smiles (list): A list of smiles for each molecule in dataset.
            add_hydrogen (bool): Whether to add H after smile translation.
            sanitize (bool): Whether sanitize molecule.
            make_conformers (bool): Try to generate 3D coordinates
            verbose (int): Print progress or info for processing, where 0 is silent. Default is 1.

        Returns:
            list: A list of mol-block information as sting.
        """
        if len(smiles) == 0:
            print("Error:kgcnn: Can not translate smiles, received empty list for %s." % self.dataset_name)
        if verbose > 0:
            print("INFO:kgcnn: Generating molecules and store %s to disk..." % self.mol_filename)
        molecule_list = []
        max_number = len(smiles)
        for i, sm in enumerate(smiles):
            mg = MolecularGraphRDKit(add_hydrogen=add_hydrogen)
            mg.from_smiles(sm, sanitize=sanitize)
            if make_conformers:
                _ = mg.node_coordinates  # Force to generate 3D coordinates
            molecule_list.append(mg.to_mol_block())
            if i % 1000 == 0:
                if verbose > 0:
                    print(" ... converted molecules {0} from {1}".format(i, max_number))
        if verbose > 0:
            print("done")
        return molecule_list

    def prepare_data(self, file_name: str = None, data_directory: str = None, dataset_name: str = None,
                     overwrite: bool = False, verbose: int = 1, smiles_column_name: str = "smiles",
                     make_conformers: bool = True,
                     add_hydrogen: bool = True, **kwargs):
        r"""Pre-computation of molecular structure.

        Args:
            file_name (str): Filename for reading into memory. Default is None.
            data_directory (str): Full path to directory containing all files. Default is None.
            dataset_name (str): Name of the dataset. Default is None.
            overwrite (bool): Overwrite existing database mol-json file. Default is False.
            verbose (int): Print progress or info for processing where 0=silent. Default is 1.
            smiles_column_name (str): Column name where smiles are given in csv-file. Default is "smiles".
            make_conformers (bool): Whether to make conformers. Default is True.
            add_hydrogen (bool): Whether to add H after smile translation. Default is True.

        Returns:
            self
        """
        if file_name is not None:
            self.file_name = file_name
        if data_directory is not None:
            self.data_directory = data_directory
        if dataset_name is not None:
            self.dataset_name = dataset_name

        mol_filename = self.mol_filename
        if os.path.exists(os.path.join(self.data_directory, mol_filename)) and not overwrite:
            if verbose > 0:
                print("INFO:kgcnn: Found rdkit mol.json of pre-computed structures.")
            return self
        filepath = os.path.join(self.data_directory, self.file_name)
        data = pd.read_csv(filepath)
        # print(data)
        smiles = data[smiles_column_name].values
        mb = self._smiles_to_mol_list(smiles, add_hydrogen=add_hydrogen, sanitize=True, make_conformers=make_conformers,
                                      verbose=verbose)
        save_json_file(mb, os.path.join(self.data_directory, mol_filename))

        return self

    def read_in_memory(self, file_name: str = None, data_directory: str = None, dataset_name: str = None,
                       has_conformers: bool = True, label_column_name: str = None,
                       add_hydrogen: bool = True, verbose: int = 1):
        r"""Load list of molecules from json-file named in :obj:`MoleculeNetDataset.mol_filename` into memory. And
        already extract basic graph information. No further attributes are computed as default.

        Args:
            file_name (str): Filename for reading into memory. Default is None.
            data_directory (str): Full path to directory containing all files. Default is None.
            dataset_name (str): Name of the dataset. Default is None.
            has_conformers (bool): If molecules have 3D coordinates pre-computed.
            label_column_name (str): Column name where labels are given in csv-file. Default is None.
            add_hydrogen (bool): Whether to add H after smile translation.
            verbose (int): Print progress or info for processing where 0=silent. Default is 1.

        Returns:
            self
        """
        if file_name is not None:
            self.file_name = file_name
        if data_directory is not None:
            self.data_directory = data_directory
        if dataset_name is not None:
            self.dataset_name = dataset_name

        data = pd.read_csv(os.path.join(self.data_directory, self.file_name))
        # print(data.columns)
        self.data_keys = data.columns
        if isinstance(label_column_name, str):
            graph_labels_all = np.expand_dims(np.array(data[label_column_name]), axis=-1)
        elif isinstance(label_column_name, list):
            graph_labels_all = np.concatenate([np.expand_dims(np.array(data[x]), axis=-1) for x in label_column_name],
                                              axis=-1)
        elif isinstance(label_column_name, slice):
            graph_labels_all = np.array(data.iloc[:, label_column_name])
        else:
            raise ValueError("ERROR:kgcnn: Column label definition must be list or string, got %s" % label_column_name)

        mol_path = os.path.join(self.data_directory, self.mol_filename)
        if not os.path.exists(mol_path):
            raise FileNotFoundError("ERROR:kgcnn: Can not load molecules for dataset %s" % self.dataset_name)

        if verbose > 0:
            print("INFO:kgcnn: Read mol-blocks from mol.json of pre-computed structures...")
        mols = load_json_file(mol_path)

        # Main loop to read molecules from mol-block
        atoms = []
        coords = []
        number = []
        edgind = []
        edges = []
        num_mols = len(mols)
        graph_labels = []
        counter_iter = 0
        for i, x in enumerate(mols):
            mg = MolecularGraphRDKit(add_hydrogen=add_hydrogen).from_mol_block(x, sanitize=True)
            if mg.mol is None:
                print(" ... skip molecule {0} as it could not be converted to mol-object".format(i))
                continue
            atoms.append(mg.node_symbol)
            if has_conformers:
                coords.append(mg.node_coordinates)
            number.append(mg.node_number)
            temp_edge = mg.edge_number
            edgind.append(temp_edge[0])
            edges.append(np.array(temp_edge[1], dtype="int"))
            counter_iter += 1
            graph_labels.append(graph_labels_all[i])
            if i % 1000 == 0:
                if verbose > 0:
                    print(" ... read molecules {0} from {1}".format(i, num_mols))
        self.node_symbol = atoms
        self.node_coordinates = coords if has_conformers else None
        self.node_number = number
        self.graph_size = [len(x) for x in atoms]
        self.edge_indices = edgind
        self.length = counter_iter
        self.graph_labels = graph_labels
        self.edge_number = edges

        if verbose > 0:
            print("done")

        return self

    def set_attributes(self,
                       nodes=None,
                       edges=None,
                       graph=None,
                       encoder_nodes=None,
                       encoder_edges=None,
                       encoder_graph=None,
                       add_hydrogen: bool = False,
                       has_conformers: bool = True,
                       verbose: int = 1):
        r"""Set further molecular attributes or features by string identifier. Requires :obj:`MolecularGraphRDKit`.
        Reset edges and nodes with new attributes and edge indices. Default values are features that has been used
        by `Luo et al (2019) <https://doi.org/10.1021/acs.jmedchem.9b00959>`_.

        Args:
            nodes (list): A list of node attributes
            edges (list): A list of edge attributes
            graph (list): A list of graph attributes.
            encoder_nodes (dict): A dictionary of callable encoder where the key matches the attribute.
            encoder_edges (dict): A dictionary of callable encoder where the key matches the attribute.
            encoder_graph (dict): A dictionary of callable encoder where the key matches the attribute.
            add_hydrogen (bool): Whether to remove hydrogen.
            has_conformers (bool): If molecules have 3D coordinates pre-computed.
            verbose (int): Print progress or info for processing where 0=silent. Default is 1.

        Returns:
            self
        """
        mol_path = os.path.join(self.data_directory, self.mol_filename)
        if not os.path.exists(mol_path):
            raise FileNotFoundError("ERROR:kgcnn: Can not load molecules for dataset %s" % self.dataset_name)

        if verbose > 0:
            print("INFO:kgcnn: Making attributes...")

        mols = load_json_file(mol_path)

        # Choose default values here:
        if nodes is None:
            nodes = ['Symbol', 'TotalDegree', 'FormalCharge', 'NumRadicalElectrons', 'Hybridization',
                     'IsAromatic', 'IsInRing', 'TotalNumHs', 'CIPCode', "ChiralityPossible", "ChiralTag"]
        if edges is None:
            edges = ['BondType', 'IsAromatic', 'IsConjugated', 'IsInRing', "Stereo"]
        if graph is None:
            graph = ['ExactMolWt', 'NumAtoms']
        if encoder_nodes is None:
            encoder_nodes = {
                "Symbol": OneHotEncoder(
                    ['B', 'C', 'N', 'O', 'F', 'Si', 'P', 'S', 'Cl', 'As', 'Se', 'Br', 'Te', 'I', 'At'], dtype="str"),
                "Hybridization": OneHotEncoder([2, 3, 4, 5, 6]),
                "TotalDegree": OneHotEncoder([0, 1, 2, 3, 4, 5], add_unknown=False),
                "TotalNumHs": OneHotEncoder([0, 1, 2, 3, 4], add_unknown=False),
                "CIPCode": OneHotEncoder(['R', 'S'], add_unknown=False, dtype="str")
            }
        if encoder_edges is None:
            encoder_edges = {
                "BondType": OneHotEncoder([1, 2, 3, 12], add_unknown=False),
                "Stereo": OneHotEncoder([0, 1, 2, 3], add_unknown=False),
            }
        if encoder_graph is None:
            encoder_graph = {}

        for key, value in encoder_nodes.items():
            encoder_nodes[key] = self._deserialize_encoder(value)
        for key, value in encoder_edges.items():
            encoder_edges[key] = self._deserialize_encoder(value)
        for key, value in encoder_graph.items():
            encoder_graph[key] = self._deserialize_encoder(value)

        # Reset all attributes
        graph_attributes = []
        node_attributes = []
        edge_attributes = []
        edge_indices = []
        node_coordinates = []
        node_symbol = []
        node_number = []
        num_mols = len(mols)
        for i, sm in enumerate(mols):
            mg = MolecularGraphRDKit(add_hydrogen=add_hydrogen).from_mol_block(sm, sanitize=True)
            if mg.mol is None:
                print(" ... skip molecule {0} as it could not be converted to mol-object".format(i))
                continue
            node_attributes.append(np.array(mg.node_attributes(nodes, encoder_nodes), dtype="float32"))
            edge_attributes.append(np.array(mg.edge_attributes(edges, encoder_edges)[1], dtype="float32"))
            edge_indices.append(np.array(mg.edge_indices, dtype="int64"))
            graph_attributes.append(np.array(mg.graph_attributes(graph, encoder_graph), dtype="float32"))
            node_symbol.append(mg.node_symbol)
            if has_conformers:
                node_coordinates.append(np.array(mg.node_coordinates, dtype="float32"))
            node_number.append(mg.node_number)
            if i % 1000 == 0:
                if verbose > 0:
                    print(" ... read molecules {0} from {1}".format(i, num_mols))

        self.graph_size = [len(x) for x in node_attributes]
        self.graph_attributes = graph_attributes
        self.node_attributes = node_attributes
        self.edge_attributes = edge_attributes
        self.edge_indices = edge_indices
        self.node_coordinates = node_coordinates
        self.node_symbol = node_symbol
        self.node_number = node_number

        if verbose > 0:
            print("done")
            for key, value in encoder_nodes.items():
                if hasattr(value, "found_values"):
                    print("INFO:kgcnn: OneHotEncoder", key, "found", value.found_values)
            for key, value in encoder_edges.items():
                if hasattr(value, "found_values"):
                    print("INFO:kgcnn: OneHotEncoder", key, "found", value.found_values)
            for key, value in encoder_graph.items():
                if hasattr(value, "found_values"):
                    print("INFO:kgcnn: OneHotEncoder", key, "found", value.found_values)

        return self

    @staticmethod
    def _deserialize_encoder(encoder_identifier):
        """Simple entry point for serialization. Will maybe include keras in the future.

        Args:
            encoder_identifier: Identifier, class or function of an encoder.

        Returns:
            obj: Deserialized encoder.
        """
        if isinstance(encoder_identifier, dict):
            if encoder_identifier["class_name"] == "OneHotEncoder":
                return OneHotEncoder.from_config(encoder_identifier["config"])
        elif hasattr(encoder_identifier, "__call__"):
            return encoder_identifier
        else:
            raise ValueError("ERROR:kgcnn: Unable to deserialize encoder %s " % encoder_identifier)
