#!/usr/bin/env python
# coding: latin-1
"""
This module is designed to communicate with the PicoBorg Reverse

Use by creating an instance of the class, call the Init function, then command as desired, e.g.
import PicoBorgRev
PBR = PicoBorgRev.PicoBorgRev()
PBR.Init()
# User code here, use PBR to control the board

Multiple boards can be used when configured with different I²C addresses by creating multiple instances, e.g.
import PicoBorgRev
PBR1 = PicoBorgRev.PicoBorgRev()
PBR2 = PicoBorgRev.PicoBorgRev()
PBR1.i2cAddress = 0x44
PBR2.i2cAddress = 0x45
PBR1.Init()
PBR2.Init()
# User code here, use PBR1 and PBR2 to control each board separately

For explanations of the functions available call the Help function, e.g.
import PicoBorgRev
PBR = PicoBorgRev.PicoBorgRev()
PBR.Help()
See the website at www.piborg.org/picoborgreverse for more details
"""

# Import the libraries we need
import io
import fcntl
import types
import time

# Constant values
I2C_SLAVE               = 0x0703
PWM_MAX                 = 255
I2C_MAX_LEN             = 4

I2C_ID_PICOBORG_REV     = 0x15

COMMAND_SET_LED         = 1     # Set the LED status
COMMAND_GET_LED         = 2     # Get the LED status
COMMAND_SET_A_FWD       = 3     # Set motor 2 PWM rate in a forwards direction
COMMAND_SET_A_REV       = 4     # Set motor 2 PWM rate in a reverse direction
COMMAND_GET_A           = 5     # Get motor 2 direction and PWM rate
COMMAND_SET_B_FWD       = 6     # Set motor 1 PWM rate in a forwards direction
COMMAND_SET_B_REV       = 7     # Set motor 1 PWM rate in a reverse direction
COMMAND_GET_B           = 8     # Get motor 1 direction and PWM rate
COMMAND_ALL_OFF         = 9     # Switch everything off
COMMAND_RESET_EPO       = 10    # Resets the EPO flag, use after EPO has been tripped and switch is now clear
COMMAND_GET_EPO         = 11    # Get the EPO latched flag
COMMAND_SET_EPO_IGNORE  = 12    # Set the EPO ignored flag, allows the system to run without an EPO
COMMAND_GET_EPO_IGNORE  = 13    # Get the EPO ignored flag
COMMAND_GET_DRIVE_FAULT = 14    # Get the drive fault flag, indicates faults such as short-circuits and under voltage
COMMAND_SET_ALL_FWD     = 15    # Set all motors PWM rate in a forwards direction
COMMAND_SET_ALL_REV     = 16    # Set all motors PWM rate in a reverse direction
COMMAND_SET_FAILSAFE    = 17    # Set the failsafe flag, turns the motors off if communication is interrupted
COMMAND_GET_FAILSAFE    = 18    # Get the failsafe flag
COMMAND_SET_ENC_MODE    = 19    # Set the board into encoder or speed mode
COMMAND_GET_ENC_MODE    = 20    # Get the boards current mode, encoder or speed
COMMAND_MOVE_A_FWD      = 21    # Move motor 2 forward by n encoder ticks
COMMAND_MOVE_A_REV      = 22    # Move motor 2 reverse by n encoder ticks
COMMAND_MOVE_B_FWD      = 23    # Move motor 1 forward by n encoder ticks
COMMAND_MOVE_B_REV      = 24    # Move motor 1 reverse by n encoder ticks
COMMAND_MOVE_ALL_FWD    = 25    # Move all motors forward by n encoder ticks
COMMAND_MOVE_ALL_REV    = 26    # Move all motors reverse by n encoder ticks
COMMAND_GET_ENC_MOVING  = 27    # Get the status of encoders moving
COMMAND_SET_ENC_SPEED   = 28    # Set the maximum PWM rate in encoder mode
COMMAND_GET_ENC_SPEED   = 29    # Get the maximum PWM rate in encoder mode
COMMAND_GET_ID          = 0x99  # Get the board identifier
COMMAND_SET_I2C_ADD     = 0xAA  # Set a new I2C address

COMMAND_VALUE_FWD       = 1     # I2C value representing forward
COMMAND_VALUE_REV       = 2     # I2C value representing reverse

COMMAND_VALUE_ON        = 1     # I2C value representing on
COMMAND_VALUE_OFF       = 0     # I2C value representing off


