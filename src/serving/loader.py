import io
from typing import Any, Protocol
import joblib

# ---------------------------------------------------------
# Custom Exceptions for Loading
# ---------------------------------------------------------
class ModelLoadError(Exception):
    pass

class UnsupportedModelFormat(Exception):
    pass

class InvalidModelArtifact(Exception):
    pass

# ---------------------------------------------------------
# Abstraction (Interface)
# ---------------------------------------------------------
class ModelLoader(Protocol):
    """
    Interface for different model loaders.
    """
    def load(self, artifact_bytes: bytes) -> Any:
        ...

# ---------------------------------------------------------
# Implementation for Scikit-Learn + Joblib
# ---------------------------------------------------------
class SklearnJoblibLoader:
    def load(self, artifact_bytes: bytes) -> Any:
        try:
            # Convert bytes to an in-memory virtual file (file-like object)
            virtual_file = io.BytesIO(artifact_bytes)

            # Load the model from the virtual file
            model = joblib.load(virtual_file)

            # Validation: Is this actually a Scikit-Learn model?
            # (Machine learning models usually have 'predict' or 'transform' methods)
            if not hasattr(model, "predict") and not hasattr(model, "transform"):
                raise InvalidModelArtifact(
                    "The loaded object is not a valid scikit-learn model "
                    "(missing 'predict' or 'transform' methods)."
                )

            return model

        except InvalidModelArtifact:
            raise
        except Exception as e:
            # Handle cases where the file is corrupted or invalid
            raise ModelLoadError(f"Failed to load scikit-learn model: {str(e)}")