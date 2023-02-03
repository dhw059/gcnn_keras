import os.path
import numpy as np
import logging
from sklearn.preprocessing import StandardScaler as StandardScalerSklearn
from kgcnn.data.utils import save_json_file, load_json_file


logging.basicConfig()  # Module logger
module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.INFO)


class StandardScalerSklearnBase(StandardScalerSklearn):
    r"""Base standard scaler of :obj:`sklearn` with added functionality to save and load weights of this scaler similar
    to keras layers and objects.

    .. code-block:: python

        import numpy as np
        from kgcnn.scaler.scaler import StandardScalerSklearnBase
        data = np.random.rand(5).reshape((5,1))
        scaler = StandardScalerSklearnBase()
        scaler.fit(X=data)
        print(scaler.get_weights())
        print(scaler.get_config())

    """
    _attributes_list_sklearn = ["n_features_in_", "mean_", "scale_", "var_", "feature_names_in_", "n_samples_seen_"]

    def __init__(self, *, copy=True, with_mean=True, with_std=True):
        super(StandardScalerSklearnBase, self).__init__(copy=copy, with_mean=with_mean, with_std=with_std)

    def get_scaling(self):
        """Get scale of shape (1, n_properties)."""
        if not hasattr(self, "scale_"):
            return
        scale = np.array(self.scale_)
        scale = np.expand_dims(scale, axis=0)
        return scale

    def get_config(self) -> dict:
        """Get configuration for scaler."""
        config = super(StandardScalerSklearnBase, self).get_params()
        return config

    def set_config(self, config: dict):
        """Set configuration for scaler.

        Args:
            config (dict): Config dictionary.
        """
        self.set_params(**config)

    def get_weights(self) -> dict:
        """Get weights for this scaler after fit."""
        weight_dict = dict()
        for x in self._attributes_list_sklearn:
            if hasattr(self, x):
                value = getattr(self, x)
                value_update = {x: np.array(value).tolist()} if value is not None else {x: value}
                weight_dict.update(value_update)
        return weight_dict

    def set_weights(self, weights: dict):
        """Set weights for this scaler.

        Args:
            weights (dict): Weight dictionary.
        """
        for item, value in weights.items():
            if item in self._attributes_list_sklearn:
                setattr(self, item, np.array(value))
            else:
                module_logger.warning("`StandardScaler` got unknown weight '%s'." % item)

    def save_weights(self, file_path: str):
        """Save weights as numpy to file.

        Args:
            file_path: Filepath to save weights.
        """
        weights = self.get_weights()
        # Make them all numpy arrays for save.
        for key, value in weights.items():
            weights[key] = np.array(value)
        if len(weights) > 0:
            np.savez(os.path.splitext(file_path)[0] + ".npz", **weights)
        else:
            module_logger.warning("Error, no weights to save for `StandardScaler`.")

    def save(self, file_path: str):
        """Save scaler serialization to file.

        Args:
            file_path: Filepath to save scaler serialization.
        """
        conf = self.get_config()
        weights = self.get_weights()
        full_info = {"class_name": type(self).__name__, "module_name": type(self).__module__,
                     "config": conf, "weights": weights}
        save_json_file(full_info, os.path.splitext(file_path)[0] + ".json")

    def load(self, file_path: str):
        """Load scaler serialization from file.

        Args:
            file_path: Filepath to load scaler serialization.
        """
        full_info = load_json_file(file_path)
        # Could verify class_name and module_name here.
        self.set_config(full_info["config"])
        self.set_weights(full_info["weights"])
        return self