def ScanForPicoBorgReverse(busNumber = 1):
    """
ScanForPicoBorgReverse([busNumber])

Scans the I²C bus for a PicoBorg Reverse boards and returns a list of all usable addresses
The busNumber if supplied is which I²C bus to scan, 0 for Rev 1 boards, 1 for Rev 2 boards, if not supplied the default is 1
    """
    found = []
    print 'Scanning I²C bus #%d' % (busNumber)
    bus = PicoBorgRev()
    for address in range(0x03, 0x78, 1):
        try:
            bus.InitBusOnly(busNumber, address)
            i2cRecv = bus.RawRead(COMMAND_GET_ID, I2C_MAX_LEN)
            if len(i2cRecv) == I2C_MAX_LEN:
                if i2cRecv[1] == I2C_ID_PICOBORG_REV:
                    print 'Found PicoBorg Reverse at %02X' % (address)
                    found.append(address)
                else:
                    pass
            else:
                pass
        except KeyboardInterrupt:
            raise
        except:
            pass
    if len(found) == 0:
        print 'No PicoBorg Reverse boards found, is bus #%d correct (should be 0 for Rev 1, 1 for Rev 2)' % (busNumber)
    elif len(found) == 1:
        print '1 PicoBorg Reverse board found'
    else:
        print '%d PicoBorg Reverse boards found' % (len(found))
    return found


def SetNewAddress(newAddress, oldAddress = -1, busNumber = 1):
    """
SetNewAddress(newAddress, [oldAddress], [busNumber])

Scans the I²C bus for the first PicoBorg Reverse and sets it to a new I2C address
If oldAddress is supplied it will change the address of the board at that address rather than scanning the bus
The busNumber if supplied is which I²C bus to scan, 0 for Rev 1 boards, 1 for Rev 2 boards, if not supplied the default is 1
Warning, this new I²C address will still be used after resetting the power on the device
    """
    if newAddress < 0x03:
        print 'Error, I²C addresses below 3 (0x03) are reserved, use an address between 3 (0x03) and 119 (0x77)'
        return
    elif newAddress > 0x77:
        print 'Error, I²C addresses above 119 (0x77) are reserved, use an address between 3 (0x03) and 119 (0x77)'
        return
    if oldAddress < 0x0:
        found = ScanForPicoBorgReverse(busNumber)
        if len(found) < 1:
            print 'No PicoBorg Reverse boards found, cannot set a new I²C address!'
            return
        else:
            oldAddress = found[0]
    print 'Changing I²C address from %02X to %02X (bus #%d)' % (oldAddress, newAddress, busNumber)
    bus = PicoBorgRev()
    bus.InitBusOnly(busNumber, oldAddress)
    try:
        i2cRecv = bus.RawRead(COMMAND_GET_ID, I2C_MAX_LEN)
        if len(i2cRecv) == I2C_MAX_LEN:
            if i2cRecv[1] == I2C_ID_PICOBORG_REV:
                foundChip = True
                print 'Found PicoBorg Reverse at %02X' % (oldAddress)
            else:
                foundChip = False
                print 'Found a device at %02X, but it is not a PicoBorg Reverse (ID %02X instead of %02X)' % (oldAddress, i2cRecv[1], I2C_ID_PICOBORG_REV)
        else:
            foundChip = False
            print 'Missing PicoBorg Reverse at %02X' % (oldAddress)
    except KeyboardInterrupt:
        raise
    except:
        foundChip = False
        print 'Missing PicoBorg Reverse at %02X' % (oldAddress)
    if foundChip:
        bus.RawWrite(COMMAND_SET_I2C_ADD, [newAddress])
        time.sleep(0.1)
        print 'Address changed to %02X, attempting to talk with the new address' % (newAddress)
        try:
            bus.InitBusOnly(busNumber, newAddress)
            i2cRecv = bus.RawRead(COMMAND_GET_ID, I2C_MAX_LEN)
            if len(i2cRecv) == I2C_MAX_LEN:
                if i2cRecv[1] == I2C_ID_PICOBORG_REV:
                    foundChip = True
                    print 'Found PicoBorg Reverse at %02X' % (newAddress)
                else:
                    foundChip = False
                    print 'Found a device at %02X, but it is not a PicoBorg Reverse (ID %02X instead of %02X)' % (newAddress, i2cRecv[1], I2C_ID_PICOBORG_REV)
            else:
                foundChip = False
                print 'Missing PicoBorg Reverse at %02X' % (newAddress)
        except KeyboardInterrupt:
            raise
        except:
            foundChip = False
            print 'Missing PicoBorg Reverse at %02X' % (newAddress)
    if foundChip:
        print 'New I²C address of %02X set successfully' % (newAddress)
    else:
        print 'Failed to set new I²C address...'


