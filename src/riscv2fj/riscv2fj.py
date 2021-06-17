from elftools.elf.elffile import ELFFile


RV_LUI = 0b0110111
RV_AUIPC = 0b0010111
RV_JAL = 0b1101111
RV_JALR = 0b1100111

RV_B = 0b1100011
RV_BEQ = 0b000
RV_BNE = 0b001
RV_BLT = 0b100
RV_BGE = 0b101
RV_BLTU = 0b110
RV_BGEU = 0b111

RV_L = 0b0000011
RV_LB = 0b000
RV_LH = 0b001
RV_LW = 0b010
RV_LBU = 0b100
RV_LHU = 0b101

RV_S = 0b0100011
RV_SB = 0b000
RV_SH = 0b001
RV_SW = 0b010


def r_type(macro_name, op):
    return f'    .{macro_name} __rv_x{(op >> 7) & 0x1f} __rv_x{(op >> 15) & 0x1f} __rv_x{(op >> 20) & 0x1f}    \\\\ op 0x{op:08x}\n'


def i_type(macro_name, op):
    imm = op >> 20
    return f'    .{macro_name} __rv_x{(op >> 15) & 0x1f} 0x{imm:x}    \\\\ op 0x{op:08x}\n'


def s_type(macro_name, op):
    imm11_5 = op >> 25
    imm4_0 = (op >> 7) & 0x1f
    imm = (imm11_5 << 5) | (imm4_0 << 0)
    return f'    .{macro_name} __rv_x{(op >> 15) & 0x1f} __rv_x{(op >> 20) & 0x1f} 0x{imm:x}    \\\\ op 0x{op:08x}\n'


def b_type(macro_name, op):
    imm12 = op >> 31
    imm10_5 = (op >> 25) & 0x3f
    imm4_1 = (op >> 8) & 0xf
    imm11 = (op >> 7) & 0x1
    imm = (imm12 << 12) | (imm10_5 << 5) | (imm4_1 << 1) | (imm11 << 11)
    return f'    .{macro_name} __rv_x{(op >> 15) & 0x1f} __rv_x{(op >> 20) & 0x1f} 0x{imm:x}    \\\\ op 0x{op:08x}\n'


def u_type(macro_name, op):
    imm = op & 0xfffff000
    return f'    .{macro_name} __rv_x{(op >> 7) & 0x1f} 0x{imm:x}    \\\\ op 0x{op:08x}\n'


def j_type(macro_name, op):
    imm20 = op >> 31
    imm10_1 = (op >> 21) & 0x3ff
    imm11 = (op >> 20) & 0x1
    imm_19_12 = (op >> 12) & 0xff
    imm = (imm20 << 20) | (imm10_1 << 1) | (imm11 << 11) | (imm_19_12 << 12)
    return f'    .{macro_name} __rv_x{(op >> 7) & 0x1f} 0x{imm:x}    \\\\ op 0x{op:08x}\n'


def write_op(file, op):
    opcode = op & 0x7f
    funct3 = (op >> 12) & 7
    funct7 = op >> 25
    x0_changed = False

    if opcode == RV_LUI:
        file.write(u_type('RV_LUI', op))
    elif opcode == RV_AUIPC:
        file.write(u_type('RV_AUIPC', op))
    elif opcode == RV_JAL:
        file.write(j_type('RV_JAL', op))
    elif opcode == RV_JALR:
        if funct3 != 0:
            file.write(f'    // ERROR - bad funct3 at RV_JALR op - 0x{op:08x}\n')
        else:
            file.write(i_type('RV_JALR', op))

    elif opcode == RV_B:
        if funct3 == RV_BEQ:
            file.write(b_type('RV_BEQ', op))
        elif funct3 == RV_BNE:
            file.write(b_type('RV_BNE', op))
        elif funct3 == RV_BLT:
            file.write(b_type('RV_BLT', op))
        elif funct3 == RV_BGE:
            file.write(b_type('RV_BGE', op))
        elif funct3 == RV_BLTU:
            file.write(b_type('RV_BLTU', op))
        elif funct3 == RV_BGEU:
            file.write(b_type('RV_BGEU', op))

    else:
        file.write(f'    \\\\TODO not-implemented op 0x{op:08x}\n')
        # TODO real ops here.

    x0_changed = True
    if x0_changed:
        file.write('    .zero 32 x0\n')


def addr_label(addr):
    return f'__RV_ADDR_{addr:08X}'


def write_data(file, data, vaddr, reserved):
    file.write(f'.segment __RV_MEM + 0x{vaddr:08x}*8*dw\n')
    for byte in data:
        file.write(f'.var 8 {byte}\n')
    if reserved > 0:
        file.write(f'.reserve {reserved}*8*dw\n')
    file.write(f'\n\n')


def write_text(ops_file, jmp_file, data, vaddr):
    jmp_file.write(f'.segment __RV_JMP + 0x{vaddr:08x}/4*dw\n')
    for i in range(0, len(data), 4):
        op = int.from_bytes(data[i:i+4], 'little')
        addr = vaddr + i
        label = addr_label(addr)
        jmp_file.write(f';{label}\n')
        ops_file.write(f'{label}:\n')
        write_op(ops_file, op)
        ops_file.write(f'\n')

    jmp_file.write(f'\n\n')
    ops_file.write(f'\n\n')


def riscv2fj(elf_path, mem_path, jmp_path, ops_path):
    mem_fj = open(mem_path, 'w')
    jmp_fj = open(jmp_path, 'w')
    ops_fj = open(ops_path, 'w')

    with open(elf_path, 'rb') as f:
        elf = ELFFile(f)
        ops_fj.write(f"__RV_MEM = 1<<(w-1)                      \\\\ start of memory\n"
                     f"__RV_JMP = __RV_MEM - (__RV_MEM / 32)    \\\\ start of jump table\n\n"
                     f";{addr_label(elf['e_entry'])}                      \\\\ entry point\n"
                     f".riscv_init                              \\\\ init registers, structs, functions\n\n\n\n")

        for seg in elf.iter_segments():
            if seg['p_type'] != 'PT_LOAD':
                continue

            flags, vaddr, filesz, memsz = seg['p_flags'], seg['p_vaddr'], seg['p_filesz'], seg['p_memsz']
            data = seg.data()
            if flags & 1:   # if execute flag is on
                write_text(ops_fj, jmp_fj, data, vaddr)
            write_data(mem_fj, data, vaddr, memsz - filesz)

    mem_fj.close()
    jmp_fj.close()
    ops_fj.close()


if __name__ == '__main__':
    riscv2fj('sample_exe64.elf', 'mem.fj', 'jmp.fj', 'ops.fj')