class StandardScaler(StandardScalerSklearnBase):
    r"""Standard scaler that inherits from :obj:`sklearn.preprocessing.StandardScaler` .
    Included unused kwarg 'atomic_number' to be compatible with some material oriented scaler.

    .. code-block:: python

        import numpy as np
        from kgcnn.scaler.scaler import StandardScaler
        data = np.random.rand(5).reshape((5,1))
        scaler = StandardScaler()
        scaler.fit(X=data)
        print(scaler.get_weights())
        print(scaler.get_config())
        print(scaler.inverse_transform(scaler.transform(X=data)))
        print(data)
        scaler.save("example.json")
        new_scaler = StandardScaler()
        new_scaler.load("example.json")
        print(new_scaler.inverse_transform(scaler.transform(X=data)))

    """

    # noinspection PyPep8Naming
    def fit(self, X, *, y=None, sample_weight=None, atomic_number=None):
        """Compute the mean and std to be used for later scaling.

        Args:
            X (np.ndarray): Array of shape (n_samples, n_features)
                The data used to compute the mean and standard deviation
                used for later scaling along the feature's axis.
            y (None): Ignored.
            sample_weight (np.ndarray): Individual weights for each sample.
            atomic_number (list, None): Ignored.

        Returns:
            self: Fitted scaler.
        """
        return super(StandardScaler, self).fit(X=X, y=y, sample_weight=sample_weight)

    # noinspection PyPep8Naming
    def partial_fit(self, X, y=None, sample_weight=None, atomic_number=None):
        r"""Online computation of mean and std on X for later scaling.
        All of X is processed as a single batch. This is intended for cases
        when :meth:`fit` is not feasible due to very large number of
        `n_samples` or because X is read from a continuous stream.
        The algorithm for incremental mean and std is given in Equation 1.5a,b
        in `Chan, et al. (1982) <https://www.tandfonline.com/doi/abs/10.1080/00031305.1983.10483115>`_ .

        Args:
            X (np.ndarray): Array of shape (n_samples, n_features)
                The data used to compute the mean and standard deviation
                used for later scaling along the feature's axis.
            y (np.ndarray, None): Ignored.
            sample_weight (np.ndarray): Array-like of shape (n_samples,), default=None
                Individual weights for each sample.
            atomic_number (list): Not used.

        Returns:
            self: Fitted scaler.
        """
        # For partial fit internally uses args and not kwargs.
        # Can not request kwargs after argument X here.
        return super(StandardScaler, self).partial_fit(X=X, y=y, sample_weight=sample_weight)

    # noinspection PyPep8Naming
    def fit_transform(self, X, *, y=None, atomic_number=None, **fit_params):
        r"""Perform fit and standardization by centering and scaling.

        Args:
            X (np.ndarray): Array of shape (n_samples, n_features).
                The data used to scale along the feature's axis.
            y (np.ndarray, None): Ignored.
            atomic_number (list): Not used.
            fit_params: Additional fit kwargs.

        Returns:
            X_tr (np.ndarray): Transformed array of shape (n_samples, n_features).
        """
        return super(StandardScaler, self).fit_transform(X=X, y=y, **fit_params)

    # noinspection PyPep8Naming
    def transform(self, X, *, copy=None, atomic_number=None):
        """Perform standardization by centering and scaling.

        Args:
            X (np.ndarray): Array of shape (n_samples, n_features).
                The data used to scale along the feature's axis.
            copy (bool): Copy the input X or not.
            atomic_number (list): Not used.

        Returns:
            X_tr (np.ndarray): Transformed array of shape (n_samples, n_features).
        """
        return super(StandardScaler, self).transform(X=X, copy=copy)

    # noinspection PyPep8Naming
    def inverse_transform(self, X, *, copy: bool = None, atomic_number=None):
        r"""Scale back the data to the original representation.

        Args:
            X (np.ndarray): Array of shape (n_samples, n_features).
                The data used to scale along the feature's axis.
            copy (bool): Copy the input X or not.
            atomic_number (list): Not used.

        Returns:
            X_tr (np.ndarray): Transformed array of shape (n_samples, n_features).
        """
        return super(StandardScaler, self).inverse_transform(X=X, copy=copy)


