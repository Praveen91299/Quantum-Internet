import sys

import random
from qutip import *

# sys.path.append("../..")
from _5_The_Physical_Layer.qubit_carriers.qubit import Qubit
print("imported Qubit object")

# sys.path.append("../..")
from common.global_state_container import global_state_container
print("imported global_state_container global variable")

class RepeaterHardware(object):
    def __init__(self, parent_repeater, qubits=2):
        self.parent_repeater = parent_repeater
        self.global_state = global_state_container.state
        self.left_qubit = Qubit(self)
        self.right_qubit = Qubit(self)
        self.left_optical_fiber = None
        self.right_optical_fiber = None                                         
#         self.memoryQubits = []

    def connect_right_fiber(self, fiber):
        self.right_optical_fiber = fiber
    
    def connect_left_fiber(self, fiber):
        self.left_optical_fiber = fiber
    
    def send_message(self, obj, msg):
        obj.handle_message(msg)

    def handle_message(self, msg):
        msg = msg.split('-')
        # id of the sender
        id = msg[0]
        if msg[1] == "decohered":
            # notify the link layer
            msg2 = packLinkExpired() #specify which link expired#
            self.send_message(self.parent_repeater, msg2)

    def swap_entanglement(self): 
        # proper quantum gates will be performed here.
        # find the positions of the qubits in the globalState state
        # apply the right qutip gates. Assume ideal gates at this point while you're
        # building the thing.
        # Do stuff to the global state container's state.
        CNOT = cnot(N=self.global_state.N, control=self.left_qubit[0].id, target=self.right_qubit[0].id)
        new_state = CNOT * self.global_state.state * CNOT.dag()
        Z180 = rz(180, N=self.global_state.N, target=self.left_qubit[0].id)
        Y90  = ry(90, N=self.global_state.N, target=self.left_qubit[0].id)
        H = Y90 * Z180
        new_state = H * new_state * H.dag()
        self.global_state.update_state(new_state)
        measurement_result1 = self.measure(self.left_qubit[0])
        measurement_result2 = self.measure(self.right_qubit[0])     
        # notify the parent repeater so that it can send the classical data to
        # the other repeater.
        msg = {'msg' : "entanglement swapping done", 
               'measurement_result1' : measurement_result1,
               'measurement_result2' : measurement_result2}
        self.send_message(self.parent_repeater, msg)
        # Now the parent repeater should notify the remote repeater
        # that swapping is done and should give it the measurement results.

    def apply_swap_corrections(self, qubitId, measurement_result1, measurement_result2):
        if measurement_result1 == 0 and measurement_result1 == 0:
            return
        elif measurement_result1 == 0 and measurement_result1 == 1:
            correction = rz(180, N=self.global_state.N, target=qubitId)
        elif measurement_result1 == 1 and measurement_result1 == 0:
            correction = rx(180, N=self.global_state.N, target=qubitId)
        elif measurement_result1 == 1 and measurement_result1 == 1:
            correction = rz(180, N=self.global_state.N, target=qubitId)
            correction = rx(180, N=self.global_state.N, target=qubitId) * correction
        new_state = correction * self.global_state.state * correction.dag()
        self.global_state.update_state(new_state)
        msg = {'msg' : "entanglement swapping corrections applied"}
        self.send_message(self.parent_repeater, msg)

    def measure(self, qubit, basis = "01"):
        # https://inst.eecs.berkeley.edu/~cs191/fa14/lectures/lecture10.pdf
        rho = self.global_state.state
        # construct the projectors
        P0 = tensor([identity(2) for _ in range(qubit.Id)] + 
                    basis(2,0) * basis(2,0).dag() + 
                    [identity(2) for _ in range(qubit.Id + 1, self.global_state.N)])
        P1 = tensor([identity(2) for _ in range(qubit.Id)] + 
                    basis(2,1) * basis(2,0).dag() + 
                    [identity(2) for _ in range(qubit.Id + 1, self.global_state.N)])
        # compute the probabilities of the 1 and 0 outcomes
        p0 = (P0 * rho).tr()
        p1 = (P1 * rho).tr() # check that p1 = 1 - p0
        # choose an outcome at random using the probabilities above.
        result = 0 if random.random() < p0 else 1
        # simulate state collapse
        new_state = P0 * rho * P0 / p0 if result == 0 else P1 * rho * P1 / p1
        # update globalState
        self.global_state.update_state(new_state)
        # return the measurement result
        return result

    def load_qubit_on_photon(self, qubit, photon):  # both qubit and photon are qubit objects
        # swaps the state of the photon and the local qubit 
        # (the photon should be initialized to |0>. The initialization 
        # can be noisy).
        SWAP = swap(N=self.global_state.N, targets=[qubit.id, photon.id])
        newState = SWAP * self.global_state.state * SWAP.dag()
        self.global_state.update_state(newState)

    def unload_qubit_from_photon(self, qubit, photon):
        # swaps the state of the photon and the local qubit 
        # (the local qubit should be initialized to |0>. The initialization 
        # can be noisy). 
        SWAP = swap(N=self.global_state.N, targets=[qubit.id, photon.id])
        new_state = SWAP * self.global_state.state * SWAP.dag()
        self.global_state.update_state(new_state)

    def send_photon(self, photon, fiber):
        fiber.carry_photon(photon)

    def receive_photon(self, photon):
        # This function is called by an optical fiber to
        # alert the repeaterHardware to receive the incoming photon.
        # The repeaterHardware chooses a (physical) qubit on which to unload the 
        # qubit carried on the photon.
        self.unload_qubit_from_photon(qubit, photon)

    def attempt_link_creation(self, remote_repeater):
        # remote is a repeater object.
        # here the physical details of link creation will be implemented:
        # 1. create EPR pair. Store one half locally and load the other on a photon.
        # 2. send the photon to the remote receiver.
        theQubit = self.left_qubit if self.parent_repeater.netId > remote_repeater.netId else self.rightQubit
        theOpticalFiber = self.left_optical_fiber if self.parent_repeater.netId > remote_repeater.netId else self.right_optical_fiber
        thePhoton = theOpticalFiber.photon12 if self.parent_repeater.netId > remote_repeater.netId else theOpticalFiber.photon12
        self.load_qubit_on_photon(theQubit, thePhoton)
        self.send_photon(thePhoton, theOpticalFiber)
        # 3. (for later) check somehow that we have a good link.
        # support for heralding stations and photon transmission, etc.

    def attempt_distillation(self):
        # apply gates on the qubits here
        return
