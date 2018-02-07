from types import MappingProxyType
from typing import Iterable, Mapping

from .istate import IState


EMPTY_DICT = MappingProxyType(dict())


class IActuator(IState):
    """
    IActuator capability is usually mapped to Actuators.
    Devices with this capability are capable to act, i.e.
    perform some actions in the real world like playing
    music and changing tracks, turning power on and off,
    turning light on and off and so on.
    """
    @property
    def commands(self) -> Iterable[str]:
        """
        Returns a list of command (command names) that
        can be executed by this Thing.

        Availability of the following commands is mandatory:

        - activate;
        - deactivate;
        - toggle.

        For details about such commands see the definition
        of the corresponding methods

        :return: a list of commands that can be executed by
                 this Thing
        """
        raise NotImplementedError()

    def execute(self, command: str, args: Mapping = EMPTY_DICT) -> None:
        """
        Accepts the specified command on execution

        :param command: a name of command to be executed
               (see 'commands' property for a list of
                available commands)
        :param args: a mapping with keyword arguments to be
               passed on command execution
        :return: None
        """
        raise NotImplementedError()

    def activate(self) -> None:
        """
        Switches the Thing to one of the 'active' states

        :return: None
        """
        raise NotImplementedError()

    def deactivate(self) -> None:
        """
        Switches the Thing to one of the 'inactive' states

        :return: None
        """
        raise NotImplementedError()

    def toggle(self) -> None:
        """
        Switched the Thing from a current state to an
        opposite one (deactivates if active, activates if
        inactive)

        :return: None
        """
        raise NotImplementedError()