# Class used to control PicoBorg Reverse
class PicoBorgRev:
    """
This module is designed to communicate with the PicoBorg Reverse

busNumber               I²C bus on which the PicoBorg Reverse is attached (Rev 1 is bus 0, Rev 2 is bus 1)
bus                     the smbus object used to talk to the I²C bus
i2cAddress              The I²C address of the PicoBorg Reverse chip to control
foundChip               True if the PicoBorg Reverse chip can be seen, False otherwise
printFunction           Function reference to call when printing text, if None "print" is used
    """

    # Shared values used by this class
    busNumber               = 1     # Check here for Rev 1 vs Rev 2 and select the correct bus
    i2cAddress              = 0x44  # I²C address, override for a different address
    foundChip               = False
    printFunction           = None
    i2cWrite                = None
    i2cRead                 = None


    def RawWrite(self, command, data):
        """
RawWrite(command, data)

Sends a raw command on the I2C bus to the PicoBorg Reverse
Command codes can be found at the top of PicoBorgRev.py, data is a list of 0 or more byte values

Under most circumstances you should use the appropriate function instead of RawWrite
        """
        rawOutput = chr(command)
        for singleByte in data:
            rawOutput += chr(singleByte)
        self.i2cWrite.write(rawOutput)


    def RawRead(self, command, length, retryCount = 3):
        """
RawRead(command, length, [retryCount])

Reads data back from the PicoBorg Reverse after sending a GET command
Command codes can be found at the top of PicoBorgRev.py, length is the number of bytes to read back

The function checks that the first byte read back matches the requested command
If it does not it will retry the request until retryCount is exhausted (default is 3 times)

Under most circumstances you should use the appropriate function instead of RawRead
        """
        while retryCount > 0:
            self.RawWrite(command, [])
            rawReply = self.i2cRead.read(length)
            reply = []
            for singleByte in rawReply:
                reply.append(ord(singleByte))
            if command == reply[0]:
                break
            else:
                retryCount -= 1
        if retryCount > 0:
            return reply
        else:
            raise IOError('I2C read for command %d failed' % (command))


    def InitBusOnly(self, busNumber, address):
        """
InitBusOnly(busNumber, address)

Prepare the I2C driver for talking to a PicoBorg Reverse on the specified bus and I2C address
This call does not check the board is present or working, under most circumstances use Init() instead
        """
        self.busNumber = busNumber
        self.i2cAddress = address
        self.i2cRead = io.open("/dev/i2c-" + str(self.busNumber), "rb", buffering = 0)
        fcntl.ioctl(self.i2cRead, I2C_SLAVE, self.i2cAddress)
        self.i2cWrite = io.open("/dev/i2c-" + str(self.busNumber), "wb", buffering = 0)
        fcntl.ioctl(self.i2cWrite, I2C_SLAVE, self.i2cAddress)


    def Print(self, message):
        """
Print(message)

Wrapper used by the PicoBorgRev instance to print messages, will call printFunction if set, print otherwise
        """
        if self.printFunction == None:
            print message
        else:
            self.printFunction(message)


    def NoPrint(self, message):
        """
NoPrint(message)

Does nothing, intended for disabling diagnostic printout by using:
PBR = PicoBorgRev.PicoBorgRev()
PBR.printFunction = PBR.NoPrint
        """
        pass


    def Init(self, tryOtherBus = False):
        """
Init([tryOtherBus])

Prepare the I2C driver for talking to the PicoBorg Reverse

If tryOtherBus is True, this function will attempt to use the other bus if the PicoBorg Reverse devices can not be found on the current busNumber
    This is only really useful for early Raspberry Pi models!
        """
        self.Print('Loading PicoBorg Reverse on bus %d, address %02X' % (self.busNumber, self.i2cAddress))

        # Open the bus
        self.i2cRead = io.open("/dev/i2c-" + str(self.busNumber), "rb", buffering = 0)
        fcntl.ioctl(self.i2cRead, I2C_SLAVE, self.i2cAddress)
        self.i2cWrite = io.open("/dev/i2c-" + str(self.busNumber), "wb", buffering = 0)
        fcntl.ioctl(self.i2cWrite, I2C_SLAVE, self.i2cAddress)

        # Check for PicoBorg Reverse
        try:
            i2cRecv = self.RawRead(COMMAND_GET_ID, I2C_MAX_LEN)
            if len(i2cRecv) == I2C_MAX_LEN:
                if i2cRecv[1] == I2C_ID_PICOBORG_REV:
                    self.foundChip = True
                    self.Print('Found PicoBorg Reverse at %02X' % (self.i2cAddress))
                else:
                    self.foundChip = False
                    self.Print('Found a device at %02X, but it is not a PicoBorg Reverse (ID %02X instead of %02X)' % (self.i2cAddress, i2cRecv[1], I2C_ID_PICOBORG_REV))
            else:
                self.foundChip = False
                self.Print('Missing PicoBorg Reverse at %02X' % (self.i2cAddress))
        except KeyboardInterrupt:
            raise
        except:
            self.foundChip = False
            self.Print('Missing PicoBorg Reverse at %02X' % (self.i2cAddress))

        # See if we are missing chips
        if not self.foundChip:
            self.Print('PicoBorg Reverse was not found')
            if tryOtherBus:
                if self.busNumber == 1:
                    self.busNumber = 0
                else:
                    self.busNumber = 1
                self.Print('Trying bus %d instead' % (self.busNumber))
                self.Init(False)
            else:
                self.Print('Are you sure your PicoBorg Reverse is properly attached, the correct address is used, and the I2C drivers are running?')
                self.bus = None
        else:
            self.Print('PicoBorg Reverse loaded on bus %d' % (self.busNumber))


    def SetMotor2(self, power):
        """
SetMotor2(power)

Sets the drive level for motor 2, from +1 to -1.
e.g.
SetMotor2(0)     -> motor 2 is stopped
SetMotor2(0.75)  -> motor 2 moving forward at 75% power
SetMotor2(-0.5)  -> motor 2 moving reverse at 50% power
SetMotor2(1)     -> motor 2 moving forward at 100% power
        """
        if power < 0:
            # Reverse
            command = COMMAND_SET_A_REV
            pwm = -int(PWM_MAX * power)
            if pwm > PWM_MAX:
                pwm = PWM_MAX
        else:
            # Forward / stopped
            command = COMMAND_SET_A_FWD
            pwm = int(PWM_MAX * power)
            if pwm > PWM_MAX:
                pwm = PWM_MAX

        try:
            self.RawWrite(command, [pwm])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending motor 2 drive level!')


    def GetMotor2(self):
        """
power = GetMotor2()

Gets the drive level for motor 2, from +1 to -1.
e.g.
0     -> motor 2 is stopped
0.75  -> motor 2 moving forward at 75% power
-0.5  -> motor 2 moving reverse at 50% power
1     -> motor 2 moving forward at 100% power
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_A, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading motor 2 drive level!')
            return

        power = float(i2cRecv[2]) / float(PWM_MAX)

        if i2cRecv[1] == COMMAND_VALUE_FWD:
            return power
        elif i2cRecv[1] == COMMAND_VALUE_REV:
            return -power
        else:
            return


    def SetMotor1(self, power):
        """
