""" Output capability module

Basic output capability, creates simple connection between an object
and an observing node.

"decoded_output" for Ensembles.
"""

import nengo
from capability import Capability


class OutputCap(Capability):
    """Output capability class.
    """

    @property
    def name(self):
        """ Returns name of this capability, which is 'output'.
        """
        return "output"  # 'decoded_ouput' for ensembles

    def supports_obj(self, obj):
        """ Returns true if node is type Ensemble or Neurons.
        """
        return issubclass(obj.__class__, (nengo.Node, nengo.Ensemble,
                                          nengo.objects.Neurons))

    def get_out_dimensions(self, obj):
        """ Returns number of dimensions of node.
        """
        if (issubclass(obj.__class__, nengo.Node)):
            return obj.size_out
        elif (issubclass(obj.__class__, nengo.Ensemble)):
            return obj.dimensions
        elif (issubclass(obj.__class__, nengo.objects.Neurons)):
            return obj.n_neurons
        else:
            raise ValueError("output_cap does not support given object")

    def connect_node(self, node, obj):
        """ Create 'simple' connection between object and node
        For Ensembles, this gives us 'decoded_output'.

        TODO - specify filters
        """
        if (issubclass(obj.__class__, nengo.Node)):
            nengo.Connection(obj, node, synapse=None)
        elif (issubclass(obj.__class__, (nengo.Ensemble,
                                         nengo.objects.Neurons))):
            nengo.Connection(obj, node, synapse=0.005)
        else:
            raise ValueError("output_cap does not support given object")