class StandardLabelScaler(StandardScalerSklearnBase):
    r"""Standard scaler for labels that inherits from :obj:`sklearn.preprocessing.StandardScaler` .
    Included unused kwarg 'atomic_number' to be compatible with some material oriented scaler.
    Uses `y` argument for scaling labels and `X` is ignored.

    .. code-block:: python

        import numpy as np
        from kgcnn.scaler.scaler import StandardLabelScaler
        data = np.random.rand(5).reshape((5,1))
        scaler = StandardLabelScaler()
        scaler.fit(y=data)
        print(scaler.fit_transform(y=data))
        print(scaler.get_weights())
        print(scaler.get_config())
        print(scaler.inverse_transform(y=scaler.transform(y=data)))
        print(data)
        scaler.save("example.json")
        new_scaler = StandardLabelScaler()
        new_scaler.load("example.json")
        print(new_scaler.inverse_transform(y=scaler.transform(y=data)))

    """

    def _assert_has_y(self, y):
        if y is None:
            raise ValueError(
                "Require labels in `y` for `%s`. Input must be e.g. 'fit(y=data)'." % type(self).__name__)

    # noinspection PyPep8Naming
    def fit(self, y, *, X=None, sample_weight=None, atomic_number=None):
        r"""Compute the mean and std to be used for later scaling.

        Args:
            y (np.ndarray): Array of shape (n_samples, n_labels)
                The data used to compute the mean and standard deviation
                used for later scaling along the feature's axis.
            X (None): Ignored.
            sample_weight (np.ndarray): Individual weights for each sample.
            atomic_number (list): Ignored.

        Returns:
            self: Fitted scaler.
        """
        # fit() of sklearn uses reset and partial fit.
        self._assert_has_y(y)
        self._reset()
        return self.partial_fit(y=y, X=X, sample_weight=sample_weight)

    # noinspection PyPep8Naming
    def partial_fit(self, y, X=None, sample_weight=None, atomic_number=None):
        r"""Online computation of mean and std on y for later scaling.
        All of y is processed as a single batch. This is intended for cases
        when :meth:`fit` is not feasible due to very large number of
        `n_samples` or because y is read from a continuous stream.
        The algorithm for incremental mean and std is given in Equation 1.5a,b
        in `Chan, et al. (1982) <https://www.tandfonline.com/doi/abs/10.1080/00031305.1983.10483115>`_ .

        Args:
            y (np.ndarray): Array of shape (n_samples, n_labels)
                The data used to compute the mean and standard deviation
                used for later scaling along the feature's axis.
            X (None): Ignored.
            sample_weight (np.ndarray): Individual weights for each sample.
            atomic_number (list): Ignored.

        Returns:
            self: Fitted scaler.
        """
        # For partial fit internally uses args and not kwargs.
        # Can not request kwargs after argument X, y here.
        self._assert_has_y(y)
        # Just changing order of x,y here.
        return super(StandardLabelScaler, self).partial_fit(X=y, y=None, sample_weight=sample_weight)

    # noinspection PyPep8Naming
    def fit_transform(self, y=None, *, X=None, atomic_number=None, **fit_params):
        r"""Perform fit and standardization by centering and scaling.

        Args:
            y (None): Array of shape (n_samples, n_labels)
                The data used to compute the mean and standard deviation
                used for later scaling along the feature's axis.
            X (np.ndarray): Ignored.
            atomic_number (list): Ignored.
            fit_params (Any): Kwargs for fit.

        Returns:
            y_tr (np.ndarray): Transformed array of shape (n_samples, n_labels).
        """
        # Just changing order of x,y here.
        return super(StandardLabelScaler, self).fit_transform(X=y, y=None, **fit_params)

    # noinspection PyPep8Naming
    def transform(self, y=None, *, X=None, copy=None, atomic_number=None):
        r"""Perform standardization by centering and scaling.

        Args:
            X (np.ndarray): Ignored.
            y (None): Array of shape (n_samples, n_labels)
                The data used to scale along the feature's axis.
            atomic_number (list): Ignored.
            copy (bool): Copy the input `y` or not.

        Returns:
            y_tr (np.ndarray): Transformed array of shape (n_samples, n_labels).
        """
        # Just changing order of x,y here.
        return super(StandardLabelScaler, self).transform(X=y, copy=copy)

    # noinspection PyPep8Naming
    def inverse_transform(self, X=None, y=None, *, copy: bool = None, atomic_number=None):
        r"""Scale back the data to the original representation.

        Args:
            X (np.ndarray, None): Ignored. Default is None.
            y (None): Array of shape (n_samples, n_labels)
                The data used to scale along the feature's axis.
            atomic_number (list): Ignored.
            copy (bool): Copy the input `y` or not.

        Returns:
            y_tr (np.ndarray): Transformed array of shape (n_samples, n_labels).
        """
        # Just changing order of x,y here.
        return super(StandardLabelScaler, self).inverse_transform(X=y, copy=copy)