SetMotor1(power)

Sets the drive level for motor 1, from +1 to -1.
e.g.
SetMotor1(0)     -> motor 1 is stopped
SetMotor1(0.75)  -> motor 1 moving forward at 75% power
SetMotor1(-0.5)  -> motor 1 moving reverse at 50% power
SetMotor1(1)     -> motor 1 moving forward at 100% power
        """
        if power < 0:
            # Reverse
            command = COMMAND_SET_B_REV
            pwm = -int(PWM_MAX * power)
            if pwm > PWM_MAX:
                pwm = PWM_MAX
        else:
            # Forward / stopped
            command = COMMAND_SET_B_FWD
            pwm = int(PWM_MAX * power)
            if pwm > PWM_MAX:
                pwm = PWM_MAX

        try:
            self.RawWrite(command, [pwm])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending motor 1 drive level!')


    def GetMotor1(self):
        """
power = GetMotor1()

Gets the drive level for motor 1, from +1 to -1.
e.g.
0     -> motor 1 is stopped
0.75  -> motor 1 moving forward at 75% power
-0.5  -> motor 1 moving reverse at 50% power
1     -> motor 1 moving forward at 100% power
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_B, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading motor 1 drive level!')
            return

        power = float(i2cRecv[2]) / float(PWM_MAX)

        if i2cRecv[1] == COMMAND_VALUE_FWD:
            return power
        elif i2cRecv[1] == COMMAND_VALUE_REV:
            return -power
        else:
            return


    def SetMotors(self, power):
        """
SetMotors(power)

Sets the drive level for all motors, from +1 to -1.
e.g.
SetMotors(0)     -> all motors are stopped
SetMotors(0.75)  -> all motors are moving forward at 75% power
SetMotors(-0.5)  -> all motors are moving reverse at 50% power
SetMotors(1)     -> all motors are moving forward at 100% power
        """
        if power < 0:
            # Reverse
            command = COMMAND_SET_ALL_REV
            pwm = -int(PWM_MAX * power)
            if pwm > PWM_MAX:
                pwm = PWM_MAX
        else:
            # Forward / stopped
            command = COMMAND_SET_ALL_FWD
            pwm = int(PWM_MAX * power)
            if pwm > PWM_MAX:
                pwm = PWM_MAX

        try:
            self.RawWrite(command, [pwm])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending all motors drive level!')


    def MotorsOff(self):
        """
MotorsOff()

Sets all motors to stopped, useful when ending a program
        """
        try:
            self.RawWrite(COMMAND_ALL_OFF, [0])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending motors off command!')


    def SetLed(self, state):
        """
SetLed(state)

Sets the current state of the LED, False for off, True for on
        """
        if state:
            level = COMMAND_VALUE_ON
        else:
            level = COMMAND_VALUE_OFF

        try:
            self.RawWrite(COMMAND_SET_LED, [level])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending LED state!')


    def GetLed(self):
        """
state = GetLed()

Reads the current state of the LED, False for off, True for on
        """ 
        try:
            i2cRecv = self.RawRead(COMMAND_GET_LED, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading LED state!')
            return

        if i2cRecv[1] == COMMAND_VALUE_OFF:
            return False
        else:
            return True


    def ResetEpo(self):
        """
ResetEpo()

Resets the EPO latch state, use to allow movement again after the EPO has been tripped
        """
        try:
            self.RawWrite(COMMAND_RESET_EPO, [0])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed resetting EPO!')


    def GetEpo(self):
        """
state = GetEpo()

Reads the system EPO latch state.
If False the EPO has not been tripped, and movement is allowed.
If True the EPO has been tripped, movement is disabled if the EPO is not ignored (see SetEpoIgnore)
    Movement can be re-enabled by calling ResetEpo.
        """ 
        try:
            i2cRecv = self.RawRead(COMMAND_GET_EPO, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading EPO ignore state!')
            return

        if i2cRecv[1] == COMMAND_VALUE_OFF:
            return False
        else:
            return True


    def SetEpoIgnore(self, state):
        """
SetEpoIgnore(state)

Sets the system to ignore or use the EPO latch, set to False if you have an EPO switch, True if you do not
        """
        if state:
            level = COMMAND_VALUE_ON
        else:
            level = COMMAND_VALUE_OFF

        try:
            self.RawWrite(COMMAND_SET_EPO_IGNORE, [level])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending EPO ignore state!')


    def GetEpoIgnore(self):
        """
state = GetEpoIgnore()

Reads the system EPO ignore state, False for using the EPO latch, True for ignoring the EPO latch
        """ 
        try:
            i2cRecv = self.RawRead(COMMAND_GET_EPO_IGNORE, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading EPO ignore state!')
            return

        if i2cRecv[1] == COMMAND_VALUE_OFF:
            return False
        else:
            return True


    def SetCommsFailsafe(self, state):
        """
SetCommsFailsafe(state)

Sets the system to enable or disable the communications failsafe
The failsafe will turn the motors off unless it is commanded at least once every 1/4 of a second
Set to True to enable this failsafe, set to False to disable this failsafe
The failsafe is disabled at power on
        """
        if state:
            level = COMMAND_VALUE_ON
        else:
            level = COMMAND_VALUE_OFF

        try:
            self.RawWrite(COMMAND_SET_FAILSAFE, [level])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending communications failsafe state!')


    def GetCommsFailsafe(self):
        """
state = GetCommsFailsafe()

Read the current system state of the communications failsafe, True for enabled, False for disabled
The failsafe will turn the motors off unless it is commanded at least once every 1/4 of a second
        """ 
        try:
            i2cRecv = self.RawRead(COMMAND_GET_FAILSAFE, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading communications failsafe state!')
            return

        if i2cRecv[1] == COMMAND_VALUE_OFF:
            return False
        else:
            return True


    def GetDriveFault(self):
        """
state = GetDriveFault()

Reads the system drive fault state, False for no problems, True for a fault has been detected
Faults may indicate power problems, such as under-voltage (not enough power), and may be cleared by setting a lower drive power
If a fault is persistent, it repeatably occurs when trying to control the board, this may indicate a wiring problem such as:
    * The supply is not powerful enough for the motors
        The board has a bare minimum requirement of 6V to operate correctly
        A recommended minimum supply of 7.2V should be sufficient for smaller motors
    * The + and - connections for either motor are connected to each other
    * Either + or - is connected to ground (GND, also known as 0V or earth)
    * Either + or - is connected to the power supply (V+, directly to the battery or power pack)
    * One of the motors may be damaged
Faults will self-clear, they do not need to be reset, however some faults require both motors to be moving at less than 100% to clear
The easiest way to check is to put both motors at a low power setting which is high enough for them to rotate easily, such as 30%
Note that the fault state may be true at power up, this is normal and should clear when both motors have been driven
If there are no faults but you cannot make your motors move check GetEpo to see if the safety switch has been tripped
For more details check the website at www.piborg.org/picoborgrev and double check the wiring instructions
        """ 
        try:
            i2cRecv = self.RawRead(COMMAND_GET_DRIVE_FAULT, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading the drive fault state!')
            return

        if i2cRecv[1] == COMMAND_VALUE_OFF:
            return False
        else:
            return True


    def SetEncoderMoveMode(self, state):
        """
SetEncoderMoveMode(state)

Sets the system to enable or disable the encoder based move mode
In encoder move mode (enabled) the EncoderMoveMotor* commands are available to move fixed distances
In non-encoder move mode (disabled) the SetMotor* commands should be used to set drive levels
The encoder move mode requires that the encoder feedback is attached to an encoder signal, see the website at www.piborg.org/picoborgrev for wiring instructions
The encoder based move mode is disabled at power on
        """
        if state:
            level = COMMAND_VALUE_ON
        else:
            level = COMMAND_VALUE_OFF

        try:
            self.RawWrite(COMMAND_SET_ENC_MODE, [level])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending the encoder move mode!')


    def GetEncoderMoveMode(self):
        """
state = GetEncoderMoveMode()

Read the current system state of the encoder based move mode, True for enabled (encoder moves), False for disabled (power level moves)
        """ 
        try:
            i2cRecv = self.RawRead(COMMAND_GET_ENC_MODE, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading the encoder move mode!')
            return

        if i2cRecv[1] == COMMAND_VALUE_OFF:
            return False
        else:
            return True


    def EncoderMoveMotor2(self, counts):
        """
EncoderMoveMotor2(counts)

Moves motor 2 until it has seen a number of encoder counts, up to 32767
Use negative values to move in reverse
e.g.
EncoderMoveMotor2(100)   -> motor 2 moving forward for 100 counts
EncoderMoveMotor2(-50)   -> motor 2 moving reverse for 50 counts
EncoderMoveMotor2(5)     -> motor 2 moving forward for 5 counts
        """
        counts = int(counts)
        if counts < 0:
            # Reverse
            command = COMMAND_MOVE_A_REV
            counts = -counts
        else:
            # Forward
            command = COMMAND_MOVE_A_FWD

        if counts > 32767:
            self.Print('Cannot move %d counts in one go, moving 32767 counts instead' % (counts))
            counts = 32767
        countsLow = counts & 0xFF
        countsHigh = (counts >> 8) & 0xFF

        try:
            self.RawWrite(command, [countsHigh, countsLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending motor 2 move request!')


    def EncoderMoveMotor1(self, counts):
        """
EncoderMoveMotor1(counts)

Moves motor 1 until it has seen a number of encoder counts, up to 32767
Use negative values to move in reverse
e.g.
EncoderMoveMotor1(100)   -> motor 1 moving forward for 100 counts
EncoderMoveMotor1(-50)   -> motor 1 moving reverse for 50 counts
EncoderMoveMotor1(5)     -> motor 1 moving forward for 5 counts
        """
        counts = int(counts)
        if counts < 0:
            # Reverse
            command = COMMAND_MOVE_B_REV
            counts = -counts
        else:
            # Forward
            command = COMMAND_MOVE_B_FWD

        if counts > 32767:
            self.Print('Cannot move %d counts in one go, moving 32767 counts instead' % (counts))
            counts = 32767
        countsLow = counts & 0xFF
        countsHigh = (counts >> 8) & 0xFF

        try:
            self.RawWrite(command, [countsHigh, countsLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending motor 1 move request!')


    def EncoderMoveMotors(self, counts):
        """
EncoderMoveMotors(counts)

Moves all motors until they have each seen a number of encoder counts, up to 65535
Use negative values to move in reverse
e.g.
EncoderMoveMotors(100)   -> all motors moving forward for 100 counts
EncoderMoveMotors(-50)   -> all motors moving reverse for 50 counts
EncoderMoveMotors(5)     -> all motors moving forward for 5 counts
        """
        counts = int(counts)
        if counts < 0:
            # Reverse
            command = COMMAND_MOVE_ALL_REV
            counts = -counts
        else:
            # Forward
            command = COMMAND_MOVE_ALL_FWD
        countsLow = counts & 0xFF
        countsHigh = (counts >> 8) & 0xFF

        if counts > 32767:
            self.Print('Cannot move %d counts in one go, moving 32767 counts instead' % (counts))
            counts = 32767


        try:
            self.RawWrite(command, [countsHigh, countsLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending motors move request!')


    def IsEncoderMoving(self):
        """
state = IsEncoderMoving()

Reads the current state of the encoder motion, False for all motors have finished, True for any motor is still moving
        """ 
        try:
            i2cRecv = self.RawRead(COMMAND_GET_ENC_MOVING, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading motor encoder moving state!')
            return

        if i2cRecv[1] == COMMAND_VALUE_OFF:
            return False
        else:
            return True


    def WaitWhileEncoderMoving(self, timeout = -1):
        """
success = WaitWhileEncoderMoving([timeout])

Waits until all motors have finished performing encoder based moves
If the motors stop moving the function will return True
If a timeout is provided the function will return False after timeout seconds if the motors are still in motion
        """
        startTime = time.time()
        while self.IsEncoderMoving():
            if timeout >= 0:
                if (time.time() - startTime) >= timeout:
                    self.Print('Timed out after %d seconds waiting for encoder moves to complete' % (timeout))
                    return False
            time.sleep(0.1)
        return True


    def SetEncoderSpeed(self, power):
        """
SetEncoderSpeed(power)

Sets the drive limit for encoder based moves, from 0 to 1.
e.g.
SetEncoderSpeed(0.01)  -> motors may move at up to 1% power
SetEncoderSpeed(0.1)   -> motors may move at up to 10% power
SetEncoderSpeed(0.5)   -> motors may move at up to 50% power
SetEncoderSpeed(1)     -> motors may move at up to 100% power
        """
        pwm = int(PWM_MAX * power)
        if pwm > PWM_MAX:
            pwm = PWM_MAX

        try:
            self.RawWrite(COMMAND_SET_ENC_SPEED, [pwm])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending motor encoder move speed limit!')


    def GetEncoderSpeed(self):
        """
power = GetEncoderSpeed()

Gets the drive limit for encoder based moves, from 0 to 1.
e.g.
0.01  -> motors may move at up to 1% power
0.1   -> motors may move at up to 10% power
0.5   -> motors may move at up to 50% power
1     -> motors may move at up to 100% power
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_ENC_SPEED, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading motor encoder move speed limit!')
            return

        power = float(i2cRecv[1]) / float(PWM_MAX)
        return power


    def Help(self):
        """
Help()

Displays the names and descriptions of the various functions and settings provided
        """
        funcList = [PicoBorgRev.__dict__.get(a) for a in dir(PicoBorgRev) if isinstance(PicoBorgRev.__dict__.get(a), types.FunctionType)]
        funcListSorted = sorted(funcList, key = lambda x: x.func_code.co_firstlineno)

        print self.__doc__
        print
        for func in funcListSorted:
            print '=== %s === %s' % (func.func_name, func.func_doc)

