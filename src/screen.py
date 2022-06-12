import sys
import time
from enum import Enum

class Serial:
    def hasBit(self) -> bool:
        raise Exception("not implemented")

    def readBit(self) -> bool:
        raise Exception("not implemented")

    def canWriteBit(self) -> bool:
        raise Exception("not implemented")

    def writeBit(self, bit) -> bool:
        raise Exception("not implemented")


class Screen(Serial):
    RESOLUTION=(32, 24)

    class Ops(Enum):
        SETPIXEL = 0
        FILLRECT = 1

    class States(Enum):
        WAITING_OP = 1
        WAITING_PARAMS_SETPIXEL = 2
        WAITING_PARAMS_FILLRECT = 3

    def __init__(self):
        self.state = Screen.States.WAITING_OP

        self.readBuffer = 0
        self.readBufferLen = 0

        self.writeBuffer = 0
        self.writeBufferLen = 0

        self.frameBuffer = [[0 for i in range(Screen.RESOLUTION[0])] for j in range(Screen.RESOLUTION[1])]

    def hasBit(self) -> bool:
        return (self.readBufferLen > 0)

    def readBit(self) -> bool:
        while self.readBufferLen <= 0:
            time.sleep(0.1)

        self.readBufferLen -= 1
        return (self.readBuffer & (1 << (self.readBufferLen))) >> (self.readBufferLen)

    def canWriteBit(self) -> bool:
        return True

    def writeBit(self, bit) -> bool:
        if self.state == Screen.States.WAITING_OP:
            if bit == False:
                self.state = Screen.States.WAITING_PARAMS_SETPIXEL
            elif bit == True:
                self.state = Screen.States.WAITING_PARAMS_FILLRECT
        else:
            self.writeBuffer <<= 1
            self.writeBuffer |= bit
            self.writeBufferLen += 1

            if self.state == Screen.States.WAITING_PARAMS_SETPIXEL:
                pass    # TBD
            elif self.state == Screen.States.WAITING_PARAMS_FILLRECT:
                # [5 bits x][5 bits y][5 bits w][5 bits h][1 bit color]
                MSG_LEN = 21
                if self.writeBufferLen >= MSG_LEN:
                    color = self.readInt(1)
                    h = self.readInt(5)
                    w = self.readInt(5)
                    y = self.readInt(5)
                    x = self.readInt(5)

                    #print(f"read {x}, {y}, {w}, {h}, {color}")

                    for i in range(h):
                        self.cursor_location(y+i, 2*x)

                        for j in range(w):
                            self.frameBuffer[y+i][x+j] = color
                            print(('#' if color else '.'), end=" ")

                    #self.updateScreen()

                    self.state = Screen.States.WAITING_OP
                    self.cursor_location(Screen.RESOLUTION[1], Screen.RESOLUTION[0])

        return True

    def readInt(self, numBits) -> int:
        v = (self.writeBuffer & ((1 << numBits) - 1))
        self.writeBuffer >>= numBits
        self.writeBufferLen -= numBits

        return v

    def updateScreen(self) -> None:
        for i in range(Screen.RESOLUTION[1]):
            for j in range(Screen.RESOLUTION[0]):
                print(('#' if self.frameBuffer[i][j] else '.'), end=" ")

            print()

        print()

    def cursor_location(self, x, y):
        sys.stdout.write("\x1b7\x1b[%d;%dH" % (x+1, y+1))
        sys.stdout.flush()


if __name__ == "__main__":
    screen = Screen()

    # clear screen
    write = [
            1,  # OP
            0,  # X
            0,
            0,
            0,
            0,
            0,  # Y
            0,
            0,
            0,
            0,
            1,  # W
            1,
            1,
            1,
            1,
            1,  # H
            1,
            0,
            0,
            0,
            0,  # COLOR
    ]

    for v in write:
        screen.writeBit(v)

    # draw left paddle
    [screen.writeBit(v) for v in [1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 1]]
    # draw right paddle
    [screen.writeBit(v) for v in [1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 1]]
    # draw ball
    [screen.writeBit(v) for v in [1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1]]
