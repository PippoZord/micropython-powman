from machine import mem32
from micropython import const

# POWMAN BASE ADDRESS
POWMAN_BASE = const(0x40100000)

# PASSWORD FOR POWMAN
PASS = const(0x5AFE0000)

# GENERIC REGISTER OFFSET
VREG_LP_ENTRY = const(0x10)
STATE         = const(0x38)
TIMER         = const(0x88)
INTE          = const(0xE4)

# OFFSET FOR TIME REGISTER
SET_TIME_15TO0  = const(0x6C)
SET_TIME_31TO16 = const(0x68)
SET_TIME_47TO32 = const(0x64)
SET_TIME_63TO48 = const(0x60)

# OFFSET FOR ALARM REGISTER
ALARM_TIME_15TO0  = const(0x84)
ALARM_TIME_31TO16 = const(0x80)
ALARM_TIME_47TO32 = const(0x7C)
ALARM_TIME_63TO48 = const(0x78)

# OFFSET FOR READING TIME
READ_TIME_UPPER = const(0x70)
READ_TIME_LOWER = const(0x74)

# OFFSET FOR BOOT REGISTER
BOOT0 = const(0xD0)
BOOT1 = const(0xD4)
BOOT2 = const(0xD8)
BOOT3 = const(0xDC)

# OFFSET POWER CONFIGURATION
DBG_PWRCFG = const(0xA4)



def powmanInit(absTimeMs):
    print("Initializing time", absTimeMs)

    # Stop timer
    mem32[POWMAN_BASE + TIMER] = PASS | 0x00

    # Set time (64 bit split in 4 x 16 bit)
    mem32[POWMAN_BASE + SET_TIME_15TO0]  = PASS | (absTimeMs & 0xFFFF)
    mem32[POWMAN_BASE + SET_TIME_31TO16] = PASS | ((absTimeMs >> 16) & 0xFFFF)
    mem32[POWMAN_BASE + SET_TIME_47TO32] = PASS | ((absTimeMs >> 32) & 0xFFFF)
    mem32[POWMAN_BASE + SET_TIME_63TO48] = PASS | ((absTimeMs >> 48) & 0xFFFF)

    # Start timer
    # RUN + CLEAR + CLEAR ALARM
    mem32[POWMAN_BASE + TIMER] = PASS | 0x46

    # Ignore debugger
    mem32[POWMAN_BASE + DBG_PWRCFG] = PASS | 0x01


def _getCurrentTime():
    while True:
        hi1 = mem32[POWMAN_BASE + READ_TIME_UPPER]
        lo  = mem32[POWMAN_BASE + READ_TIME_LOWER]
        hi2 = mem32[POWMAN_BASE + READ_TIME_UPPER]

        if hi1 == hi2:
            return (hi1 << 32) | lo

def _forceReboot():
    mem32[POWMAN_BASE + BOOT0] = 0
    mem32[POWMAN_BASE + BOOT1] = 0
    mem32[POWMAN_BASE + BOOT2] = 0
    mem32[POWMAN_BASE + BOOT3] = 0

def _powmanPowerOff():
    # Set low power mode
    mem32[POWMAN_BASE + VREG_LP_ENTRY] = PASS | 0x0004

    _forceReboot()

    # Switch off system
    # Bit 3: SWCORE, Bit 2: XIP, Bit 1: SRAM0, Bit 0: SRAM1
    mem32[POWMAN_BASE + STATE] = PASS | 0x00F0

    # Wait for interrupt / alarm
    machine.idle()         # = WFI
    


def PowmanOffForMs(sleepingMs):
    alarmTime = sleepingMs + _getCurrentTime()
    print("Going to sleep for", sleepingMs, "ms")
    # Enable interrupt
    mem32[POWMAN_BASE + INTE] = PASS | 0x02

    # Stop timer
    mem32[POWMAN_BASE + TIMER] = PASS | 0x00

    # Write alarm time
    mem32[POWMAN_BASE + ALARM_TIME_15TO0]  = PASS | (alarmTime & 0xFFFF)
    mem32[POWMAN_BASE + ALARM_TIME_31TO16] = PASS | ((alarmTime >> 16) & 0xFFFF)
    mem32[POWMAN_BASE + ALARM_TIME_47TO32] = PASS | ((alarmTime >> 32) & 0xFFFF)
    mem32[POWMAN_BASE + ALARM_TIME_63TO48] = PASS | ((alarmTime >> 48) & 0xFFFF)

    # Start timer + reset alarm bit
    mem32[POWMAN_BASE + TIMER] = PASS | 0x72

    _powmanPowerOff()