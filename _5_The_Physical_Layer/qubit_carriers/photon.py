import sys

sys.path.append("../..")
from common.global_state_container import global_state_container
print("imported global_state_container module", global_state_container)

class Photon(object):
    def __init__(self, parent_optical_fiber):
        self.global_state = global_state_container.state
        self.id = self.global_state.create_qubit()
        self.parent_optical_fiber = parent_optical_fiber
        
    # reset the state of the photon to the pure |0> state. 
    # This should be done everytime the qubit is used, 
    # because in real experiments the photon is absorbed 
    # and we have to use a new photon.
    def reset(self):               
        # Resetting is non-trivial! If the qubit 
        # you are initialization /reseting is entangled with other 
        # qubits you can mess up, or more precisely, lose track, of 
        # the state of the other qubits. The other qubit becomes 
        # entangled with the environment, which we generally 
        # don't have access to.
        pass 
