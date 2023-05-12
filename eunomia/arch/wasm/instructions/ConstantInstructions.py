# emulate the constant related instructions

import re
from struct import unpack

from eunomia.arch.wasm.exceptions import UnsupportInstructionError
from eunomia.arch.wasm.shadow import shadow
from z3 import BitVecVal, Float32, Float64, FPVal


class ConstantInstructions:
    def __init__(self, instr_name, instr_operand, instr_string):
        self.instr_name = instr_name
        self.instr_operand = instr_operand
        self.instr_str = instr_string

    # TODO overflow check in this function?
    def emulate(self, state, ro_data_section):
        # there are two types of const: i and f, like:
        # i32.const 0
        # f64.const 0x1.9p+6 (;=100;)
        # thus we have to deal with the different situations
        mnemonic = self.instr_str.split(' ')[0]
        const_num = self.instr_str.split(' ')[-1]
        const_type_prefix, _ = mnemonic.split('.')

        if const_type_prefix == 'i32':
            state.symbolic_stack.append(BitVecVal(const_num, 32))


            const_num = int(const_num)
            _shadow = shadow(False, False)
            for low, up in state.memory_manager.data_section:
                if low == const_num:
                    _shadow = shadow(False, True, BitVecVal(const_num, 32), False, up - low, False)
                    break
            for low, up in ro_data_section:
                if const_num >= low and const_num < up:
                    _shadow = shadow(False, True, low, False, up - low)
                    break

            state.shadow_stack.append(_shadow)
        elif const_type_prefix == 'i64':
            state.symbolic_stack.append(BitVecVal(const_num, 64))
            state.shadow_stack.append(shadow(False,False))
        elif const_type_prefix == 'f32' or const_type_prefix == 'f64':
            # extract float number 100 from (;=100;)
            # TODO: need to be verified
            num_found = re.search(';=([0-9.-]+);', const_num)
            if num_found:
                float_num = num_found.group(1)
                if const_type_prefix == 'f32':
                    state.symbolic_stack.append(FPVal(float_num, Float32()))
                    state.shadow_stack.append(shadow(False,False))
                else:
                    state.symbolic_stack.append(FPVal(float_num, Float64()))
                    state.shadow_stack.append(shadow(False,False))
            elif const_num[:2] == '0x':
                # remove '0x' prefix
                const_num = const_num[2:]
                # extend with '0' till const_num length is 4 bytes
                current_const_num_length = len(const_num)

                need_zero = (8 - current_const_num_length) if const_type_prefix == 'f32' else (
                    16 - current_const_num_length)
                const_num = '0' * need_zero + const_num

                if const_type_prefix == 'f32':
                    float_num = unpack('!f', bytes.fromhex(const_num))[0]
                    state.symbolic_stack.append(FPVal(float_num, Float32()))
                    state.shadow_stack.append(shadow(False,False))
                else:
                    float_num = unpack('!d', bytes.fromhex(const_num))[0]
                    state.symbolic_stack.append(FPVal(float_num, Float64()))
                    state.shadow_stack.append(shadow(False,False))
            else:
                raise UnsupportInstructionError
        else:
            raise UnsupportInstructionError

        return [state]
