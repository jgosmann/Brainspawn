""" Module for factory for capabilities.
"""

from output_cap import OutputCap
from spikes_cap import SpikesCap


class CapFactory(object):
    """ Capability factory class.
    Gets a list of all caps.
    """

    _caps = None

    @classmethod
    def get_caps(cls):
        """ Returns a list of all capabilities.
        *NB* - nengo doesn't support VoltageCap at the moment.
        """
        if (not cls._caps):
            cls._caps = [OutputCap(), SpikesCap()]
        return cls._caps
